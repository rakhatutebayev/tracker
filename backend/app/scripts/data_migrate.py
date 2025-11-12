#!/usr/bin/env python
"""Export/Import tracker data between environments.

Usage examples:
  Export (from source env):
    python -m app.scripts.data_migrate export --out ./dump

  Import (on production):
    python -m app.scripts.data_migrate import --inp ./dump --mode truncate

Database connection is read from env DATABASE_URL. Fallbacks:
  postgresql+asyncpg://traccar:traccar@localhost:5432/traccar
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.database import Device, Position, Trip, Stop, Event, Geofence


CHUNK = 1000


async def iter_rows(session, model) -> AsyncIterator[Any]:
    offset = 0
    while True:
        result = await session.execute(select(model).offset(offset).limit(CHUNK))
        rows = result.scalars().all()
        if not rows:
            break
        for r in rows:
            yield r
        offset += len(rows)


def row_to_dict(obj) -> Dict[str, Any]:
    d = {}
    for c in obj.__table__.columns:
        v = getattr(obj, c.name)
        # Serialize datetimes to ISO
        if hasattr(v, 'isoformat'):
            v = v.isoformat()
        d[c.name] = v
    return d


async def export_all(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        'devices': out_dir / 'devices.jsonl',
        'positions': out_dir / 'positions.jsonl',
        'trips': out_dir / 'trips.jsonl',
        'stops': out_dir / 'stops.jsonl',
        'events': out_dir / 'events.jsonl',
        'geofences': out_dir / 'geofences.jsonl',
    }
    async with AsyncSessionLocal() as session:
        for name, model in (
            ('devices', Device),
            ('positions', Position),
            ('trips', Trip),
            ('stops', Stop),
            ('events', Event),
            ('geofences', Geofence),
        ):
            path = files[name]
            with path.open('w', encoding='utf-8') as f:
                async for row in iter_rows(session, model):
                    f.write(json.dumps(row_to_dict(row), ensure_ascii=False) + '\n')
            print(f"Exported {name} -> {path}")


async def truncate_all(session):
    # Order matters due to FKs
    for table in ('trips', 'stops', 'events', 'positions', 'devices', 'geofences'):
        await session.execute(text(f'TRUNCATE TABLE {table} RESTART IDENTITY CASCADE'))
    await session.commit()


async def import_file(session, path: Path, model, pk: str = 'id'):
    # Insert with explicit primary keys
    objs: List[Any] = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            # Parse ISO datetimes back to naive datetimes via fromisoformat if needed
            for c in model.__table__.columns:
                if c.type.__class__.__name__ == 'DateTime' and isinstance(data.get(c.name), str):
                    try:
                        # fromisoformat supports 'YYYY-mm-ddTHH:MM:SS[.ffffff]'
                        from datetime import datetime
                        data[c.name] = datetime.fromisoformat(data[c.name].replace('Z',''))
                    except Exception:
                        pass
            obj = model(**data)
            objs.append(obj)
            if len(objs) >= CHUNK:
                session.add_all(objs)
                await session.flush()
                objs.clear()
    if objs:
        session.add_all(objs)
        await session.flush()


async def reset_sequences(session):
    tables = ['devices', 'positions', 'trips', 'stops', 'events', 'geofences']
    for t in tables:
        # Build dynamic SQL safely (table names can't be parameterized in PG prepared statements)
        sql = f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 0))"
        await session.execute(text(sql))
    await session.commit()


async def import_all(inp_dir: Path, mode: str):
    async with AsyncSessionLocal() as session:
        if mode == 'truncate':
            await truncate_all(session)

        # Import order: devices -> positions -> trips -> stops -> events -> geofences
        mapping = [
            ('devices.jsonl', Device),
            ('positions.jsonl', Position),
            ('trips.jsonl', Trip),
            ('stops.jsonl', Stop),
            ('events.jsonl', Event),
            ('geofences.jsonl', Geofence),
        ]
        for fname, model in mapping:
            path = inp_dir / fname
            if not path.exists():
                print(f"Skip {fname}: not found")
                continue
            print(f"Importing {fname} ...")
            await import_file(session, path, model)
            await session.commit()

        await reset_sequences(session)
        print("Import completed.")


def main():
    parser = argparse.ArgumentParser(description='Tracker data migrate')
    sub = parser.add_subparsers(dest='cmd', required=True)

    pexp = sub.add_parser('export', help='Export all tables to JSONL files')
    pexp.add_argument('--out', required=True, help='Output directory')

    pimp = sub.add_parser('import', help='Import tables from JSONL files')
    pimp.add_argument('--inp', required=True, help='Input directory')
    pimp.add_argument('--mode', choices=['truncate', 'append'], default='truncate')

    args = parser.parse_args()
    if args.cmd == 'export':
        asyncio.run(export_all(Path(args.out)))
    elif args.cmd == 'import':
        asyncio.run(import_all(Path(args.inp), args.mode))


if __name__ == '__main__':
    main()

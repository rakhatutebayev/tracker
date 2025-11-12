#!/usr/bin/env python
"""Regenerate weekly positions for Hyundai HD35 (Х149ВН25).

Creates 7 days of data, 2 trips per day. Each trip targets total route distance
in the 20–50 km range around Almaty and nearby districts and assigns a realistic
duration based on a random average speed (≈28–45 km/h). This yields realistic
average speeds in reports (≈30–45 km/h) instead of underestimations caused by
overly long fixed durations.
"""

import asyncio
from datetime import datetime, timedelta
import math
import random
from sqlalchemy import select, delete, text

from app.core.database import AsyncSessionLocal
from app.models.database import Device, Position, Trip, Stop, Event


# Representative anchors around Almaty and nearby districts
ANCHORS = [
    (43.2382, 76.9453),  # Center
    (43.2550, 76.9200),  # Turksib (N)
    (43.2100, 77.0000),  # East suburbs
    (43.1950, 76.9700),  # Medeu (S)
    (43.2600, 76.9100),  # Far north
    (43.2320, 76.8800),  # West
    (43.2850, 76.9500),  # North-East
    (43.2250, 77.0500),  # Far East
]


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def jitter(lat, lon, max_km=1.0):
    # Rough degree offsets for small jitter near given point
    # 1 deg lat ~ 111 km; 1 deg lon ~ 88 km near Almaty
    dlat = (random.uniform(-max_km, max_km)) / 111.0
    dlon = (random.uniform(-max_km, max_km)) / 88.0
    return lat + dlat, lon + dlon


async def regenerate_hd35_week():
    target_name = "Hyundai HD35 (Х149ВН25)"
    async with AsyncSessionLocal() as session:
        # Find or create device
        res = await session.execute(select(Device).where(Device.name == target_name))
        device = res.scalar_one_or_none()
        if device is None:
            device = Device(
                unique_id="KZ-HD35-X149VN25",
                name=target_name,
                category="truck",
                model="Hyundai HD35",
                phone="+77001234567",
                contact="Водитель",
            )
            session.add(device)
            await session.flush()
        # Clean previous data: delete trips referencing positions first to avoid FK violations
        # Strong cleanup using raw SQL to avoid FK issues
        await session.execute(
            text(
                """
                DELETE FROM trips
                WHERE device_id = :id
                   OR start_position_id IN (SELECT id FROM positions WHERE device_id = :id)
                   OR end_position_id   IN (SELECT id FROM positions WHERE device_id = :id)
                """
            ),
            {"id": device.id},
        )
        await session.execute(delete(Stop).where(Stop.device_id == device.id))
        await session.execute(delete(Event).where(Event.device_id == device.id))
        await session.execute(delete(Position).where(Position.device_id == device.id))
        await session.commit()

    # Generate 7 days, 2 trips per day, each trip ~20-50 km with realistic duration derived from speed
        base_end = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        base_start = base_end - timedelta(days=6)

        def add_pos(lat, lon, fix_time, speed):
            pos = Position(
                device_id=device.id,
                latitude=lat,
                longitude=lon,
                altitude=650,
                speed=speed,
                course=random.randint(0, 360),
                accuracy=5,
                fix_time=fix_time,
            )
            session.add(pos)

        for d in range(7):
            day_date = (base_start + timedelta(days=d))

            # two trips: morning and afternoon
            for trip_index in range(2):
                start_anchor = random.choice(ANCHORS)
                end_anchor = random.choice(ANCHORS)
                # ensure start and end are not identical
                tries = 0
                while end_anchor == start_anchor and tries < 5:
                    end_anchor = random.choice(ANCHORS)
                    tries += 1

                start_lat, start_lon = jitter(*start_anchor, max_km=1.5)
                end_lat, end_lon = jitter(*end_anchor, max_km=1.5)
                # pick a mid anchor to bend the path and increase total length
                mid_anchor = random.choice(ANCHORS)
                mid_lat, mid_lon = jitter(*mid_anchor, max_km=2.0)

                d1 = haversine_km(start_lat, start_lon, mid_lat, mid_lon)
                d2 = haversine_km(mid_lat, mid_lon, end_lat, end_lon)
                total_dist = d1 + d2
                # Adjust mid and end to get total in [20,50]
                adjust_tries = 0
                while (total_dist < 20.0 or total_dist > 50.0) and adjust_tries < 120:
                    # move mid farther to add length predominantly
                    mid_lat, mid_lon = jitter(*random.choice(ANCHORS), max_km=8)
                    end_lat, end_lon = jitter(*end_anchor, max_km=6)
                    d1 = haversine_km(start_lat, start_lon, mid_lat, mid_lon)
                    d2 = haversine_km(mid_lat, mid_lon, end_lat, end_lon)
                    total_dist = d1 + d2
                    adjust_tries += 1

                # Final enforcement: if still out of range, scale mid point outward radially from start
                if total_dist < 20.0:
                    scale = 20.0 / max(total_dist, 0.1)
                    mid_lat = start_lat + (mid_lat - start_lat) * scale
                    mid_lon = start_lon + (mid_lon - start_lon) * scale
                    d1 = haversine_km(start_lat, start_lon, mid_lat, mid_lon)
                    d2 = haversine_km(mid_lat, mid_lon, end_lat, end_lon)
                    total_dist = d1 + d2
                elif total_dist > 50.0:
                    scale = 50.0 / total_dist
                    mid_lat = start_lat + (mid_lat - start_lat) * scale
                    mid_lon = start_lon + (mid_lon - start_lon) * scale
                    d1 = haversine_km(start_lat, start_lon, mid_lat, mid_lon)
                    d2 = haversine_km(mid_lat, mid_lon, end_lat, end_lon)
                    total_dist = d1 + d2

                # number of points for smooth polyline (split across two legs)
                points = random.randint(10, 16)
                leg1_points = max(5, points // 2)
                leg2_points = points - leg1_points + 1  # include mid point overlap
                # Derive duration from target average speed for realism
                target_avg_speed = random.uniform(28, 45)  # km/h realistic urban/suburban for truck
                duration_hours = total_dist / target_avg_speed
                duration_min = max(25, int(duration_hours * 60))  # enforce a sensible lower bound
                start_hour = 9 if trip_index == 0 else 15
                start_time = day_date.replace(hour=start_hour)
                # build leg 1: start -> mid
                for i in range(leg1_points):
                    t_ratio = i / (points - 1)
                    r = i / (leg1_points - 1) if leg1_points > 1 else 1
                    lat = start_lat + (mid_lat - start_lat) * r
                    lon = start_lon + (mid_lon - start_lon) * r
                    lat, lon = jitter(lat, lon, max_km=0.25)
                    fix_time = start_time + timedelta(minutes=int(t_ratio * duration_min))
                    # Generate instantaneous speed around target with variation
                    base_speed = target_avg_speed * random.uniform(0.85, 1.15)
                    speed = max(5, min(base_speed, 75))
                    add_pos(lat, lon, fix_time, speed)
                # build leg 2: mid -> end (skip duplicate mid point)
                for i in range(1, leg2_points):
                    t_ratio = (leg1_points - 1 + i) / (points - 1)
                    r = i / (leg2_points - 1) if leg2_points > 1 else 1
                    lat = mid_lat + (end_lat - mid_lat) * r
                    lon = mid_lon + (end_lon - mid_lon) * r
                    lat, lon = jitter(lat, lon, max_km=0.25)
                    fix_time = start_time + timedelta(minutes=int(t_ratio * duration_min))
                    base_speed = target_avg_speed * random.uniform(0.85, 1.15)
                    speed = max(5, min(base_speed, 75))
                    add_pos(lat, lon, fix_time, speed)

            # add a big gap between day trips to ensure they split
            # nothing to add here, the time windows already create gaps

        # commit after all days generated
        await session.commit()
    print("✅ Hyundai HD35 (Х149ВН25): regenerated weekly positions (2 trips/day, 7 days)")
    print("   ℹ️  Each trip enforced into 20–50 km range with realistic speed & duration (≈28–45 km/h)")


if __name__ == "__main__":
    asyncio.run(regenerate_hd35_week())

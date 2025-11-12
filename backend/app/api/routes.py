"""API routes for devices, positions, and reports."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_

from app.core.database import get_db
from app.models.database import Device, Position, Trip
from app.models.schemas import (
    DeviceOut, PositionOut, PositionLatest, TripReportParams, TripReport, TripReportItem, StopOut
)
from app.services.trip_service import TripService

router = APIRouter(prefix="/api", tags=["tracker"])


# ==================== Devices ====================

@router.get("/devices", response_model=List[DeviceOut])
async def list_devices(session: AsyncSession = Depends(get_db)):
    """List all devices."""
    result = await session.execute(select(Device).order_by(Device.name))
    devices = result.scalars().all()
    return devices


@router.get("/devices/{device_id}", response_model=DeviceOut)
async def get_device(device_id: int, session: AsyncSession = Depends(get_db)):
    """Get device by ID."""
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# ==================== Positions ====================

@router.get("/positions/latest", response_model=List[PositionLatest])
async def get_latest_positions(session: AsyncSession = Depends(get_db)):
    """Get latest position for each device (live map)."""
    # Get all devices
    stmt = select(Device).order_by(Device.id)
    result = await session.execute(stmt)
    devices = result.scalars().all()

    latest_positions = []
    for device in devices:
        pos_stmt = select(Position).where(
            Position.device_id == device.id
        ).order_by(desc(Position.fix_time)).limit(1)

        pos_result = await session.execute(pos_stmt)
        position = pos_result.scalar_one_or_none()

        if position:
            latest_positions.append(
                PositionLatest(
                    id=position.id,
                    device_id=position.device_id,
                    device_name=device.name,
                    latitude=position.latitude,
                    longitude=position.longitude,
                    speed=position.speed,
                    fix_time=position.fix_time,
                    server_time=position.server_time,
                )
            )

    return latest_positions


@router.get("/positions/history", response_model=List[PositionOut])
async def get_positions_history(
    device_id: int = Query(...),
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Get positions history for a device in a date range (chronological).

    Frontend may pass timezone-aware ISO strings. Convert to naive UTC to match DB.
    """

    def to_naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    from_dt = to_naive_utc(from_date)
    to_dt = to_naive_utc(to_date)

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")

    stmt = (
        select(Position)
        .where(
            and_(
                Position.device_id == device_id,
                Position.fix_time >= from_dt,
                Position.fix_time <= to_dt,
            )
        )
        .order_by(Position.fix_time.asc())
    )
    result = await session.execute(stmt)
    positions = result.scalars().all()
    return positions

@router.get("/stops", response_model=List[StopOut])
async def get_stops(
    device_id: int = Query(...),
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Get derived stops between trips for a device within a date range.

    We compute stops as intervals between consecutive trips where the vehicle is idle.
    Arrival is the end_time of previous trip; departure is the start_time of the next trip.
    """

    def to_naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    from_dt = to_naive_utc(from_date)
    to_dt = to_naive_utc(to_date)

    if from_dt > to_dt:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")

    # Ensure trips detected/updated for the window
    await TripService.detect_trips(session, device_id, from_dt, to_dt)

    stops = await TripService.compute_stops_from_trips(session, device_id, from_dt, to_dt)

    # Add device name
    device = (await session.execute(select(Device).where(Device.id == device_id))).scalar_one_or_none()
    device_name = device.name if device else None

    return [
        StopOut(
            id=None,
            device_id=device_id,
            device_name=device_name,
            latitude=s["latitude"],
            longitude=s["longitude"],
            arrival_time=s["arrival_time"],
            departure_time=s.get("departure_time"),
            duration=s["duration"],
            address=None,
        )
        for s in stops
    ]


@router.get("/positions/{device_id}", response_model=List[PositionOut])
async def get_device_positions(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    """Get last N positions for a device."""
    result = await session.execute(
        select(Position)
        .where(Position.device_id == device_id)
        .order_by(desc(Position.fix_time))
        .limit(limit)
    )
    positions = result.scalars().all()
    return positions[::-1]  # Reverse to chronological order


# ==================== Reports ====================

@router.post("/reports/trips", response_model=TripReport)
async def get_trip_report(
    params: TripReportParams,
    session: AsyncSession = Depends(get_db),
):
    """Get trip report for device(s) in date range.

    Frontend may submit timezone-aware ISO datetimes. Our DB stores naive UTC timestamps.
    Normalize incoming datetimes to naive UTC before querying to avoid asyncpg codec errors
    like "can't subtract offset-naive and offset-aware datetimes".
    """

    def to_naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        # Convert to UTC then drop tzinfo
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    from_date = to_naive_utc(params.from_date)
    to_date = to_naive_utc(params.to_date)

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")

    # Detect trips if a single device is specified
    if params.device_id:
        await TripService.detect_trips(session, params.device_id, from_date, to_date)

    # Get trips
    trips = await TripService.get_trips(
        session,
        device_id=params.device_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Format report
    trip_items = []
    total_distance = 0
    total_duration = 0

    for trip in trips:
        # Get device name
        device_stmt = select(Device).where(Device.id == trip.device_id)
        device_result = await session.execute(device_stmt)
        device = device_result.scalar_one()

        trip_items.append(
            TripReportItem(
                trip_id=trip.id,
                device_name=device.name,
                start_point=trip.start_address or f"{trip.start_lat:.4f}, {trip.start_lon:.4f}",
                start_lat=trip.start_lat,
                start_lon=trip.start_lon,
                start_time=trip.start_time,
                end_point=trip.end_address or f"{trip.end_lat:.4f}, {trip.end_lon:.4f}",
                end_lat=trip.end_lat,
                end_lon=trip.end_lon,
                end_time=trip.end_time,
                duration_hours=trip.duration / 3600 if trip.duration else 0,
                distance_km=trip.distance or 0,
                avg_speed=trip.avg_speed,
                max_speed=trip.max_speed,
            )
        )

        total_distance += trip.distance or 0
        total_duration += trip.duration or 0

    period = f"{from_date.date()} to {to_date.date()}"
    device_name = None
    if params.device_id:
        device_stmt = select(Device).where(Device.id == params.device_id)
        device_result = await session.execute(device_stmt)
        device = device_result.scalar_one_or_none()
        device_name = device.name if device else None

    return TripReport(
        period=period,
        device_id=params.device_id,
        device_name=device_name,
        total_distance=round(total_distance, 2),
        total_duration=total_duration,
        trip_count=len(trip_items),
        trips=trip_items,
    )


@router.get("/reports/summary")
async def get_summary_report(
    device_id: int,
    from_date: datetime = Query(...),
    to_date: datetime = Query(...),
    session: AsyncSession = Depends(get_db),
):
    """Get summary report (distance, duration, etc.).

    Normalize incoming timezone-aware datetimes to naive UTC to match DB storage
    and avoid offset-aware/naive arithmetic errors.
    """

    def to_naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    from_date = to_naive_utc(from_date)
    to_date = to_naive_utc(to_date)

    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be <= to_date")

    trips = await TripService.get_trips(
        session,
        device_id=device_id,
        from_date=from_date,
        to_date=to_date,
    )

    total_distance = sum(trip.distance or 0 for trip in trips)
    total_duration = sum(trip.duration or 0 for trip in trips)
    max_speed = max((trip.max_speed for trip in trips if trip.max_speed), default=0)
    avg_speed = (total_distance / (total_duration / 3600)) if total_duration > 0 else 0

    return {
        "period": f"{from_date.date()} to {to_date.date()}",
        "device_id": device_id,
        "trip_count": len(trips),
        "total_distance_km": round(total_distance, 2),
        "total_duration_sec": total_duration,
        "total_duration_hours": round(total_duration / 3600, 2),
        "avg_speed": round(avg_speed, 2),
        "max_speed": round(max_speed, 2),
    }

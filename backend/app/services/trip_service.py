"""Trip detection and management service."""

import math
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Device, Position, Trip, Stop
from app.core.config import settings


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in km."""
    R = 6371  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class TripService:
    """Service for trip and stop detection."""

    @staticmethod
    async def detect_trips(session: AsyncSession, device_id: int, from_date: datetime, to_date: datetime):
        """
        Detect trips from positions.
        
        Algorithm:
        1. Get all positions for device in date range (ordered by time).
        2. Group into trips: when speed > TRIP_MIN_SPEED_KMH, it's moving.
        3. When speed < threshold for TRIP_IDLE_THRESHOLD_SEC, it's a stop.
        4. Create Trip and Stop records.
        """
        # Remove existing trips in this window to avoid duplication on re-detect
        await session.execute(
            delete(Trip).where(
                and_(
                    Trip.device_id == device_id,
                    Trip.start_time >= from_date,
                    Trip.end_time <= to_date,
                )
            )
        )

        stmt = select(Position).where(
            and_(
                Position.device_id == device_id,
                Position.fix_time >= from_date,
                Position.fix_time <= to_date,
            )
        ).order_by(Position.fix_time)

        result = await session.execute(stmt)
        positions = result.scalars().all()

        if len(positions) < 2:
            return

        trips = []
        stops = []
        current_trip = None
        last_stop_end = None

        for i, pos in enumerate(positions):
            is_moving = (pos.speed or 0) >= settings.TRIP_MIN_SPEED_KMH
            # Determine time gap from previous position
            if i > 0:
                prev = positions[i - 1]
                gap_sec = (pos.fix_time - prev.fix_time).total_seconds()
            else:
                gap_sec = 0

            # If gap exceeds max allowed, force-close current trip (if any) before processing pos
            if current_trip is not None and gap_sec > settings.TRIP_MAX_GAP_SEC:
                last_pos_in_trip = current_trip["positions"][-1]
                forced_trip = {
                    **current_trip,
                    "end_position_id": last_pos_in_trip.id,
                    "end_lat": last_pos_in_trip.latitude,
                    "end_lon": last_pos_in_trip.longitude,
                    "end_time": last_pos_in_trip.fix_time,
                    "end_address": None,
                }
                forced_trip["distance"] = TripService._calc_distance(forced_trip["positions"])\
                
                forced_trip["duration"] = int((forced_trip["end_time"] - forced_trip["start_time"]).total_seconds())
                if forced_trip["duration"] >= settings.TRIP_MIN_DURATION_SEC:
                    forced_trip["avg_speed"] = (forced_trip["distance"] / (forced_trip["duration"] / 3600)) if forced_trip["duration"] > 0 else 0
                    forced_trip["position_count"] = len(forced_trip["positions"])
                    trips.append(forced_trip)
                current_trip = None

            if is_moving:
                if current_trip is None:
                    # Start new trip
                    current_trip = {
                        "device_id": device_id,
                        "start_position_id": pos.id,
                        "start_lat": pos.latitude,
                        "start_lon": pos.longitude,
                        "start_time": pos.fix_time,
                        "start_address": None,
                        "positions": [pos],
                        "max_speed": pos.speed or 0,
                    }
                else:
                    # Continue trip
                    current_trip["positions"].append(pos)
                    if pos.speed:
                        current_trip["max_speed"] = max(current_trip["max_speed"], pos.speed)

            else:  # Not moving
                if current_trip is not None:
                    # End trip
                    prev_pos = current_trip["positions"][-1]
                    trip = {
                        **current_trip,
                        "end_position_id": prev_pos.id,
                        "end_lat": prev_pos.latitude,
                        "end_lon": prev_pos.longitude,
                        "end_time": prev_pos.fix_time,
                        "end_address": None,
                    }

                    # Calculate trip stats
                    trip["distance"] = TripService._calc_distance(trip["positions"])
                    trip["duration"] = int((trip["end_time"] - trip["start_time"]).total_seconds())

                    if trip["duration"] >= settings.TRIP_MIN_DURATION_SEC:
                        trip["avg_speed"] = (trip["distance"] / (trip["duration"] / 3600)) if trip["duration"] > 0 else 0
                        trip["position_count"] = len(trip["positions"])
                        trips.append(trip)

                    current_trip = None

                    # Start stop
                    if last_stop_end is None or (pos.fix_time - last_stop_end).total_seconds() > settings.TRIP_IDLE_THRESHOLD_SEC:
                        last_stop_time = pos.fix_time
                    else:
                        last_stop_time = last_stop_end

        # Handle last trip if still moving at end
        if current_trip is not None:
            last_pos = current_trip["positions"][-1]
            trip = {
                **current_trip,
                "end_position_id": last_pos.id,
                "end_lat": last_pos.latitude,
                "end_lon": last_pos.longitude,
                "end_time": last_pos.fix_time,
                "end_address": None,
            }
            trip["distance"] = TripService._calc_distance(trip["positions"])
            trip["duration"] = int((trip["end_time"] - trip["start_time"]).total_seconds())
            if trip["duration"] >= settings.TRIP_MIN_DURATION_SEC:
                trip["avg_speed"] = (trip["distance"] / (trip["duration"] / 3600)) if trip["duration"] > 0 else 0
                trip["position_count"] = len(trip["positions"])
                trips.append(trip)

        # Save trips and stops
        for trip_data in trips:
            trip = Trip(
                device_id=trip_data["device_id"],
                start_position_id=trip_data["start_position_id"],
                start_lat=trip_data["start_lat"],
                start_lon=trip_data["start_lon"],
                start_time=trip_data["start_time"],
                start_address=trip_data.get("start_address"),
                end_position_id=trip_data["end_position_id"],
                end_lat=trip_data["end_lat"],
                end_lon=trip_data["end_lon"],
                end_time=trip_data["end_time"],
                end_address=trip_data.get("end_address"),
                distance=trip_data["distance"],
                duration=trip_data["duration"],
                max_speed=trip_data.get("max_speed"),
                avg_speed=trip_data.get("avg_speed"),
                position_count=trip_data.get("position_count", 0),
            )
            session.add(trip)

        await session.commit()

    @staticmethod
    def _calc_distance(positions: List[Position]) -> float:
        """Calculate total distance traveled from position list."""
        if len(positions) < 2:
            return 0

        distance = 0
        for i in range(len(positions) - 1):
            p1 = positions[i]
            p2 = positions[i + 1]
            distance += haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

        return round(distance, 2)

    @staticmethod
    async def get_trips(
        session: AsyncSession,
        device_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Trip]:
        """Get trips with optional filters."""
        query = select(Trip)

        if device_id:
            query = query.where(Trip.device_id == device_id)

        if from_date:
            query = query.where(Trip.start_time >= from_date)

        if to_date:
            query = query.where(Trip.end_time <= to_date)

        query = query.order_by(desc(Trip.start_time)).limit(limit)

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def compute_stops_from_trips(
        session: AsyncSession,
        device_id: int,
        from_date: datetime,
        to_date: datetime,
    ) -> List[dict]:
        """Derive stop intervals between sequential trips for a device within a period.

        A stop is defined as the idle interval between the end of one trip and the start of the next trip.
        We return lightweight dicts suitable for API serialization without persisting to DB to avoid
        duplication and idempotency concerns.
        """
        trips = await TripService.get_trips(
            session,
            device_id=device_id,
            from_date=from_date,
            to_date=to_date,
            limit=10000,
        )

        # Trips are returned in desc(start_time); sort ascending for interval computation
        trips_sorted = sorted(trips, key=lambda t: t.start_time)

        stops: List[dict] = []
        for i in range(len(trips_sorted) - 1):
            t1 = trips_sorted[i]
            t2 = trips_sorted[i + 1]

            # Define stop as [t1.end_time -> t2.start_time] at location t1.end_{lat,lon}
            if t2.start_time > t1.end_time:
                duration = int((t2.start_time - t1.end_time).total_seconds())
                if duration >= settings.TRIP_IDLE_THRESHOLD_SEC:
                    stops.append(
                        {
                            "device_id": device_id,
                            "latitude": t1.end_lat,
                            "longitude": t1.end_lon,
                            "arrival_time": t1.end_time,
                            "departure_time": t2.start_time,
                            "duration": duration,
                        }
                    )

        return stops

    @staticmethod
    async def get_trip_with_device(session: AsyncSession, trip_id: int) -> Optional[Tuple[Trip, Device]]:
        """Get trip with device info."""
        stmt = select(Trip).where(Trip.id == trip_id)
        result = await session.execute(stmt)
        trip = result.scalar_one_or_none()

        if trip:
            device_stmt = select(Device).where(Device.id == trip.device_id)
            device_result = await session.execute(device_stmt)
            device = device_result.scalar_one()
            return trip, device

        return None

"""Pydantic schemas for API requests/responses."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# Device schemas
class DeviceCreate(BaseModel):
    unique_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    category: str = "car"
    phone: Optional[str] = None
    model: Optional[str] = None


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    phone: Optional[str] = None
    model: Optional[str] = None
    disabled: Optional[bool] = None


class DeviceOut(BaseModel):
    id: int
    unique_id: str
    name: str
    category: str
    phone: Optional[str]
    model: Optional[str]
    disabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Position schemas
class PositionCreate(BaseModel):
    device_id: int
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    speed: Optional[float] = None
    course: Optional[float] = None
    accuracy: Optional[float] = None
    fix_time: datetime
    attributes: Optional[str] = None


class PositionOut(BaseModel):
    id: int
    device_id: int
    latitude: float
    longitude: float
    altitude: Optional[float]
    speed: Optional[float]
    course: Optional[float]
    accuracy: Optional[float]
    fix_time: datetime
    server_time: datetime

    class Config:
        from_attributes = True


class PositionLatest(BaseModel):
    """Latest position with device info."""
    id: int
    device_id: int
    device_name: str
    latitude: float
    longitude: float
    speed: Optional[float]
    fix_time: datetime
    server_time: datetime

    class Config:
        from_attributes = True


# Trip schemas
class TripCreate(BaseModel):
    device_id: int
    start_lat: float
    start_lon: float
    start_time: datetime
    start_address: Optional[str] = None
    end_lat: float
    end_lon: float
    end_time: datetime
    end_address: Optional[str] = None
    distance: float = 0
    duration: int = 0


class TripOut(BaseModel):
    id: int
    device_id: int
    device_name: Optional[str] = None
    start_lat: float
    start_lon: float
    start_time: datetime
    start_address: Optional[str]
    end_lat: float
    end_lon: float
    end_time: datetime
    end_address: Optional[str]
    distance: float  # км
    duration: int  # секунды
    max_speed: Optional[float]
    avg_speed: Optional[float]
    position_count: int

    class Config:
        from_attributes = True


# Stop schemas
class StopOut(BaseModel):
    id: Optional[int] = None  # virtual stops may not have persistent IDs
    device_id: int
    device_name: Optional[str] = None
    latitude: float
    longitude: float
    arrival_time: datetime
    departure_time: Optional[datetime] = None
    duration: int  # секунды (между arrival и departure)
    address: Optional[str] = None

    class Config:
        from_attributes = True


# Report schemas
class TripReportParams(BaseModel):
    """Параметры отчета по поездкам."""
    device_id: Optional[int] = None
    from_date: datetime
    to_date: datetime
    group_by: Optional[str] = None  # "day", "week", "month"


class TripReportItem(BaseModel):
    """Строка отчета по поездке."""
    trip_id: int
    device_name: str
    start_point: str  # адрес или "Unknown"
    start_lat: float
    start_lon: float
    start_time: datetime
    end_point: str
    end_lat: float
    end_lon: float
    end_time: datetime
    duration_hours: float
    distance_km: float
    avg_speed: Optional[float]
    max_speed: Optional[float]


class TripReport(BaseModel):
    """Полный отчет по поездкам."""
    period: str  # "2025-11-01 to 2025-11-30"
    device_id: Optional[int]
    device_name: Optional[str]
    total_distance: float
    total_duration: int  # секунды
    trip_count: int
    trips: List[TripReportItem]


# WebSocket schemas
class LivePositionUpdate(BaseModel):
    """Live position update (WebSocket)."""
    device_id: int
    device_name: str
    latitude: float
    longitude: float
    speed: Optional[float]
    course: Optional[float]
    fix_time: datetime


class WebSocketMessage(BaseModel):
    """Generic WS message."""
    type: str  # "position_update", "trip_start", "trip_end", etc.
    data: dict

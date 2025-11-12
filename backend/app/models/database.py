"""Database models for GPS tracker."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Device(Base):
    """GPS tracker device."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    unique_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(64), default="car")
    phone = Column(String(20))
    model = Column(String(255))
    contact = Column(String(255))
    disabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    positions = relationship("Position", back_populates="device", cascade="all, delete-orphan")
    trips = relationship("Trip", back_populates="device", cascade="all, delete-orphan")
    stops = relationship("Stop", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(id={self.id}, name={self.name}, unique_id={self.unique_id})>"


class Position(Base):
    """GPS position record."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float)
    speed = Column(Float)  # km/h
    course = Column(Float)  # bearing/heading
    accuracy = Column(Float)
    fix_time = Column(DateTime, nullable=False, index=True)  # GPS time
    server_time = Column(DateTime, default=datetime.utcnow, index=True)
    attributes = Column(Text)  # JSON: ignition, power, fuel, etc.

    device = relationship("Device", back_populates="positions")

    __table_args__ = (
        Index("ix_positions_device_time", "device_id", "fix_time"),
    )

    def __repr__(self):
        return f"<Position(id={self.id}, device={self.device_id}, lat={self.latitude}, lon={self.longitude})>"


class Trip(Base):
    """Vehicle trip (route from point A to B)."""
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)

    # Start point
    start_position_id = Column(Integer, ForeignKey("positions.id"))
    start_lat = Column(Float, nullable=False)
    start_lon = Column(Float, nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    start_address = Column(String(512))

    # End point
    end_position_id = Column(Integer, ForeignKey("positions.id"))
    end_lat = Column(Float, nullable=False)
    end_lon = Column(Float, nullable=False)
    end_time = Column(DateTime, nullable=False, index=True)
    end_address = Column(String(512))

    # Trip stats
    distance = Column(Float, default=0)  # km
    duration = Column(Integer)  # seconds
    max_speed = Column(Float)
    avg_speed = Column(Float)
    position_count = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    device = relationship("Device", back_populates="trips")

    __table_args__ = (
        Index("ix_trips_device_time", "device_id", "start_time"),
    )

    def __repr__(self):
        return f"<Trip(id={self.id}, device={self.device_id}, start={self.start_time}, end={self.end_time})>"


class Stop(Base):
    """Vehicle stop (parked, idle)."""
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    address = Column(String(512))

    # Stop stats
    duration = Column(Integer)  # seconds
    position_count = Column(Integer, default=0)

    device = relationship("Device", back_populates="stops")

    __table_args__ = (
        Index("ix_stops_device_time", "device_id", "start_time"),
    )

    def __repr__(self):
        return f"<Stop(id={self.id}, device={self.device_id}, start={self.start_time})>"


class Event(Base):
    """Event (ignition on/off, overspeed, geofence, etc.)."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    type = Column(String(64), nullable=False)  # ignition_on, ignition_off, overspeed, geofence_enter, etc.
    event_time = Column(DateTime, nullable=False, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    data = Column(Text)  # JSON payload

    __table_args__ = (
        Index("ix_events_device_time", "device_id", "event_time"),
    )

    def __repr__(self):
        return f"<Event(id={self.id}, device={self.device_id}, type={self.type}, time={self.event_time})>"


class Geofence(Base):
    """Geographic fence for notifications."""
    __tablename__ = "geofences"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius = Column(Float, default=500)  # meters
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Geofence(id={self.id}, name={self.name})>"

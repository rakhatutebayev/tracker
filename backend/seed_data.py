#!/usr/bin/env python
"""Seed test data for tracker."""

import asyncio
from datetime import datetime, timedelta
import random
from app.core.database import AsyncSessionLocal
from app.models.database import Device, Position


async def seed_data():
    """Add test devices and positions."""
    async with AsyncSessionLocal() as session:
        # Create test devices
        devices = [
            Device(unique_id="T001", name="Truck-001", category="truck", model="Volvo FH16"),
            Device(unique_id="T002", name="Truck-002", category="truck", model="Scania R440"),
            Device(unique_id="T003", name="Truck-003", category="truck", model="Mercedes Actros"),
        ]
        
        session.add_all(devices)
        await session.flush()  # Flush to get device IDs
        
        # Add positions for each device
        now = datetime.utcnow()
        for device in devices:
            for i in range(1, 6):
                pos = Position(
                    device_id=device.id,
                    latitude=51.1694 + random.uniform(-0.1, 0.1),  # Almaty coords
                    longitude=71.4491 + random.uniform(-0.1, 0.1),
                    altitude=0,
                    speed=random.randint(0, 120),
                    course=random.randint(0, 360),
                    accuracy=5,
                    fix_time=now - timedelta(hours=i*2),
                )
                session.add(pos)
        
        await session.commit()
        print("✅ Test data seeded successfully!")
        print(f"   - {len(devices)} devices created")
        print(f"   - 15 positions created")


if __name__ == "__main__":
    asyncio.run(seed_data())

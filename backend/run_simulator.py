#!/usr/bin/env python
"""Real-time position simulator for tracking vehicles.

Simulates continuous vehicle movement through Almaty, updating positions
every 10-30 seconds to demonstrate live tracking capabilities.
"""

import asyncio
import random
from datetime import datetime
from app.core.database import AsyncSessionLocal
from app.models.database import Position, Device


# Almaty locations grid for realistic routing
ALMATY_LOCATIONS = {
    "Саркан": {"lat": 43.2382, "lon": 76.9453},
    "Центр": {"lat": 43.2350, "lon": 76.9400},
    "Абай": {"lat": 43.2420, "lon": 76.9380},
    "Керей-Жанибек": {"lat": 43.2280, "lon": 76.9500},
    "Панфилова": {"lat": 43.2400, "lon": 76.9350},
    "Ауезова": {"lat": 43.2320, "lon": 76.9420},
    "Бауыржана Момушулы": {"lat": 43.2270, "lon": 76.9550},
    "Ул. Жамбыла": {"lat": 43.2450, "lon": 76.9300},
    "Микрорайон Медеу": {"lat": 43.1950, "lon": 76.9700},
    "Чунарь": {"lat": 43.2100, "lon": 77.0000},
    "Турксиб": {"lat": 43.2550, "lon": 76.9200},
    "Актюбинская": {"lat": 43.2600, "lon": 76.9100},
}


async def simulate_vehicle_movement():
    """Continuously update vehicle positions to simulate real-time movement."""
    
    async with AsyncSessionLocal() as session:
        # Get all devices
        from sqlalchemy import select
        result = await session.execute(select(Device))
        devices = result.scalars().all()
        
        if not devices:
            print("❌ No devices found. Run seed_almaty.py first.")
            return
        
        # Initialize route for each device
        vehicle_routes = {}
        for device in devices:
            locations = list(ALMATY_LOCATIONS.keys())
            random.shuffle(locations)
            vehicle_routes[device.id] = {
                "locations": locations,
                "index": 0,
                "current_lat": None,
                "current_lon": None,
            }
        
        print(f"\n🚀 Starting real-time position simulator")
        print(f"📊 Tracking {len(devices)} vehicles")
        print(f"🗺️  Coverage area: Almaty city + suburbs\n")
        
        iteration = 0
        try:
            while True:
                iteration += 1
                timestamp = datetime.utcnow()
                
                for device in devices:
                    route = vehicle_routes[device.id]
                    
                    # Get current and next location
                    current_loc_name = route["locations"][route["index"]]
                    next_index = (route["index"] + 1) % len(route["locations"])
                    next_loc_name = route["locations"][next_index]
                    
                    current_loc = ALMATY_LOCATIONS[current_loc_name]
                    next_loc = ALMATY_LOCATIONS[next_loc_name]
                    
                    # Interpolate position between current and next
                    progress = random.random()
                    
                    lat = current_loc["lat"] + (next_loc["lat"] - current_loc["lat"]) * progress
                    lon = current_loc["lon"] + (next_loc["lon"] - current_loc["lon"]) * progress
                    
                    # Add small random variation
                    lat += random.uniform(-0.001, 0.001)
                    lon += random.uniform(-0.001, 0.001)
                    
                    # Realistic speed (0-120 km/h)
                    speed = random.choice([0, 0] + [random.randint(25, 120)] * 3)
                    
                    # Create position
                    position = Position(
                        device_id=device.id,
                        latitude=lat,
                        longitude=lon,
                        altitude=random.randint(600, 700),
                        speed=speed,
                        course=random.randint(0, 360),
                        accuracy=5,
                        fix_time=timestamp,
                    )
                    session.add(position)
                    
                    # Move to next location occasionally
                    if random.random() < 0.3:
                        route["index"] = next_index
                
                await session.commit()
                
                # Print status every 10 iterations
                if iteration % 10 == 0:
                    print(f"✅ Iteration {iteration}: Updated {len(devices)} vehicles at {timestamp.strftime('%H:%M:%S')}")
                
                # Wait 10-30 seconds before next update
                wait_time = random.randint(10, 30)
                await asyncio.sleep(wait_time)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Simulator stopped.")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  GPS TRACKER - REAL-TIME POSITION SIMULATOR")
    print("="*60)
    print("\nPress Ctrl+C to stop\n")
    
    try:
        asyncio.run(simulate_vehicle_movement())
    except KeyboardInterrupt:
        print("✅ Simulator shutdown complete")

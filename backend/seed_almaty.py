#!/usr/bin/env python
"""Generate realistic test vehicles with Almaty city coordinates."""

import asyncio
from datetime import datetime, timedelta
import random
from app.core.database import AsyncSessionLocal
from app.models.database import Device, Position


# Real Almaty city neighborhoods and coordinates
ALMATY_LOCATIONS = {
    "Саркан": {"lat": 43.2382, "lon": 76.9453},  # Old center
    "Центр": {"lat": 43.2350, "lon": 76.9400},  # Downtown
    "Абай": {"lat": 43.2420, "lon": 76.9380},  # Abay avenue
    "Керей-Жанибек": {"lat": 43.2280, "lon": 76.9500},  # Central area
    "Панфилова": {"lat": 43.2400, "lon": 76.9350},  # North center
    "Ауезова": {"lat": 43.2320, "lon": 76.9420},  # West center
    "Бауыржана Момушулы": {"lat": 43.2270, "lon": 76.9550},  # South
    "Ул. Жамбыла": {"lat": 43.2450, "lon": 76.9300},  # North
    "Микрорайон Медеу": {"lat": 43.1950, "lon": 76.9700},  # South area (Medeu)
    "Чунарь": {"lat": 43.2100, "lon": 77.0000},  # East suburbs
    "Турксиб": {"lat": 43.2550, "lon": 76.9200},  # North suburbs
    "Актюбинская": {"lat": 43.2600, "lon": 76.9100},  # Far north
}

# Realistic Kazakhstan vehicle brands and models
VEHICLES = [
    {"brand": "Toyota", "model": "Hilux", "category": "truck"},
    {"brand": "Volvo", "model": "FH16", "category": "truck"},
    {"brand": "Scania", "model": "R440", "category": "truck"},
    {"brand": "Mercedes", "model": "Actros", "category": "truck"},
    {"brand": "Hyundai", "model": "HD35", "category": "truck"},
    {"brand": "Isuzu", "model": "NPR", "category": "truck"},
    {"brand": "KamAZ", "model": "5490", "category": "truck"},
    {"brand": "Gazelle", "model": "3302", "category": "truck"},
    {"brand": "Volkswagen", "model": "Crafter", "category": "van"},
    {"brand": "Ford", "model": "Transit", "category": "van"},
]

# Kazakhstan license plate format: [Letter] [3 digits] [2 letters] [2 digits]
# Example: A123BC25 (25 = Almaty region)
def generate_plate():
    """Generate realistic Kazakhstan license plate."""
    letters_start = random.choice("АКВЕМНОРСТУХ")  # Common Cyrillic letters
    letters_end = random.choice("АКВЕМНОРСТУХ") + random.choice("АКВЕМНОРСТУХ")
    numbers = f"{random.randint(100, 999)}"
    region = "25"  # Almaty region code
    return f"{letters_start}{numbers}{letters_end}{region}"


async def seed_vehicles():
    """Create realistic vehicles with Almaty location paths."""
    async with AsyncSessionLocal() as session:
        vehicles_created = []
        
        # Create 5 vehicles
        for i in range(5):
            vehicle = VEHICLES[i]
            unique_id = f"KZ-{random.randint(10000, 99999)}"
            plate = generate_plate()
            
            device = Device(
                unique_id=unique_id,
                name=f"{vehicle['brand']} {vehicle['model']} ({plate})",
                category=vehicle['category'],
                model=f"{vehicle['brand']} {vehicle['model']}",
                phone=f"+7700{random.randint(100000, 999999)}",
                contact=f"Водитель {i+1}"
            )
            session.add(device)
            await session.flush()
            vehicles_created.append((device.id, device.name))
            
            # Generate 10 positions for each vehicle (route through Almaty)
            location_names = list(ALMATY_LOCATIONS.keys())
            random.shuffle(location_names)
            route = location_names[:10]
            
            now = datetime.utcnow()
            
            for j, location_name in enumerate(route):
                loc = ALMATY_LOCATIONS[location_name]
                
                # Add slight randomization to coordinates (±0.005)
                lat = loc["lat"] + random.uniform(-0.005, 0.005)
                lon = loc["lon"] + random.uniform(-0.005, 0.005)
                
                # Create time progression: each point ~30 min to 2 hours apart
                time_offset = timedelta(
                    hours=j * random.randint(1, 2),
                    minutes=random.randint(0, 59)
                )
                fix_time = now - time_offset
                
                # Realistic speed variation
                speed = random.choice([0, 0, 0] + [random.randint(30, 120)] * 3)  # Mostly moving
                
                position = Position(
                    device_id=device.id,
                    latitude=lat,
                    longitude=lon,
                    altitude=random.randint(600, 700),  # Almaty elevation
                    speed=speed,
                    course=random.randint(0, 360),
                    accuracy=5,
                    fix_time=fix_time,
                )
                session.add(position)
        
        await session.commit()
        
        print("\n✅ Realistic test vehicles created successfully!\n")
        for device_id, name in vehicles_created:
            print(f"   🚛 [{device_id}] {name}")
        print(f"\n   📍 Total: {len(vehicles_created)} vehicles")
        print(f"   📊 Total: {len(vehicles_created) * 10} position points")
        print(f"   🗺️  Coverage: Almaty city + suburbs")


if __name__ == "__main__":
    asyncio.run(seed_vehicles())

"""WebSocket manager for live position updates."""

from typing import Dict, Set, List
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
from app.models.schemas import LivePositionUpdate


class ConnectionManager:
    """Manage WebSocket connections for live tracking."""

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # device_id -> set of WebSockets
        self.client_subscriptions: Dict[WebSocket, Set[int]] = {}  # WebSocket -> set of device_ids

    async def connect(self, websocket: WebSocket, device_ids: List[int]):
        """Subscribe client to device updates."""
        await websocket.accept()
        self.client_subscriptions[websocket] = set(device_ids)

        for device_id in device_ids:
            if device_id not in self.active_connections:
                self.active_connections[device_id] = set()
            self.active_connections[device_id].add(websocket)

    def disconnect(self, websocket: WebSocket):
        """Unsubscribe client."""
        device_ids = self.client_subscriptions.pop(websocket, set())
        for device_id in device_ids:
            if device_id in self.active_connections:
                self.active_connections[device_id].discard(websocket)
                if not self.active_connections[device_id]:
                    del self.active_connections[device_id]

    async def broadcast_position(self, position_update: LivePositionUpdate):
        """Broadcast position update to all subscribed clients."""
        device_id = position_update.device_id

        if device_id not in self.active_connections:
            return

        message = {
            "type": "position_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": position_update.model_dump(),
        }

        message_json = json.dumps(message)
        disconnected = []

        for websocket in self.active_connections[device_id]:
            try:
                await websocket.send_text(message_json)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    async def broadcast_trip_start(self, device_id: int, device_name: str, latitude: float, longitude: float):
        """Broadcast trip start event."""
        if device_id not in self.active_connections:
            return

        message = {
            "type": "trip_start",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "device_id": device_id,
                "device_name": device_name,
                "latitude": latitude,
                "longitude": longitude,
            },
        }

        message_json = json.dumps(message)
        for websocket in self.active_connections[device_id]:
            try:
                await websocket.send_text(message_json)
            except Exception:
                self.disconnect(websocket)

    async def broadcast_trip_end(self, device_id: int, device_name: str, latitude: float, longitude: float, duration: int, distance: float):
        """Broadcast trip end event."""
        if device_id not in self.active_connections:
            return

        message = {
            "type": "trip_end",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "device_id": device_id,
                "device_name": device_name,
                "latitude": latitude,
                "longitude": longitude,
                "duration_sec": duration,
                "distance_km": distance,
            },
        }

        message_json = json.dumps(message)
        for websocket in self.active_connections[device_id]:
            try:
                await websocket.send_text(message_json)
            except Exception:
                self.disconnect(websocket)


# Global connection manager
ws_manager = ConnectionManager()

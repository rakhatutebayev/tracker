from fastapi import FastAPI, WebSocket, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

from app.core.config import settings
from app.core.database import init_db, close_db, get_db
from app.api.routes import router as api_router
from app.api.websocket import ws_manager
from app.models.schemas import LivePositionUpdate

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

# CORS
# Explicit CORS origins for dev, plus optional production origins via env (CORS_ORIGINS)
allowed_origins = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if settings.CORS_ORIGINS:
    extra = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    allowed_origins.extend(extra)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(api_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    await init_db()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database on shutdown."""
    await close_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/version")
async def version():
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}


@app.websocket("/ws/tracker")
async def websocket_tracker(websocket: WebSocket, devices: str = Query(...)):
    """
    WebSocket endpoint for live position tracking.
    
    Usage: ws://localhost:8000/ws/tracker?devices=1,2,3
    """
    device_ids = [int(d) for d in devices.split(",") if d.strip().isdigit()]

    if not device_ids:
        await websocket.close(code=1008, reason="No valid device IDs")
        return

    await ws_manager.connect(websocket, device_ids)

    try:
        while True:
            # Keep connection alive, receive heartbeat or messages
            data = await websocket.receive_text()
            # Client can send heartbeat or commands (future use)
    except Exception as e:
        ws_manager.disconnect(websocket)
        print(f"WebSocket error: {e}")


from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Tracker Backend (Python)"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://traccar:traccar@localhost:5432/traccar"
    DATABASE_ECHO: bool = False

    # Server
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: Optional[str] = None  # comma-separated list of origins for production

    # Trip detection (configurable)
    TRIP_MIN_DURATION_SEC: int = 60  # минимум 1 минута
    TRIP_MIN_SPEED_KMH: float = 5.0
    TRIP_IDLE_THRESHOLD_SEC: int = 300  # 5 минут без движения = стоп
    TRIP_MAX_GAP_SEC: int = 1800  # 30 минут разрыва между точками завершает поездку

    class Config:
        env_file = ".env"


settings = Settings() 

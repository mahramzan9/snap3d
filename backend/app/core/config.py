"""
snap3D — Application Configuration
All settings come from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import List
import secrets


class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATABASE_URL: str = "postgresql+asyncpg://snap3d:snap3d@localhost:5432/snap3d"
    REDIS_URL: str = "redis://localhost:6379/0"
    S3_ENDPOINT: str = ""
    S3_BUCKET: str = "snap3d-files"
    S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    CDN_BASE_URL: str = ""
    TRIPO3D_API_KEY: str = ""
    TRIPO3D_BASE_URL: str = "https://api.tripo3d.ai/v2/openapi"
    MESHY_API_KEY: str = ""
    MESHY_BASE_URL: str = "https://api.meshy.ai/v2"
    REPLICATE_API_TOKEN: str = ""
    RECONSTRUCTION_PROVIDER: str = "tripo3d"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "https://snap3d.app"]
    MAX_IMAGE_FREE: int = 20
    MAX_IMAGES_PRO: int = 50
    MAX_FILE_SIZE_MB: int = 20
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    OCTOPRIONT_DEFAULT_TIMEOUT: int = 30
    BAMBU_CLOUD_BASE_URL: str = "https://api.bambulab.com"
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

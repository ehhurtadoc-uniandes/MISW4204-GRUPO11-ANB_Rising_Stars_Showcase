from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://anb_user:anb_password@postgres:5432/anb_db"
    
    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://redis:6379/0"
    
    # File Storage
    upload_dir: str = "/app/uploads"
    processed_dir: str = "/app/processed_videos"
    max_file_size_mb: int = 100
    
    # Celery Configuration
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # ANB Configuration
    anb_logo_path: str = "/app/assets/anb_logo.png"
    video_max_duration: int = 30
    video_resolution: str = "720p"
    
    model_config = {"env_file": ".env"}


settings = Settings()
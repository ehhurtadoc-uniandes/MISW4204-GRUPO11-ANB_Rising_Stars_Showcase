from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    NOTE: Default values are for LOCAL DEVELOPMENT (Docker Compose).
    In PRODUCTION (AWS), these values are OVERRIDDEN by the .env file.
    """
    
    # Database
    # Default: Local development (Docker Compose service name "postgres")
    # Production: Overridden by .env with RDS endpoint
    database_url: str = "postgresql://anb_user:anb_password@postgres:5432/anbdb"
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_user: Optional[str] = None
    postgres_password: Optional[str] = None
    postgres_db: Optional[str] = None
    
    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis Configuration
    # Default: Local development (Docker Compose service name "redis")
    # Production: Overridden by .env with EC2 Redis private IP
    redis_url: str = "redis://redis:6379/0"
    
    # File Storage
    storage_type: str = "local"  # "local" or "cloud"
    upload_dir: str = "/app/uploads"
    processed_dir: str = "/app/processed_videos"
    max_file_size_mb: int = 100
    
    # S3 Configuration (for cloud storage)
    # Production: Overridden by .env with actual S3 bucket name
    aws_region: str = "us-east-1"
    s3_bucket_name: str = ""
    s3_upload_prefix: str = "uploads/"
    s3_processed_prefix: str = "processed_videos/"
    
    # AWS Credentials (required if not using IAM roles)
    # Production: Overridden by .env with actual AWS credentials
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    
    # Celery Configuration
    # Default: Local development (Docker Compose service name "redis")
    # Production: Overridden by .env with EC2 Redis private IP
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    
    # Environment
    # Production: Overridden by .env (ENVIRONMENT=production, DEBUG=False)
    environment: str = "development"
    debug: bool = True
    
    # ANB Configuration
    anb_logo_path: str = "/app/assets/anb_logo.png"
    video_max_duration: int = 30
    video_resolution: str = "720p"
    
    model_config = {"env_file": ".env"}


settings = Settings()
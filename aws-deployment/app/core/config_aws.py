from pydantic_settings import BaseSettings
from typing import Optional
import os


class AWSSettings(BaseSettings):
    # Database Configuration
    database_url: str = "postgresql://anb_user:anb_password@localhost:5432/anb_db"
    
    # JWT Configuration
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    
    # File Storage - AWS NFS Configuration
    upload_dir: str = "/mnt/nfs/uploads"
    processed_dir: str = "/mnt/nfs/processed_videos"
    assets_dir: str = "/mnt/nfs/assets"
    max_file_size_mb: int = 100
    
    # Celery Configuration
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Environment
    environment: str = "production"
    debug: bool = False
    
    # ANB Configuration
    anb_logo_path: str = "/mnt/nfs/assets/anb_logo.png"
    video_max_duration: int = 30
    video_resolution: str = "720p"
    
    # AWS Specific Configuration
    aws_region: str = "us-east-1"
    nfs_server_ip: Optional[str] = None
    
    # Database connection details for AWS RDS
    postgres_host: Optional[str] = None
    postgres_port: int = 5432
    postgres_user: str = "anb_user"
    postgres_password: Optional[str] = None
    postgres_db: str = "anb_db"
    
    # Redis connection details for AWS ElastiCache
    redis_endpoint: Optional[str] = None
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Override with environment variables if they exist
        if os.getenv("DATABASE_URL"):
            self.database_url = os.getenv("DATABASE_URL")
        
        if os.getenv("SECRET_KEY"):
            self.secret_key = os.getenv("SECRET_KEY")
        
        if os.getenv("REDIS_URL"):
            self.redis_url = os.getenv("REDIS_URL")
        
        if os.getenv("CELERY_BROKER_URL"):
            self.celery_broker_url = os.getenv("CELERY_BROKER_URL")
        
        if os.getenv("CELERY_RESULT_BACKEND"):
            self.celery_result_backend = os.getenv("CELERY_RESULT_BACKEND")
        
        if os.getenv("ENVIRONMENT"):
            self.environment = os.getenv("ENVIRONMENT")
        
        if os.getenv("DEBUG"):
            self.debug = os.getenv("DEBUG").lower() == "true"
        
        if os.getenv("NFS_SERVER_IP"):
            self.nfs_server_ip = os.getenv("NFS_SERVER_IP")
        
        if os.getenv("POSTGRES_HOST"):
            self.postgres_host = os.getenv("POSTGRES_HOST")
        
        if os.getenv("POSTGRES_PASSWORD"):
            self.postgres_password = os.getenv("POSTGRES_PASSWORD")
        
        if os.getenv("REDIS_ENDPOINT"):
            self.redis_endpoint = os.getenv("REDIS_ENDPOINT")
        
        if os.getenv("AWS_REGION"):
            self.aws_region = os.getenv("AWS_REGION")
        
        # Update file paths based on NFS configuration
        if self.nfs_server_ip:
            self.upload_dir = "/mnt/nfs/uploads"
            self.processed_dir = "/mnt/nfs/processed_videos"
            self.assets_dir = "/mnt/nfs/assets"
            self.anb_logo_path = "/mnt/nfs/assets/anb_logo.png"
        
        # Update database URL if individual components are provided
        if self.postgres_host and self.postgres_password:
            self.database_url = f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        
        # Update Redis URL if endpoint is provided
        if self.redis_endpoint:
            self.redis_url = f"redis://{self.redis_endpoint}:6379/0"
            self.celery_broker_url = f"redis://{self.redis_endpoint}:6379/0"
            self.celery_result_backend = f"redis://{self.redis_endpoint}:6379/0"
    
    model_config = {"env_file": ".env"}


# Create settings instance
settings = AWSSettings()

from abc import ABC, abstractmethod
from typing import Optional
import os
import shutil
import logging
from app.core.config import settings
try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

logger = logging.getLogger(__name__)


class FileStorageInterface(ABC):
    """Abstract interface for file storage"""
    
    @abstractmethod
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        """Save file and return file path"""
        pass
    
    @abstractmethod
    def get_file_path(self, filename: str, directory: str) -> str:
        """Get full file path"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass


class LocalFileStorage(FileStorageInterface):
    """Local file system storage implementation"""
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.processed_dir = settings.processed_dir
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create directories if they don't exist"""
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
    
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        """Save file to local storage"""
        full_directory = os.path.join(directory)
        os.makedirs(full_directory, exist_ok=True)
        
        file_path = os.path.join(full_directory, filename)
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        return file_path
    
    def get_file_path(self, filename: str, directory: str) -> str:
        """Get full file path"""
        return os.path.join(directory, filename)
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from local storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        return os.path.exists(file_path)
    
    def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy file from source to destination"""
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)
            return True
        except Exception:
            return False


class S3FileStorage(FileStorageInterface):
    """AWS S3 storage implementation"""
    
    def __init__(self):
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for S3 storage. Install it with: pip install boto3")
        
        if not settings.s3_bucket_name:
            raise ValueError("S3_BUCKET_NAME must be set when using cloud storage")
        
        # Configure boto3 client with credentials if provided
        client_kwargs = {'region_name': settings.aws_region}
        
        # Use credentials if provided (for cases without IAM roles)
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs['aws_access_key_id'] = settings.aws_access_key_id
            client_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
        
        self.s3_client = boto3.client('s3', **client_kwargs)
        self.bucket_name = settings.s3_bucket_name
        self.upload_prefix = settings.s3_upload_prefix
        self.processed_prefix = settings.s3_processed_prefix
    
    def _get_s3_key(self, filename: str, directory: str) -> str:
        """Get S3 key for file"""
        if directory == 'uploads' or directory == settings.upload_dir:
            return f"{self.upload_prefix}{filename}"
        elif directory == 'processed_videos' or directory == settings.processed_dir:
            return f"{self.processed_prefix}{filename}"
        else:
            return f"{directory}/{filename}"
    
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        """Save file to S3"""
        key = self._get_s3_key(filename, directory)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data
            )
            return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            raise Exception(f"Error uploading to S3: {str(e)}")
    
    def get_file_path(self, filename: str, directory: str) -> str:
        """
        Get S3 file URL.
        
        Since the bucket is configured as public for read access,
        we return a direct URL (simpler, no expiration).
        For private buckets, you would need to use presigned URLs.
        """
        key = self._get_s3_key(filename, directory)
        
        # Direct URL format: https://bucket.s3.region.amazonaws.com/key
        # This works for public buckets (which is our configuration)
        direct_url = f"https://{self.bucket_name}.s3.{settings.aws_region}.amazonaws.com/{key}"
        return direct_url
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from S3"""
        try:
            # Extract key from path
            if file_path.startswith('s3://'):
                key = file_path.replace(f's3://{self.bucket_name}/', '')
            else:
                # Assume it's just the key
                key = file_path
            
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in S3"""
        try:
            # Extract key from path
            if file_path.startswith('s3://'):
                key = file_path.replace(f's3://{self.bucket_name}/', '')
            else:
                key = file_path
            
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
    
    def download_file(self, s3_path: str, local_path: str) -> bool:
        """Download file from S3 to local path"""
        try:
            # Extract key from S3 path
            if s3_path.startswith('s3://'):
                # Remove s3://bucket/ prefix
                key = s3_path.replace(f's3://{self.bucket_name}/', '')
            else:
                # Assume it's just the key
                key = s3_path
            
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, key, local_path)
            return True
        except ClientError as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return False
    
    def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy file within S3 or from local to S3"""
        try:
            # Extract destination key
            if dest_path.startswith('s3://'):
                dest_key = dest_path.replace(f's3://{self.bucket_name}/', '')
            else:
                dest_key = dest_path
            
            # Handle source path
            if src_path.startswith('s3://'):
                # S3 to S3 copy
                src_key = src_path.replace(f's3://{self.bucket_name}/', '')
                copy_source = {'Bucket': self.bucket_name, 'Key': src_key}
                self.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.bucket_name,
                    Key=dest_key
                )
            else:
                # Local file to S3 - read and upload
                with open(src_path, 'rb') as f:
                    file_data = f.read()
                self.s3_client.put_object(Bucket=self.bucket_name, Key=dest_key, Body=file_data)
            
            return True
        except Exception:
            return False


class CloudFileStorage(FileStorageInterface):
    """Cloud storage implementation (alias for S3FileStorage)"""
    
    def __init__(self, cloud_config: dict = None):
        # Use S3FileStorage as implementation
        self.s3_storage = S3FileStorage()
    
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        return self.s3_storage.save_file(file_data, filename, directory)
    
    def get_file_path(self, filename: str, directory: str) -> str:
        return self.s3_storage.get_file_path(filename, directory)
    
    def delete_file(self, file_path: str) -> bool:
        return self.s3_storage.delete_file(file_path)
    
    def file_exists(self, file_path: str) -> bool:
        return self.s3_storage.file_exists(file_path)


# Storage factory
def get_file_storage() -> FileStorageInterface:
    """Get file storage implementation based on configuration"""
    storage_type = getattr(settings, 'storage_type', 'local')
    
    if storage_type == 'cloud':
        return S3FileStorage()
    else:
        return LocalFileStorage()
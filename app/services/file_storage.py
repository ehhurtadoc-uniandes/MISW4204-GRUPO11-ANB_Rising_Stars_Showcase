from abc import ABC, abstractmethod
from typing import Optional
import os
import shutil
from app.core.config import settings


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


class CloudFileStorage(FileStorageInterface):
    """Cloud storage implementation (placeholder for future AWS S3/Azure Blob)"""
    
    def __init__(self, cloud_config: dict = None):
        self.cloud_config = cloud_config or {}
        # TODO: Initialize cloud storage client
    
    def save_file(self, file_data: bytes, filename: str, directory: str) -> str:
        """Save file to cloud storage"""
        # TODO: Implement cloud storage upload
        raise NotImplementedError("Cloud storage not implemented yet")
    
    def get_file_path(self, filename: str, directory: str) -> str:
        """Get cloud file URL"""
        # TODO: Return cloud file URL
        raise NotImplementedError("Cloud storage not implemented yet")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from cloud storage"""
        # TODO: Implement cloud file deletion
        raise NotImplementedError("Cloud storage not implemented yet")
    
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists in cloud"""
        # TODO: Check cloud file existence
        raise NotImplementedError("Cloud storage not implemented yet")


# Storage factory
def get_file_storage() -> FileStorageInterface:
    """Get file storage implementation based on configuration"""
    storage_type = getattr(settings, 'storage_type', 'local')
    
    if storage_type == 'cloud':
        return CloudFileStorage()
    else:
        return LocalFileStorage()
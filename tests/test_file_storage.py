import pytest
from app.services.file_storage import LocalFileStorage, get_file_storage
import tempfile
import os


def test_local_file_storage_save_file():
    """Test saving file with local storage"""
    storage = LocalFileStorage()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        file_data = b"test file content"
        filename = "test_file.txt"
        
        file_path = storage.save_file(file_data, filename, temp_dir)
        
        assert os.path.exists(file_path)
        with open(file_path, "rb") as f:
            assert f.read() == file_data


def test_local_file_storage_file_exists():
    """Test checking if file exists"""
    storage = LocalFileStorage()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        file_data = b"test file content"
        filename = "test_file.txt"
        
        file_path = storage.save_file(file_data, filename, temp_dir)
        
        assert storage.file_exists(file_path) is True
        assert storage.file_exists("/nonexistent/path") is False


def test_local_file_storage_delete_file():
    """Test deleting file"""
    storage = LocalFileStorage()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        file_data = b"test file content"
        filename = "test_file.txt"
        
        file_path = storage.save_file(file_data, filename, temp_dir)
        assert storage.file_exists(file_path) is True
        
        success = storage.delete_file(file_path)
        assert success is True
        assert storage.file_exists(file_path) is False


def test_get_file_storage():
    """Test file storage factory function"""
    storage = get_file_storage()
    assert isinstance(storage, LocalFileStorage)
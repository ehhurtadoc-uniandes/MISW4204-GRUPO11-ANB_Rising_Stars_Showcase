import pytest
import io
from unittest.mock import patch, MagicMock


def test_get_my_videos_empty(authenticated_client):
    """Test getting videos when user has none"""
    client, token_data = authenticated_client
    
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert response.json() == []


def test_get_my_videos_unauthorized(client):
    """Test getting videos without authentication"""
    response = client.get("/api/videos")
    assert response.status_code == 403


@patch('app.workers.video_processor.process_video_task.delay')
@patch('app.services.file_storage.get_file_storage')
def test_upload_video_success(mock_storage, mock_task, authenticated_client):
    """Test successful video upload"""
    client, token_data = authenticated_client
    
    # Mock file storage
    mock_storage_instance = MagicMock()
    mock_storage_instance.save_file.return_value = "/app/uploads/test_video.mp4"
    mock_storage.return_value = mock_storage_instance
    
    # Mock Celery task
    mock_task.return_value.id = "test-task-id"
    
    # Create fake video file
    video_content = b"fake video content"
    video_file = io.BytesIO(video_content)
    
    response = client.post(
        "/api/videos/upload",
        files={"video_file": ("test_video.mp4", video_file, "video/mp4")},
        data={"title": "Test Video"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "task_id" in data
    assert data["task_id"] == "test-task-id"


def test_upload_video_unauthorized(client):
    """Test video upload without authentication"""
    video_content = b"fake video content"
    video_file = io.BytesIO(video_content)
    
    response = client.post(
        "/api/videos/upload",
        files={"video_file": ("test_video.mp4", video_file, "video/mp4")},
        data={"title": "Test Video"}
    )
    
    assert response.status_code == 403


def test_upload_video_invalid_format(authenticated_client):
    """Test upload with invalid file format"""
    client, token_data = authenticated_client
    
    # Create fake text file
    text_content = b"fake text content"
    text_file = io.BytesIO(text_content)
    
    response = client.post(
        "/api/videos/upload",
        files={"video_file": ("test_file.txt", text_file, "text/plain")},
        data={"title": "Test Video"}
    )
    
    assert response.status_code == 400
    assert "Tipo de archivo no válido" in response.json()["detail"]


@patch('app.services.file_storage.get_file_storage')
def test_upload_video_too_large(mock_storage, authenticated_client):
    """Test upload with file too large"""
    client, token_data = authenticated_client
    
    # Create fake large video file (simulate size check)
    large_video_content = b"x" * (101 * 1024 * 1024)  # 101MB
    video_file = io.BytesIO(large_video_content)
    
    response = client.post(
        "/api/videos/upload",
        files={"video_file": ("large_video.mp4", video_file, "video/mp4")},
        data={"title": "Large Video"}
    )
    
    assert response.status_code == 400
    assert "muy grande" in response.json()["detail"]


def test_get_video_detail_not_found(authenticated_client):
    """Test getting detail of non-existent video"""
    client, token_data = authenticated_client
    
    response = client.get("/api/videos/nonexistent-id")
    assert response.status_code == 404
    assert "Video no encontrado" in response.json()["detail"]


def test_delete_video_not_found(authenticated_client):
    """Test deleting non-existent video"""
    client, token_data = authenticated_client
    
    response = client.delete("/api/videos/nonexistent-id")
    assert response.status_code == 404
    assert "Video no encontrado" in response.json()["detail"]


def test_get_videos_with_invalid_token(client):
    """Test accessing videos with invalid token"""
    client.headers.update({
        "Authorization": "Bearer invalid-token"
    })
    
    response = client.get("/api/videos")
    assert response.status_code == 403
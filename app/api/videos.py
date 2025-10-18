from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.services.video_service import VideoService
from app.services.file_storage import get_file_storage
from app.schemas.video import (
    VideoCreate, VideoResponse, VideoListResponse, 
    VideoUploadResponse, VideoDeleteResponse
)
from app.schemas.user import UserResponse
from app.models.video import VideoStatus
from app.core.config import settings
from app.workers.celery_app import celery_app
from app.core.config import settings

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED, response_model=VideoUploadResponse)
async def upload_video(
    title: str = Form(...),
    video_file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload a video for processing"""
    
    # Validate file type
    allowed_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'}
    file_extension = os.path.splitext(video_file.filename)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no válido. Solo se permiten videos."
        )
    
    # Validate file size
    file_content = await video_file.read()
    file_size_mb = len(file_content) / (1024 * 1024)
    
    if file_size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo es muy grande. Tamaño máximo: {settings.max_file_size_mb}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    
    # Save file
    file_storage = get_file_storage()
    file_path = file_storage.save_file(
        file_content, 
        unique_filename, 
        settings.upload_dir
    )
    
    # Create video record
    video_data = VideoCreate(title=title)
    video = VideoService.create_video(
        db, video_data, current_user.id, video_file.filename, file_path
    )
    
    # Enqueue processing task
    task = celery_app.send_task(
        'app.workers.video_processor.process_video_task',
        args=[str(video.id), file_path],
        queue='video_queue'
    )
    
    # Update video with task ID
    video.task_id = task.id
    db.commit()
    
    return VideoUploadResponse(
        message="Video subido correctamente. Procesamiento en curso.",
        task_id=task.id
    )


@router.get("", response_model=List[VideoListResponse])
def get_my_videos(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all videos uploaded by the current user"""
    videos = VideoService.get_user_videos(db, current_user.id)
    
    result = []
    for video in videos:
        video_data = VideoListResponse(
            video_id=str(video.id),
            title=video.title,
            status=video.status,
            uploaded_at=video.created_at,
            processed_at=video.processed_at,
            processed_url=f"/api/videos/{video.id}/download" if video.status == VideoStatus.processed else None
        )
        result.append(video_data)
    
    return result


@router.get("/{video_id}", response_model=VideoResponse)
def get_video_detail(
    video_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific video"""
    # First check if video exists (without user filter)
    video_exists = VideoService.get_video_by_id_any_user(db, video_id)
    if not video_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video no encontrado"
        )
    
    # Then check if user owns the video
    video = VideoService.get_video_by_id(db, video_id, current_user.id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este video"
        )
    
    # Get vote count
    vote_count = VideoService.get_video_vote_count(db, video_id)
    
    return VideoResponse(
        video_id=str(video.id),
        title=video.title,
        status=video.status,
        uploaded_at=video.created_at,
        processed_at=video.processed_at,
        original_url=f"/api/videos/{video.id}/original" if video.original_path else None,
        processed_url=f"/api/videos/{video.id}/download" if video.status == VideoStatus.processed else None,
        votes=vote_count
    )


@router.delete("/{video_id}", response_model=VideoDeleteResponse)
def delete_video(
    video_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a video if conditions are met"""
    # First check if video exists (without user filter)
    video_exists = VideoService.get_video_by_id_any_user(db, video_id)
    if not video_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video no encontrado"
        )
    
    # Then check if user owns the video
    video = VideoService.get_video_by_id(db, video_id, current_user.id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para eliminar este video"
        )
    
    # Check if video can be deleted
    if video.status not in [VideoStatus.uploaded, VideoStatus.failed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el video porque ya está siendo procesado o habilitado para votación"
        )
    
    success = VideoService.delete_video(db, video_id, current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo eliminar el video"
        )
    
    return VideoDeleteResponse(
        message="El video ha sido eliminado exitosamente.",
        video_id=video_id
    )
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import logging
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
from app.services.sqs_service import get_sqs_service
# Legacy Celery support (for backward compatibility)
try:
    from app.workers.celery_app import celery_app
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    celery_app = None

logger = logging.getLogger(__name__)

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
    
    # Enqueue processing task using SQS (Entrega 4)
    sqs_service = get_sqs_service()
    message_id = sqs_service.send_video_processing_message(
        video_id=str(video.id),
        video_path=file_path
    )
    
    if not message_id:
        # Fallback to Celery if SQS is not configured (backward compatibility)
        if CELERY_AVAILABLE and celery_app:
            logger.warning("SQS not configured, falling back to Celery")
            task = celery_app.send_task(
                'app.workers.video_processor.process_video_task',
                args=[str(video.id), file_path],
                queue='video_queue'
            )
            message_id = task.id
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo encolar la tarea de procesamiento. Verifique la configuración de SQS."
            )
    
    # Update video with task ID (message_id from SQS or Celery)
    video.task_id = message_id
    db.commit()
    
    return VideoUploadResponse(
        message="Video subido correctamente. Procesamiento en curso.",
        task_id=message_id
    )


@router.get("", response_model=List[VideoListResponse])
def get_my_videos(
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all videos uploaded by the current user"""
    videos = VideoService.get_user_videos(db, current_user.id)
    
    result = []
    file_storage = get_file_storage()
    for video in videos:
        # Get processed URL: if processed_path is a URL (starts with http), use it directly
        # Otherwise, if it's an S3 path, get the public URL, or use download endpoint for local
        processed_url = None
        if video.status == VideoStatus.processed and video.processed_path:
            if video.processed_path.startswith('http://') or video.processed_path.startswith('https://'):
                # Already a public URL
                processed_url = video.processed_path
            elif video.processed_path.startswith('s3://'):
                # S3 path, extract filename and get public URL
                # Extract filename from S3 path: s3://bucket/prefix/filename
                parts = video.processed_path.split('/')
                filename = parts[-1]
                processed_url = file_storage.get_file_path(filename, settings.processed_dir)
            else:
                # Local path, use download endpoint
                processed_url = f"/api/videos/{video.id}/download"
        
        video_data = VideoListResponse(
            video_id=str(video.id),
            title=video.title,
            status=video.status,
            uploaded_at=video.created_at,
            processed_at=video.processed_at,
            processed_url=processed_url
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
    
    # Get processed URL: if processed_path is a URL (starts with http), use it directly
    # Otherwise, if it's an S3 path, get the public URL, or use download endpoint for local
    file_storage = get_file_storage()
    processed_url = None
    if video.status == VideoStatus.processed and video.processed_path:
        if video.processed_path.startswith('http://') or video.processed_path.startswith('https://'):
            # Already a public URL
            processed_url = video.processed_path
        elif video.processed_path.startswith('s3://'):
            # S3 path, extract filename and get public URL
            # Extract filename from S3 path: s3://bucket/prefix/filename
            parts = video.processed_path.split('/')
            filename = parts[-1]
            processed_url = file_storage.get_file_path(filename, settings.processed_dir)
        else:
            # Local path, use download endpoint
            processed_url = f"/api/videos/{video.id}/download"
    
    return VideoResponse(
        video_id=str(video.id),
        title=video.title,
        status=video.status,
        uploaded_at=video.created_at,
        processed_at=video.processed_at,
        original_url=f"/api/videos/{video.id}/original" if video.original_path else None,
        processed_url=processed_url,
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
    # Allow deletion of uploaded, failed, or processed videos
    # Only block deletion if video is currently being processed
    if video.status == VideoStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el video porque está siendo procesado actualmente"
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
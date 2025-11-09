from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.services.video_service import VideoService
from app.services.vote_service import VoteService
from app.services.file_storage import get_file_storage
from app.schemas.vote import VoteResponse, RankingItem, PublicVideoResponse
from app.schemas.user import UserResponse
from app.models.video import VideoStatus
from app.core.config import settings

router = APIRouter()


@router.get("/videos", response_model=List[PublicVideoResponse])
def get_public_videos(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all public videos available for voting"""
    videos = VideoService.get_public_videos(db, limit, offset)
    
    result = []
    file_storage = get_file_storage()
    for video in videos:
        vote_count = VideoService.get_video_vote_count(db, str(video.id))
        
        # Get processed URL: if processed_path is a URL (starts with http), use it directly
        # Otherwise, if it's an S3 path, get the public URL, or use download endpoint for local
        processed_url = None
        if video.processed_path:
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
        
        video_data = PublicVideoResponse(
            video_id=str(video.id),
            title=video.title,
            username=f"{video.owner.first_name} {video.owner.last_name}",
            city=video.owner.city,
            processed_url=processed_url,
            votes=vote_count
        )
        result.append(video_data)
    
    return result


@router.post("/videos/{video_id}/vote", response_model=VoteResponse)
def vote_for_video(
    video_id: str,
    current_user: UserResponse = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Cast a vote for a video"""
    
    # Check if video exists and is processed
    video = VideoService.get_video_by_id(db, video_id)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video no encontrado"
        )
    
    if video.status != VideoStatus.processed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El video no está disponible para votación"
        )
    
    # Cast vote
    success = VoteService.cast_vote(db, current_user.id, video_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has votado por este video"
        )
    
    return VoteResponse(message="Voto registrado exitosamente.")


@router.get("/ranking", response_model=List[RankingItem])
def get_rankings(
    city: Optional[str] = Query(None, description="Filtrar por ciudad"),
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """Get current ranking of players by votes"""
    ranking = VoteService.get_ranking(db, city, limit)
    return ranking
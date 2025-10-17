from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.services.video_service import VideoService
from app.services.vote_service import VoteService
from app.schemas.vote import VoteResponse, RankingItem, PublicVideoResponse
from app.schemas.user import UserResponse
from app.models.video import VideoStatus

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
    for video in videos:
        vote_count = VideoService.get_video_vote_count(db, str(video.id))
        
        video_data = PublicVideoResponse(
            video_id=str(video.id),
            title=video.title,
            username=f"{video.owner.first_name} {video.owner.last_name}",
            city=video.owner.city,
            processed_url=f"/api/videos/{video.id}/download",
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


@router.get("/rankings", response_model=List[RankingItem])
def get_rankings(
    city: Optional[str] = Query(None, description="Filtrar por ciudad"),
    limit: int = Query(default=50, le=100),
    db: Session = Depends(get_db)
):
    """Get current ranking of players by votes"""
    ranking = VoteService.get_ranking(db, city, limit)
    return ranking
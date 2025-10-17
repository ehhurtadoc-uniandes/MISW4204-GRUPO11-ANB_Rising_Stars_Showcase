from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.models.vote import Vote
from app.schemas.video import VideoCreate
import os
import uuid


class VideoService:
    @staticmethod
    def create_video(db: Session, video: VideoCreate, user_id: int, original_filename: str, file_path: str) -> Video:
        """Create a new video record"""
        video_id = str(uuid.uuid4())
        db_video = Video(
            id=video_id,
            title=video.title,
            original_filename=original_filename,
            original_path=file_path,
            owner_id=user_id,
            status=VideoStatus.uploaded
        )
        db.add(db_video)
        db.commit()
        db.refresh(db_video)
        return db_video

    @staticmethod
    def get_user_videos(db: Session, user_id: int) -> List[Video]:
        """Get all videos for a user"""
        return db.query(Video).filter(Video.owner_id == user_id).all()

    @staticmethod
    def get_video_by_id(db: Session, video_id: str, user_id: int = None) -> Video:
        """Get video by ID, optionally filtered by user"""
        query = db.query(Video).filter(Video.id == video_id)
        if user_id:
            query = query.filter(Video.owner_id == user_id)
        return query.first()

    @staticmethod
    def delete_video(db: Session, video_id: str, user_id: int) -> bool:
        """Delete a video if conditions are met"""
        video = VideoService.get_video_by_id(db, video_id, user_id)
        if not video:
            return False
        
        # Check if video can be deleted (not published for voting)
        # For now, we allow deletion if status is uploaded or failed
        if video.status not in [VideoStatus.uploaded, VideoStatus.failed]:
            return False
        
        # Delete physical files
        try:
            if os.path.exists(video.original_path):
                os.remove(video.original_path)
            if video.processed_path and os.path.exists(video.processed_path):
                os.remove(video.processed_path)
        except Exception:
            pass  # Continue even if file deletion fails
        
        db.delete(video)
        db.commit()
        return True

    @staticmethod
    def update_video_status(db: Session, video_id: str, status: VideoStatus, 
                          processed_path: str = None, error_message: str = None):
        """Update video status and processed path"""
        video = db.query(Video).filter(Video.id == video_id).first()
        if video:
            video.status = status
            if processed_path:
                video.processed_path = processed_path
            if error_message:
                video.error_message = error_message
            if status == VideoStatus.processed:
                video.processed_at = func.now()
            db.commit()
            db.refresh(video)

    @staticmethod
    def get_public_videos(db: Session, limit: int = 100, offset: int = 0) -> List[Video]:
        """Get processed videos available for public voting"""
        return db.query(Video).filter(
            Video.status == VideoStatus.processed
        ).offset(offset).limit(limit).all()

    @staticmethod
    def get_video_vote_count(db: Session, video_id: str) -> int:
        """Get vote count for a video"""
        return db.query(Vote).filter(Vote.video_id == video_id).count()
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List
from app.models.vote import Vote
from app.models.video import Video, VideoStatus
from app.models.user import User
from app.schemas.vote import RankingItem


class VoteService:
    @staticmethod
    def cast_vote(db: Session, user_id: int, video_id: str) -> bool:
        """Cast a vote for a video"""
        # Check if user has already voted for this video
        existing_vote = db.query(Vote).filter(
            Vote.voter_id == user_id,
            Vote.video_id == video_id
        ).first()
        
        if existing_vote:
            return False  # User already voted
        
        # Check if video exists and is processed
        video = db.query(Video).filter(
            Video.id == video_id,
            Video.status == VideoStatus.processed
        ).first()
        
        if not video:
            return False  # Video not found or not processed
        
        # Create vote
        vote = Vote(voter_id=user_id, video_id=video_id)
        db.add(vote)
        db.commit()
        return True

    @staticmethod
    def get_ranking(db: Session, city: str = None, limit: int = 100) -> List[RankingItem]:
        """Get ranking of players by vote count"""
        query = db.query(
            User.first_name,
            User.last_name,
            User.city,
            func.count(Vote.id).label('vote_count')
        ).join(
            Video, Video.owner_id == User.id
        ).join(
            Vote, Vote.video_id == Video.id
        ).filter(
            Video.status == VideoStatus.processed
        )
        
        if city:
            query = query.filter(User.city == city)
        
        results = query.group_by(
            User.id, User.first_name, User.last_name, User.city
        ).order_by(desc('vote_count')).limit(limit).all()
        
        ranking = []
        for position, result in enumerate(results, 1):
            ranking.append(RankingItem(
                position=position,
                username=f"{result.first_name} {result.last_name}",
                city=result.city,
                votes=result.vote_count
            ))
        
        return ranking

    @staticmethod
    def has_user_voted(db: Session, user_id: int, video_id: str) -> bool:
        """Check if user has voted for a video"""
        vote = db.query(Vote).filter(
            Vote.voter_id == user_id,
            Vote.video_id == video_id
        ).first()
        return vote is not None
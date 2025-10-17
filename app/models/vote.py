from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Foreign Keys
    voter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)

    # Relationships
    voter = relationship("User", back_populates="votes")
    video = relationship("Video", back_populates="votes")

    # Constraints
    __table_args__ = (
        UniqueConstraint('voter_id', 'video_id', name='unique_user_video_vote'),
    )
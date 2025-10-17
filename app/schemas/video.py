from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.video import VideoStatus


class VideoCreate(BaseModel):
    title: str


class VideoResponse(BaseModel):
    video_id: str
    title: str
    status: VideoStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    original_url: Optional[str] = None
    processed_url: Optional[str] = None
    votes: Optional[int] = 0

    class Config:
        from_attributes = True


class VideoListResponse(BaseModel):
    video_id: str
    title: str
    status: VideoStatus
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    processed_url: Optional[str] = None

    class Config:
        from_attributes = True


class VideoUploadResponse(BaseModel):
    message: str
    task_id: str


class VideoDeleteResponse(BaseModel):
    message: str
    video_id: str
from pydantic import BaseModel
from typing import Optional


class VoteResponse(BaseModel):
    message: str


class RankingItem(BaseModel):
    position: int
    username: str
    city: str
    votes: int


class PublicVideoResponse(BaseModel):
    video_id: str
    title: str
    username: str
    city: str
    processed_url: str
    votes: int

    class Config:
        from_attributes = True
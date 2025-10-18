import pytest


def test_get_public_videos_empty(client):
    """Test getting public videos when none exist"""
    response = client.get("/api/public/videos")
    assert response.status_code == 200
    assert response.json() == []


def test_get_public_videos_with_params(client):
    """Test getting public videos with pagination parameters"""
    response = client.get("/api/public/videos?limit=10&offset=0")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_vote_for_nonexistent_video(authenticated_client):
    """Test voting for a video that doesn't exist"""
    client, token_data = authenticated_client
    
    response = client.post("/api/public/videos/nonexistent-id/vote")
    assert response.status_code == 404
    assert "Video no encontrado" in response.json()["detail"]


def test_vote_unauthorized(client):
    """Test voting without authentication"""
    response = client.post("/api/public/videos/some-video-id/vote")
    assert response.status_code == 403


def test_get_rankings_empty(client):
    """Test getting rankings when no votes exist"""
    response = client.get("/api/public/rankings")
    assert response.status_code == 200
    assert response.json() == []


def test_get_rankings_with_city_filter(client):
    """Test getting rankings with city filter"""
    response = client.get("/api/public/rankings?city=Bogotá")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_rankings_with_limit(client):
    """Test getting rankings with limit parameter"""
    response = client.get("/api/public/rankings?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_vote_with_invalid_token(client):
    """Test voting with invalid token"""
    client.headers.update({
        "Authorization": "Bearer invalid-token"
    })
    
    response = client.post("/api/public/videos/some-video-id/vote")
    assert response.status_code == 401
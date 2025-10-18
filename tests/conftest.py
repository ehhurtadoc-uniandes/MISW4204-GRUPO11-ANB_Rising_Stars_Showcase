import pytest
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# Test database URL - use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Override settings for testing
os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

# Create test engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the database dependency
def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the override
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def client():
    """Create test client"""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "testuser@example.com",
        "first_name": "Test",
        "last_name": "User",
        "city": "Bogotá",
        "country": "Colombia",
        "password1": "testpassword123",
        "password2": "testpassword123"
    }


@pytest.fixture
def test_login_data():
    """Test login data"""
    return {
        "email": "testuser@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def authenticated_client(client, test_user_data, test_login_data):
    """Create authenticated client with token"""
    # Create user
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 201
    
    # Login to get token
    response = client.post("/api/auth/login", json=test_login_data)
    assert response.status_code == 200
    token_data = response.json()
    
    # Create client with auth headers
    client.headers.update({
        "Authorization": f"Bearer {token_data['access_token']}"
    })
    
    return client, token_data
import pytest
from app.core.security import create_access_token, verify_password, get_password_hash


def test_create_access_token():
    """Test JWT token creation"""
    email = "test@example.com"
    token = create_access_token(subject=email)
    
    assert isinstance(token, str)
    assert len(token) > 0


def test_password_hashing():
    """Test password hashing and verification"""
    password = "testpassword123"
    hashed = get_password_hash(password)
    
    assert isinstance(hashed, str)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_verify_password_with_wrong_password():
    """Test password verification with wrong password"""
    password = "testpassword123"
    wrong_password = "wrongpassword"
    hashed = get_password_hash(password)
    
    assert verify_password(wrong_password, hashed) is False
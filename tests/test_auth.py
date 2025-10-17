import pytest
from fastapi.testclient import TestClient


def test_signup_success(client, test_user_data):
    """Test successful user registration"""
    response = client.post("/api/auth/signup", json=test_user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["first_name"] == test_user_data["first_name"]
    assert data["last_name"] == test_user_data["last_name"]
    assert data["city"] == test_user_data["city"]
    assert data["country"] == test_user_data["country"]
    assert "id" in data
    assert data["is_active"] is True


def test_signup_duplicate_email(client, test_user_data):
    """Test registration with duplicate email"""
    # First registration
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 201
    
    # Duplicate registration
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 400
    assert "email ya está registrado" in response.json()["detail"]


def test_signup_password_mismatch(client, test_user_data):
    """Test registration with password mismatch"""
    user_data = test_user_data.copy()
    user_data["password2"] = "different_password"
    
    response = client.post("/api/auth/signup", json=user_data)
    assert response.status_code == 422  # Validation error


def test_signup_weak_password(client, test_user_data):
    """Test registration with weak password"""
    user_data = test_user_data.copy()
    user_data["password1"] = "123"
    user_data["password2"] = "123"
    
    response = client.post("/api/auth/signup", json=user_data)
    assert response.status_code == 422  # Validation error


def test_login_success(client, test_user_data, test_login_data):
    """Test successful login"""
    # First create user
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 201
    
    # Then login
    response = client.post("/api/auth/login", json=test_login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
    assert "expires_in" in data


def test_login_invalid_email(client, test_login_data):
    """Test login with invalid email"""
    response = client.post("/api/auth/login", json=test_login_data)
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


def test_login_invalid_password(client, test_user_data):
    """Test login with invalid password"""
    # Create user
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 201
    
    # Login with wrong password
    login_data = {
        "email": test_user_data["email"],
        "password": "wrongpassword"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Email o contraseña incorrectos" in response.json()["detail"]


def test_login_missing_fields(client):
    """Test login with missing fields"""
    response = client.post("/api/auth/login", json={"email": "test@example.com"})
    assert response.status_code == 422  # Validation error
    
    response = client.post("/api/auth/login", json={"password": "password"})
    assert response.status_code == 422  # Validation error
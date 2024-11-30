import pytest
from fastapi.testclient import TestClient
from fastapi.security import OAuth2PasswordRequestForm
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
from uuid import uuid4

from FastAPI_Services.main import app

client = TestClient(app)

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "testsecretkey")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "test-account")
    monkeypatch.setenv("SNOWFLAKE_USER", "test-user")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "test-password")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "test-db")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "test-schema")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "test-warehouse")

@pytest.fixture
def mock_dependencies(mock_env):
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_s3 = MagicMock()
    
    mock_conn.cursor.return_value = mock_cursor
    
    with patch("FastAPI_Services.main.get_snowflake_connection", return_value=mock_conn), \
         patch("FastAPI_Services.main.s3_client", mock_s3), \
         patch("FastAPI_Services.main.initialize_user_profiles_table"):
        yield mock_cursor, mock_s3, mock_conn

def test_register_user_success(mock_dependencies):
    mock_cursor, mock_s3, _ = mock_dependencies
    test_user_id = str(uuid4())
    mock_cursor.fetchone.side_effect = [
        None,  # No existing user
        (datetime.now(),)  # created_at timestamp
    ]
    
    files = {
        "resume": ("resume.pdf", BytesIO(b"resume content"), "application/pdf"),
        "cover_letter": ("cover.pdf", BytesIO(b"cover letter content"), "application/pdf")
    }
    form_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123"
    }
    
    response = client.post("/register", files=files, data=form_data)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert "resume_link" in response.json()
    assert "cover_letter_link" in response.json()

def test_register_user_duplicate_email(mock_dependencies):
    mock_cursor, _, _ = mock_dependencies
    mock_cursor.fetchone.return_value = ("test@example.com", "existinguser")
    
    files = {
        "resume": ("resume.pdf", BytesIO(b"content"), "application/pdf"),
        "cover_letter": ("cover.pdf", BytesIO(b"content"), "application/pdf")
    }
    form_data = {
        "email": "test@example.com",
        "username": "newuser",
        "password": "securepass123"
    }
    
    response = client.post("/register", files=files, data=form_data)
    assert response.status_code == 400


def test_login_invalid_credentials(mock_dependencies):
    mock_cursor, _, _ = mock_dependencies
    mock_cursor.fetchone.return_value = None
    
    form_data = {
        "username": "wronguser",
        "password": "wrongpass"
    }
    
    response = client.post("/login", data=form_data)
    assert response.status_code == 401

def test_unauthorized_access(mock_dependencies):
    response = client.get("/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401


def test_register_missing_files(mock_dependencies):
    form_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123"
    }
    
    response = client.post("/register", data=form_data)
    assert response.status_code == 422
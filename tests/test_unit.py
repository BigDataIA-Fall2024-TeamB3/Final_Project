import pytest
import time
from datetime import timedelta
from FastAPI_Services.main import hash_password, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import jwt, ExpiredSignatureError

def test_hash_password():
    password = "securepassword"
    hashed = hash_password(password)
    assert verify_password(password, hashed)

def test_verify_password():
    password = "mypassword"
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)

def test_create_access_token_expiry():
    # Create a token with a very short lifespan
    data = {"sub": "testuser"}
    token = create_access_token(data, timedelta(seconds=1))  # Token expires in 1 second

    # Wait for 2 seconds to ensure the token is expired
    time.sleep(2)

    # Attempt to decode the token and expect an ExpiredSignatureError
    with pytest.raises(ExpiredSignatureError):
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

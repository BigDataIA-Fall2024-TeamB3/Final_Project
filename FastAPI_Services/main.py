from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator, ValidationError
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext
import boto3
import os
from uuid import uuid4, UUID
from typing import Optional
from snowflake.connector import connect, ProgrammingError
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import json
from io import BytesIO

# Load environment variables
load_dotenv()

# Environment variables for database, AWS, and authentication
# Snowflake connection details
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

# Initialize AWS S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

# Security and hashing utilities
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Query to create user_profiles table
CREATE_USER_PROFILES_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS user_profiles (
    id STRING PRIMARY KEY,                        -- Randomly generated UUID
    username STRING UNIQUE NOT NULL,             -- Username
    email STRING UNIQUE NOT NULL,                -- Email
    hashed_password STRING NOT NULL,             -- Hashed password
    resume_link STRING,                          -- Resume link (S3 URL)
    cover_letter_link STRING,                    -- Cover letter link (S3 URL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Timestamp when record was created
    updated_at TIMESTAMP                          -- Timestamp when record was last updated
);
"""


# Snowflake connection function
def get_snowflake_connection():
    try:
        return connect(
            user=SNOWFLAKE_USER,
            password=SNOWFLAKE_PASSWORD,
            account=SNOWFLAKE_ACCOUNT,
            database=SNOWFLAKE_DATABASE,
            schema=SNOWFLAKE_SCHEMA,
            warehouse=SNOWFLAKE_WAREHOUSE,
        )
    except ProgrammingError as e:
        raise HTTPException(status_code=500, detail=f"Snowflake connection error: {e}")

# Create the user_profiles table if it doesn't exist
def initialize_user_profiles_table():
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        cur.execute(CREATE_USER_PROFILES_TABLE_QUERY)
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user_profiles table: {e}")
    finally:
        cur.close()
        conn.close()

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception

    # Retrieve user from database
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()
        query = f"SELECT id, email, resume_link, cover_letter_link, created_at, updated_at FROM {SNOWFLAKE_SCHEMA}.user_profiles WHERE username = %(username)s"
        cur.execute(query, {'username': token_data.username})
        user = cur.fetchone()
        if user is None:
            raise credentials_exception
        user_out = UserOut(
            id=user[0],
            username=token_data.username,
            email=user[1],
            resume_link=user[2],
            cover_letter_link=user[3],
            created_at=user[4],
            updated_at=user[5],
        )
        return user_out
    except Exception as e:
        print(f"Error retrieving user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error.")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

# Hashing and authentication functions
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str):
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()

        # Use parameterized query to prevent SQL injection
        query = f"SELECT id, hashed_password FROM {SNOWFLAKE_SCHEMA}.user_profiles WHERE username = %(username)s"
        cur.execute(query, {'username': username})
        user = cur.fetchone()
        if user and verify_password(password, user[1]):
            return {"id": user[0], "username": username}
        return None
    except Exception as e:
        print(f"Error during authentication: {str(e)}")
        return None
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @field_validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric.")
        if len(v) < 3 or len(v) > 10:
            raise ValueError("Username must be between 3 and 30 characters.")
        return v

    @field_validator('password')
    def password_strength(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    resume_link: Optional[str]
    cover_letter_link: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_user_profiles_table()  # Ensure the table is created on startup
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/register", response_model=UserOut)
async def register_user(
    email: EmailStr = Form(..., description="User's email address"),
    username: str = Form(..., description="Desired username"),
    password: str = Form(..., description="User's password"),
    resume: UploadFile = File(...),
    cover_letter: UploadFile = File(...)
):
    try:
        resume_content = await resume.read()
        cover_letter_content = await cover_letter.read()

        # Validate `user` fields using Pydantic model
        try:
            user_model = UserCreate(email=email, username=username, password=password)
        except ValidationError as ve:
            error_details = [{"loc": err["loc"], "msg": err["msg"]} for err in ve.errors()]
            raise HTTPException(status_code=400, detail={"validation_errors": error_details})
        # Validate `user` fields using Pydantic model

        user_model = UserCreate(email=email, username=username, password=password)

        # Validate file uploads
        if not resume or not cover_letter:
            raise HTTPException(status_code=400, detail="Both 'resume' and 'cover_letter' files are required.")

        # **Check if the email already exists**
        conn = get_snowflake_connection()
        cur = conn.cursor()
        
        check_user_query = """
        SELECT email, username FROM user_profiles WHERE email = %(email)s OR username = %(username)s
        """
        cur.execute(check_user_query, {'email': user_model.email, 'username': user_model.username})
        existing_user = cur.fetchone()

        if existing_user:
            existing_email, existing_username = existing_user

            if existing_email.lower() == user_model.email.lower():
                raise HTTPException(status_code=400, detail="A user with this email already exists.")
            elif existing_username.lower() == user_model.username.lower():
                raise HTTPException(status_code=400, detail="A user with this username already exists.")
            else:
                # This case should not occur but added for completeness
                raise HTTPException(status_code=400, detail="A user with this email or username already exists.")
        
        # Proceed with file uploads and user creation
        hashed_password = hash_password(user_model.password)
        user_id = str(uuid4())
        folder_name = f"user-profiles/{user_id}/"

        resume_key = f"{folder_name}resume.pdf"
        cover_letter_key = f"{folder_name}cover_letter.pdf"

        resume_stream = BytesIO(resume_content)
        cover_letter_stream = BytesIO(cover_letter_content)
        
        # Upload files to S3 (ensure s3_client is properly initialized)
        s3_client.upload_fileobj(
            resume_stream,
            AWS_S3_BUCKET_NAME,
            resume_key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )
        
        s3_client.upload_fileobj(
            cover_letter_stream,
            AWS_S3_BUCKET_NAME,
            cover_letter_key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )

        resume_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{resume_key}"
        cover_letter_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{cover_letter_key}"

        # **Insert user data into Snowflake with updated_at set to NULL**
        insert_query = """
        INSERT INTO user_profiles 
            (id, username, email, hashed_password, resume_link, cover_letter_link, created_at, updated_at)
        VALUES
            (%(id)s, %(username)s, %(email)s, %(hashed_password)s, %(resume_link)s, %(cover_letter_link)s, current_timestamp(), NULL)
        """
        
        params = {
            'id': user_id,
            'username': user_model.username,
            'email': user_model.email,
            'hashed_password': hashed_password,
            'resume_link': resume_url,
            'cover_letter_link': cover_letter_url
        }

        cur.execute(insert_query, params)
        conn.commit()

        # Retrieve created_at timestamp; updated_at will be None
        cur.execute(
            "SELECT created_at FROM user_profiles WHERE id = %(id)s",
            {'id': user_id}
        )        
        
        result = cur.fetchone()
        if result:
            created_at = result[0]
            updated_at = None  # Since updated_at is NULL during registration
        else:
            raise HTTPException(status_code=500, detail="User creation failed.")

        return {
            "id": user_id,
            "username": user_model.username,
            "email": user_model.email,
            "resume_link": resume_url,
            "cover_letter_link": cover_letter_url,
            "created_at": created_at,
            "updated_at": updated_at
        }

    except HTTPException as e:
        # Re-raise HTTPExceptions to be handled by FastAPI
        raise e

    except Exception as e:
        print(f"Error details: {str(e)}")  # Detailed error logging
        raise HTTPException(status_code=500, detail="An error occurred while registering the user.")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()


# Login endpoint
@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Get current user endpoint
@app.get("/users/me", response_model=UserOut)
async def read_users_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@app.put("/users/me/files", response_model=UserOut)
async def update_user_files(
    resume: Optional[UploadFile] = File(None, description="Updated resume file"),
    cover_letter: Optional[UploadFile] = File(None, description="Updated cover letter file"),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Updates the logged-in user's resume and/or cover letter.
    """
    try:
        conn = get_snowflake_connection()
        cur = conn.cursor()

        folder_name = f"user-profiles/{current_user.id}/"
        updates = {}
        if resume:
            # Read resume content and upload to S3
            resume_content = await resume.read()
            resume_key = f"{folder_name}resume.pdf"
            resume_stream = BytesIO(resume_content)
            s3_client.upload_fileobj(
                resume_stream,
                AWS_S3_BUCKET_NAME,
                resume_key,
                ExtraArgs={"ContentType": "application/pdf"}
            )
            updates["resume_link"] = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{resume_key}"

        if cover_letter:
            # Read cover letter content and upload to S3
            cover_letter_content = await cover_letter.read()
            cover_letter_key = f"{folder_name}cover_letter.pdf"
            cover_letter_stream = BytesIO(cover_letter_content)
            s3_client.upload_fileobj(
                cover_letter_stream,
                AWS_S3_BUCKET_NAME,
                cover_letter_key,
                ExtraArgs={"ContentType": "application/pdf"}
            )
            updates["cover_letter_link"] = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{cover_letter_key}"

        if not updates:
            raise HTTPException(status_code=400, detail="No files provided for update.")

        # Construct the SQL update query dynamically
        update_query = f"""
        UPDATE {SNOWFLAKE_SCHEMA}.user_profiles
        SET updated_at = current_timestamp()
        """
        update_params = {}
        for key, value in updates.items():
            update_query += f", {key} = %({key})s"
            update_params[key] = value
        update_query += " WHERE id = %(id)s"
        update_params["id"] = str(current_user.id)

        # Execute the update query
        cur.execute(update_query, update_params)
        conn.commit()

        # Retrieve updated user data
        cur.execute(
            f"""
            SELECT id, username, email, resume_link, cover_letter_link, created_at, updated_at 
            FROM {SNOWFLAKE_SCHEMA}.user_profiles
            WHERE id = %(id)s
            """,
            {"id": str(current_user.id)}
        )
        user = cur.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found after update.")

        # Return updated user details
        return UserOut(
            id=user[0],
            username=user[1],
            email=user[2],
            resume_link=user[3],
            cover_letter_link=user[4],
            created_at=user[5],
            updated_at=user[6],
        )

    except HTTPException as e:
        raise e

    except Exception as e:
        print(f"Error details: {str(e)}")  # Log error details
        raise HTTPException(status_code=500, detail="An error occurred while updating files.")

    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

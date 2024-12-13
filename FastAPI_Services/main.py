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

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import pandas as pd
import snowflake.connector
import ast

# Load environment variables
load_dotenv()

# Environment variables for database, AWS, and authentication
# Snowflake connection details
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_USER_PROFILES_DB = os.getenv("SNOWFLAKE_USER_PROFILES_DB")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

import os

if "OPENAI_API_KEY" not in os.environ:
    raise ValueError("The OPENAI_API_KEY environment variable must be set.")

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
            database=SNOWFLAKE_USER_PROFILES_DB,
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

# Retrieve Snowflake connection details from environment variables
account = os.getenv('SNOWFLAKE_ACCOUNT')
user = os.getenv('SNOWFLAKE_USER')
password = os.getenv('SNOWFLAKE_PASSWORD')
database = os.getenv('SNOWFLAKE_JOBSDB')
schema = os.getenv('SNOWFLAKE_SCHEMA')
warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')

# Pydantic models for request/response
class JobSearchResponse(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    parsed_query: Dict[str, List[str]]
    sql: str

class ErrorResponse(BaseModel):
    status: str
    message: str
    parsed_query: Dict[str, List[str]]


# TypedDict for Agent State
class AgentState(TypedDict):
    natural_query: str
    parsed_query: Dict[str, List[str]]
    sql: str
    results: str
    final_output: str

    # Initialize LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def parse_natural_query(state: AgentState) -> AgentState:
    parser_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at parsing job search queries. Extract the column names 
        and their corresponding values based on the following schema map:
        {{
            "role": "SEARCH_QUERY",
            "job": "SEARCH_QUERY",
            "title": "TITLE",
            "company": "COMPANY",
            "location": "LOCATION",
            "description": "DESCRIPTION",
            "posted_date": "POSTED_DATE"
        }}

        Include relevant synonyms for each value from this synonym map:
        {{
            "SEARCH_QUERY": {{
                "data": [
                    "data", "data engineer", "data scientist", 
                    "data analyst", "data specialist", "data science", 
                    "data engineering", "data analytics"
                ],
                "data engineer": ["data engineer", "data engineering"],
                "data scientist": ["data scientist", "data science", "machine learning scientist"],
                "AI engineer": ["AI engineer", "artificial intelligence engineer"],
                "machine learning engineer": ["machine learning engineer", "ML engineer"],
                "data analyst": ["data analyst", "data analytics"],
                "AI/ML engineer": ["AI/ML engineer", "artificial intelligence/machine learning engineer"],
                "software engineer": ["software engineer", "software developer", "software programming"],
                "devops engineer": ["devops engineer", "site reliability engineer", "SRE"],
                "full stack engineer": ["full stack engineer", "full stack developer", "front end and back end developer"]
            }}
        }}

        If the query does not mention a specific role, job, title, company, or location explicitly (e.g., "give me jobs"), 
        or is irrelevant, return:
        {{
            'role': [], 
            'company': [], 
            'location': [], 
            'title': [], 
            'description': [], 
            'posted_date': []
        }}.

        Return a valid Python dictionary where:
        - Keys are column names from the schema map.
        - Values are lists of terms to search for, including synonyms.
        Format the output as valid Python syntax with no extra text or code blocks.
        Example: {{'column_name': ['value1', 'value2']}}"""),
        ("user", "Parse this job search query: {natural_query}")
    ])

    
    chain = parser_prompt | llm
    response = chain.invoke({
        "natural_query": state["natural_query"]
    })
    
    try:
        content = response.content if hasattr(response, 'content') else response
        print(f"Raw LLM response: {content}")
        
        sanitized_response = content.strip("```python").strip("```").strip()
        parsed = ast.literal_eval(sanitized_response)
        
        if isinstance(parsed, dict) and all(isinstance(v, list) for v in parsed.values()):
            state["parsed_query"] = parsed
        else:
            raise ValueError("Parsed query does not return valid lists of terms.")
    except Exception as e:
        state["parsed_query"] = {"error": f"Parsing error: {str(e)}"}
    
    print(f"Parsed query: {state['parsed_query']}")
    return state


def write_sql_query(state: AgentState) -> AgentState:
    conditions = []
    schema_to_table_map = {
        "role": "SEARCH_QUERY",
        "job": "SEARCH_QUERY",
        "title": "TITLE",
        "company": "COMPANY",
        "location": "LOCATION",
        "description": "DESCRIPTION",
        "posted_date": "POSTED_DATE"
    }
    
    # Consolidate and deduplicate conditions for fields mapping to the same column
    column_conditions = {}
    for schema_field, table_column in schema_to_table_map.items():
        terms = state["parsed_query"].get(schema_field, [])
        if terms:  # Only add conditions for non-empty terms
            if table_column not in column_conditions:
                column_conditions[table_column] = set()  # Use a set to avoid duplicates
            column_conditions[table_column].update(terms)  # Add terms to the set

    # Generate SQL WHERE clause
    for table_column, terms in column_conditions.items():
        if terms:  # Avoid empty conditions
            term_conditions = [f"{table_column} ILIKE '%{term}%'" for term in sorted(terms)]
            conditions.append(f"({' OR '.join(term_conditions)})")
    
    if conditions:
        where_clause = " AND ".join(conditions)
        sql_query = f"SELECT * FROM JOBLISTINGS WHERE {where_clause}"
    else:
        sql_query = "SELECT * FROM JOBLISTINGS"  # Default query if no conditions
    
    state["sql"] = sql_query
    print(f"Generated SQL: {state['sql']}")
    return state

# Execute Query
def execute_query(state: AgentState) -> AgentState:
    try:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            database=database,
            schema=schema,
            warehouse=warehouse
        )
        cursor = conn.cursor()
        cursor.execute(state["sql"])
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()
        state["results"] = pd.DataFrame(results, columns=columns)
        cursor.close()
        conn.close()
    except Exception as e:
        state["results"] = f"Error: {str(e)}"
    return state

# Format Output
def format_output(state: AgentState) -> AgentState:
    if isinstance(state["results"], pd.DataFrame):
        state["final_output"] = {
            "status": "success",
            "parsed_query": state["parsed_query"],
            "data": state["results"].to_dict(orient="records"),
            "sql": state["sql"]
        }
    else:
        state["final_output"] = {
            "status": "error",
            "message": "No results found or error in query.",
            "parsed_query": state["parsed_query"]
        }
    return state


# Create Workflow
def create_workflow():
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("parse_query", parse_natural_query)
    workflow.add_node("write_query", write_sql_query)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("format_output", format_output)
    
    # Add edges
    workflow.add_edge("parse_query", "write_query")
    workflow.add_edge("write_query", "execute_query")
    workflow.add_edge("execute_query", "format_output")
    
    workflow.set_entry_point("parse_query")
    workflow.set_finish_point("format_output")
    
    return workflow.compile()

# Add this to your existing endpoint
@app.get("/search/jobs", response_model=JobSearchResponse)
async def search_job_listings(
    query: str,
    current_user: UserOut = Depends(get_current_user)
):
    try:
        graph = create_workflow()
        initial_state = {
            "natural_query": query,
            "parsed_query": {},
            "sql": "",
            "results": "",
            "final_output": ""
        }
        result = graph.invoke(initial_state)
        
        if result["final_output"]["status"] == "error":
            raise HTTPException(
                status_code=400,
                detail=result["final_output"]["message"]
            )
            
        return result["final_output"]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
# Snowflake connection function for USER_RESULTS_DB
def get_user_results_db_connection():
    try:
        return connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            database=os.getenv("SNOWFLAKE_USER_RESULTS_DB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        )
    except ProgrammingError as e:
        raise HTTPException(status_code=500, detail=f"Snowflake connection error for USER_RESULTS_DB: {e}")
    
@app.post("/jobs/save")
async def save_job(
    job_id: str = Form(...),
    title: str = Form(None),
    company: str = Form(None),
    location: str = Form(None),
    description: str = Form(None),
    job_highlights: str = Form(None),
    apply_links: str = Form(None),
    posted_date: str = Form(None),
    status: str = Form("Not Applied"),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Save job details for the logged-in user.
    Creates a new table for the user based on their UUID if it does not already exist.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor()

        # Ensure the UUID is converted to a string before replacing characters
        table_name = f"user_{str(current_user.id).replace('-', '_')}"

        # Create table if it doesn't exist
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            job_id STRING NOT NULL,                -- Unique Job ID
            title STRING,                          -- Job title
            company STRING,                        -- Company name
            location STRING,                       -- Job location
            description TEXT,                      -- Job description
            job_highlights TEXT,                   -- Job highlights
            apply_links STRING,                    -- Application link
            posted_date STRING,                    -- Job posting date
            status STRING DEFAULT 'Not Applied',   -- Application status
            feedback TEXT,                         -- Feedback on the application
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Creation timestamp
            updated_at TIMESTAMP,                  -- Update timestamp
            PRIMARY KEY (job_id)                   -- Primary key for unique jobs
        );
        """
        cur.execute(create_table_query)

        # Use a MERGE statement for upserting
        merge_query = f"""
        MERGE INTO {table_name} AS target
        USING (SELECT
            %(job_id)s AS job_id,
            %(title)s AS title,
            %(company)s AS company,
            %(location)s AS location,
            %(description)s AS description,
            %(job_highlights)s AS job_highlights,
            %(apply_links)s AS apply_links,
            %(posted_date)s AS posted_date,
            %(status)s AS status,
            CURRENT_TIMESTAMP AS updated_at
        ) AS source
        ON target.job_id = source.job_id
        WHEN MATCHED THEN UPDATE SET
            title = source.title,
            company = source.company,
            location = source.location,
            description = source.description,
            job_highlights = source.job_highlights,
            apply_links = source.apply_links,
            posted_date = source.posted_date,
            status = source.status,
            updated_at = source.updated_at
        WHEN NOT MATCHED THEN INSERT (
            job_id, title, company, location, description, 
            job_highlights, apply_links, posted_date, status, created_at, updated_at
        )
        VALUES (
            source.job_id, source.title, source.company, source.location, source.description,
            source.job_highlights, source.apply_links, source.posted_date, source.status, CURRENT_TIMESTAMP, NULL
        );
        """
        params = {
            'job_id': job_id,
            'title': title,
            'company': company,
            'location': location,
            'description': description,
            'job_highlights': job_highlights,
            'apply_links': apply_links,
            'posted_date': posted_date,
            'status': status
        }

        cur.execute(merge_query, params)
        conn.commit()

        return {"message": f"Job saved successfully in table '{table_name}'."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving job: {e}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

@app.get("/jobs/saved", response_model=list)
async def get_saved_jobs(current_user: UserOut = Depends(get_current_user)):
    """
    Fetch all saved jobs for the logged-in user.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor()

        # Dynamically generate the table name
        table_name = f"user_{str(current_user.id).replace('-', '_')}"

        # Query to fetch all jobs
        fetch_jobs_query = f"SELECT * FROM {table_name};"
        cur.execute(fetch_jobs_query)
        columns = [col[0] for col in cur.description]  # Get column names
        rows = cur.fetchall()

        # Format results as a list of dictionaries
        saved_jobs = [dict(zip(columns, row)) for row in rows]

        return saved_jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching saved jobs: {e}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

@app.put("/jobs/update-status")
async def update_job_status(
    job_id: str = Form(...),
    new_status: str = Form(...),
    current_user: UserOut = Depends(get_current_user)
):
    """
    Update the status of a saved job for the logged-in user.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor() 

        # Dynamically generate the table name
        table_name = f"user_{str(current_user.id).replace('-', '_')}"

        # Update query
        update_query = f"""
        UPDATE {table_name}
        SET status = %(new_status)s, updated_at = CURRENT_TIMESTAMP
        WHERE job_id = %(job_id)s;
        """
        params = {'job_id': job_id, 'new_status': new_status}
        cur.execute(update_query, params)
        conn.commit()

        return {"message": "Job status updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating job status: {e}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

@app.delete("/jobs/{job_id}", response_model=dict)
async def delete_job(job_id: str, current_user: UserOut = Depends(get_current_user)):
    """
    Endpoint to delete a saved job by job_id for the logged-in user.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor()

        # Generate the user's table name dynamically based on their UUID
        table_name = f"user_{str(current_user.id).replace('-', '_')}"  # Convert UUID to string first

        # Check if the table exists
        check_table_query = f"""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = '{table_name.upper()}' 
        AND TABLE_SCHEMA = '{os.getenv("SNOWFLAKE_SCHEMA").upper()}';
        """
        cur.execute(check_table_query)
        if cur.fetchone()[0] == 0:
            raise HTTPException(status_code=404, detail="No saved jobs found for this user.")

        # Delete the job
        delete_query = f"DELETE FROM {table_name} WHERE job_id = %s"
        cur.execute(delete_query, (job_id,))
        conn.commit()

        # Check if the job was deleted
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found or already deleted.")

        return {"message": "Job deleted successfully."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

import fitz 

def extract_text_from_pdf(pdf_content: bytes) -> str:
    text = ""
    try:
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")
    return text

import requests

@app.post("/feedback")
async def generate_feedback(
    job_id: str,
    description: str,
    highlights: str,
    current_user: UserOut = Depends(get_current_user),
):
    """
    Generate detailed feedback for the user's resume and cover letter based on the job description and highlights.
    """
    try:
        # Fetch the publicly accessible links for the resume and cover letter
        resume_link = current_user.resume_link
        cover_letter_link = current_user.cover_letter_link
        if not resume_link or not cover_letter_link:
            raise HTTPException(status_code=400, detail="Resume or cover letter not found.")

        # Fetch the files from the public URLs
        resume_response = requests.get(resume_link)
        cover_letter_response = requests.get(cover_letter_link)

        # Check for successful retrieval
        if resume_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch resume from the provided URL.")
        if cover_letter_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch cover letter from the provided URL.")

        # Extract text from PDFs
        resume_text = extract_text_from_pdf(resume_response.content)
        cover_letter_text = extract_text_from_pdf(cover_letter_response.content)

        # Debug: Log extracted content (optional, remove in production)
        print("=== Extracted Resume Content ===")
        print(resume_text)
        print("\n=== Extracted Cover Letter Content ===")
        print(cover_letter_text)

        # Prepare context for the LLM
        context = {
            "job_description": description,
            "job_highlights": highlights,
            "resume_text": resume_text,
            "cover_letter_text": cover_letter_text,
        }

        # Create a prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert career advisor."),
            ("user", """
                Job Description:
                {job_description}

                Job Highlights:
                {job_highlights}

                Candidate's Resume:
                {resume_text}

                Candidate's Cover Letter:
                {cover_letter_text}

                Instructions:
                - Validate the document type before providing feedback:
                    - If the content is not a resume or cover letter, respond with: "The provided content is not relevant for resume or cover letter feedback. Please provide relevant documents."
                - Provide detailed feedback on the resume and cover letter separately if valid:
                    - For the resume:
                        - Assess how well it aligns with the job description and highlights.
                        Example: "The resume lists project management experience, which aligns well with the job requirement for managing cross-functional teams. However, it lacks specific details about the size or scope of projects managed. Include quantifiable metrics like team size or budget managed to strengthen alignment."
                        - Provide specific suggestions for improvement, such as tailoring skills, optimizing keywords, or restructuring sections for clarity.
                        Example: "The 'Skills' section could include keywords directly from the job description, such as 'Agile methodology' or 'data-driven decision making.'"
                        - Highlight any missing sections or areas for enhancement (e.g., education, work experience, or technical skills).
                        Example: "The resume does not include a 'Technical Skills' section, which is crucial for this role. Add a section highlighting your proficiency with tools like Jira, Tableau, or SQL."
                        - Provide a relevance score (0-100) indicating how well the resume matches the job requirements.
                        Example: "Relevance Score: 85/100. The resume aligns well overall but could benefit from more tailored keywords and quantifiable achievements."
                    - For the cover letter:
                        - Evaluate its tone, structure, and alignment with the job description and highlights.
                        Example: "The tone of the cover letter is professional but lacks enthusiasm for the specific role. Adding a sentence about why you are excited about this company's mission would improve it."
                        - Suggest ways to make the cover letter more compelling and tailored, such as emphasizing achievements or customizing the tone to the company culture.
                        Example: "Mention your success in reducing project timelines by 20% in your last role to demonstrate your ability to meet the job's emphasis on efficiency."
                        - Highlight areas where it lacks personalization or fails to address key job requirements.
                        Example: "The cover letter is generic and does not mention the company's recent product launch, which is a key highlight. Include a sentence demonstrating your knowledge of this and how your skills can contribute to its success."
                    - If either the resume or cover letter has insufficient content or is overly generic, provide constructive feedback to address this.
                        Example: "The resume provides only a list of job titles without describing responsibilities or achievements. Include bullet points that explain your impact in each role."

                Focus on actionable feedback that helps the candidate improve alignment with the job.
            """),
        ])

        # Initialize LangChain LLM
        chat_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        response = chat_llm.invoke(prompt_template.format(**context))

        return {"feedback": response.content}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    

@app.post("/chat-feedback")
async def chat_feedback(
    document_type: str = Form(..., description="Type of document (resume or cover letter)"),
    question: str = Form(..., description="User's specific question"),
    description: str = Form(..., description="Job description for context"),
    highlights: str = Form(..., description="Job highlights for context"),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Generate feedback for a specific question based on the user's selected document.
    """
    try:
        # Get public resume and cover letter links
        if document_type == "resume":
            document_link = current_user.resume_link
        elif document_type == "cover_letter":
            document_link = current_user.cover_letter_link
        else:
            raise HTTPException(status_code=400, detail="Invalid document type.")

        if not document_link:
            raise HTTPException(status_code=400, detail="Selected document not found.")

        # Fetch the document content
        document_response = requests.get(document_link)
        if document_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch the document.")

        document_text = extract_text_from_pdf(document_response.content)

        # Prepare context for the LLM
        context = {
            "job_description": description,
            "job_highlights": highlights,
            "document_text": document_text,
            "question": question,
        }
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a career coach specializing in job applications."),
            ("user", """
                Job Description:
                {job_description}

                Job Highlights:
                {job_highlights}

                Selected Document Content:
                {document_text}

                Question:
                {question}

                Instructions:
                - If the document content is a resume:
                    - Provide detailed suggestions and improvements based on the alignment with the job description and highlights.
                    - Highlight specific areas that can be improved, such as tailoring skills, optimizing keywords, or structuring the resume for clarity and relevance.
                    - Provide a relevance score (0-100) indicating how well the resume matches the job requirements, based on factors like skills, experience, and alignment with job highlights.
                - If the document content is a cover letter:
                    - Provide detailed suggestions and improvements based on how well it aligns with the job description and highlights.
                    - Suggest ways to make the cover letter more compelling and tailored, such as emphasizing achievements or aligning the tone with the company culture.
                - If the document content is irrelevant (not a resume or cover letter):
                    - Respond with: "The provided content is not relevant for resume or cover letter feedback. Please provide relevant documents."
                - If the user asks anything irrelevant (not related to job applications, resumes, or cover letters):
                    - Respond with: "The question is not related to job applications, resumes, or cover letters. I can only assist with these topics."
                - Address edge cases such as:
                    - Missing key sections in the resume (e.g., education, work experience).
                    - Overly generic cover letters that lack customization.
                    - Documents with insufficient content for evaluation.
                - Focus feedback specifically on how the document content can better align with the job requirements and make a stronger impact.

                Provide your response accordingly.
            """),
        ])

        # Generate response using LangChain LLM
        chat_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        response = chat_llm.invoke(prompt_template.format(**context))

        return {"response": response.content}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


class SaveFeedbackRequest(BaseModel):
    job_id: str
    feedback: str

@app.post("/jobs/save-feedback")
async def save_feedback(
    feedback_request: SaveFeedbackRequest,
    current_user: UserOut = Depends(get_current_user),
):
    """
    Save feedback to the logged-in user's saved jobs table.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor()

        # Get the table name for the current user
        table_name = f"user_{str(current_user.id).replace('-', '_')}"
        
        # Update the feedback for the specific job
        update_query = f"""
        UPDATE {table_name}
        SET feedback = %(feedback)s, updated_at = CURRENT_TIMESTAMP
        WHERE job_id = %(job_id)s
        """
        params = {
            "job_id": feedback_request.job_id,
            "feedback": feedback_request.feedback,
        }
        cur.execute(update_query, params)
        conn.commit()

        return {"message": "Feedback saved successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving feedback: {str(e)}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

# Snowflake connection function
def get_snowflake_joblistings_connection():
    try:
        return connect(
            user = os.getenv("SNOWFLAKE_USER"),
            password = os.getenv("SNOWFLAKE_PASSWORD"),
            account = os.getenv("SNOWFLAKE_ACCOUNT"),
            database = os.getenv("SNOWFLAKE_JOBSDB"),
            schema = os.getenv("SNOWFLAKE_SCHEMA"),
            warehouse = os.getenv("SNOWFLAKE_WAREHOUSE"),
        )
    except ProgrammingError as e:
        raise HTTPException(status_code=500, detail=f"Snowflake connection error: {e}")
 
@app.get("/jobs/listings", response_model=list)
async def get_job_listings(current_user: UserOut = Depends(get_current_user)):
    """
    Fetch all job listings for authenticated users.
    """
    try:
        # Establish Snowflake connection
        conn = get_snowflake_joblistings_connection()
        cur = conn.cursor()

        # Query to fetch all job listings
        fetch_listings_query = "SELECT * FROM JOBLISTINGS;"
        cur.execute(fetch_listings_query)
        columns = [col[0] for col in cur.description]  # Get column names
        rows = cur.fetchall()

        # Format results as a list of dictionaries
        job_listings = [dict(zip(columns, row)) for row in rows]

        return job_listings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching job listings: {e}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

@app.get("/users/jobs", response_model=list)
async def get_user_jobs(current_user: UserOut = Depends(get_current_user)):
    """
    Fetch the entire table of saved jobs for the logged-in user.
    """
    try:
        conn = get_user_results_db_connection()
        cur = conn.cursor()

        # Dynamically create the user-specific table name
        table_name = f"user_{str(current_user.id).replace('-', '_')}"

        # Query all rows from the user's table
        fetch_query = f"SELECT * FROM {table_name};"
        cur.execute(fetch_query)
        rows = cur.fetchall()
        columns = [col[0] for col in cur.description]

        # Convert rows to a list of dictionaries
        jobs = [dict(zip(columns, row)) for row in rows]

        return jobs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user jobs: {str(e)}")
    finally:
        if "cur" in locals() and cur:
            cur.close()
        if "conn" in locals() and conn:
            conn.close()

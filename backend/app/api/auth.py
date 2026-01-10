from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.models.snowflake_db import SnowflakeHelper
from app.models.schemas import UserCreate, UserResponse, Token, UserLogin
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user_snowflake,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter()

@router.post("/register")
async def register(user: UserCreate):
    """Register a new user"""
    # Check if user exists
    existing_user = SnowflakeHelper.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = SnowflakeHelper.insert_user(
        email=user.email,
        full_name=user.full_name,
        hashed_password=get_password_hash(user.password)
    )
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Get created user
    db_user = SnowflakeHelper.get_user_by_id(user_id)
    
    return {
        "id": db_user['ID'],
        "email": db_user['EMAIL'],
        "full_name": db_user['FULL_NAME'],
        "created_at": db_user['CREATED_AT']
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and receive access token"""
    # Get user by email
    user = SnowflakeHelper.get_user_by_email(form_data.username)  # username is email
    
    if not user or not verify_password(form_data.password, user['HASHED_PASSWORD']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['EMAIL'], "user_id": user['ID']},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user_snowflake)):
    """Get current user information"""
    return {
        "id": current_user['ID'],
        "email": current_user['EMAIL'],
        "full_name": current_user['FULL_NAME'],
        "created_at": current_user['CREATED_AT']
    }

@router.post("/logout")
async def logout():
    """Logout endpoint (client should remove token)"""
    return {"message": "Successfully logged out"}

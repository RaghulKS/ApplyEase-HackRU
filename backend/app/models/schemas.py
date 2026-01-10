from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Profile Schemas
class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[float] = None

class Experience(BaseModel):
    company: str
    position: str
    description: str
    start_date: str
    end_date: Optional[str] = None
    current: bool = False

class ProfileUpdate(BaseModel):
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    education: Optional[List[Education]] = None
    experience: Optional[List[Experience]] = None
    skills: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None

class ProfileResponse(ProfileUpdate):
    id: int
    user_id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Resume Schemas
class ResumeUpload(BaseModel):
    filename: str
    content: str  # Base64 encoded file content
    is_primary: bool = False

class ResumeResponse(BaseModel):
    id: int
    filename: str
    parsed_content: Optional[Dict[str, Any]]
    is_primary: bool
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# Application Schemas
class ApplicationCreate(BaseModel):
    company_name: str
    position: str
    job_url: Optional[str] = None
    application_url: Optional[str] = None
    notes: Optional[str] = None

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    submission_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    submitted_at: Optional[datetime] = None

class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    position: str
    job_url: Optional[str]
    application_url: Optional[str]
    status: str
    submission_data: Optional[Dict[str, Any]]
    notes: Optional[str]
    submitted_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Field Detection Schemas
class FieldDetectionRequest(BaseModel):
    fields: List[Dict[str, Any]]  # List of form fields with their properties
    url: Optional[str] = None

class FieldDetectionResponse(BaseModel):
    classified_fields: List[Dict[str, Any]]
    suggestions: Dict[str, Any]

# Chatbot Schemas
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    field_context: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    field_info: Dict[str, Any]
    resume_context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None
    confidence: float = 1.0

# Saved Response Schemas
class SavedResponseCreate(BaseModel):
    field_type: str
    field_label: Optional[str] = None
    response: str
    company: Optional[str] = None

class SavedResponseResponse(BaseModel):
    id: int
    field_type: str
    field_label: Optional[str]
    response: str
    company: Optional[str]
    usage_count: int
    created_at: datetime
    last_used: Optional[datetime]
    
    class Config:
        from_attributes = True

# Google Sheets Integration
class SheetUpdateRequest(BaseModel):
    application_id: int
    data: Dict[str, Any]

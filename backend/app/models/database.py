from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/data/applyease.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    resumes = relationship("Resume", back_populates="user")
    applications = relationship("Application", back_populates="user")
    saved_responses = relationship("SavedResponse", back_populates="user")

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    phone = Column(String)
    linkedin_url = Column(String)
    github_url = Column(String)
    portfolio_url = Column(String)
    education = Column(JSON)  # List of education entries
    experience = Column(JSON)  # List of experience entries
    skills = Column(JSON)  # List of skills
    certifications = Column(JSON)  # List of certifications
    preferences = Column(JSON)  # User preferences for applications
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="profile")

class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    parsed_content = Column(JSON)  # Structured resume data
    raw_text = Column(Text)  # Raw text from resume
    is_primary = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")

class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_name = Column(String, nullable=False)
    position = Column(String, nullable=False)
    job_url = Column(String)
    application_url = Column(String)
    status = Column(String, default="pending")  # pending, submitted, rejected, interview, offer
    submission_data = Column(JSON)  # All fields submitted
    notes = Column(Text)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="applications")

class SavedResponse(Base):
    __tablename__ = "saved_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    field_type = Column(String, nullable=False)  # Type of field (e.g., "why_company", "cover_letter")
    field_label = Column(String)  # Original field label
    response = Column(Text, nullable=False)
    company = Column(String)  # Optional company association
    embedding = Column(JSON)  # Vector embedding for similarity search
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    user = relationship("User", back_populates="saved_responses")

class FieldMapping(Base):
    __tablename__ = "field_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    field_selector = Column(String)  # CSS selector or identifier
    field_label = Column(String)  # Label text
    field_type = Column(String)  # Classified type
    site_domain = Column(String)  # Website domain
    confidence = Column(Integer)  # Classification confidence
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    """Initialize the database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

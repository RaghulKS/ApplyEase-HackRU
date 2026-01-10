from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import os
from typing import List
from pathlib import Path

from app.models.snowflake_db import SnowflakeHelper, SnowflakeConnection
from app.models.schemas import ResumeResponse
from app.utils.auth import get_current_user_snowflake
from app.services.resume_parser import ResumeParser

router = APIRouter()
resume_parser = ResumeParser()

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    is_primary: bool = False,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Upload and parse a resume (PDF or DOCX)"""
    # Validate file type
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ['.pdf', '.docx', '.doc']:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported"
        )
    
    user_id = current_user['ID']
    
    # Save file
    upload_dir = f"backend/data/resumes/{user_id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse resume
    parsed_content = resume_parser.parse_resume(file_path)
    
    if not parsed_content:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse resume. Please check the file format."
        )
    
    # If this is primary, unset other primary resumes
    if is_primary:
        SnowflakeConnection.execute_update(
            "UPDATE resume_data SET is_primary = FALSE WHERE user_id = %s AND is_primary = TRUE",
            (user_id,)
        )
    
    # Prepare resume data for Snowflake
    resume_data = {
        'filename': file.filename,
        'parsed_content': parsed_content,
        'raw_text': parsed_content.get('raw_text', ''),
        'name': parsed_content.get('name'),
        'email': parsed_content.get('email'),
        'phone': parsed_content.get('phone'),
        'linkedin_url': parsed_content.get('linkedin_url'),
        'github_url': parsed_content.get('github_url'),
        'portfolio_url': parsed_content.get('portfolio_url'),
        'education': parsed_content.get('education', []),
        'experience': parsed_content.get('experience', []),
        'skills': parsed_content.get('skills', []),
        'certifications': parsed_content.get('certifications', []),
        'is_primary': is_primary
    }
    
    # Save to Snowflake
    resume_id = SnowflakeHelper.insert_resume_data(user_id, resume_data)
    
    if not resume_id:
        raise HTTPException(status_code=500, detail="Failed to save resume data")
    
    return {
        "id": resume_id,
        "filename": file.filename,
        "parsed_content": parsed_content,
        "is_primary": is_primary,
        "uploaded_at": parsed_content.get('parsed_at')
    }

@router.get("/")
async def get_resumes(
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Get all user resumes"""
    user_id = current_user['ID']
    resumes = SnowflakeConnection.execute_query(
        "SELECT * FROM resume_data WHERE user_id = %s ORDER BY uploaded_at DESC",
        (user_id,)
    )
    
    return [
        {
            "id": r['ID'],
            "filename": r['FILENAME'],
            "parsed_content": r['PARSED_CONTENT'],
            "is_primary": r['IS_PRIMARY'],
            "uploaded_at": r['UPLOADED_AT']
        }
        for r in resumes
    ]

@router.get("/primary")
async def get_primary_resume(
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Get primary resume with full details"""
    user_id = current_user['ID']
    resume = SnowflakeHelper.get_primary_resume(user_id)
    
    if not resume:
        raise HTTPException(status_code=404, detail="No primary resume found")
    
    return {
        "id": resume['ID'],
        "filename": resume['FILENAME'],
        "name": resume['NAME'],
        "email": resume['EMAIL'],
        "phone": resume['PHONE'],
        "linkedin_url": resume['LINKEDIN_URL'],
        "github_url": resume['GITHUB_URL'],
        "portfolio_url": resume['PORTFOLIO_URL'],
        "education": resume['EDUCATION'],
        "experience": resume['EXPERIENCE'],
        "skills": resume['SKILLS'],
        "certifications": resume['CERTIFICATIONS'],
        "parsed_content": resume['PARSED_CONTENT'],
        "is_primary": resume['IS_PRIMARY'],
        "uploaded_at": resume['UPLOADED_AT']
    }

@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Delete a resume"""
    user_id = current_user['ID']
    
    # Get resume to check ownership and get file path
    resume = SnowflakeConnection.execute_query(
        "SELECT * FROM resume_data WHERE id = %s AND user_id = %s",
        (resume_id, user_id)
    )
    
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    # Delete file from filesystem
    file_path = f"backend/data/resumes/{user_id}/{resume[0]['FILENAME']}"
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            pass  # File might not exist
    
    # Delete from database
    SnowflakeConnection.execute_update(
        "DELETE FROM resume_data WHERE id = %s AND user_id = %s",
        (resume_id, user_id)
    )
    
    return {"message": "Resume deleted successfully"}

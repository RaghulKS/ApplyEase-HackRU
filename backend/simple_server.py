from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import re
import sys
sys.path.append(os.path.dirname(__file__))

from app.models.snowflake_db import SnowflakeConnection, SnowflakeHelper, init_db

import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully")
else:
    print("⚠ WARNING: GEMINI_API_KEY not found in .env file!")
    print("  AI responses will be disabled until you add your API key.")

app = FastAPI(title="ApplyEase API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    try:
        print("Initializing Snowflake connection...")
        init_db()
        print("✓ Snowflake connected successfully!")
        print("✓ All data will be saved to Snowflake database")
    except Exception as e:
        print("=" * 50)
        print("⚠ WARNING: Snowflake connection failed!")
        print(f"  Error: {str(e)[:200]}")
        print("  ")
        print("  SOLUTION: Get a fresh OAuth token:")
        print("    1. Run: python get_snowflake_token.py")
        print("    2. Copy the token to your .env file")
        print("  ")
        print("  Backend will continue with IN-MEMORY storage")
        print("  (data will be lost when server restarts)")
        print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    try:
        SnowflakeConnection.close_pool()
    except:
        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_profile_cache = None
applications_cache = []
ml_data_cache = {
    "field_classifications": [],
    "generated_responses": [],
    "user_corrections": []
}

PERSONAL_USER_ID = 1

class UserProfile(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    birthday: Optional[str] = None
    location: Optional[str] = None  # City, State
    address: Optional[str] = None
    postal_code: Optional[str] = None
    
    ethnicity: Optional[str] = None
    authorized_us: Optional[str] = None  # Yes/No
    require_sponsorship: Optional[str] = None  # Yes/No
    has_disability: Optional[str] = None  # Yes/No/Prefer not to say
    lgbtq: Optional[str] = None  # Yes/No/Prefer not to say
    gender: Optional[str] = None
    veteran_status: Optional[str] = None  # Yes/No
    
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    resume_text: Optional[str] = None
    resume_filename: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []  # [{company, title, start_date, end_date, description}]
    education: List[Dict[str, Any]] = []  # [{institution, degree, field, start_date, end_date, gpa}]

class Application(BaseModel):
    company_name: str
    position: str
    job_url: Optional[str] = None
    status: str = "pending"
    submission_data: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    applied_date: Optional[str] = None

class MLLogEntry(BaseModel):
    field_type: str
    field_label: str
    generated_response: Optional[str] = None
    user_response: Optional[str] = None
    confidence: Optional[float] = None

# Routes
@app.get("/")
async def root():
    profile_exists = user_profile_cache is not None or get_user_profile_from_snowflake() is not None
    return {
        "message": "ApplyEase API - Personal Edition",
        "version": "1.0.0",
        "status": "operational",
        "profile_exists": profile_exists
    }

@app.get("/health")
async def health():
    # Try to get real counts from Snowflake
    apps_count = len(applications_cache)
    ml_count = len(ml_data_cache["field_classifications"])
    
    try:
        # Get real counts from Snowflake
        apps_result = SnowflakeConnection.execute_query(
            "SELECT COUNT(*) as count FROM applications WHERE user_id = %s",
            (PERSONAL_USER_ID,)
        )
        if apps_result:
            apps_count = apps_result[0].get('COUNT', apps_count)
        
        ml_result = SnowflakeConnection.execute_query(
            "SELECT COUNT(*) as count FROM ml_logs WHERE user_id = %s",
            (PERSONAL_USER_ID,)
        )
        if ml_result:
            ml_count = ml_result[0].get('COUNT', ml_count)
    except:
        pass  # Use cache counts if Snowflake unavailable
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "profile_set": user_profile_cache is not None or get_user_profile_from_snowflake() is not None,
            "applications_count": apps_count,
            "ml_entries": ml_count,
            "snowflake_connected": True  # Will be set during init
        }
    }

# Helper functions for Snowflake storage
def get_user_profile_from_snowflake() -> Optional[Dict[str, Any]]:
    """Get user profile from Snowflake"""
    try:
        # Get user info
        user = SnowflakeHelper.get_user_by_id(PERSONAL_USER_ID)
        if not user:
            return None
        
        # Get resume data
        resume = SnowflakeHelper.get_primary_resume(PERSONAL_USER_ID)
        
        # Combine into profile
        profile = {
            "first_name": user.get('FULL_NAME', '').split()[0] if user.get('FULL_NAME') else None,
            "last_name": user.get('FULL_NAME', '').split()[-1] if user.get('FULL_NAME') and len(user.get('FULL_NAME', '').split()) > 1 else None,
            "email": user.get('EMAIL'),
        }
        
        if resume:
            profile.update({
                "phone": resume.get('PHONE'),
                "linkedin_url": resume.get('LINKEDIN_URL'),
                "github_url": resume.get('GITHUB_URL'),
                "portfolio_url": resume.get('PORTFOLIO_URL'),
                "resume_text": resume.get('RAW_TEXT'),
                "resume_filename": resume.get('FILENAME'),
                "skills": json.loads(resume.get('SKILLS', '[]')) if resume.get('SKILLS') else [],
                "experience": json.loads(resume.get('EXPERIENCE', '[]')) if resume.get('EXPERIENCE') else [],
                "education": json.loads(resume.get('EDUCATION', '[]')) if resume.get('EDUCATION') else [],
            })
        
        return profile
    except Exception as e:
        print(f"Error getting profile from Snowflake: {e}")
        return user_profile_cache

# User Profile Endpoints
@app.get("/api/profile")
async def get_profile():
    """Get user profile"""
    global user_profile_cache
    
    # Try to get from Snowflake first
    profile = get_user_profile_from_snowflake()
    
    # Fall back to cache
    if not profile:
        profile = user_profile_cache
    
    if not profile:
        return {"exists": False, "profile": None}
    
    return {"exists": True, "profile": profile}

@app.post("/api/profile")
async def create_or_update_profile(profile: UserProfile):
    """Create or update user profile"""
    global user_profile_cache
    
    try:
        profile_data = profile.dict()
        profile_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Save to cache
        user_profile_cache = profile_data
        
        # Try to save to Snowflake
        try:
            # Check if user exists
            user = SnowflakeHelper.get_user_by_id(PERSONAL_USER_ID)
            
            if not user:
                # Create user first
                full_name = f"{profile_data['first_name']} {profile_data['last_name']}"
                user_id = SnowflakeHelper.insert_user(
                    email=profile_data['email'],
                    full_name=full_name,
                    hashed_password="no_password_needed"  # No auth for personal use
                )
                print(f"✓ Created user in Snowflake with ID: {user_id}")
            
            # Save resume data
            resume_data = {
                "filename": profile_data.get('resume_filename'),
                "raw_text": profile_data.get('resume_text'),
                "name": f"{profile_data['first_name']} {profile_data['last_name']}",
                "email": profile_data['email'],
                "phone": profile_data.get('phone'),
                "linkedin_url": profile_data.get('linkedin_url'),
                "github_url": profile_data.get('github_url'),
                "portfolio_url": profile_data.get('portfolio_url'),
                "education": profile_data.get('education', []),
                "experience": profile_data.get('experience', []),
                "skills": profile_data.get('skills', []),
                "certifications": [],
                "is_primary": True,
                "parsed_content": profile_data
            }
            
            resume_id = SnowflakeHelper.insert_resume_data(PERSONAL_USER_ID, resume_data)
            print(f"✓ Saved resume data to Snowflake with ID: {resume_id}")
            
        except Exception as e:
            print(f"⚠ Warning: Failed to save to Snowflake: {e}")
            print("  Data saved to memory only.")
        
        print(f"Profile saved successfully for: {profile_data.get('first_name')} {profile_data.get('last_name')}")
        
        return {
            "success": True,
            "message": "Profile saved successfully",
            "profile": profile_data
        }
    except Exception as e:
        print(f"Error saving profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {str(e)}")

@app.get("/api/profile/reset")
async def reset_profile():
    """Reset user profile (for testing)"""
    global user_profile_cache, applications_cache, ml_data_cache
    user_profile_cache = None
    applications_cache = []
    ml_data_cache = {
        "field_classifications": [],
        "generated_responses": [],
        "user_corrections": []
    }
    print("Profile and data reset!")
    return {
        "success": True,
        "message": "Profile and all data reset successfully (Snowflake data preserved)"
    }

@app.post("/api/profile/resume")
async def upload_resume(file: UploadFile = File(...)):
    """Upload and parse resume file"""
    global user_profile_cache
    
    try:
        content = await file.read()
        
        # Extract text based on file type
        resume_text = ""
        if file.filename.endswith('.txt'):
            resume_text = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            # Use PyPDF2 for PDF parsing
            try:
                import io
                import PyPDF2
                pdf_file = io.BytesIO(content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    resume_text += page.extract_text() + "\n"
                print(f"✓ PDF parsed: {len(resume_text)} characters extracted")
            except Exception as e:
                print(f"⚠ PDF parsing error: {e}")
                resume_text = content.decode('utf-8', errors='ignore')
        elif file.filename.endswith(('.doc', '.docx')):
            # Use python-docx for Word files
            try:
                import io
                import docx
                doc = docx.Document(io.BytesIO(content))
                for paragraph in doc.paragraphs:
                    resume_text += paragraph.text + "\n"
                print(f"✓ DOCX parsed: {len(resume_text)} characters extracted")
            except Exception as e:
                print(f"⚠ DOCX parsing error: {e}")
                resume_text = content.decode('utf-8', errors='ignore')
        else:
            resume_text = content.decode('utf-8', errors='ignore')
        
        print(f"Extracted text length: {len(resume_text)} characters")
        print(f"First 500 chars:\n{resume_text[:500]}")
        print("-" * 50)
        
        # Parse resume and extract information
        parsed_data = parse_resume(resume_text)
        print(f"\nParsed data:")
        print(f"  Name: {parsed_data.get('first_name')} {parsed_data.get('last_name')}")
        print(f"  Email: {parsed_data.get('email')}")
        print(f"  Phone: {parsed_data.get('phone')}")
        print(f"  Education entries: {len(parsed_data.get('education', []))}")
        print(f"  Experience entries: {len(parsed_data.get('experience', []))}")
        print(f"  Skills: {len(parsed_data.get('skills', []))}")
        print("-" * 50)
        
        # Initialize or update profile with parsed data
        if not user_profile_cache:
            user_profile_cache = parsed_data
        else:
            # Update existing profile with parsed data (don't overwrite if field already exists)
            for key, value in parsed_data.items():
                if value and (key not in user_profile_cache or not user_profile_cache.get(key)):
                    user_profile_cache[key] = value
        
        user_profile_cache["resume_text"] = resume_text
        user_profile_cache["resume_filename"] = file.filename
        user_profile_cache["resume_uploaded_at"] = datetime.utcnow().isoformat()
        
        return {
            "success": True,
            "message": "Resume uploaded and parsed successfully",
            "filename": file.filename,
            "parsed_data": parsed_data
        }
    except Exception as e:
        print(f"Resume upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")

# User Profile Endpoints
@app.get("/api/profile")
async def get_profile():
    """Get user profile"""
    global user_profile_cache
    
    # Try to get from Snowflake first
    profile = get_user_profile_from_snowflake()
    
    # Fall back to cache
    if not profile:
        profile = user_profile_cache
    
    if not profile:
        return {"exists": False, "profile": None}
    
    return {"exists": True, "profile": profile}

def parse_resume(resume_text: str) -> Dict[str, Any]:
    """Parse resume text and extract structured information"""
    parsed = {
        "first_name": None,
        "last_name": None,
        "email": None,
        "phone": None,
        "location": None,
        "address": None,
        "linkedin_url": None,
        "github_url": None,
        "skills": [],
        "experience": [],
        "education": []
    }
    
    lines = resume_text.split('\n')
    
    # Extract email
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    email_match = re.search(email_pattern, resume_text)
    if email_match:
        parsed["email"] = email_match.group()
    
    # Extract phone
    phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,5}[-\s\.]?[0-9]{3,5}'
    phone_match = re.search(phone_pattern, resume_text)
    if phone_match:
        parsed["phone"] = phone_match.group()
    
    # Extract LinkedIn
    linkedin_pattern = r'linkedin\.com/in/[\w-]+'
    linkedin_match = re.search(linkedin_pattern, resume_text, re.IGNORECASE)
    if linkedin_match:
        parsed["linkedin_url"] = f"https://{linkedin_match.group()}"
    
    # Extract GitHub
    github_pattern = r'github\.com/[\w-]+'
    github_match = re.search(github_pattern, resume_text, re.IGNORECASE)
    if github_match:
        parsed["github_url"] = f"https://{github_match.group()}"
    
    # Extract name (usually first line or first non-empty line)
    for line in lines[:5]:
        line = line.strip()
        if line and not re.search(email_pattern, line) and not re.search(phone_pattern, line):
            # Likely the name
            name_parts = line.split()
            if len(name_parts) >= 2:
                parsed["first_name"] = name_parts[0]
                parsed["last_name"] = name_parts[-1]
                break
    
    # Extract location (look for city, state patterns)
    location_pattern = r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,?\s*[A-Z]{2})'
    location_match = re.search(location_pattern, resume_text)
    if location_match:
        parsed["location"] = location_match.group()
    
    # Parse Education section
    education_section = extract_section(resume_text, ['education', 'academic background', 'qualifications'])
    if education_section:
        parsed["education"] = parse_education(education_section)
    
    # Parse Experience section
    experience_section = extract_section(resume_text, ['experience', 'work history', 'employment', 'professional experience'])
    if experience_section:
        parsed["experience"] = parse_experience(experience_section)
    
    # Parse Skills section
    skills_section = extract_section(resume_text, ['skills', 'technical skills', 'competencies'])
    if skills_section:
        parsed["skills"] = parse_skills(skills_section)
    
    return parsed

def extract_section(text: str, keywords: List[str]) -> str:
    """Extract a section from resume based on keywords"""
    lines = text.split('\n')
    section_lines = []
    in_section = False
    
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()
        
        # Check if this line is a section header
        if any(keyword in line_lower for keyword in keywords):
            in_section = True
            continue
        
        # Check if we've hit another section
        if in_section and line_lower and line.isupper() and len(line.strip()) > 3:
            break
        
        if in_section and line.strip():
            section_lines.append(line)
    
    return '\n'.join(section_lines)

def parse_education(section_text: str) -> List[Dict[str, Any]]:
    """Parse education section"""
    education_list = []
    lines = section_text.split('\n')
    
    current_edu = {}
    for line in lines:
        line = line.strip()
        if not line:
            if current_edu:
                education_list.append(current_edu)
                current_edu = {}
            continue
        
        # Look for university/college names (usually capitalized or have "University" keyword)
        if any(word in line for word in ['University', 'College', 'Institute', 'School']):
            if current_edu and 'institution' in current_edu:
                education_list.append(current_edu)
                current_edu = {}
            current_edu['institution'] = line
        
        # Look for degrees
        elif any(degree in line for degree in ['Bachelor', 'Master', 'PhD', 'B.S.', 'M.S.', 'B.A.', 'M.A.', 'Associate']):
            current_edu['degree'] = line
        
        # Look for dates (e.g., 2020-2024, Sept 2020 - May 2024)
        elif re.search(r'\d{4}', line):
            current_edu['dates'] = line
        
        # Look for GPA
        elif 'gpa' in line.lower() or re.search(r'\d\.\d{1,2}', line):
            current_edu['gpa'] = line
        
        else:
            # Probably field of study or description
            if 'field' not in current_edu:
                current_edu['field'] = line
    
    if current_edu:
        education_list.append(current_edu)
    
    return education_list

def parse_experience(section_text: str) -> List[Dict[str, Any]]:
    """Parse work experience section"""
    experience_list = []
    lines = section_text.split('\n')
    
    current_exp = {}
    description_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if description_lines and current_exp:
                current_exp['description'] = ' '.join(description_lines)
                description_lines = []
            if current_exp:
                experience_list.append(current_exp)
                current_exp = {}
            continue
        
        # Look for company names (often in bold or all caps in original)
        if line.isupper() or (len(line) > 5 and not line.startswith('•') and not line.startswith('-')):
            if current_exp:
                if description_lines:
                    current_exp['description'] = ' '.join(description_lines)
                    description_lines = []
                experience_list.append(current_exp)
            current_exp = {'company': line}
        
        # Look for job titles (often have keywords like "Engineer", "Developer", "Manager", etc.)
        elif not current_exp.get('title') and any(word in line for word in ['Engineer', 'Developer', 'Manager', 'Analyst', 'Designer', 'Intern', 'Specialist']):
            current_exp['title'] = line
        
        # Look for dates
        elif re.search(r'\d{4}', line) and not current_exp.get('dates'):
            current_exp['dates'] = line
        
        # Everything else is description
        else:
            description_lines.append(line.lstrip('•-').strip())
    
    if description_lines and current_exp:
        current_exp['description'] = ' '.join(description_lines)
    if current_exp:
        experience_list.append(current_exp)
    
    return experience_list

def parse_skills(section_text: str) -> List[str]:
    """Parse skills section"""
    skills = []
    
    # Split by common delimiters
    skill_text = section_text.replace('\n', ',')
    skill_items = re.split(r'[,;•\-\|]', skill_text)
    
    for item in skill_items:
        item = item.strip()
        if item and len(item) > 1 and len(item) < 50:
            skills.append(item)
    
    return skills[:20]  # Limit to 20 skills

# Applications Endpoints
@app.get("/api/applications")
async def get_applications():
    """Get all applications"""
    try:
        # Try to get from Snowflake
        apps = SnowflakeConnection.execute_query(
            "SELECT * FROM applications WHERE user_id = %s ORDER BY created_at DESC",
            (PERSONAL_USER_ID,)
        )
        return {"applications": apps, "total": len(apps)}
    except Exception as e:
        print(f"Error getting applications from Snowflake: {e}")
        return {"applications": applications_cache, "total": len(applications_cache)}

@app.post("/api/applications")
async def create_application(application: Application):
    """Save a new application"""
    global applications_cache
    
    app_dict = application.dict()
    app_dict["created_at"] = datetime.utcnow().isoformat()
    if not app_dict.get("applied_date"):
        app_dict["applied_date"] = datetime.utcnow().isoformat()
    
    # Save to cache
    app_dict["id"] = len(applications_cache) + 1
    applications_cache.append(app_dict)
    
    # Try to save to Snowflake
    try:
        query = """
            INSERT INTO applications (
                user_id, company_name, position, job_url, application_url,
                status, submission_data, notes, submitted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, %s)
        """
        SnowflakeConnection.execute_update(query, (
            PERSONAL_USER_ID,
            app_dict["company_name"],
            app_dict["position"],
            app_dict.get("job_url"),
            app_dict.get("job_url"),  # application_url same as job_url for now
            app_dict["status"],
            json.dumps(app_dict.get("submission_data", {})),
            app_dict.get("notes"),
            app_dict.get("applied_date")
        ))
        print(f"✓ Application saved to Snowflake: {app_dict['position']} at {app_dict['company_name']}")
    except Exception as e:
        print(f"⚠ Warning: Failed to save application to Snowflake: {e}")
        print("  Application saved to memory only.")
    
    return {
        "success": True,
        "message": "Application saved",
        "application": app_dict
    }

@app.get("/api/applications/{app_id}")
async def get_application(app_id: int):
    """Get specific application"""
    try:
        result = SnowflakeConnection.execute_query(
            "SELECT * FROM applications WHERE user_id = %s AND id = %s",
            (PERSONAL_USER_ID, app_id)
        )
        if result:
            return {"application": result[0]}
    except:
        for app in applications_cache:
            if app.get("id") == app_id:
                return {"application": app}
    
    raise HTTPException(status_code=404, detail="Application not found")

@app.put("/api/applications/{app_id}")
async def update_application(app_id: int, application: Application):
    """Update application status"""
    app_dict = application.dict()
    app_dict["updated_at"] = datetime.utcnow().isoformat()
    
    # Try to update in Snowflake
    try:
        query = """
            UPDATE applications 
            SET status = %s, submission_data = PARSE_JSON(%s), notes = %s, updated_at = CURRENT_TIMESTAMP()
            WHERE user_id = %s AND id = %s
        """
        SnowflakeConnection.execute_update(query, (
            app_dict["status"],
            json.dumps(app_dict.get("submission_data", {})),
            app_dict.get("notes"),
            PERSONAL_USER_ID,
            app_id
        ))
        print(f"✓ Application updated in Snowflake: {app_id}")
    except Exception as e:
        print(f"⚠ Warning: Failed to update application in Snowflake: {e}")
        # Update cache
        for i, app in enumerate(applications_cache):
            if app.get("id") == app_id:
                app_dict["id"] = app_id
                applications_cache[i] = app_dict
                return {"success": True, "application": app_dict}
    
    return {"success": True, "application": app_dict}

@app.get("/api/applications/stats/summary")
async def get_application_stats():
    """Get application statistics"""
    try:
        # Get from Snowflake
        apps = SnowflakeConnection.execute_query(
            "SELECT status FROM applications WHERE user_id = %s",
            (PERSONAL_USER_ID,)
        )
        total = len(apps)
        pending = sum(1 for app in apps if app.get("STATUS") == "pending")
        submitted = sum(1 for app in apps if app.get("STATUS") == "submitted")
        rejected = sum(1 for app in apps if app.get("STATUS") == "rejected")
        interview = sum(1 for app in apps if app.get("STATUS") == "interview")
    except:
        # Fall back to cache
        total = len(applications_cache)
        pending = sum(1 for app in applications_cache if app.get("status") == "pending")
        submitted = sum(1 for app in applications_cache if app.get("status") == "submitted")
        rejected = sum(1 for app in applications_cache if app.get("status") == "rejected")
        interview = sum(1 for app in applications_cache if app.get("status") == "interview")
    
    return {
        "total": total,
        "pending": pending,
        "submitted": submitted,
        "rejected": rejected,
        "interview": interview
    }

# ML Data Endpoints
@app.post("/api/ml/log")
async def log_ml_data(entry: MLLogEntry):
    """Log ML predictions and user corrections"""
    global ml_data_cache
    
    log_entry = entry.dict()
    log_entry["timestamp"] = datetime.utcnow().isoformat()
    ml_data_cache["field_classifications"].append(log_entry)
    
    # Try to save to Snowflake
    try:
        ml_log = {
            "user_id": PERSONAL_USER_ID,
            "model_name": "field_classifier",
            "model_version": "1.0",
            "input_data": {"field_type": log_entry["field_type"], "field_label": log_entry["field_label"]},
            "output_data": {"generated": log_entry.get("generated_response"), "user": log_entry.get("user_response")},
            "prediction_type": "field_classification",
            "confidence_score": log_entry.get("confidence"),
            "field_classification": {},
            "performance_metrics": {},
            "execution_time_ms": 0,
            "success": True,
            "error_message": None
        }
        SnowflakeHelper.log_ml_prediction(ml_log)
        print(f"✓ ML data logged to Snowflake")
    except Exception as e:
        print(f"⚠ Warning: Failed to log ML data to Snowflake: {e}")
    
    return {"success": True, "message": "ML data logged"}

@app.get("/api/ml/data")
async def get_ml_data():
    """Get ML training data"""
    try:
        # Get from Snowflake
        logs = SnowflakeConnection.execute_query(
            "SELECT * FROM ml_logs WHERE user_id = %s ORDER BY created_at DESC LIMIT 1000",
            (PERSONAL_USER_ID,)
        )
        return {
            "total_entries": len(logs),
            "data": {"field_classifications": logs}
        }
    except:
        return {
            "total_entries": len(ml_data_cache["field_classifications"]),
            "data": ml_data_cache
        }

# Field Detection/Classification Endpoints
@app.post("/api/fields/detect")
async def detect_fields(data: Dict[str, Any]):
    """Detect and classify form fields"""
    fields = data.get("fields", [])
    
    # Simple classification (can enhance with actual ML model later)
    classified = {
        "standard_fields": [],
        "unique_fields": [],
        "suggestions": {}
    }
    
    standard_keywords = {
        "first_name": ["first name", "given name", "firstname"],
        "middle_name": ["middle name", "middle initial", "middlename"],
        "last_name": ["last name", "surname", "family name", "lastname"],
        "full_name": ["full name", "name", "your name"],
        "email": ["email", "e-mail", "email address"],
        "phone": ["phone", "telephone", "mobile", "contact number"],
        "birthday": ["birthday", "birth date", "date of birth", "dob"],
        "location": ["city", "location", "city/state", "where do you live"],
        "address": ["address", "street address", "home address"],
        "postal_code": ["zip", "postal code", "zip code", "postal"],
        "linkedin": ["linkedin", "linkedin url", "linkedin profile"],
        "github": ["github", "github url", "github profile"],
        "portfolio": ["portfolio", "website", "personal website"],
        "ethnicity": ["ethnicity", "race", "ethnic background"],
        "gender": ["gender", "sex"],
        "veteran": ["veteran", "military", "veteran status"],
        "disability": ["disability", "disabled", "accommodation"],
        "lgbtq": ["lgbtq", "sexual orientation", "gender identity"],
        "authorized_us": ["authorized", "work authorization", "us work", "legally authorized"],
        "sponsorship": ["sponsorship", "visa", "require sponsorship", "visa sponsorship"],
        "education": ["school", "university", "college", "degree", "education"],
        "experience": ["experience", "work", "employment", "company"],
        "skills": ["skills", "technical", "competencies"]
    }
    
    for field in fields:
        label = field.get("label", "").lower()
        field_type = None
        
        # Check if it's a standard field
        for std_type, keywords in standard_keywords.items():
            if any(keyword in label for keyword in keywords):
                field_type = std_type
                classified["standard_fields"].append({**field, "classified_as": std_type})
                
                # Add suggestion from user profile if available
                profile = user_profile_cache or get_user_profile_from_snowflake()
                if profile:
                    suggestion = None
                    
                    if std_type == "first_name" and profile.get("first_name"):
                        suggestion = profile["first_name"]
                    elif std_type == "middle_name":
                        # If middle name exists, use it; otherwise leave blank
                        suggestion = profile.get("middle_name", "")
                    elif std_type == "last_name" and profile.get("last_name"):
                        suggestion = profile["last_name"]
                    elif std_type == "full_name" and profile.get("first_name") and profile.get("last_name"):
                        # Include middle name if exists
                        middle = f" {profile['middle_name']}" if profile.get("middle_name") else ""
                        suggestion = f"{profile['first_name']}{middle} {profile['last_name']}"
                    elif std_type == "email" and profile.get("email"):
                        suggestion = profile["email"]
                    elif std_type == "phone" and profile.get("phone"):
                        suggestion = profile["phone"]
                    elif std_type == "birthday" and profile.get("birthday"):
                        suggestion = profile["birthday"]
                    elif std_type == "location" and profile.get("location"):
                        suggestion = profile["location"]
                    elif std_type == "address" and profile.get("address"):
                        suggestion = profile["address"]
                    elif std_type == "postal_code" and profile.get("postal_code"):
                        suggestion = profile["postal_code"]
                    elif std_type == "linkedin" and profile.get("linkedin_url"):
                        suggestion = profile["linkedin_url"]
                    elif std_type == "github" and profile.get("github_url"):
                        suggestion = profile["github_url"]
                    elif std_type == "portfolio" and profile.get("portfolio_url"):
                        suggestion = profile["portfolio_url"]
                    elif std_type == "ethnicity" and profile.get("ethnicity"):
                        suggestion = profile["ethnicity"]
                    elif std_type == "gender" and profile.get("gender"):
                        suggestion = profile["gender"]
                    elif std_type == "veteran" and profile.get("veteran_status"):
                        suggestion = profile["veteran_status"]
                    elif std_type == "disability" and profile.get("has_disability"):
                        suggestion = profile["has_disability"]
                    elif std_type == "lgbtq" and profile.get("lgbtq"):
                        suggestion = profile["lgbtq"]
                    elif std_type == "authorized_us" and profile.get("authorized_us"):
                        suggestion = profile["authorized_us"]
                    elif std_type == "sponsorship" and profile.get("require_sponsorship"):
                        suggestion = profile["require_sponsorship"]
                    
                    if suggestion:
                        classified["suggestions"][field.get("id")] = suggestion
                break
        
        # If not standard, mark as unique
        if not field_type:
            classified["unique_fields"].append(field)
    
    return classified

# Chatbot/AI Response Generation
@app.post("/api/chatbot/generate")
async def generate_response(data: Dict[str, Any]):
    """Generate AI response for unique fields using Gemini and resume context"""
    field_info = data.get("field_info", {})
    company_info = data.get("company_info", {})
    
    field_label = field_info.get("label", "Unknown Field")
    field_type = field_info.get("type", "text")
    is_group = field_info.get("isGroup", False)
    options = field_info.get("options", [])
    company_name = company_info.get("name", "this company")
    
    # Get user profile for context
    profile = user_profile_cache or get_user_profile_from_snowflake()
    
    if not profile:
        return {"response": "Please set up your profile first to generate personalized responses."}
    
    # Check if Gemini is configured
    if not GEMINI_API_KEY:
        return {"response": "AI service not configured. Please add GEMINI_API_KEY to .env file."}
    
    print(f"\n{'='*60}")
    print(f"🤖 GEMINI AI REQUEST")
    print(f"{'='*60}")
    print(f"Question: {field_label}")
    print(f"Type: {'Multiple Choice' if is_group else 'Text Response'}")
    if is_group:
        print(f"Options: {[opt.get('label') or opt.get('value') for opt in options]}")
    print(f"Company: {company_name}")
    
    # Build user context from profile
    name = f"{profile.get('first_name', '')} {profile.get('middle_name', '')} {profile.get('last_name', '')}".strip()
    email = profile.get('email', '')
    phone = profile.get('phone', '')
    location = profile.get('location', '')
    
    # Skills
    skills = profile.get('skills', [])
    skills_text = ', '.join(skills) if skills else 'various technical skills'
    
    # Experience
    experience_text = ""
    if profile.get('experience'):
        for exp in profile.get('experience')[:2]:  # Top 2 most recent
            company = exp.get('company', '')
            title = exp.get('title', '')
            dates = exp.get('dates', '')
            description = exp.get('description', '')
            experience_text += f"\n- {title} at {company} ({dates})"
            if description:
                experience_text += f": {description[:150]}"
    
    # Education
    education_text = ""
    if profile.get('education'):
        for edu in profile.get('education'):
            institution = edu.get('institution', '')
            degree = edu.get('degree', '')
            field = edu.get('field', '')
            dates = edu.get('dates', '')
            gpa = edu.get('gpa', '')
            education_text += f"\n- {degree} in {field} from {institution} ({dates})"
            if gpa:
                education_text += f" - GPA: {gpa}"
    
    # Diversity info
    authorized_us = profile.get('authorized_us', '')
    require_sponsorship = profile.get('require_sponsorship', '')
    veteran_status = profile.get('veteran_status', '')
    disability = profile.get('has_disability', '')
    ethnicity = profile.get('ethnicity', '')
    gender = profile.get('gender', '')
    
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Build prompt based on field type
        if is_group and options:
            # For multiple choice questions
            option_values = [opt.get('label') or opt.get('value') for opt in options]
            
            prompt = f"""You are helping a job applicant answer an application question.

APPLICANT INFORMATION:
Name: {name}
Location: {location}
Skills: {skills_text}

Work Experience:{experience_text if experience_text else ' None provided'}

Education:{education_text if education_text else ' None provided'}

Additional Information:
- Work Authorization (US): {authorized_us}
- Requires Sponsorship: {require_sponsorship}
- Veteran Status: {veteran_status}
- Disability Status: {disability}
- Ethnicity: {ethnicity}
- Gender: {gender}

APPLICATION QUESTION:
"{field_label}"

AVAILABLE OPTIONS (you MUST choose EXACTLY one of these):
{chr(10).join(f'- {opt}' for opt in option_values)}

INSTRUCTIONS:
1. Read the question carefully
2. Consider the applicant's profile information above
3. Choose the MOST APPROPRIATE option from the list
4. Respond with ONLY the exact option text, nothing else
5. If unsure and "Prefer not to say" is available, choose that
6. For work authorization questions, use the "Work Authorization (US)" field
7. For sponsorship questions, use the "Requires Sponsorship" field
8. For diversity questions, use the corresponding profile fields

YOUR RESPONSE (choose one option exactly as written):"""

        else:
            # For text/essay questions
            prompt = f"""You are helping a job applicant write a compelling response to an application question.

APPLICANT INFORMATION:
Name: {name}
Email: {email}
Location: {location}
Skills: {skills_text}

Work Experience:{experience_text if experience_text else ' None provided'}

Education:{education_text if education_text else ' None provided'}

APPLICATION DETAILS:
Company: {company_name}
Question: "{field_label}"

INSTRUCTIONS:
1. Write a compelling, professional response (2-4 sentences for short answers, 1-2 paragraphs for essays)
2. Base your response on the applicant's actual experience, skills, and education
3. Be specific and authentic - reference real details from their profile
4. Tailor the response to {company_name}
5. Keep the tone professional but personable
6. Make it sound natural, not robotic
7. Do NOT make up experiences or skills not in the profile
8. If the profile lacks relevant information, write a general but strong response

YOUR RESPONSE:"""

        print(f"\n📤 Sending prompt to Gemini API...")
        print(f"Prompt length: {len(prompt)} characters")
        
        # Generate response
        response_obj = model.generate_content(prompt)
        response_text = response_obj.text.strip()
        
        print(f"\n✅ GEMINI RESPONSE RECEIVED:")
        print(f"{response_text[:200]}{'...' if len(response_text) > 200 else ''}")
        print(f"{'='*60}\n")
        
        # For grouped fields, validate the response matches an option
        if is_group and options:
            option_values = [opt.get('label') or opt.get('value') for opt in options]
            
            # Try exact match first
            if response_text in option_values:
                final_response = response_text
            else:
                # Try case-insensitive match
                response_lower = response_text.lower()
                matched = False
                for opt_val in option_values:
                    if opt_val.lower() == response_lower or opt_val.lower() in response_lower or response_lower in opt_val.lower():
                        final_response = opt_val
                        matched = True
                        print(f"✓ Matched AI response to option: {opt_val}")
                        break
                
                if not matched:
                    # Fallback to first option
                    final_response = option_values[0]
                    print(f"⚠ AI response didn't match options, using first option: {final_response}")
            
            response_text = final_response
        
        return {
            "response": response_text,
            "field": field_label,
            "company": company_name,
            "isGroup": is_group
        }
    
    except Exception as e:
        print(f"\n❌ GEMINI API ERROR: {str(e)}\n")
        return {"response": f"Error generating AI response: {str(e)[:100]}"}

@app.post("/api/chatbot/save-unique-field")
async def save_unique_field(data: Dict[str, Any]):
    """Save unique field response for future use"""
    global ml_data_cache
    
    response_data = {
        **data,
        "timestamp": datetime.utcnow().isoformat()
    }
    ml_data_cache["generated_responses"].append(response_data)
    
    # Try to save to Snowflake
    try:
        field_data = {
            "user_id": PERSONAL_USER_ID,
            "field_label": data.get("field_label", ""),
            "field_type": data.get("field_type", "text"),
            "field_context": data.get("context", {}),
            "user_response": data.get("user_response"),
            "ai_generated_response": data.get("ai_response"),
            "final_response": data.get("final_response", data.get("user_response")),
            "company": data.get("company"),
            "position": data.get("position"),
            "confidence_score": data.get("confidence"),
            "embedding": []
        }
        SnowflakeHelper.save_unique_field_response(field_data)
        print(f"✓ Unique field response saved to Snowflake")
    except Exception as e:
        print(f"⚠ Warning: Failed to save unique field to Snowflake: {e}")
    
    return {"success": True, "message": "Response saved"}

@app.get("/api/chatbot/unique-fields")
async def get_unique_fields():
    """Get previously answered unique fields"""
    try:
        # Get from Snowflake
        fields = SnowflakeConnection.execute_query(
            "SELECT * FROM unique_fields WHERE user_id = %s ORDER BY created_at DESC",
            (PERSONAL_USER_ID,)
        )
        return {"fields": fields}
    except:
        return {"fields": ml_data_cache["generated_responses"]}

if __name__ == "__main__":
    import uvicorn
    print("="*50)
    print("ApplyEase Backend Starting...")
    print("Personal Edition (No Authentication)")
    print("Server: http://localhost:8001")
    print("="*50)
    uvicorn.run(app, host="127.0.0.1", port=8001)
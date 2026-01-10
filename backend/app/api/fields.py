from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, User, UserProfile, Resume
from app.models.schemas import FieldDetectionRequest, FieldDetectionResponse
from app.utils.auth import get_current_user
from app.ml.field_classifier import FieldClassifier

router = APIRouter()
field_classifier = FieldClassifier()

@router.post("/detect", response_model=FieldDetectionResponse)
async def detect_fields(
    request: FieldDetectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect and classify form fields"""
    # Classify fields
    results = field_classifier.classify_fields(request.fields)
    
    # Get user profile for auto-fill suggestions
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_primary == True
    ).first()
    
    suggestions = {}
    
    # Generate suggestions for standard fields
    for field in results['standard_fields']:
        field_id = field.get('id') or field.get('name')
        category = field['classification']['category']
        
        if category == 'personal':
            if profile:
                field_name = field.get('name', '').lower()
                if 'phone' in field_name:
                    suggestions[field_id] = profile.phone
                elif 'email' in field_name:
                    suggestions[field_id] = current_user.email
                elif 'name' in field_name:
                    suggestions[field_id] = current_user.full_name
        
        elif category == 'links':
            if profile:
                field_name = field.get('name', '').lower()
                if 'linkedin' in field_name:
                    suggestions[field_id] = profile.linkedin_url
                elif 'github' in field_name:
                    suggestions[field_id] = profile.github_url
                elif 'portfolio' in field_name or 'website' in field_name:
                    suggestions[field_id] = profile.portfolio_url
        
        elif category == 'education' and profile and profile.education:
            education = profile.education[0] if isinstance(profile.education, list) else profile.education
            field_name = field.get('name', '').lower()
            if 'school' in field_name or 'university' in field_name:
                suggestions[field_id] = education.get('institution')
            elif 'degree' in field_name:
                suggestions[field_id] = education.get('degree')
            elif 'gpa' in field_name:
                suggestions[field_id] = str(education.get('gpa', ''))
    
    return FieldDetectionResponse(
        classified_fields=results,
        suggestions=suggestions
    )

@router.post("/validate")
async def validate_fields(
    fields: dict,
    current_user: User = Depends(get_current_user)
):
    """Validate form fields before submission"""
    errors = []
    warnings = []
    
    for field_id, value in fields.items():
        # Check for empty required fields
        if not value:
            warnings.append(f"Field {field_id} appears to be empty")
        
        # Check for placeholder text still present
        if value and any(placeholder in value.lower() for placeholder in ['enter', 'type here', 'your answer']):
            warnings.append(f"Field {field_id} may still contain placeholder text")
        
        # Check for excessive length
        if value and len(value) > 5000:
            errors.append(f"Field {field_id} exceeds maximum length")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

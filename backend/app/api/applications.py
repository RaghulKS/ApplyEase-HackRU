from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.database import get_db, User, Application
from app.models.schemas import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.utils.auth import get_current_user
from app.services.sheets_tracker import GoogleSheetsTracker

router = APIRouter()
sheets_tracker = GoogleSheetsTracker()

@router.post("/", response_model=ApplicationResponse)
async def create_application(
    application: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new application"""
    db_application = Application(
        user_id=current_user.id,
        **application.dict()
    )
    
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    # Add to Google Sheets
    sheets_tracker.add_application({
        'id': db_application.id,
        'company_name': db_application.company_name,
        'position': db_application.position,
        'job_url': db_application.job_url,
        'application_url': db_application.application_url,
        'date_applied': datetime.utcnow().strftime('%Y-%m-%d'),
        'status': 'Applied'
    })
    
    return db_application

@router.get("/", response_model=List[ApplicationResponse])
async def get_applications(
    status: Optional[str] = None,
    company: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user applications with optional filters"""
    query = db.query(Application).filter(Application.user_id == current_user.id)
    
    if status:
        query = query.filter(Application.status == status)
    if company:
        query = query.filter(Application.company_name.ilike(f"%{company}%"))
    
    applications = query.order_by(Application.created_at.desc()).all()
    return applications

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific application"""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return application

@router.put("/{application_id}", response_model=ApplicationResponse)
async def update_application(
    application_id: int,
    update: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update application"""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Update fields
    update_data = update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)
    
    application.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(application)
    
    # Update Google Sheets
    sheets_tracker.update_application(str(application_id), update_data)
    
    return application

@router.delete("/{application_id}")
async def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete application"""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    db.delete(application)
    db.commit()
    
    return {"message": "Application deleted successfully"}

@router.get("/stats/summary")
async def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get application statistics"""
    total = db.query(Application).filter(Application.user_id == current_user.id).count()
    
    # Get counts by status
    status_counts = {}
    for status in ['pending', 'submitted', 'rejected', 'interview', 'offer']:
        count = db.query(Application).filter(
            Application.user_id == current_user.id,
            Application.status == status
        ).count()
        status_counts[status] = count
    
    # Get from Google Sheets for more detailed stats
    sheets_stats = sheets_tracker.get_statistics()
    
    return {
        'total': total,
        'by_status': status_counts,
        'sheets_stats': sheets_stats
    }

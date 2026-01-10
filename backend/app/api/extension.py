"""
Extension-specific API endpoints
These endpoints are designed for the Chrome extension with simplified authentication
IN-MEMORY STORAGE MODE - No Snowflake required
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime
import os

# In-memory storage
applications_store = []
next_id = 1

# Try Google Sheets (optional)
try:
    from app.services.sheets_tracker import GoogleSheetsTracker
    from app.utils.logger import setup_logger
    logger = setup_logger(__name__)
    sheets_tracker = GoogleSheetsTracker()
    SHEETS_AVAILABLE = sheets_tracker.client is not None
except Exception as e:
    print(f"⚠ Google Sheets not available: {e}")
    sheets_tracker = None
    SHEETS_AVAILABLE = False
    # Simple logger fallback
    class SimpleLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
    logger = SimpleLogger()

router = APIRouter()

# Simple API key for extension (in production, use proper auth)
EXTENSION_API_KEY = os.getenv("EXTENSION_API_KEY", "applyease-extension-dev-key")


def verify_extension_key(x_api_key: Optional[str] = Header(None)):
    """Verify extension API key"""
    if not x_api_key or x_api_key != EXTENSION_API_KEY:
        # For development, allow requests without key
        logger.warning("Extension API called without valid key")
        return None
    return x_api_key


@router.post("/track-application")
async def track_application(
    application: dict,
    x_api_key: Optional[str] = Header(None)
):
    """
    Track a job application from the extension
    IN-MEMORY STORAGE - No Snowflake required!
    """
    global next_id
    
    try:
        # Verify API key (optional in dev mode)
        verify_extension_key(x_api_key)
        
        # Extract application data
        company_name = application.get('company_name', 'Unknown Company')
        position = application.get('position', 'Unknown Position')
        job_url = application.get('job_url', '')
        application_url = application.get('application_url', '')
        submission_data = application.get('submission_data', {})
        status = application.get('status', 'submitted')
        notes = application.get('notes', '')
        
        # Create application record (in-memory)
        app_record = {
            'id': next_id,
            'company_name': company_name,
            'position': position,
            'job_url': job_url,
            'application_url': application_url,
            'status': status,
            'submission_data': submission_data,
            'notes': notes,
            'created_at': datetime.utcnow().isoformat(),
            'submitted_at': datetime.utcnow().isoformat()
        }
        
        # Save to in-memory store
        applications_store.append(app_record)
        application_id = next_id
        next_id += 1
        
        logger.info(f"✓ Application saved to memory: {company_name} - {position} (ID: {application_id})")
        
        # Sync to Google Sheets (optional)
        sheets_synced = False
        if SHEETS_AVAILABLE and sheets_tracker:
            try:
                sheets_success = sheets_tracker.add_application({
                    'id': application_id,
                    'date_applied': datetime.utcnow().strftime('%Y-%m-%d'),
                    'company_name': company_name,
                    'position': position,
                    'location': submission_data.get('location', ''),
                    'job_url': job_url,
                    'application_url': application_url,
                    'status': status.capitalize(),
                    'notes': notes,
                    'application_method': 'ApplyEase Extension',
                })
                
                if sheets_success:
                    logger.info(f"✓ Synced to Google Sheets: {company_name} - {position}")
                    sheets_synced = True
                else:
                    logger.warning(f"⚠ Google Sheets sync failed: {company_name} - {position}")
                    
            except Exception as sheets_error:
                logger.warning(f"⚠ Google Sheets error: {sheets_error}")
        
        return {
            "success": True,
            "message": "Application tracked successfully (in-memory)",
            "application_id": application_id,
            "company_name": company_name,
            "position": position,
            "storage": "in-memory",
            "synced_to_sheets": sheets_synced
        }
        
    except Exception as e:
        logger.error(f"Error tracking application: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track application: {str(e)}"
        )


@router.get("/health")
async def extension_health():
    """Health check for extension connectivity"""
    return {
        "status": "ok",
        "storage": "in-memory",
        "google_sheets_connected": SHEETS_AVAILABLE,
        "applications_count": len(applications_store),
        "message": "Extension API is ready (in-memory mode)"
    }

@router.get("/applications")
async def get_applications():
    """Get all tracked applications from memory"""
    return {
        "applications": applications_store,
        "count": len(applications_store),
        "storage": "in-memory"
    }

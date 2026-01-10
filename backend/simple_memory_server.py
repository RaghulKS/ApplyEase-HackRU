"""Simple in-memory server for ApplyEase without external databases."""
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, List
from datetime import datetime
import os
from dotenv import load_dotenv
import uvicorn

load_dotenv()

applications_db = []
next_app_id = 1

try:
    from app.services.sheets_tracker import GoogleSheetsTracker
    sheets_tracker = GoogleSheetsTracker()
    SHEETS_AVAILABLE = sheets_tracker.client is not None
    print(f"Google Sheets: {'Connected' if SHEETS_AVAILABLE else 'Disabled'}")
except Exception as e:
    print(f"Google Sheets: Disabled ({e})")
    sheets_tracker = None
    SHEETS_AVAILABLE = False

app = FastAPI(
    title="ApplyEase API - In-Memory Edition",
    description="Job application tracking with in-memory storage",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "ApplyEase API - In-Memory Edition",
        "version": "2.0.0",
        "storage": "in-memory",
        "google_sheets": "connected" if SHEETS_AVAILABLE else "disabled",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "storage": "in-memory",
        "google_sheets_connected": SHEETS_AVAILABLE,
        "applications_count": len(applications_db)
    }

@app.post("/api/extension/track-application")
async def track_application(
    application: dict,
    x_api_key: Optional[str] = Header(None)
):
    """
    Track a job application from the extension
    Stores in memory and optionally syncs to Google Sheets
    """
    global next_app_id
    
    try:
        # Extract application data
        company_name = application.get('company_name', 'Unknown Company')
        position = application.get('position', 'Unknown Position')
        job_url = application.get('job_url', '')
        application_url = application.get('application_url', '')
        submission_data = application.get('submission_data', {})
        status = application.get('status', 'submitted')
        notes = application.get('notes', '')
        
        # Create application record
        app_record = {
            'id': next_app_id,
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
        
        # Save to in-memory storage
        applications_db.append(app_record)
        application_id = next_app_id
        next_app_id += 1
        
        print(f"✓ Application saved to memory: {company_name} - {position} (ID: {application_id})")
        
        # Sync to Google Sheets if available
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
                    print(f"✓ Synced to Google Sheets: {company_name} - {position}")
                    sheets_synced = True
                else:
                    print(f"⚠ Google Sheets sync failed for: {company_name} - {position}")
                    
            except Exception as sheets_error:
                print(f"⚠ Google Sheets error: {sheets_error}")
        
        return {
            "success": True,
            "message": "Application tracked successfully",
            "application_id": application_id,
            "company_name": company_name,
            "position": position,
            "storage": "in-memory",
            "synced_to_sheets": sheets_synced
        }
        
    except Exception as e:
        print(f"✗ Error tracking application: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track application: {str(e)}"
        )

@app.get("/api/extension/health")
async def extension_health():
    """Health check for extension connectivity"""
    return {
        "status": "ok",
        "storage": "in-memory",
        "google_sheets_connected": SHEETS_AVAILABLE,
        "message": "Extension API is ready (in-memory mode)"
    }

@app.get("/api/applications")
async def get_applications():
    """Get all applications from memory"""
    return {
        "applications": applications_db,
        "count": len(applications_db),
        "storage": "in-memory"
    }

@app.delete("/api/applications/{application_id}")
async def delete_application(application_id: int):
    """Delete an application from memory"""
    global applications_db
    applications_db = [app for app in applications_db if app['id'] != application_id]
    return {"message": "Application deleted", "id": application_id}

@app.delete("/api/applications/clear")
async def clear_applications():
    """Clear all applications (useful for testing)"""
    global applications_db, next_app_id
    count = len(applications_db)
    applications_db = []
    next_app_id = 1
    return {"message": f"Cleared {count} applications", "count": count}

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*60)
    print("ApplyEase Backend - In-Memory Edition")
    print("="*60)
    print(f"Storage: In-Memory (data lost on restart)")
    print(f"Google Sheets: {'Connected' if SHEETS_AVAILABLE else 'Disabled'}")
    print(f"Server: http://localhost:8001")
    print(f"Docs: http://localhost:8001/docs")
    print("="*60)
    print("Server ready to track applications")
    print("="*60 + "\n")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting ApplyEase In-Memory Server...")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )

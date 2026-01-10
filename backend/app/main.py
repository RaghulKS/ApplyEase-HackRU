from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from dotenv import load_dotenv
import os

from app.api import auth, profile, resume, applications, chatbot, fields, ml_insights, extension
from app.models.snowflake_db import init_db, SnowflakeConnection
from app.ml.field_classifier import FieldClassifier
from app.utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__)

field_classifier = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global field_classifier
    
    logger.info("Starting ApplyEase Backend...")
    
    try:
        logger.info("Initializing Snowflake connection...")
        init_db()
        logger.info("Snowflake initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Snowflake: {e}")
        logger.warning("Backend will continue without database")
    
    # Initialize ML models (with error handling)
    try:
        logger.info("Loading ML models...")
        field_classifier = FieldClassifier()
        field_classifier.load_or_train()
        logger.info("ML models loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML models: {e}")
        logger.warning("Backend will continue without ML classification")
        logger.warning("To fix: pip install --upgrade torch transformers sentence-transformers")
        field_classifier = None
    
    logger.info("ApplyEase Backend started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ApplyEase Backend...")
    try:
        SnowflakeConnection.close_pool()
    except:
        pass

app = FastAPI(
    title="ApplyEase API",
    description="AI-powered job application automation system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your extension ID
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(profile.router, prefix="/api/profile", tags=["User Profile"])
app.include_router(resume.router, prefix="/api/resume", tags=["Resume"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Chatbot"])
app.include_router(fields.router, prefix="/api/fields", tags=["Field Detection"])
app.include_router(ml_insights.router, prefix="/api/ml/insights", tags=["ML Insights"])
app.include_router(extension.router, prefix="/api/extension", tags=["Extension API"])

@app.get("/")
async def root():
    return {
        "message": "ApplyEase API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "field_classifier": "loaded" if field_classifier else "not loaded"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("API_HOST", "127.0.0.1"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=True
    )



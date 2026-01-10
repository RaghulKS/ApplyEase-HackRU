from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
import time

from app.models.snowflake_db import SnowflakeHelper, SnowflakeConnection
from app.models.schemas import ChatRequest, ChatResponse, SavedResponseCreate, SavedResponseResponse
from app.utils.auth import get_current_user_snowflake
from app.services.chatbot import ApplicationChatbot

router = APIRouter()
chatbot = ApplicationChatbot()

@router.post("/generate", response_model=ChatResponse)
async def generate_response(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Generate AI response for a unique field with context from resume"""
    user_id = current_user['ID']
    start_time = time.time()
    
    # Get user's primary resume for context
    resume = SnowflakeHelper.get_primary_resume(user_id)
    
    resume_context = {}
    if resume:
        resume_context = {
            'name': resume.get('NAME'),
            'email': resume.get('EMAIL'),
            'phone': resume.get('PHONE'),
            'education': resume.get('EDUCATION'),
            'experience': resume.get('EXPERIENCE'),
            'skills': resume.get('SKILLS'),
            'certifications': resume.get('CERTIFICATIONS')
        }
    
    # Check if similar field was answered before
    field_label = request.field_info.get('label', '')
    previous_responses = SnowflakeHelper.find_similar_unique_fields(user_id, field_label, limit=5)
    
    previous_responses_data = [
        {'field_label': r['FIELD_LABEL'], 'response': r['FINAL_RESPONSE'] or r['AI_GENERATED_RESPONSE']}
        for r in previous_responses
        if r.get('FINAL_RESPONSE') or r.get('AI_GENERATED_RESPONSE')
    ]
    
    # Generate AI response with ML insights
    result = chatbot.generate_response(
        field_info=request.field_info,
        resume_context=resume_context,
        company_info=request.field_info.get('company_info'),
        previous_responses=previous_responses_data,
        user_input=request.messages[-1].content if request.messages else None,
        user_id=user_id  # Pass user_id to get ML insights
    )
    
    # Log the ML prediction
    execution_time = (time.time() - start_time) * 1000
    SnowflakeHelper.log_ml_prediction({
        'user_id': user_id,
        'model_name': 'gemini-chatbot',
        'model_version': '1.0',
        'input_data': {
            'field_info': request.field_info,
            'messages': [{'role': m.role, 'content': m.content} for m in request.messages] if request.messages else []
        },
        'output_data': result,
        'prediction_type': 'unique_field_response',
        'confidence_score': result.get('confidence', 0.0),
        'execution_time_ms': execution_time,
        'success': True
    })
    
    return ChatResponse(**result)

@router.post("/save-unique-field")
async def save_unique_field_response(
    field_label: str,
    field_type: Optional[str] = None,
    user_response: Optional[str] = None,
    ai_response: Optional[str] = None,
    final_response: Optional[str] = None,
    company: Optional[str] = None,
    position: Optional[str] = None,
    field_context: Optional[dict] = None,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Save a unique field response for future reference"""
    user_id = current_user['ID']
    
    field_data = {
        'user_id': user_id,
        'field_label': field_label,
        'field_type': field_type,
        'field_context': field_context or {},
        'user_response': user_response,
        'ai_generated_response': ai_response,
        'final_response': final_response or user_response or ai_response,
        'company': company,
        'position': position,
        'confidence_score': 0.85,
        'embedding': []  # TODO: Add embedding generation
    }
    
    response_id = SnowflakeHelper.save_unique_field_response(field_data)
    
    return {
        "id": response_id,
        "message": "Unique field response saved successfully",
        "field_label": field_label
    }

@router.get("/unique-fields")
async def get_unique_field_responses(
    field_label: Optional[str] = None,
    company: Optional[str] = None,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Get saved unique field responses"""
    user_id = current_user['ID']
    
    if field_label:
        responses = SnowflakeHelper.find_similar_unique_fields(user_id, field_label)
    else:
        query = "SELECT * FROM unique_fields WHERE user_id = %s"
        params = [user_id]
        
        if company:
            query += " AND company = %s"
            params.append(company)
        
        query += " ORDER BY created_at DESC LIMIT 50"
        responses = SnowflakeConnection.execute_query(query, tuple(params))
    
    return [
        {
            "id": r['ID'],
            "field_label": r['FIELD_LABEL'],
            "field_type": r['FIELD_TYPE'],
            "final_response": r['FINAL_RESPONSE'],
            "ai_generated_response": r['AI_GENERATED_RESPONSE'],
            "company": r['COMPANY'],
            "position": r['POSITION'],
            "usage_count": r['USAGE_COUNT'],
            "created_at": r['CREATED_AT']
        }
        for r in responses
    ]

@router.post("/learn")
async def learn_from_feedback(
    field_info: dict,
    original: str,
    edited: str,
    field_label: str,
    company: Optional[str] = None,
    position: Optional[str] = None,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """Learn from user edits and feedback - saves to unique_fields table"""
    user_id = current_user['ID']
    
    # Calculate improvement
    result = chatbot.learn_from_feedback(
        field_info=field_info,
        original_response=original,
        edited_response=edited,
        feedback=feedback
    )
    
    # Save the edited response to unique_fields
    field_data = {
        'user_id': user_id,
        'field_label': field_label,
        'field_type': field_info.get('type'),
        'field_context': field_info,
        'ai_generated_response': original,
        'user_response': edited,
        'final_response': edited,
        'company': company,
        'position': position,
        'confidence_score': result.get('improvement_ratio', 0.5),
        'embedding': []
    }
    
    SnowflakeHelper.save_unique_field_response(field_data)
    
    # Log ML feedback
    SnowflakeHelper.log_ml_prediction({
        'user_id': user_id,
        'model_name': 'gemini-chatbot',
        'model_version': '1.0',
        'input_data': {'original': original, 'field_info': field_info},
        'output_data': {'edited': edited, 'improvement': result},
        'prediction_type': 'user_feedback',
        'confidence_score': result.get('improvement_ratio', 0.5),
        'execution_time_ms': 0,
        'success': True
    })
    
    return {"message": "Feedback recorded and saved", "improvement": result}

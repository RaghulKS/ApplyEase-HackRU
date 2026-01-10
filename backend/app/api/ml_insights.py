from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.ml.insights_engine import get_ml_insights
from app.utils.auth import get_current_user_snowflake

router = APIRouter()

@router.get("/field-classification")
async def get_field_classification_insights(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user_snowflake)
):
    """
    Get insights from field classification predictions
    """
    user_id = current_user['ID']
    insights_engine = get_ml_insights()
    
    try:
        insights = insights_engine.get_field_classification_insights(user_id=user_id, days=days)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/unique-fields")
async def get_unique_field_insights(
    field_label: Optional[str] = None,
    current_user: dict = Depends(get_current_user_snowflake)
):
    """
    Get insights about unique field responses
    """
    user_id = current_user['ID']
    insights_engine = get_ml_insights()
    
    try:
        insights = insights_engine.get_unique_field_insights(user_id=user_id, field_label=field_label)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/chatbot-performance")
async def get_chatbot_performance_insights(
    days: int = Query(default=30, ge=1, le=365),
    current_user: dict = Depends(get_current_user_snowflake)
):
    """
    Get insights about chatbot performance
    """
    user_id = current_user['ID']
    insights_engine = get_ml_insights()
    
    try:
        insights = insights_engine.get_chatbot_performance_insights(user_id=user_id, days=days)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/aggregated")
async def get_aggregated_insights(
    current_user: dict = Depends(get_current_user_snowflake)
):
    """
    Get comprehensive aggregated insights for the user
    """
    user_id = current_user['ID']
    insights_engine = get_ml_insights()
    
    try:
        insights = insights_engine.get_aggregated_insights(user_id=user_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@router.get("/recommendations")
async def get_learning_recommendations(
    current_user: dict = Depends(get_current_user_snowflake)
):
    """
    Get personalized recommendations based on ML insights
    """
    user_id = current_user['ID']
    insights_engine = get_ml_insights()
    
    try:
        recommendations = insights_engine.get_learning_recommendations(user_id=user_id)
        return {
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

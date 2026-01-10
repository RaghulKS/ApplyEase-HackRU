"""
ML Insights Engine - Aggregates and provides insights from ML training data
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict

from app.models.snowflake_db import SnowflakeConnection
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class MLInsightsEngine:
    """
    Aggregates ML predictions and provides insights for AI responses
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 300  # 5 minutes cache
    
    def get_field_classification_insights(self, user_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get insights from field classification predictions
        
        Args:
            user_id: Optional user_id to filter by specific user
            days: Number of days to look back (default 30)
        
        Returns:
            Dictionary containing aggregated insights
        """
        cache_key = f"field_insights_{user_id}_{days}"
        
        # Check cache
        if cache_key in self.cache and cache_key in self.cache_expiry:
            if datetime.now() < self.cache_expiry[cache_key]:
                logger.info(f"Returning cached insights for {cache_key}")
                return self.cache[cache_key]
        
        try:
            # Query ML logs for field classification
            query = """
                SELECT 
                    user_id,
                    input_data,
                    output_data,
                    confidence_score,
                    field_classification,
                    execution_time_ms,
                    created_at
                FROM ml_logs
                WHERE prediction_type = 'field_classification'
                AND created_at >= DATEADD(day, -%s, CURRENT_TIMESTAMP())
            """
            params = [days]
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC LIMIT 1000"
            
            results = SnowflakeConnection.execute_query(query, tuple(params))
            
            # Aggregate insights
            insights = {
                'total_predictions': len(results),
                'average_confidence': 0.0,
                'average_execution_time': 0.0,
                'field_type_distribution': defaultdict(int),
                'category_distribution': defaultdict(int),
                'common_field_patterns': defaultdict(int),
                'unique_field_trends': [],
                'performance_metrics': {
                    'high_confidence_rate': 0.0,
                    'fast_predictions': 0
                }
            }
            
            if not results:
                return insights
            
            # Process results
            total_confidence = 0
            total_execution = 0
            high_confidence_count = 0
            unique_field_labels = defaultdict(int)
            
            for row in results:
                # Confidence
                confidence = row.get('CONFIDENCE_SCORE', 0)
                total_confidence += confidence
                if confidence > 0.8:
                    high_confidence_count += 1
                
                # Execution time
                exec_time = row.get('EXECUTION_TIME_MS', 0)
                total_execution += exec_time
                if exec_time < 100:  # Fast predictions under 100ms
                    insights['performance_metrics']['fast_predictions'] += 1
                
                # Field classification data
                field_class = row.get('FIELD_CLASSIFICATION', {})
                if isinstance(field_class, dict):
                    insights['field_type_distribution']['standard'] += field_class.get('standard_count', 0)
                    insights['field_type_distribution']['unique'] += field_class.get('unique_count', 0)
                
                # Output data analysis
                output = row.get('OUTPUT_DATA', {})
                if isinstance(output, dict):
                    # Analyze standard fields
                    for field in output.get('standard_fields', []):
                        category = field.get('classification', {}).get('category')
                        if category:
                            insights['category_distribution'][category] += 1
                    
                    # Analyze unique fields
                    for field in output.get('unique_fields', []):
                        label = field.get('label', '').lower()
                        if label:
                            unique_field_labels[label] += 1
            
            # Calculate averages
            insights['average_confidence'] = total_confidence / len(results) if results else 0
            insights['average_execution_time'] = total_execution / len(results) if results else 0
            insights['performance_metrics']['high_confidence_rate'] = high_confidence_count / len(results) if results else 0
            
            # Get most common unique field patterns
            insights['unique_field_trends'] = [
                {'label': label, 'frequency': count}
                for label, count in sorted(unique_field_labels.items(), key=lambda x: x[1], reverse=True)[:10]
            ]
            
            # Convert defaultdicts to regular dicts for JSON serialization
            insights['field_type_distribution'] = dict(insights['field_type_distribution'])
            insights['category_distribution'] = dict(insights['category_distribution'])
            
            # Cache the results
            self.cache[cache_key] = insights
            self.cache_expiry[cache_key] = datetime.now() + timedelta(seconds=self.cache_ttl)
            
            logger.info(f"Generated field classification insights: {insights['total_predictions']} predictions analyzed")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get field classification insights: {e}")
            return {
                'error': str(e),
                'total_predictions': 0
            }
    
    def get_unique_field_insights(self, user_id: int, field_label: Optional[str] = None) -> Dict[str, Any]:
        """
        Get insights for unique field responses for a specific user
        
        Args:
            user_id: User ID to get insights for
            field_label: Optional field label to filter
        
        Returns:
            Insights about user's unique field response patterns
        """
        try:
            # Get unique field responses
            query = """
                SELECT 
                    field_label,
                    field_type,
                    company,
                    position,
                    confidence_score,
                    usage_count,
                    LENGTH(final_response) as response_length,
                    created_at,
                    last_used
                FROM unique_fields
                WHERE user_id = %s
            """
            params = [user_id]
            
            if field_label:
                query += " AND LOWER(field_label) LIKE LOWER(%s)"
                params.append(f"%{field_label}%")
            
            query += " ORDER BY created_at DESC LIMIT 500"
            
            results = SnowflakeConnection.execute_query(query, tuple(params))
            
            insights = {
                'total_saved_responses': len(results),
                'field_type_breakdown': defaultdict(int),
                'average_response_length': 0,
                'most_common_questions': [],
                'reusability_score': 0.0,
                'confidence_trend': 0.0,
                'recent_activity': []
            }
            
            if not results:
                return insights
            
            # Analyze patterns
            total_length = 0
            total_usage = 0
            total_confidence = 0
            field_frequencies = defaultdict(int)
            
            for row in results:
                field_frequencies[row.get('FIELD_LABEL', 'Unknown')] += 1
                total_length += row.get('RESPONSE_LENGTH', 0)
                total_usage += row.get('USAGE_COUNT', 0)
                total_confidence += row.get('CONFIDENCE_SCORE', 0)
                
                # Track field types
                field_type = row.get('FIELD_TYPE', 'text')
                insights['field_type_breakdown'][field_type] += 1
            
            # Calculate metrics
            insights['average_response_length'] = total_length / len(results) if results else 0
            insights['reusability_score'] = total_usage / len(results) if results else 0
            insights['confidence_trend'] = total_confidence / len(results) if results else 0
            
            # Most common questions
            insights['most_common_questions'] = [
                {'question': label, 'frequency': count}
                for label, count in sorted(field_frequencies.items(), key=lambda x: x[1], reverse=True)[:5]
            ]
            
            # Recent activity
            insights['recent_activity'] = [
                {
                    'field': row.get('FIELD_LABEL'),
                    'company': row.get('COMPANY'),
                    'position': row.get('POSITION'),
                    'date': row.get('CREATED_AT')
                }
                for row in results[:5]
            ]
            
            insights['field_type_breakdown'] = dict(insights['field_type_breakdown'])
            
            logger.info(f"Generated unique field insights for user {user_id}: {insights['total_saved_responses']} responses")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get unique field insights: {e}")
            return {
                'error': str(e),
                'total_saved_responses': 0
            }
    
    def get_chatbot_performance_insights(self, user_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """
        Get insights about chatbot performance and response quality
        """
        try:
            query = """
                SELECT 
                    user_id,
                    confidence_score,
                    execution_time_ms,
                    success,
                    output_data,
                    created_at
                FROM ml_logs
                WHERE prediction_type = 'unique_field_response'
                AND created_at >= DATEADD(day, -%s, CURRENT_TIMESTAMP())
            """
            params = [days]
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC LIMIT 1000"
            
            results = SnowflakeConnection.execute_query(query, tuple(params))
            
            insights = {
                'total_generations': len(results),
                'success_rate': 0.0,
                'average_confidence': 0.0,
                'average_response_time': 0.0,
                'quality_metrics': {
                    'high_quality_responses': 0,
                    'requires_review_count': 0
                },
                'usage_trend': []
            }
            
            if not results:
                return insights
            
            # Analyze
            success_count = 0
            total_confidence = 0
            total_time = 0
            high_quality = 0
            requires_review = 0
            
            for row in results:
                if row.get('SUCCESS'):
                    success_count += 1
                
                confidence = row.get('CONFIDENCE_SCORE', 0)
                total_confidence += confidence
                if confidence > 0.85:
                    high_quality += 1
                
                total_time += row.get('EXECUTION_TIME_MS', 0)
                
                output = row.get('OUTPUT_DATA', {})
                if isinstance(output, dict) and output.get('requires_review'):
                    requires_review += 1
            
            insights['success_rate'] = success_count / len(results) if results else 0
            insights['average_confidence'] = total_confidence / len(results) if results else 0
            insights['average_response_time'] = total_time / len(results) if results else 0
            insights['quality_metrics']['high_quality_responses'] = high_quality
            insights['quality_metrics']['requires_review_count'] = requires_review
            
            logger.info(f"Generated chatbot performance insights: {insights['total_generations']} generations analyzed")
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get chatbot performance insights: {e}")
            return {
                'error': str(e),
                'total_generations': 0
            }
    
    def get_aggregated_insights(self, user_id: int) -> Dict[str, Any]:
        """
        Get comprehensive insights for a user to inform AI responses
        
        This is called by the chatbot before generating responses
        """
        logger.info(f"Aggregating insights for user {user_id}")
        
        return {
            'field_classification': self.get_field_classification_insights(user_id=user_id, days=30),
            'unique_fields': self.get_unique_field_insights(user_id=user_id),
            'chatbot_performance': self.get_chatbot_performance_insights(user_id=user_id, days=30),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_learning_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Provide recommendations based on ML insights
        """
        insights = self.get_aggregated_insights(user_id)
        recommendations = []
        
        # Check unique field patterns
        unique_insights = insights.get('unique_fields', {})
        if unique_insights.get('total_saved_responses', 0) < 5:
            recommendations.append({
                'type': 'data_collection',
                'priority': 'high',
                'message': 'Save more unique field responses to improve AI suggestions',
                'action': 'Continue applying to jobs and saving your responses'
            })
        
        # Check reusability
        reusability = unique_insights.get('reusability_score', 0)
        if reusability < 1.0:
            recommendations.append({
                'type': 'optimization',
                'priority': 'medium',
                'message': 'Your responses could be more reusable across applications',
                'action': 'Consider creating more general responses that work for multiple companies'
            })
        
        # Check confidence
        chatbot_insights = insights.get('chatbot_performance', {})
        avg_confidence = chatbot_insights.get('average_confidence', 0)
        if avg_confidence < 0.7:
            recommendations.append({
                'type': 'quality',
                'priority': 'high',
                'message': 'AI confidence is lower than optimal',
                'action': 'Provide more detailed profile and resume information'
            })
        
        return recommendations


# Global instance for easy access
_insights_engine = None

def get_ml_insights() -> MLInsightsEngine:
    """Get the global ML insights engine instance"""
    global _insights_engine
    if _insights_engine is None:
        _insights_engine = MLInsightsEngine()
    return _insights_engine

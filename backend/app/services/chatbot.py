import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
import json

from app.utils.logger import setup_logger
from app.ml.insights_engine import get_ml_insights

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain


load_dotenv()
logger = setup_logger(__name__)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class ApplicationChatbot:
    """AI chatbot for generating application responses"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("Gemini API key not found. Chatbot will use fallback responses.")
            self.llm = None
        else:
            genai.configure(api_key=self.api_key)
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=self.api_key,
                temperature=0.7,
                max_output_tokens=500
            )
        
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # System prompt for the chatbot
        self.system_prompt = """
        You are an AI assistant helping users fill out job application forms.
        Your role is to generate appropriate, professional responses based on:
        1. The user's resume and profile information
        2. The specific field/question being asked
        3. The company and position being applied for
        4. Previous successful responses
        
        Guidelines:
        - Be concise and relevant (most fields have character limits)
        - Maintain a professional yet personable tone
        - Tailor responses to the specific company/role when possible
        - Use concrete examples from the user's experience
        - Avoid generic or clichéd responses
        - If unsure, ask for clarification
        """
    
    def generate_response(
        self,
        field_info: Dict[str, Any],
        resume_context: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None,
        previous_responses: Optional[List[Dict[str, Any]]] = None,
        user_input: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate a response for a specific field"""
        
        if not self.llm:
            return self._generate_fallback_response(field_info, resume_context)
        
        try:
            # Get ML insights if user_id provided
            ml_insights = None
            if user_id:
                insights_engine = get_ml_insights()
                ml_insights = insights_engine.get_aggregated_insights(user_id)
                logger.info(f"Retrieved ML insights for user {user_id}")
            
            # Prepare context with ML insights
            context = self._prepare_context(
                field_info, resume_context, company_info, previous_responses, ml_insights
            )
            
            # Create the prompt
            prompt = self._create_prompt(context, user_input)
            
            # Generate response
            response = self.llm.predict(prompt)
            
            # Post-process response
            response = self._post_process_response(response, field_info)
            
            return {
                'response': response,
                'confidence': 0.85,
                'suggestions': self._generate_suggestions(field_info, resume_context),
                'requires_review': self._should_review(field_info),
                'ml_insights_used': ml_insights is not None
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_fallback_response(field_info, resume_context)
    
    def _prepare_context(
        self,
        field_info: Dict[str, Any],
        resume_context: Dict[str, Any],
        company_info: Optional[Dict[str, Any]],
        previous_responses: Optional[List[Dict[str, Any]]],
        ml_insights: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare context for the LLM"""
        context = {
            'field': {
                'label': field_info.get('label', ''),
                'type': field_info.get('type', ''),
                'max_length': field_info.get('maxLength', 500),
                'placeholder': field_info.get('placeholder', '')
            },
            'user': {
                'name': resume_context.get('name', ''),
                'skills': resume_context.get('skills', []),
                'education': resume_context.get('education', []),
                'experience': resume_context.get('experience', [])
            }
        }
        
        if company_info:
            context['company'] = {
                'name': company_info.get('name', ''),
                'position': company_info.get('position', ''),
                'description': company_info.get('description', '')
            }
        
        if previous_responses:
            # Include similar previous responses
            context['similar_responses'] = previous_responses[:3]
        
        if ml_insights:
            # Include ML insights for better response generation
            unique_insights = ml_insights.get('unique_fields', {})
            context['ml_insights'] = {
                'common_questions': unique_insights.get('most_common_questions', [])[:3],
                'average_response_length': unique_insights.get('average_response_length', 0),
                'field_trends': ml_insights.get('field_classification', {}).get('unique_field_trends', [])[:5]
            }
        
        return context
    
    def _create_prompt(self, context: Dict[str, Any], user_input: Optional[str]) -> str:
        """Create prompt for the LLM"""
        prompt_parts = [
            self.system_prompt,
            f"\nField to fill: {context['field']['label']}",
            f"Field type: {context['field']['type']}",
            f"Max length: {context['field'].get('max_length', 'No limit')}"
        ]
        
        if context['field'].get('placeholder'):
            prompt_parts.append(f"Placeholder text: {context['field']['placeholder']}")
        
        # Add user context
        prompt_parts.append(f"\nUser Information:")
        prompt_parts.append(f"Name: {context['user']['name']}")
        
        if context['user']['skills']:
            prompt_parts.append(f"Skills: {', '.join(context['user']['skills'][:10])}")
        
        if context['user']['education']:
            edu = context['user']['education'][0]
            prompt_parts.append(f"Education: {edu.get('degree', 'Degree')} from {edu.get('institution', 'University')}")
        
        if context['user']['experience']:
            exp = context['user']['experience'][0]
            prompt_parts.append(f"Recent Experience: {exp.get('position', 'Position')} at {exp.get('company', 'Company')}")
        
        # Add company context if available
        if 'company' in context:
            prompt_parts.append(f"\nCompany: {context['company']['name']}")
            prompt_parts.append(f"Position: {context['company']['position']}")
        
        # Add user input if provided
        if user_input:
            prompt_parts.append(f"\nUser's input/guidance: {user_input}")
        
        # Add similar responses if available
        if 'similar_responses' in context:
            prompt_parts.append("\nSimilar successful responses:")
            for resp in context['similar_responses']:
                prompt_parts.append(f"- {resp.get('response', '')}")
        
        # Add ML insights if available
        if 'ml_insights' in context:
            ml_insights = context['ml_insights']
            if ml_insights.get('average_response_length'):
                prompt_parts.append(f"\nTypical response length: {int(ml_insights['average_response_length'])} characters")
            
            if ml_insights.get('common_questions'):
                prompt_parts.append("\nCommon questions you've answered successfully:")
                for q in ml_insights['common_questions']:
                    prompt_parts.append(f"- {q.get('question', '')}")
        
        prompt_parts.append("\nGenerate an appropriate response for this field:")
        
        return "\n".join(prompt_parts)
    
    def _post_process_response(self, response: str, field_info: Dict[str, Any]) -> str:
        """Post-process the generated response"""
        # Trim to max length if specified
        max_length = field_info.get('maxLength')
        if max_length and len(response) > max_length:
            response = response[:max_length-3] + "..."
        
        # Clean up response
        response = response.strip()
        
        # Remove any prompt artifacts
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        return response
    
    def _generate_suggestions(self, field_info: Dict[str, Any], resume_context: Dict[str, Any]) -> List[str]:
        """Generate alternative suggestions"""
        suggestions = []
        
        field_label = field_info.get('label', '').lower()
        
        # Generate suggestions based on field type
        if 'why' in field_label or 'interest' in field_label:
            suggestions = [
                "Mention specific projects or technologies the company uses",
                "Reference the company's mission or values",
                "Connect your experience to the role requirements"
            ]
        elif 'experience' in field_label or 'project' in field_label:
            suggestions = [
                "Use the STAR method (Situation, Task, Action, Result)",
                "Quantify your achievements with numbers",
                "Focus on relevant technical skills"
            ]
        elif 'strength' in field_label or 'skill' in field_label:
            suggestions = [
                "Provide specific examples",
                "Relate to job requirements",
                "Show continuous learning"
            ]
        
        return suggestions[:3]
    
    def _should_review(self, field_info: Dict[str, Any]) -> bool:
        """Determine if the response should be reviewed by user"""
        # Always review certain types of fields
        review_keywords = ['salary', 'compensation', 'visa', 'authorization', 'criminal', 'legal']
        field_label = field_info.get('label', '').lower()
        
        return any(keyword in field_label for keyword in review_keywords)
    
    def _generate_fallback_response(self, field_info: Dict[str, Any], resume_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback response when LLM is not available"""
        field_label = field_info.get('label', '').lower()
        response = ""
        
        # Generate template responses based on field type
        if 'why' in field_label and 'company' in field_label:
            response = "I am excited about the opportunity to contribute to your team with my skills in [relevant skills]. Your company's work in [company focus] aligns with my career goals."
        elif 'why' in field_label and 'role' in field_label:
            response = "This role aligns perfectly with my background in [relevant experience] and my passion for [relevant field]."
        elif 'experience' in field_label:
            if resume_context.get('experience'):
                exp = resume_context['experience'][0]
                response = f"In my role as {exp.get('position', 'Professional')} at {exp.get('company', 'my previous company')}, I {exp.get('description', 'gained valuable experience')}."
        elif 'strength' in field_label:
            skills = resume_context.get('skills', [])
            if skills:
                response = f"My key strengths include {', '.join(skills[:3])} which I've developed through hands-on experience."
        else:
            response = "[Please provide your response here]"
        
        return {
            'response': response,
            'confidence': 0.5,
            'suggestions': self._generate_suggestions(field_info, resume_context),
            'requires_review': True,
            'is_fallback': True
        }
    
    def learn_from_feedback(
        self,
        field_info: Dict[str, Any],
        original_response: str,
        edited_response: str,
        feedback: Optional[str] = None
    ):
        """Learn from user edits and feedback"""
        # Store the edited response for future reference
        learning_data = {
            'field': field_info,
            'original': original_response,
            'edited': edited_response,
            'feedback': feedback,
            'improvement_ratio': self._calculate_improvement(original_response, edited_response)
        }
        
        # In a real implementation, this would update the model or fine-tune it
        logger.info(f"Learning from user feedback: {learning_data['improvement_ratio']:.2f} improvement")
        
        return learning_data
    
    def _calculate_improvement(self, original: str, edited: str) -> float:
        """Calculate improvement score between original and edited response"""
        if original == edited:
            return 0.0
        
        # Simple heuristic: longer responses with more specific content are better
        length_ratio = len(edited) / max(len(original), 1)
        
        # Check for more specific keywords
        specific_keywords = ['specifically', 'particularly', 'for example', 'such as', 'including']
        original_specificity = sum(1 for kw in specific_keywords if kw in original.lower())
        edited_specificity = sum(1 for kw in specific_keywords if kw in edited.lower())
        
        specificity_improvement = (edited_specificity - original_specificity) * 0.1
        
        return min(1.0, max(0.0, length_ratio * 0.5 + specificity_improvement + 0.3))
    
    def batch_generate(
        self,
        fields: List[Dict[str, Any]],
        resume_context: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate responses for multiple fields at once"""
        responses = []
        
        for field in fields:
            response = self.generate_response(
                field_info=field,
                resume_context=resume_context,
                company_info=company_info
            )
            responses.append({
                'field_id': field.get('id') or field.get('name'),
                'field_label': field.get('label'),
                **response
            })
        
        return responses

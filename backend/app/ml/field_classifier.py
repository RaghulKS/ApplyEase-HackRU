import os
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import json
from pathlib import Path
import time

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import sentence_transformers, but make it optional
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception as e:
    logger.warning(f"sentence_transformers not available: {e}")
    logger.warning("Field classification will use fallback method")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

class FieldClassifier:
    """ML model to classify form fields as standard or unique"""
    
    # Standard field categories that can be auto-filled
    STANDARD_FIELDS = {
        'personal': ['name', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'address', 'city', 'state', 'zip', 'country'],
        'education': ['school', 'university', 'degree', 'major', 'gpa', 'graduation', 'education'],
        'experience': ['company', 'position', 'title', 'employer', 'work_experience', 'years_experience'],
        'links': ['linkedin', 'github', 'portfolio', 'website', 'resume', 'cv'],
        'legal': ['work_authorization', 'visa_status', 'citizenship', 'eligible_to_work'],
        'demographics': ['gender', 'ethnicity', 'veteran_status', 'disability'],
        'availability': ['start_date', 'available_date', 'notice_period'],
        'compensation': ['salary', 'expected_salary', 'compensation', 'rate']
    }
    
    # Unique field indicators that require custom responses
    UNIQUE_INDICATORS = [
        'why', 'describe', 'tell us', 'explain', 'elaborate', 'essay',
        'cover letter', 'motivation', 'interest', 'passion', 'goal',
        'achievement', 'challenge', 'project', 'contribution', 'experience with',
        'how would you', 'what makes you', 'additional information'
    ]
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.encoder = SentenceTransformer(model_name)
            except Exception as e:
                logger.warning(f"Failed to load SentenceTransformer: {e}")
                self.encoder = None
        else:
            self.encoder = None
            
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model_path = Path(os.getenv("FIELD_CLASSIFIER_MODEL_PATH", "./backend/data/field_classifier.pkl"))
        self.training_data_path = Path("./backend/data/field_training_data.json")
        self.is_trained = False
        self.use_fallback = not SENTENCE_TRANSFORMERS_AVAILABLE
    
    def _extract_features(self, field_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from a field for classification"""
        # Get field properties
        field_name = field_data.get('name', '').lower()
        field_label = field_data.get('label', '').lower()
        field_type = field_data.get('type', '')
        placeholder = field_data.get('placeholder', '').lower()
        required = field_data.get('required', False)
        max_length = field_data.get('maxLength', 0)
        
        # Check for standard field indicators
        is_standard = 0
        for category, keywords in self.STANDARD_FIELDS.items():
            for keyword in keywords:
                if keyword in field_name or keyword in field_label:
                    is_standard = 1
                    break
        
        # Check for unique field indicators
        is_unique = 0
        for indicator in self.UNIQUE_INDICATORS:
            if indicator in field_label or indicator in placeholder:
                is_unique = 1
                break
        
        # Additional features
        is_text_area = 1 if field_type == 'textarea' else 0
        is_long_text = 1 if max_length > 200 else 0
        is_required = 1 if required else 0
        
        # Create text embedding
        if self.encoder is not None:
            # Use sentence transformer
            text = f"{field_name} {field_label} {placeholder}"
            text_embedding = self.encoder.encode(text)
        else:
            # Fallback: simple feature extraction
            text_embedding = self._simple_text_features(field_name, field_label, placeholder)
        
        # Combine all features
        features = np.concatenate([
            text_embedding,
            [is_standard, is_unique, is_text_area, is_long_text, is_required]
        ])
        
        return features
    
    def _simple_text_features(self, field_name: str, field_label: str, placeholder: str) -> np.ndarray:
        """Simple feature extraction when sentence transformers not available"""
        # Create a fixed-size feature vector (384 dimensions to match SentenceTransformer)
        features = np.zeros(384)
        
        # Simple heuristics
        text = f"{field_name} {field_label} {placeholder}".lower()
        
        # Check for key terms and set specific features
        key_terms = {
            'name': 0, 'email': 1, 'phone': 2, 'address': 3, 'education': 4,
            'experience': 5, 'skill': 6, 'linkedin': 7, 'github': 8, 'resume': 9,
            'why': 10, 'describe': 11, 'tell': 12, 'explain': 13, 'motivation': 14,
            'cover': 15, 'letter': 16, 'essay': 17, 'project': 18, 'achievement': 19
        }
        
        for term, idx in key_terms.items():
            if term in text:
                features[idx] = 1.0
        
        # Add text length features
        features[20] = len(field_name) / 100.0
        features[21] = len(field_label) / 100.0
        features[22] = len(placeholder) / 100.0
        
        return features
    
    def _generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data if no real data exists"""
        logger.info("Generating synthetic training data...")
        
        X = []
        y = []  # 0 = standard, 1 = unique
        
        # Generate standard field examples
        standard_examples = [
            {'name': 'full_name', 'label': 'Full Name', 'type': 'text'},
            {'name': 'email', 'label': 'Email Address', 'type': 'email'},
            {'name': 'phone', 'label': 'Phone Number', 'type': 'tel'},
            {'name': 'linkedin', 'label': 'LinkedIn URL', 'type': 'url'},
            {'name': 'graduation_date', 'label': 'Expected Graduation', 'type': 'date'},
            {'name': 'gpa', 'label': 'GPA', 'type': 'number'},
            {'name': 'work_authorization', 'label': 'Are you authorized to work in the US?', 'type': 'select'},
        ]
        
        for example in standard_examples:
            features = self._extract_features(example)
            X.append(features)
            y.append(0)  # Standard field
        
        # Generate unique field examples
        unique_examples = [
            {'name': 'cover_letter', 'label': 'Why do you want to work here?', 'type': 'textarea', 'maxLength': 500},
            {'name': 'motivation', 'label': 'Tell us about yourself', 'type': 'textarea', 'maxLength': 1000},
            {'name': 'project', 'label': 'Describe a challenging project you worked on', 'type': 'textarea'},
            {'name': 'interest', 'label': 'What interests you about this role?', 'type': 'textarea'},
            {'name': 'contribution', 'label': 'How would you contribute to our team?', 'type': 'textarea'},
            {'name': 'additional', 'label': 'Additional information you would like to share', 'type': 'textarea'},
        ]
        
        for example in unique_examples:
            features = self._extract_features(example)
            X.append(features)
            y.append(1)  # Unique field
        
        return np.array(X), np.array(y)
    
    def train(self, X: np.ndarray = None, y: np.ndarray = None):
        """Train the classifier"""
        if X is None or y is None:
            X, y = self._generate_training_data()
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.classifier.fit(X_train, y_train)
        accuracy = self.classifier.score(X_test, y_test)
        logger.info(f"Field classifier trained with accuracy: {accuracy:.2f}")
        
        self.is_trained = True
        self.save_model()
    
    def predict(self, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict if a field is standard or unique"""
        if not self.is_trained:
            logger.warning("Model not trained, loading or training...")
            self.load_or_train()
        
        features = self._extract_features(field_data)
        features = features.reshape(1, -1)
        
        prediction = self.classifier.predict(features)[0]
        probability = self.classifier.predict_proba(features)[0]
        
        field_type = 'unique' if prediction == 1 else 'standard'
        confidence = max(probability)
        
        # Determine specific field category if standard
        category = None
        if field_type == 'standard':
            field_name = field_data.get('name', '').lower()
            field_label = field_data.get('label', '').lower()
            
            for cat, keywords in self.STANDARD_FIELDS.items():
                for keyword in keywords:
                    if keyword in field_name or keyword in field_label:
                        category = cat
                        break
                if category:
                    break
        
        return {
            'field_type': field_type,
            'category': category,
            'confidence': float(confidence),
            'requires_user_input': field_type == 'unique'
        }
    
    def classify_fields(self, fields: List[Dict[str, Any]], user_id: Optional[int] = None, log_to_db: bool = True) -> Dict[str, Any]:
        """Classify multiple fields at once and optionally log to Snowflake"""
        start_time = time.time()
        
        results = {
            'standard_fields': [],
            'unique_fields': [],
            'field_mapping': {}
        }
        
        for field in fields:
            classification = self.predict(field)
            field_id = field.get('id') or field.get('name')
            
            enhanced_field = {
                **field,
                'classification': classification
            }
            
            if classification['field_type'] == 'standard':
                results['standard_fields'].append(enhanced_field)
            else:
                results['unique_fields'].append(enhanced_field)
            
            results['field_mapping'][field_id] = classification
        
        # Log to Snowflake if requested and user_id is provided
        if log_to_db and user_id:
            try:
                from app.models.snowflake_db import SnowflakeHelper
                
                execution_time = (time.time() - start_time) * 1000
                
                SnowflakeHelper.log_ml_prediction({
                    'user_id': user_id,
                    'model_name': 'field_classifier',
                    'model_version': '1.0',
                    'input_data': {'fields': fields},
                    'output_data': results,
                    'prediction_type': 'field_classification',
                    'confidence_score': sum(f['classification']['confidence'] for f in results['standard_fields'] + results['unique_fields']) / max(len(fields), 1),
                    'field_classification': {
                        'total_fields': len(fields),
                        'standard_count': len(results['standard_fields']),
                        'unique_count': len(results['unique_fields'])
                    },
                    'execution_time_ms': execution_time,
                    'success': True
                })
            except Exception as e:
                logger.warning(f"Failed to log ML prediction to Snowflake: {e}")
        
        return results
    
    def save_model(self):
        """Save the trained model"""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.classifier, f)
        logger.info(f"Model saved to {self.model_path}")
    
    def load_model(self) -> bool:
        """Load a previously trained model"""
        if self.model_path.exists():
            with open(self.model_path, 'rb') as f:
                self.classifier = pickle.load(f)
            self.is_trained = True
            logger.info(f"Model loaded from {self.model_path}")
            return True
        return False
    
    def load_or_train(self):
        """Load existing model or train a new one"""
        if not self.load_model():
            logger.info("No existing model found, training new model...")
            self.train()

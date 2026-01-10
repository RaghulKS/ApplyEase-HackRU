import PyPDF2
import fitz  # PyMuPDF
import re
import spacy
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
import docx

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ResumeParser:
    """Parse resume PDFs and extract structured information"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy model loaded successfully")
        except Exception as e:
            logger.warning(f"spaCy model not available: {e}")
            logger.warning("Resume parsing will work with limited NER capabilities")
            self.nlp = None
        
        # Common section headers in resumes
        self.section_headers = {
            'education': ['education', 'academic', 'qualification', 'degree'],
            'experience': ['experience', 'work', 'employment', 'professional', 'career'],
            'skills': ['skills', 'technical skills', 'competencies', 'expertise'],
            'projects': ['projects', 'portfolio', 'personal projects'],
            'certifications': ['certifications', 'certificates', 'licenses'],
            'achievements': ['achievements', 'accomplishments', 'awards', 'honors']
        }
        
        # Patterns for extracting specific information
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,5}[-\s\.]?[0-9]{3,5}'
        self.linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        self.github_pattern = r'github\.com/[\w-]+'
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from PDF file using PyMuPDF for better accuracy"""
        try:
            # Try PyMuPDF first (better extraction)
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed, trying PyPDF2: {e}")
            try:
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                return text
            except Exception as e2:
                logger.error(f"Error extracting text from PDF: {e2}")
                return ""
    
    def extract_text_from_docx(self, docx_path: str) -> str:
        """Extract text content from DOCX file"""
        try:
            doc = docx.Document(docx_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            return ""
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information from resume text"""
        contact_info = {
            'email': None,
            'phone': None,
            'linkedin': None,
            'github': None
        }
        
        # Extract email
        email_match = re.search(self.email_pattern, text)
        if email_match:
            contact_info['email'] = email_match.group()
        
        # Extract phone
        phone_match = re.search(self.phone_pattern, text)
        if phone_match:
            contact_info['phone'] = phone_match.group()
        
        # Extract LinkedIn
        linkedin_match = re.search(self.linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact_info['linkedin'] = f"https://{linkedin_match.group()}"
        
        # Extract GitHub
        github_match = re.search(self.github_pattern, text, re.IGNORECASE)
        if github_match:
            contact_info['github'] = f"https://{github_match.group()}"
        
        return contact_info
    
    def extract_name(self, text: str) -> Optional[str]:
        """Extract name from resume text using NER"""
        if self.nlp:
            doc = self.nlp(text[:500])  # Usually name is at the beginning
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    return ent.text
        
        # Fallback: Look for name-like pattern at the beginning
        lines = text.split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line.split()) <= 3 and not any(char.isdigit() for char in line):
                if not re.search(self.email_pattern, line):
                    return line
        
        return None
    
    def extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information"""
        education = []
        
        # Find education section
        education_section = self._extract_section(text, 'education')
        if not education_section:
            return education
        
        # Common degree patterns
        degree_patterns = [
            r'(Bachelor|B\.?S\.?|B\.?A\.?|Master|M\.?S\.?|M\.?A\.?|PhD|Ph\.?D\.?|MBA)[^\n]*',
            r'(Computer Science|Engineering|Business|Mathematics|Physics)[^\n]*'
        ]
        
        for pattern in degree_patterns:
            matches = re.finditer(pattern, education_section, re.IGNORECASE)
            for match in matches:
                degree_text = match.group()
                
                # Extract GPA if present
                gpa_match = re.search(r'GPA[:\s]*(\d+\.\d+)', degree_text, re.IGNORECASE)
                gpa = float(gpa_match.group(1)) if gpa_match else None
                
                # Extract year
                year_match = re.search(r'(20\d{2}|19\d{2})', degree_text)
                year = year_match.group() if year_match else None
                
                education.append({
                    'degree': degree_text,
                    'gpa': gpa,
                    'year': year
                })
        
        return education
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume"""
        skills = []
        
        # Find skills section
        skills_section = self._extract_section(text, 'skills')
        if not skills_section:
            # Fallback: Look for common programming languages and tools
            common_skills = [
                'Python', 'Java', 'JavaScript', 'C++', 'C#', 'SQL', 'HTML', 'CSS',
                'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring',
                'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'Git', 'Linux',
                'Machine Learning', 'Deep Learning', 'Data Science', 'AI'
            ]
            
            for skill in common_skills:
                if re.search(r'\b' + skill + r'\b', text, re.IGNORECASE):
                    skills.append(skill)
        else:
            # Parse skills section
            lines = skills_section.split('\n')
            for line in lines:
                # Split by common delimiters
                items = re.split(r'[,;|•]', line)
                for item in items:
                    item = item.strip()
                    if item and len(item) < 50:  # Avoid long sentences
                        skills.append(item)
        
        return list(set(skills))  # Remove duplicates
    
    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience"""
        experience = []
        
        # Find experience section
        exp_section = self._extract_section(text, 'experience')
        if not exp_section:
            return experience
        
        # Split into individual experiences
        # Look for patterns like company names, dates, positions
        lines = exp_section.split('\n')
        current_exp = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_exp:
                    experience.append(current_exp)
                    current_exp = {}
                continue
            
            # Check for date patterns (indicates new position)
            date_match = re.search(r'(\d{4}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]*(\d{4}|Present)', line, re.IGNORECASE)
            if date_match:
                if current_exp:
                    experience.append(current_exp)
                current_exp = {'dates': date_match.group(), 'description': []}
            elif current_exp:
                # Check if it's a position/company line
                if any(keyword in line.lower() for keyword in ['engineer', 'developer', 'analyst', 'manager', 'intern']):
                    current_exp['position'] = line
                elif any(keyword in line.lower() for keyword in ['inc', 'corp', 'llc', 'ltd', 'company']):
                    current_exp['company'] = line
                else:
                    # Add to description
                    if 'description' not in current_exp:
                        current_exp['description'] = []
                    current_exp['description'].append(line)
        
        if current_exp:
            experience.append(current_exp)
        
        # Clean up descriptions
        for exp in experience:
            if 'description' in exp and isinstance(exp['description'], list):
                exp['description'] = ' '.join(exp['description'])
        
        return experience
    
    def _extract_section(self, text: str, section_type: str) -> Optional[str]:
        """Extract a specific section from resume text"""
        keywords = self.section_headers.get(section_type, [])
        
        for keyword in keywords:
            pattern = rf'\b{keyword}\b[:\s]*\n([\s\S]*?)(?=\n[A-Z][^\n]*:|$)'
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1)
        
        return None
    
    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        """Parse resume and extract all information"""
        logger.info(f"Parsing resume: {file_path}")
        
        # Determine file type and extract text
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            text = self.extract_text_from_docx(file_path)
        else:
            logger.error(f"Unsupported file format: {file_extension}")
            return {}
        
        if not text:
            logger.error("Failed to extract text from resume")
            return {}
        
        # Extract contact information
        contact = self.extract_contact_info(text)
        
        # Extract structured information
        parsed_data = {
            'name': self.extract_name(text),
            'email': contact.get('email'),
            'phone': contact.get('phone'),
            'linkedin_url': contact.get('linkedin'),
            'github_url': contact.get('github'),
            'portfolio_url': None,  # Can be enhanced
            'education': self.extract_education(text),
            'experience': self.extract_experience(text),
            'skills': self.extract_skills(text),
            'certifications': [],  # Can be enhanced
            'raw_text': text,
            'parsed_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Resume parsed successfully: {parsed_data.get('name', 'Unknown')}")
        return parsed_data
    
    def enhance_with_nlp(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance parsed data with NLP analysis"""
        if not self.nlp:
            logger.warning("spaCy model not available, skipping NLP enhancement")
            return parsed_data
            
        text = parsed_data.get('raw_text', '')
        
        if not text:
            return parsed_data
        
        doc = self.nlp(text)
        
        # Extract entities
        entities = {}
        for ent in doc.ents:
            if ent.label_ not in entities:
                entities[ent.label_] = []
            entities[ent.label_].append(ent.text)
        
        parsed_data['entities'] = entities
        
        # Extract key phrases (noun chunks)
        key_phrases = [chunk.text for chunk in doc.noun_chunks if len(chunk.text.split()) > 1]
        parsed_data['key_phrases'] = key_phrases[:20]  # Top 20 phrases
        
        return parsed_data

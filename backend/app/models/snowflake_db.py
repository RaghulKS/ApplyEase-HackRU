import os
import snowflake.connector
from snowflake.connector import DictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import json
from datetime import datetime

from app.utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)

class SnowflakeConnection:
    _connection: Optional[snowflake.connector.SnowflakeConnection] = None
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def initialize_pool(cls, pool_size: int = 5):
        if cls._config is not None:
            logger.warning("Connection already initialized")
            return

        try:
            cls._config = {
                'user': os.getenv('SNOWFLAKE_USER'),
                'account': os.getenv('SNOWFLAKE_ACCOUNT'),
                'authenticator': 'oauth',
                'token': os.getenv('SNOWFLAKE_TOKEN'),
                'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
                'database': os.getenv('SNOWFLAKE_DATABASE'),
                'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
            }

            role = os.getenv('SNOWFLAKE_ROLE')
            if role:
                cls._config['role'] = role

            logger.info(f"Snowflake connection initialized using OAuth")


        except Exception as e:
            logger.error(f"Failed to initialize Snowflake connection: {e}")
            raise

    @classmethod
    @contextmanager
    def get_connection(cls):
        """Get a database connection"""
        if cls._config is None:
            cls.initialize_pool()

        conn = snowflake.connector.connect(**cls._config)
        try:
            yield conn
        finally:
            conn.close()

    @classmethod
    @contextmanager
    def get_cursor(cls, dict_cursor: bool = True):
        """Get a cursor from a connection"""
        with cls.get_connection() as conn:
            cursor_class = DictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_class)
            try:
                yield cursor
            finally:
                cursor.close()

    @classmethod
    def execute_query(cls, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results"""
        try:
            with cls.get_cursor() as cursor:
                cursor.execute(query, params or ())
                results = cursor.fetchall()
                return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    @classmethod
    def execute_update(cls, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query"""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                conn.commit()
                rowcount = cursor.rowcount
                cursor.close()
                return rowcount
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            raise

    @classmethod
    def execute_many(cls, query: str, data: List[tuple]) -> int:
        """Execute batch insert/update"""
        try:
            with cls.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(query, data)
                conn.commit()
                rowcount = cursor.rowcount
                cursor.close()
                return rowcount
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            raise

    @classmethod
    def close_pool(cls):
        """Close connection configuration"""
        cls._config = None
        cls._connection = None
        logger.info("Snowflake connection closed")


# Table initialization queries
def init_snowflake_tables():
    """Initialize all required Snowflake tables"""
    
    logger.info("Initializing Snowflake tables...")
    
    tables = {
        'users': """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
            )
        """,
        
        'resume_data': """
            CREATE TABLE IF NOT EXISTS resume_data (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                filename VARCHAR(500),
                parsed_content VARIANT,
                raw_text TEXT,
                name VARCHAR(255),
                email VARCHAR(255),
                phone VARCHAR(50),
                linkedin_url VARCHAR(500),
                github_url VARCHAR(500),
                portfolio_url VARCHAR(500),
                education VARIANT,
                experience VARIANT,
                skills VARIANT,
                certifications VARIANT,
                is_primary BOOLEAN DEFAULT FALSE,
                uploaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """,
        
        'applications': """
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                position VARCHAR(255) NOT NULL,
                job_url VARCHAR(1000),
                application_url VARCHAR(1000),
                status VARCHAR(50) DEFAULT 'pending',
                submission_data VARIANT,
                notes TEXT,
                submitted_at TIMESTAMP_NTZ,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """,
        
        'unique_fields': """
            CREATE TABLE IF NOT EXISTS unique_fields (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                field_label VARCHAR(500) NOT NULL,
                field_type VARCHAR(100),
                field_context VARIANT,
                user_response TEXT,
                ai_generated_response TEXT,
                final_response TEXT,
                company VARCHAR(255),
                position VARCHAR(255),
                confidence_score FLOAT,
                embedding VARIANT,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP_NTZ,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """,
        
        'ml_logs': """
            CREATE TABLE IF NOT EXISTS ml_logs (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id INTEGER,
                model_name VARCHAR(100),
                model_version VARCHAR(50),
                input_data VARIANT,
                output_data VARIANT,
                prediction_type VARCHAR(50),
                confidence_score FLOAT,
                field_classification VARIANT,
                performance_metrics VARIANT,
                execution_time_ms FLOAT,
                success BOOLEAN,
                error_message TEXT,
                created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """,
        
        'user_profiles': """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                phone VARCHAR(50),
                linkedin_url VARCHAR(500),
                github_url VARCHAR(500),
                portfolio_url VARCHAR(500),
                education VARIANT,
                experience VARIANT,
                skills VARIANT,
                certifications VARIANT,
                preferences VARIANT,
                updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
    }
    
    # Create tables
    for table_name, create_query in tables.items():
        try:
            SnowflakeConnection.execute_update(create_query)
            logger.info(f"Table '{table_name}' initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create table '{table_name}': {e}")
            raise
    
    # Create indexes for better performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_resume_user ON resume_data(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)",
        "CREATE INDEX IF NOT EXISTS idx_unique_fields_user ON unique_fields(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_unique_fields_label ON unique_fields(field_label)",
        "CREATE INDEX IF NOT EXISTS idx_ml_logs_user ON ml_logs(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_ml_logs_type ON ml_logs(prediction_type)"
    ]
    
    for index_query in indexes:
        try:
            SnowflakeConnection.execute_update(index_query)
        except Exception as e:
            # Index might already exist, that's okay
            logger.debug(f"Index creation skipped: {e}")
    
    logger.info("All Snowflake tables and indexes initialized successfully")


# Helper functions for common operations
class SnowflakeHelper:
    """Helper functions for Snowflake operations"""
    
    @staticmethod
    def json_to_variant(data: Any) -> str:
        """Convert Python dict/list to Snowflake VARIANT format"""
        if data is None:
            return 'NULL'
        return f"PARSE_JSON('{json.dumps(data)}')"
    
    @staticmethod
    def insert_user(email: str, full_name: str, hashed_password: str) -> int:
        """Insert new user and return ID"""
        query = """
            INSERT INTO users (email, full_name, hashed_password)
            VALUES (%s, %s, %s)
        """
        SnowflakeConnection.execute_update(query, (email, full_name, hashed_password))
        
        # Get the inserted ID
        result = SnowflakeConnection.execute_query(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )
        return result[0]['ID'] if result else None
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        result = SnowflakeConnection.execute_query(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
        return result[0] if result else None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        result = SnowflakeConnection.execute_query(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        return result[0] if result else None
    
    @staticmethod
    def insert_resume_data(user_id: int, resume_data: Dict[str, Any]) -> int:
        """Insert parsed resume data"""
        query = """
            INSERT INTO resume_data (
                user_id, filename, parsed_content, raw_text, name, email, phone,
                linkedin_url, github_url, portfolio_url, education, experience,
                skills, certifications, is_primary
            ) VALUES (
                %s, %s, PARSE_JSON(%s), %s, %s, %s, %s, %s, %s, %s,
                PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s), PARSE_JSON(%s), %s
            )
        """
        
        params = (
            user_id,
            resume_data.get('filename'),
            json.dumps(resume_data.get('parsed_content', {})),
            resume_data.get('raw_text'),
            resume_data.get('name'),
            resume_data.get('email'),
            resume_data.get('phone'),
            resume_data.get('linkedin_url'),
            resume_data.get('github_url'),
            resume_data.get('portfolio_url'),
            json.dumps(resume_data.get('education', [])),
            json.dumps(resume_data.get('experience', [])),
            json.dumps(resume_data.get('skills', [])),
            json.dumps(resume_data.get('certifications', [])),
            resume_data.get('is_primary', False)
        )
        
        SnowflakeConnection.execute_update(query, params)
        
        # Get the inserted ID
        result = SnowflakeConnection.execute_query(
            "SELECT id FROM resume_data WHERE user_id = %s ORDER BY uploaded_at DESC LIMIT 1",
            (user_id,)
        )
        return result[0]['ID'] if result else None
    
    @staticmethod
    def get_primary_resume(user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's primary resume"""
        result = SnowflakeConnection.execute_query(
            "SELECT * FROM resume_data WHERE user_id = %s AND is_primary = TRUE LIMIT 1",
            (user_id,)
        )
        return result[0] if result else None
    
    @staticmethod
    def log_ml_prediction(log_data: Dict[str, Any]) -> int:
        """Log ML model prediction"""
        query = """
            INSERT INTO ml_logs (
                user_id, model_name, model_version, input_data, output_data,
                prediction_type, confidence_score, field_classification,
                performance_metrics, execution_time_ms, success, error_message
            ) VALUES (
                %s, %s, %s, PARSE_JSON(%s), PARSE_JSON(%s), %s, %s,
                PARSE_JSON(%s), PARSE_JSON(%s), %s, %s, %s
            )
        """
        
        params = (
            log_data.get('user_id'),
            log_data.get('model_name'),
            log_data.get('model_version'),
            json.dumps(log_data.get('input_data', {})),
            json.dumps(log_data.get('output_data', {})),
            log_data.get('prediction_type'),
            log_data.get('confidence_score'),
            json.dumps(log_data.get('field_classification', {})),
            json.dumps(log_data.get('performance_metrics', {})),
            log_data.get('execution_time_ms'),
            log_data.get('success', True),
            log_data.get('error_message')
        )
        
        return SnowflakeConnection.execute_update(query, params)
    
    @staticmethod
    def save_unique_field_response(field_data: Dict[str, Any]) -> int:
        """Save unique field and response"""
        query = """
            INSERT INTO unique_fields (
                user_id, field_label, field_type, field_context,
                user_response, ai_generated_response, final_response,
                company, position, confidence_score, embedding
            ) VALUES (
                %s, %s, %s, PARSE_JSON(%s), %s, %s, %s, %s, %s, %s, PARSE_JSON(%s)
            )
        """
        
        params = (
            field_data.get('user_id'),
            field_data.get('field_label'),
            field_data.get('field_type'),
            json.dumps(field_data.get('field_context', {})),
            field_data.get('user_response'),
            field_data.get('ai_generated_response'),
            field_data.get('final_response'),
            field_data.get('company'),
            field_data.get('position'),
            field_data.get('confidence_score'),
            json.dumps(field_data.get('embedding', []))
        )
        
        return SnowflakeConnection.execute_update(query, params)
    
    @staticmethod
    def find_similar_unique_fields(user_id: int, field_label: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar previously answered unique fields"""
        query = """
            SELECT * FROM unique_fields
            WHERE user_id = %s
            AND LOWER(field_label) LIKE LOWER(%s)
            ORDER BY usage_count DESC, created_at DESC
            LIMIT %s
        """
        
        # Use fuzzy matching
        search_pattern = f"%{field_label}%"
        return SnowflakeConnection.execute_query(query, (user_id, search_pattern, limit))


# Initialize on module import
def init_db():
    """Initialize database connection and tables"""
    try:
        SnowflakeConnection.initialize_pool()
        init_snowflake_tables()
        logger.info("Snowflake database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Snowflake database: {e}")
        raise


# Context manager for database sessions
@contextmanager
def get_db():
    """Get database session context"""
    with SnowflakeConnection.get_connection() as conn:
        yield conn


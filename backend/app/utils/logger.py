import logging
import sys
from pathlib import Path

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with consistent formatting"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger

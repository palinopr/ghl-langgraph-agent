"""
Simple logger setup that avoids initialization issues
"""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Get a simple logger that won't cause initialization issues"""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger
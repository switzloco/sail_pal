import logging
import os
from logging.handlers import RotatingFileHandler
from backend.config import settings

def setup_logger():
    log_dir = os.path.join(settings.data_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "vessel_debug.log")
    
    # Root logger
    logger = logging.getLogger()
    
    # Set to DEBUG if debug_mode is True, otherwise INFO
    level = logging.DEBUG if settings.debug_mode else logging.INFO
    logger.setLevel(level)
    
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Write to file (max 10MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Also print to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logging.getLogger("vessel_ops")

logger = setup_logger()

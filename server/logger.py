import os
import logging
import datetime
from enum import Enum

class Environment(Enum):
    PROD = "prod"
    STAGE = "stage"
    TEST = "test"
    DEV = "dev"

class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

# Get the environment from environment variable, default to DEV
ENVIRONMENT = Environment(os.environ.get("WINE_AI_ENV", "dev").lower())

class WineAILogger:
    """
    Logger for Wine-AI application that formats logs differently based on environment
    and adds timestamps in yyyy/mm/dd/hh/mm format.
    """
    
    def __init__(self, name="wine-ai"):
        self.logger = logging.getLogger(name)
        
        # Only configure if handlers haven't been added yet
        if not self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)
            
            # Create console handler
            console_handler = logging.StreamHandler()
            
            # Set level based on environment
            if ENVIRONMENT == Environment.PROD:
                console_handler.setLevel(logging.INFO)
            elif ENVIRONMENT == Environment.STAGE:
                console_handler.setLevel(logging.INFO)
            elif ENVIRONMENT == Environment.TEST:
                console_handler.setLevel(logging.DEBUG)
            else:  # DEV
                console_handler.setLevel(logging.DEBUG)
            
            # Create formatter
            formatter = logging.Formatter(
                '[%(asctime)s][%(levelname)s][%(name)s] %(message)s',
                datefmt='%Y/%m/%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(console_handler)
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message):
        """Log info message"""
        self.logger.info(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
    
    def critical(self, message):
        """Log critical message"""
        self.logger.critical(message)

# Default logger instance
logger = WineAILogger()

# Convenience methods for direct import
debug = logger.debug
info = logger.info
warning = logger.warning
error = logger.error
critical = logger.critical 
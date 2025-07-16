"""
Logger utility for Uma Event Scanner
"""

from datetime import datetime

class Logger:
    """Simple logging utility with timestamp"""
    
    @staticmethod
    def info(message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] INFO: {message}")
    
    @staticmethod
    def error(message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ERROR: {message}")
    
    @staticmethod
    def debug(message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] DEBUG: {message}")
    
    @staticmethod
    def warning(message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] WARNING: {message}") 
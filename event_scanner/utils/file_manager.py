"""
File manager utility for Uma Event Scanner
"""

import json
import os
import pickle
from typing import Dict, Any
from .logger import Logger

class FileManager:
    """File management utilities for JSON and pickle files"""
    
    @staticmethod
    def save_json(data: dict, filename: str) -> bool:
        """Save dictionary to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            Logger.error(f"Failed to save {filename}: {e}")
            return False
    
    @staticmethod
    def load_json(filename: str) -> dict:
        """Load dictionary from JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            Logger.error(f"Failed to load {filename}: {e}")
        return {}
    
    @staticmethod
    def save_pickle(data: Any, filename: str) -> bool:
        """Save data to pickle file"""
        try:
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            Logger.error(f"Failed to save {filename}: {e}")
            return False
    
    @staticmethod
    def load_pickle(filename: str) -> Any:
        """Load data from pickle file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            Logger.error(f"Failed to load {filename}: {e}")
        return [] 
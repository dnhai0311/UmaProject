"""
Settings and History Managers for Uma Event Scanner
Contains SettingsManager and HistoryManager classes
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from utils import Logger, FileManager

# Constants
SETTINGS_FILE = 'scanner_settings.json'
HISTORY_FILE = 'event_history.pkl'

DEFAULT_SETTINGS = {
    'scan_interval': 2.0,
    'confidence_threshold': 0.3,
    'theme': 'light',
    'last_region': None,
    'ocr_language': 'eng',
    'window_position': None,
    'auto_close_popup': True,
    'popup_timeout': 8
}


class SettingsManager:
    """Manager for application settings"""
    
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        loaded = FileManager.load_json(SETTINGS_FILE)
        if loaded:
            self.settings.update(loaded)
            Logger.info("Settings loaded successfully")
        else:
            Logger.info("Using default settings")
    
    def save_settings(self) -> bool:
        """Save settings to file"""
        success = FileManager.save_json(self.settings, SETTINGS_FILE)
        if success:
            Logger.info("Settings saved successfully")
        else:
            Logger.error("Failed to save settings")
        return success
    
    def get(self, key: str, default=None):
        """Get setting value"""
        return self.settings.get(key, default) if default is not None else self.settings.get(key)
    
    def set(self, key: str, value: Any):
        """Set setting value"""
        self.settings[key] = value
        Logger.debug(f"Setting {key} updated to {value}")
    
    def get_all_settings(self) -> Dict:
        """Get all settings"""
        return self.settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = DEFAULT_SETTINGS.copy()
        Logger.info("Settings reset to defaults")
    
    def has_setting(self, key: str) -> bool:
        """Check if setting exists"""
        return key in self.settings


class HistoryManager:
    """Manager for event history"""
    
    def __init__(self):
        self.history = []
        self.load_history()
    
    def load_history(self):
        """Load history from file"""
        self.history = FileManager.load_pickle(HISTORY_FILE)
        if self.history:
            Logger.info(f"History loaded with {len(self.history)} entries")
        else:
            Logger.info("No history found, starting fresh")
    
    def save_history(self) -> bool:
        """Save history to file"""
        success = FileManager.save_pickle(self.history, HISTORY_FILE)
        if success:
            Logger.debug("History saved successfully")
        else:
            Logger.error("Failed to save history")
        return success
    
    def add_entry(self, event: Dict, texts: List[str]):
        """Add new entry to history"""
        entry = {
            'timestamp': datetime.now(),
            'event': event,
            'texts': texts
        }
        self.history.insert(0, entry)
        
        # Keep only last 100 entries
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self.save_history()
        Logger.debug(f"Added history entry: {event.get('name', 'Unknown')}")
    
    def clear(self):
        """Clear all history"""
        self.history = []
        self.save_history()
        Logger.info("History cleared")
    
    def get_history(self) -> List[Dict]:
        """Get all history entries"""
        return self.history.copy()
    
    def get_recent_entries(self, count: int = 10) -> List[Dict]:
        """Get recent history entries"""
        return self.history[:count]
    
    def get_entry_count(self) -> int:
        """Get number of history entries"""
        return len(self.history)
    
    def search_history(self, query: str) -> List[Dict]:
        """Search history entries"""
        query_lower = query.lower()
        results = []
        
        for entry in self.history:
            event_name = entry.get('event', {}).get('name', '').lower()
            if query_lower in event_name:
                results.append(entry)
        
        return results
    
    def get_stats(self) -> Dict:
        """Get history statistics"""
        if not self.history:
            return {'total_events': 0, 'unique_events': 0, 'first_event': None, 'last_event': None}
        
        unique_events = set()
        for entry in self.history:
            event_name = entry.get('event', {}).get('name', '')
            if event_name:
                unique_events.add(event_name)
        
        return {
            'total_events': len(self.history),
            'unique_events': len(unique_events),
            'first_event': self.history[-1]['timestamp'] if self.history else None,
            'last_event': self.history[0]['timestamp'] if self.history else None
        } 
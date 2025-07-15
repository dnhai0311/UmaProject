"""
Event Database for Uma Event Scanner
Contains EventDatabase class for managing game events
"""

import json
import os
import re
from typing import List, Dict, Optional
from utils import Logger

# Constants
DATA_FILE = '../scrape/data/all_training_events.json'


class EventDatabase:
    """Database for managing Uma Musume events"""
    
    def __init__(self):
        self.events = {}
        self.load_events()
    
    def load_events(self):
        """Load events from JSON data file"""
        self.events = {}
        
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._process_event_data(data)
            except Exception as e:
                Logger.error(f"Failed to load {DATA_FILE}: {e}")
        else:
            Logger.error(f"Data file not found: {DATA_FILE}")
        
        Logger.info(f"Loaded {len(self.events)} events")
    
    def _process_event_data(self, data):
        """Process the new all_training_events.json structure"""
        if not isinstance(data, dict):
            Logger.error("Invalid data format: expected dictionary")
            return
        
        # Process characters
        if 'characters' in data:
            for character in data['characters']:
                if 'eventGroups' in character:
                    for event_group in character['eventGroups']:
                        if 'events' in event_group:
                            for event in event_group['events']:
                                name = event.get('event', '')
                                if name and self._is_english_event(name):
                                    self.events[name] = {
                                        'name': name,
                                        'choices': event.get('choices', [])
                                    }
        
        # Process support cards
        if 'supportCards' in data:
            for support_card in data['supportCards']:
                if 'eventGroups' in support_card:
                    for event_group in support_card['eventGroups']:
                        if 'events' in event_group:
                            for event in event_group['events']:
                                name = event.get('event', '')
                                if name and self._is_english_event(name):
                                    self.events[name] = {
                                        'name': name,
                                        'choices': event.get('choices', [])
                                    }
        
        # Process scenarios
        if 'scenarios' in data:
            for scenario in data['scenarios']:
                if 'eventGroups' in scenario:
                    for event_group in scenario['eventGroups']:
                        if 'events' in event_group:
                            for event in event_group['events']:
                                name = event.get('event', '')
                                if name and self._is_english_event(name):
                                    self.events[name] = {
                                        'name': name,
                                        'choices': event.get('choices', [])
                                    }
    
    def _is_english_event(self, text: str) -> bool:
        """Check if event text is in English"""
        if not text:
            return False
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return False
        if not re.search(r'[a-zA-Z]', text):
            return False
        return True
    
    def find_matching_event(self, texts: List[str]) -> Optional[Dict]:
        """Find event matching the extracted texts"""
        if not texts:
            return None
        
        combined_text = ' '.join(texts).lower()
        cleaned_text = self._clean_text(combined_text)
        
        best_match = None
        best_score = 0
        
        for event_name, event_data in self.events.items():
            score = self._calculate_match_score(cleaned_text, event_name.lower())
            if score > best_score:
                best_score = score
                best_match = event_data
        
        if best_score > 0.5 and best_match:
            Logger.info(f"Found matching event: {best_match['name']} (score: {best_score:.2f})")
            return best_match
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text for comparison"""
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return ' '.join(cleaned.split())
    
    def _calculate_match_score(self, text: str, event_name: str) -> float:
        """Calculate match score between text and event name"""
        text_clean = self._clean_text(text)
        event_clean = self._clean_text(event_name)
        
        if not text_clean or not event_clean:
            return 0
        
        if event_clean in text_clean:
            return 1.0
        
        text_words = set(text_clean.split())
        event_words = set(event_clean.split())
        
        if not event_words:
            return 0
        
        common_words = text_words.intersection(event_words)
        return len(common_words) / len(event_words)
    
    def get_event_count(self) -> int:
        """Get total number of events"""
        return len(self.events)
    
    def get_all_events(self) -> Dict:
        """Get all events"""
        return self.events.copy()
    
    def reload_events(self):
        """Reload events from file"""
        self.load_events() 
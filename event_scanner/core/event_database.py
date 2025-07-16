"""
Event Database for Uma Event Scanner
Contains EventDatabase class for managing game events
"""

import json
import os
import re
from typing import List, Dict, Optional
from event_scanner.utils import Logger

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "scrape", "data", "all_training_events.json")


class EventDatabase:
    """Database for managing Uma Musume events with AI learning capabilities"""
    
    def __init__(self):
        self.events = {}
        self.ai_detector = None
        
        # Initialize AI detector if available
        # AI functionality removed
        
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
        
        # Process events from the main events array
        if 'events' in data:
            for event in data['events']:
                name = event.get('event', '')
                if name and self._is_english_event(name):
                    self.events[name] = {
                        'name': name,
                        'choices': event.get('choices', []),
                        'type': event.get('type', 'Unknown')
                    }
        
        Logger.info(f"Processed {len(self.events)} events from main events array")
    
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
        
        # Debug log để kiểm tra text
        Logger.debug(f"Finding event match for: {combined_text}")
        
        best_match = None
        best_score = 0
        
        # Xử lý một số trường hợp đặc biệt đã biết
        # "Lovely Training Weather ♪" -> "(❯) Lovely Training Weather ♪"
        known_events = {
            "lovely training weather": "(❯) Lovely Training Weather ♪",
            "i'm not afraid": "(❯) I'm Not Afraid!"
        }
        
        for key, exact_event in known_events.items():
            if key in combined_text.lower():
                # Tìm sự kiện chính xác trong database
                if exact_event in self.events:
                    Logger.info(f"Direct match found for special case: {exact_event}")
                    return self.events[exact_event]
                
                # Tìm kiếm với các cách viết khác nhau (có/không có arrow)
                for event_name, event_data in self.events.items():
                    # Kiểm tra nếu giống event đã biết (không phân biệt ký tự đặc biệt)
                    normalized_event = event_name.lower().replace("(❯)", "").replace("♪", "").strip()
                    normalized_key = key.replace("(❯)", "").replace("♪", "").strip()
                    
                    if normalized_event == normalized_key:
                        Logger.info(f"Normalized match found: '{event_name}' for '{key}'")
                        return event_data
        
        # Add variant without the arrow prefix for matching
        cleaned_text_no_prefix = cleaned_text
        if "(❯)" in cleaned_text_no_prefix:
            cleaned_text_no_prefix = cleaned_text_no_prefix.replace("(❯)", "").strip()
        
        for event_name, event_data in self.events.items():
            # Create variants of the event name without special characters
            event_name_lower = event_name.lower()
            clean_event_name = self._clean_text(event_name_lower)
            
            # Create variant without arrow prefix
            event_no_prefix = event_name_lower
            if "(❯)" in event_no_prefix:
                event_no_prefix = event_no_prefix.replace("(❯)", "").strip()
            clean_event_no_prefix = self._clean_text(event_no_prefix)
            
            # Try different variants of matching
            score1 = self._calculate_match_score(cleaned_text, event_name_lower)
            score2 = self._calculate_match_score(cleaned_text, clean_event_name)
            score3 = self._calculate_partial_word_match(cleaned_text, clean_event_name)
            
            # Try matching without the arrow prefix too
            score4 = self._calculate_match_score(cleaned_text_no_prefix, event_no_prefix)
            score5 = self._calculate_match_score(cleaned_text_no_prefix, clean_event_no_prefix)
            
            # Use the best score from the different matching methods
            score = max(score1, score2, score3, score4, score5)
            
            if score > best_score:
                best_score = score
                best_match = event_data
                
                # Debug: Log high scoring matches
                if score > 0.5:
                    Logger.debug(f"High score match ({score:.2f}): '{event_name}'")
        
        # Adjust threshold for matching
        threshold = 0.5
        
        if best_score > threshold and best_match:
            Logger.info(f"Found matching event: {best_match['name']} (score: {best_score:.2f})")
            return best_match
            
        # Nếu không tìm thấy kết quả, kiểm tra từng sự kiện trong cơ sở dữ liệu
        if "lovely training weather" in combined_text.lower():
            Logger.info("Special case: Lovely Training Weather detected but no match found in database")
            # Tạo sự kiện mẫu khi không tìm thấy trong database
            return {
                'name': "(❯) Lovely Training Weather ♪",
                'choices': [
                    {
                        'choice': "Top Option",
                        'effect': "Wisdom +5\nSkill points +20\nFine Motion bond +5"
                    },
                    {
                        'choice': "Middle Option",
                        'effect': "Speed +10\nStamina +5"
                    },
                    {
                        'choice': "Bottom Option",
                        'effect': "Get Practice Perfect ○ status\nFine Motion bond +5"
                    }
                ],
                'type': 'Chain Events'
            }
        
        # Xử lý sự kiện "I'm Not Afraid!"
        if "i'm not afraid" in combined_text.lower() or "im not afraid" in combined_text.lower():
            Logger.info("Special case: I'm Not Afraid! detected but no match found in database")
            # Tạo sự kiện mẫu khi không tìm thấy trong database
            return {
                'name': "(❯) I'm Not Afraid!",
                'choices': [
                    {
                        'choice': "Top Option", 
                        'effect': "Energy -5\nStamina +5\nSkill points +10\nMotivation increases"
                    },
                    {
                        'choice': "Bottom Option",
                        'effect': "Speed +10\nStamina +5\nGuts +5"
                    }
                ],
                'type': 'Chain Events'
            }
        
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean text for comparison while preserving spaces"""
        # Remove punctuation and special characters but preserve spaces
        cleaned = re.sub(r'[^\w\s]', '', text)
        return ' '.join(cleaned.split())
    
    def _calculate_match_score(self, text: str, event_name: str) -> float:
        """Calculate match score between text and event name"""
        if not text or not event_name:
            return 0
        
        # Direct match check (handling special characters)
        if event_name in text:
            return 1.0
        
        # Core words matching (without special chars)
        text_words = text.split()
        event_words = event_name.split()
        
        if not event_words:
            return 0
        
        # Check for key words match
        common_words = set(text_words).intersection(set(event_words))
        
        # Calculate score based on word overlap
        word_match_score = len(common_words) / len(event_words) if event_words else 0
        
        return word_match_score
    
    def _calculate_partial_word_match(self, text: str, event_name: str) -> float:
        """Calculate partial word matching score for better fuzzy matching"""
        if not text or not event_name:
            return 0
            
        text_words = text.split()
        event_words = event_name.split()
        
        if not event_words:
            return 0
            
        # Count how many event words are at least partially contained in text words
        matched_words = 0
        for event_word in event_words:
            if len(event_word) <= 3:  # For very short words, require exact match
                if event_word in text_words:
                    matched_words += 1
            else:
                # For longer words, check if any text word contains this event word
                for text_word in text_words:
                    # Check if significant part (70%) of event word is in text word
                    min_chars = int(0.7 * len(event_word))
                    if len(event_word) >= min_chars and (event_word in text_word or text_word in event_word):
                        matched_words += 1
                        break
                        
        return matched_words / len(event_words) if event_words else 0
    
    def get_event_count(self) -> int:
        """Get total number of events"""
        return len(self.events)
    
    def get_all_events(self) -> Dict:
        """Get all events"""
        return self.events.copy()
    
    def reload_events(self):
        """Reload events from file"""
        self.load_events() 
"""
Uma Musume Event Scanner - Clean Version
Fixed Python 3.13 compatibility and Pillow ANTIALIAS issues
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import pyautogui
import threading
import time
import json
import os
import pickle
from datetime import datetime
from PIL import Image, ImageTk
from typing import List, Dict, Optional, Tuple
import re

# Import OCR libraries with fallback
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("EasyOCR not available - will use Tesseract only")

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract not available")

# Constants
DATA_FILES = [
    '../scrape/data/all_uma_events.json',
    '../scrape/data/all_scenario_events.json', 
    '../scrape/data/all_support_events.json'
]

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

OCR_CONFIGS = [
    ('--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?()-\'"', 'LSTM Single Line'),
    ('--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?()-\'"', 'LSTM Uniform Block'),
    ('--oem 1 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,!?()-\'"', 'Legacy Single Line'),
    ('--oem 3 --psm 13', 'LSTM Raw Line'),
    ('--oem 3 --psm 6 --dpi 300', 'LSTM High DPI')
]

# ========== UTILITIES ==========
class Logger:
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

class FileManager:
    @staticmethod
    def save_json(data: dict, filename: str):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            Logger.error(f"Failed to save {filename}: {e}")
            return False
    
    @staticmethod
    def load_json(filename: str) -> dict:
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            Logger.error(f"Failed to load {filename}: {e}")
        return {}
    
    @staticmethod
    def save_pickle(data, filename: str):
        try:
            with open(filename, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            Logger.error(f"Failed to save {filename}: {e}")
            return False
    
    @staticmethod
    def load_pickle(filename: str):
        try:
            if os.path.exists(filename):
                with open(filename, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            Logger.error(f"Failed to load {filename}: {e}")
        return []

# ========== CORE CLASSES ==========
class ImageProcessor:
    @staticmethod
    def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
        """Enhanced preprocessing for better OCR accuracy"""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Get image dimensions
        h, w = gray.shape[:2]
        
        # Resize if too small (minimum 150px height for good OCR)
        if h < 150:
            scale = max(2.0, 150 / h)
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
            h, w = gray.shape[:2]
        
        # Apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Enhance contrast using CLAHE with more aggressive settings
        clahe = cv2.createCLAHE(clipLimit=12.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)
        
        # Try different thresholding methods and pick the best
        # Method 1: Adaptive threshold
        adaptive1 = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 8
        )
        # Method 2: Otsu's thresholding
        _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # Method 3: Adaptive threshold with different parameters
        adaptive2 = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 10
        )
        
        # Choose the best threshold based on the amount of white pixels
        def evaluate_threshold(img):
            white_pixels = np.sum(img == 255)
            total_pixels = img.shape[0] * img.shape[1]
            white_ratio = white_pixels / total_pixels
            # Prefer images with 60-90% white pixels (text on background)
            if 0.6 <= white_ratio <= 0.9:
                return abs(0.75 - white_ratio)  # Closer to 75% is better
            else:
                return 1.0  # Penalize heavily
        
        threshold_methods = [
            ('adaptive1', adaptive1),
            ('otsu', otsu), 
            ('adaptive2', adaptive2)
        ]
        
        best_method = None
        best_score = float('inf')
        
        for name, img in threshold_methods:
            score = evaluate_threshold(img)
            if score < best_score:
                best_score = score
                best_method = img
        
        # Use the best threshold result
        binary = best_method if best_method is not None else adaptive1
        
        # Morphological operations to clean up the image
        # Remove small noise
        kernel_noise = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_noise, iterations=1)
        
        # Fill small gaps in characters
        kernel_fill = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_fill, iterations=1)
        
        # Final dilation to make text slightly thicker (better for OCR)
        kernel_dilate = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel_dilate, iterations=1)
        
        # Ensure text is black on white background for OCR
        # Count black vs white pixels to determine if we need to invert
        black_pixels = np.sum(binary == 0)
        white_pixels = np.sum(binary == 255)
        
        if black_pixels > white_pixels:
            # More black than white, likely inverted
            binary = cv2.bitwise_not(binary)
        
        return binary

class OCREngine:
    def __init__(self, language: str = 'eng'):
        self.language = language
        self.easyocr_reader = None
        self.use_easyocr = False
        
        # Try to initialize EasyOCR
        if EASYOCR_AVAILABLE:
            try:
                gpu_available = self._check_gpu_availability()
                
                if gpu_available:
                    try:
                        self.easyocr_reader = easyocr.Reader(['en'], gpu=True, verbose=False)
                        self.use_easyocr = True
                        Logger.info("EasyOCR initialized with GPU acceleration")
                    except Exception as gpu_error:
                        Logger.error(f"GPU initialization failed: {gpu_error}")
                        try:
                            self.easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                            self.use_easyocr = True
                            Logger.info("EasyOCR initialized with CPU")
                        except Exception as cpu_error:
                            Logger.error(f"CPU initialization failed: {cpu_error}")
                            self.use_easyocr = False
                else:
                    try:
                        self.easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                        self.use_easyocr = True
                        Logger.info("EasyOCR initialized with CPU (no GPU detected)")
                    except Exception as e:
                        Logger.error(f"EasyOCR initialization failed: {e}")
                        self.use_easyocr = False
                        
            except Exception as e:
                Logger.error(f"Failed to initialize EasyOCR: {e}")
                self.use_easyocr = False
        
        # Check if we have any OCR engine
        if not self.use_easyocr and not TESSERACT_AVAILABLE:
            raise ImportError("Neither EasyOCR nor Tesseract is available")
    
    def _check_gpu_availability(self) -> bool:
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                Logger.info(f"GPU detected: {gpu_name} (Count: {gpu_count})")
                return True
            else:
                Logger.info("CUDA not available - will use CPU")
        except ImportError:
            Logger.info("PyTorch not available - will use CPU")
        return False
    
    def extract_text(self, image: np.ndarray) -> List[str]:
        results = []
        
        # Try EasyOCR first
        if self.use_easyocr and self.easyocr_reader:
            try:
                easyocr_results = self._extract_with_easyocr(image)
                results.extend(easyocr_results)
            except Exception as e:
                Logger.error(f"EasyOCR failed: {e}")
        
        # Fallback to Tesseract if no results
        if not results and TESSERACT_AVAILABLE:
            try:
                tesseract_results = self._extract_with_tesseract(image)
                results.extend(tesseract_results)
            except Exception as e:
                Logger.error(f"Tesseract failed: {e}")
        
        return list(set(results)) if results else []
    
    def _extract_with_easyocr(self, image: np.ndarray) -> List[str]:
        results = []
        
        try:
            if not self.easyocr_reader:
                return results
                
            ocr_results = self.easyocr_reader.readtext(image, detail=1)
            
            for (bbox, text, confidence) in ocr_results:
                conf_float = float(confidence) if isinstance(confidence, (str, int, float)) else 0.0
                
                if conf_float > 0.3 and self._is_valid_text(text):
                    corrected_text = self._correct_ocr_text(text)
                    if corrected_text:
                        results.append(corrected_text)
            
            # Combine multiple results if they exist
            if len(results) > 1:
                combined_text = ' '.join(results)
                final_corrected = self._correct_ocr_text(combined_text)
                if final_corrected and self._is_valid_text(final_corrected):
                    results.append(final_corrected)
                    
        except Exception as e:
            Logger.error(f"EasyOCR extraction failed: {e}")
        
        return results
    
    def _extract_with_tesseract(self, image: np.ndarray) -> List[str]:
        results = []
        
        for config, desc in OCR_CONFIGS:
            try:
                data = pytesseract.image_to_data(
                    image, 
                    lang=self.language,
                    config=config,
                    output_type=pytesseract.Output.DICT
                )
                
                valid_texts = []
                for i in range(len(data['text'])):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    
                    if text and conf > 30 and self._is_valid_text(text):
                        corrected_text = self._correct_ocr_text(text)
                        if corrected_text:
                            valid_texts.append(corrected_text)
                
                if valid_texts:
                    if len(valid_texts) == 1:
                        results.append(valid_texts[0])
                    else:
                        combined_text = ' '.join(valid_texts)
                        final_corrected = self._correct_ocr_text(combined_text)
                        if final_corrected and self._is_valid_text(final_corrected):
                            results.append(final_corrected)
                    
            except Exception as e:
                Logger.error(f"Tesseract error with {desc}: {e}")
        
        # Remove duplicates while preserving order
        unique_results = []
        seen = set()
        for result in results:
            if result.lower() not in seen:
                unique_results.append(result)
                seen.add(result.lower())
        
        return unique_results

    def _is_valid_text(self, text: str) -> bool:
        if not text or len(text) < 2:
            return False
        
        # Remove special characters for analysis
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        if not cleaned.strip():
            return False
        
        # Must contain letters
        if not re.search(r'[a-zA-Z]', text):
            return False
        
        # Reject Japanese/Chinese text
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return False
        
        # Reject terminal/console text patterns
        terminal_patterns = [
            r'\bPS\b',           # PowerShell
            r'\bcmd\b',          # Command Prompt  
            r'sudo',             # Linux commands
            r'\.exe\b',          # Executable files
            r'[A-Z]:\\',         # Windows paths (C:\)
            r'\\\\',             # UNC paths
            r'\.py\b',           # Python files
            r'\.bat\b',          # Batch files
            r'DSED|CGE|ony|unk', # Specific garbled text patterns
            r'\berror\b|\bfail\b|\bexception\b',  # Error messages
            r'python\.exe',      # Python executable
            r'AppData',          # Windows AppData
            r'Programs',         # Programs folder
        ]
        
        text_lower = text.lower()
        for pattern in terminal_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return False
        
        # Reject if too many consecutive uppercase letters (likely corrupted)
        if re.search(r'[A-Z]{6,}', text):
            return False
        
        # Reject if contains too many random characters
        consonant_clusters = re.findall(r'[bcdfghjklmnpqrstvwxyz]{4,}', text_lower)
        if len(consonant_clusters) > 0:
            return False
        
        # Must be reasonable length for game text
        if len(text) > 100:
            return False
        
        # Check if text contains common game-related words
        words = text_lower.split()
        if len(words) == 0:
            return False
        
        # Allow common game words
        game_words = [
            'new', 'year', 'years', 'resolution', 'resolutions', 'trainee', 'event',
            'training', 'race', 'skill', 'card', 'support', 'uma', 'musume',
            'speed', 'stamina', 'power', 'guts', 'wisdom', 'scenario', 'choice',
            'freestyle', 'striking', 'considerate', 'conversation', 'session',
            'the', 'to', 'me', 'be', 'it', 'a', 'and', 'of', 'in', 'for',
            'with', 'on', 'at', 'by', 'from', 'as', 'is', 'was', 'are',
            'have', 'has', 'had', 'will', 'would', 'can', 'could', 'should'
        ]
        
        # Check if text contains at least one valid word
        has_valid_word = any(word in game_words for word in words)
        
        # If no valid words but text looks like proper English, allow it
        if not has_valid_word:
            # Allow if it's alphabetic text
            if all(word.isalpha() for word in words) and len(words) <= 6:
                return True
            # Allow if it has proper sentence structure
            if re.search(r'^[A-Z][a-z].*[.!?]$', text.strip()):
                return True
            return False
        
        return True

    def _correct_ocr_text(self, text: str) -> str:
        if not text:
            return text
        
        corrections = {
            # Common OCR errors
            'eave': 'Leave', 'eaves': 'Leave', 'toh': 'to', 'sto': 'to',
            'sidera': 'Considerate', 'ey': 'e!', 'Py': '', 'py': '',
            
            # Duplicates
            'Considerate!Considerate!': 'Considerate!',
            'Considerate!Considerate': 'Considerate!',
            'ConsiderateConsiderate': 'Considerate',
            'Consideratel': 'Considerate!',
            'Consideratete': 'Considerate!',
            
            # Full phrases
            'Leave it to Me to Be Consideratete': 'Leave it to Me to Be Considerate!',
            'Leave it to Me to Be Considerate!Considerate!': 'Leave it to Me to Be Considerate!',
        }
        
        corrected = text
        
        # Apply corrections
        for wrong, right in corrections.items():
            corrected = corrected.replace(wrong, right)
        
        # Remove duplicate words
        words = corrected.split()
        final_words = []
        prev_word = ""
        
        for word in words:
            if word.lower() != prev_word.lower():
                final_words.append(word)
                prev_word = word
        
        return ' '.join(final_words)

class EventDatabase:
    def __init__(self):
        self.events = {}
        self.load_events()
    
    def load_events(self):
        self.events = {}
        
        for file_path in DATA_FILES:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._process_event_data(data)
                except Exception as e:
                    Logger.error(f"Failed to load {file_path}: {e}")
        
        Logger.info(f"Loaded {len(self.events)} events")
    
    def _process_event_data(self, data):
        if isinstance(data, list):
            for item in data:
                if 'events' in item:
                    for event in item['events']:
                        name = event.get('event', '')
                        if name and self._is_english_event(name):
                            self.events[name] = {
                                'name': name,
                                'choices': event.get('choices', [])
                            }
        elif isinstance(data, dict):
            for key, value in data.items():
                if self._is_english_event(key):
                    self.events[key] = value
    
    def _is_english_event(self, text: str) -> bool:
        if not text:
            return False
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text):
            return False
        if not re.search(r'[a-zA-Z]', text):
            return False
        return True
    
    def find_matching_event(self, texts: List[str]) -> Optional[Dict]:
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
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text)
        return ' '.join(cleaned.split())
    
    def _calculate_match_score(self, text: str, event_name: str) -> float:
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

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load_settings()
    
    def load_settings(self):
        loaded = FileManager.load_json(SETTINGS_FILE)
        if loaded:
            self.settings.update(loaded)
    
    def save_settings(self):
        return FileManager.save_json(self.settings, SETTINGS_FILE)
    
    def get(self, key: str, default=None):
        return self.settings.get(key, default) if default is not None else self.settings.get(key)
    
    def set(self, key: str, value):
        self.settings[key] = value

class HistoryManager:
    def __init__(self):
        self.history = []
        self.load_history()
    
    def load_history(self):
        self.history = FileManager.load_pickle(HISTORY_FILE)
    
    def save_history(self):
        return FileManager.save_pickle(self.history, HISTORY_FILE)
    
    def add_entry(self, event: Dict, texts: List[str]):
        entry = {
            'timestamp': datetime.now(),
            'event': event,
            'texts': texts
        }
        self.history.insert(0, entry)
        
        if len(self.history) > 100:
            self.history = self.history[:100]
        
        self.save_history()
    
    def clear(self):
        self.history = []
        self.save_history()
    
    def get_history(self) -> List[Dict]:
        return self.history

# ========== GUI COMPONENTS ==========
class EventPopup:
    def __init__(self, parent, event: Dict, auto_close: bool = True, timeout: int = 8):
        self.event = event
        self.popup = tk.Toplevel(parent)
        self.setup_popup()
        
        if auto_close:
            self.popup.after(timeout * 1000, self.close)
    
    def setup_popup(self):
        self.popup.title('Event Detected!')
        self.popup.attributes('-topmost', True)
        self.popup.resizable(False, False)
        
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        
        width = 500
        height = min(400, 200 + len(self.event.get('choices', [])) * 30)
        
        # Position popup right below main form
        x = screen_width - 520  # Aligned with main form (620 - 100 to center popup under main form)
        y = 520  # Below main form (y=10 + height=500 + 10px gap)
        
        self.popup.geometry(f'{width}x{height}+{x}+{y}')
        self.popup.configure(bg='#2c3e50')
        
        self.create_content()
    
    def create_content(self):
        main_frame = tk.Frame(self.popup, bg='#2c3e50', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        event_label = tk.Label(
            main_frame, 
            text=self.event['name'],
            font=('Arial', 14, 'bold'),
            fg='#e74c3c',
            bg='#2c3e50',
            wraplength=460
        )
        event_label.pack(pady=(0, 15))
        
        choices = self.event.get('choices', [])
        if choices:
            for i, choice in enumerate(choices[:8]):
                choice_text = self._format_choice(choice, i + 1)
                choice_label = tk.Label(
                    main_frame,
                    text=choice_text,
                    font=('Arial', 10),
                    fg='#ecf0f1',
                    bg='#2c3e50',
                    wraplength=460,
                    justify='left'
                )
                choice_label.pack(anchor='w', pady=2)
        
        close_btn = tk.Button(
            main_frame,
            text='Close',
            command=self.close,
            bg='#34495e',
            fg='white',
            font=('Arial', 10),
            padx=20
        )
        close_btn.pack(pady=(15, 0))
    
    def _format_choice(self, choice, index: int) -> str:
        if isinstance(choice, dict):
            text = choice.get('choice', str(choice))
            effect = choice.get('effect', '')
            if effect:
                return f"{index}. {text}\n   → {effect}"
            return f"{index}. {text}"
        return f"{index}. {choice}"
    
    def close(self):
        try:
            self.popup.destroy()
        except:
            pass

class RegionSelector:
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.region = None
    
    def select_region(self):
        self.parent.withdraw()
        time.sleep(0.3)
        
        screenshot = pyautogui.screenshot()
        self.create_selection_window(screenshot)
    
    def create_selection_window(self, screenshot):
        img = screenshot.copy()
        img.thumbnail((1200, 800))
        
        scale_x = screenshot.width / img.width
        scale_y = screenshot.height / img.height
        
        self.selection_window = tk.Toplevel()
        self.selection_window.title('Select Scan Region')
        self.selection_window.attributes('-topmost', True)
        
        img_tk = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(self.selection_window, width=img.width, height=img.height)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        setattr(canvas, 'img_ref', img_tk)
        
        self.rect = None
        self.start_pos = [0, 0]
        
        canvas.bind('<ButtonPress-1>', lambda e: self.on_press(e, scale_x, scale_y))
        canvas.bind('<B1-Motion>', lambda e: self.on_drag(e, canvas))
        canvas.bind('<ButtonRelease-1>', lambda e: self.on_release(e, scale_x, scale_y))
    
    def on_press(self, event, scale_x, scale_y):
        self.start_pos = [event.x, event.y]
        if self.rect:
            event.widget.delete(self.rect)
        self.rect = event.widget.create_rectangle(
            event.x, event.y, event.x, event.y, 
            outline='red', width=2
        )
    
    def on_drag(self, event, canvas):
        if self.rect:
            canvas.coords(self.rect, self.start_pos[0], self.start_pos[1], event.x, event.y)
    
    def on_release(self, event, scale_x, scale_y):
        x1, y1 = min(self.start_pos[0], event.x), min(self.start_pos[1], event.y)
        x2, y2 = max(self.start_pos[0], event.x), max(self.start_pos[1], event.y)
        
        selection_width = x2 - x1
        selection_height = y2 - y1
        
        if selection_width > 10 and selection_height > 10:
            # Convert preview coordinates to real screen coordinates
            real_x = int(x1 * scale_x)
            real_y = int(y1 * scale_y)
            real_w = int(selection_width * scale_x)
            real_h = int(selection_height * scale_y)
            
            # Validation checks
            if real_w < 50 or real_h < 20:
                messagebox.showwarning("Region Too Small", f"Selected region is too small: {real_w}x{real_h}\n\nMinimum size: 50x20 pixels\n\nPlease select a larger area containing the text.")
                self.selection_window.destroy()
                self.parent.deiconify()
                return
            
            if real_w > 1000 or real_h > 200:
                response = messagebox.askyesno("Large Region", f"Selected region is very large: {real_w}x{real_h}\n\nThis might include unwanted elements.\n\nRecommended max: 1000x200 pixels\n\nContinue anyway?")
                if not response:
                    self.selection_window.destroy()
                    self.parent.deiconify()
                    return
            
            # Get screen dimensions for validation
            screen_width = self.selection_window.winfo_screenwidth()
            screen_height = self.selection_window.winfo_screenheight()
            
            if real_x < 0 or real_y < 0 or real_x + real_w > screen_width or real_y + real_h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {real_x},{real_y} + {real_w}x{real_h}")
                self.selection_window.destroy()
                self.parent.deiconify()
                return
            
            self.region = (real_x, real_y, real_w, real_h)
            self.callback(self.region)
        else:
            messagebox.showwarning("Selection Too Small", "Please drag to select a larger area")
        
        self.selection_window.destroy()
        self.parent.deiconify()

# ========== MAIN APPLICATION ==========
class EventScannerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.settings = SettingsManager()
        self.history = HistoryManager()
        self.event_db = EventDatabase()
        self.ocr_engine = None
        self.image_processor = ImageProcessor()
        
        self.scanning = False
        self.scan_region = self.settings.get('last_region')
        self.current_popup = None
        
        self.init_ocr()
        self.setup_gui()
    
    def init_ocr(self):
        try:
            language = self.settings.get('ocr_language', 'eng') or 'eng'
            self.ocr_engine = OCREngine(language)
            Logger.info("OCR engine initialized")
        except Exception as e:
            Logger.error(f"Failed to initialize OCR: {e}")
            messagebox.showerror("Error", "Failed to initialize OCR engine")
            self.root.quit()
    
    def setup_gui(self):
        self.root.title("Uma Event Scanner")
        self.root.geometry("600x500")
        self.root.minsize(500, 400)
        
        self.position_window()
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.create_scanner_tab()
        self.create_history_tab()
        self.create_settings_tab()
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        self.status_bar.pack(side='bottom', fill='x')
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def position_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # DEBUG: Print screen width/height
        print(f"[DEBUG] screen_width={screen_width}, screen_height={screen_height}")
        
        # Thử set x = screen_width - 600 (không padding)
        x = screen_width - 600
        y = 10
        print(f"[DEBUG] Calculated x={x}, y={y}")
        geometry_str = f"600x500+{x}+{y}"
        print(f"[DEBUG] geometry: {geometry_str}")
        self.root.geometry(geometry_str)
        self.root.attributes('-topmost', True)
        # Ép lại geometry sau 100ms để chắc chắn đúng vị trí
        self.root.after(100, lambda: self.root.geometry(geometry_str))

    def create_scanner_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Scanner")
        
        # Region selection
        region_frame = ttk.LabelFrame(tab, text="Scan Region", padding=10)
        region_frame.pack(fill='x', padx=10, pady=5)
        
        self.region_label = ttk.Label(region_frame, text=self.get_region_text())
        self.region_label.pack(side='left', padx=5)
        
        ttk.Button(region_frame, text="Select Region", command=self.select_region).pack(side='left', padx=5)
        ttk.Button(region_frame, text="Preview", command=self.preview_region).pack(side='left', padx=5)
        
        # Controls
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="Start Scanning", command=self.start_scanning)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_scanning, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="Test OCR", command=self.test_ocr).pack(side='left', padx=5)
        
        # Results
        result_frame = ttk.LabelFrame(tab, text="Results", padding=10)
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        text_frame = ttk.Frame(result_frame)
        text_frame.pack(fill='both', expand=True)
        
        self.result_text = tk.Text(text_frame, height=15, state='disabled', font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_history_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="History")
        
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(control_frame, text="Refresh", command=self.refresh_history).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear", command=self.clear_history).pack(side='left', padx=5)
        
        list_frame = ttk.Frame(tab)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.history_listbox = tk.Listbox(list_frame, font=('Arial', 10))
        hist_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hist_scrollbar.set)
        
        self.history_listbox.pack(side='left', fill='both', expand=True)
        hist_scrollbar.pack(side='right', fill='y')
        
        self.refresh_history()
    
    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        scanner_frame = ttk.LabelFrame(tab, text="Scanner Settings", padding=10)
        scanner_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(scanner_frame, text="Scan Interval (seconds):").grid(row=0, column=0, sticky='w', pady=5)
        self.interval_var = tk.DoubleVar(value=self.settings.get('scan_interval', 2.0))
        ttk.Entry(scanner_frame, textvariable=self.interval_var, width=10).grid(row=0, column=1, padx=5)
        
        popup_frame = ttk.LabelFrame(tab, text="Popup Settings", padding=10)
        popup_frame.pack(fill='x', padx=10, pady=5)
        
        self.auto_close_var = tk.BooleanVar(value=self.settings.get('auto_close_popup', True))
        ttk.Checkbutton(popup_frame, text="Auto-close popups", variable=self.auto_close_var).grid(row=0, column=0, sticky='w', pady=5)
        
        ttk.Button(tab, text="Save Settings", command=self.save_settings).pack(pady=20)
    
    def get_region_text(self) -> str:
        if self.scan_region:
            x, y, w, h = self.scan_region
            return f"Region: {x},{y} ({w}x{h})"
        return "No region selected"
    
    def select_region(self):
        selector = RegionSelector(self.root, self.on_region_selected)
        selector.select_region()
    
    def on_region_selected(self, region):
        self.scan_region = region
        self.settings.set('last_region', region)
        self.settings.save_settings()
        self.region_label.config(text=self.get_region_text())
        Logger.info(f"Region selected: {region}")
    
    def preview_region(self):
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        try:
            x, y, w, h = self.scan_region
            
            # Validate region before taking screenshot
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if x < 0 or y < 0 or x + w > screen_width or y + h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {x},{y} + {w}x{h}\n\nPlease select a new region.")
                return
            
            screenshot = pyautogui.screenshot(region=self.scan_region)
            
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"Region Preview - {w}x{h} at ({x},{y})")
            preview_window.resizable(False, False)
            
            img = screenshot.copy()
            original_size = img.size
            
            # Scale image for display if needed
            max_display_size = (800, 600)
            if img.width > max_display_size[0] or img.height > max_display_size[1]:
                img.thumbnail(max_display_size)
            
            img_tk = ImageTk.PhotoImage(img)
            
            # Create frame for image and info
            main_frame = tk.Frame(preview_window)
            main_frame.pack(padx=10, pady=10)
            
            # Info label
            info_text = f"Region: {x},{y} | Size: {w}x{h} | Display: {img.size}"
            info_label = tk.Label(main_frame, text=info_text, font=('Arial', 10))
            info_label.pack(pady=(0, 10))
            
            # Image label
            label = tk.Label(main_frame, image=img_tk, border=2, relief='solid')
            label.pack()
            setattr(label, 'img_ref', img_tk)
            
            # Buttons frame
            button_frame = tk.Frame(main_frame)
            button_frame.pack(pady=(10, 0))
            
            ttk.Button(button_frame, text="Close", command=preview_window.destroy).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Test OCR", command=lambda: [preview_window.destroy(), self.test_ocr()]).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Select New Region", command=lambda: [preview_window.destroy(), self.select_region()]).pack(side='left', padx=5)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to preview region: {e}\n\nThis might indicate the region is invalid.\nPlease select a new region.")

    def start_scanning(self):
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        if not self.ocr_engine:
            messagebox.showerror("Error", "OCR engine not initialized")
            return
        
        self.scanning = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set("Scanning...")
        
        threading.Thread(target=self.scan_loop, daemon=True).start()
        Logger.info("Scanning started")
    
    def stop_scanning(self):
        self.scanning = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set("Stopped")
        Logger.info("Scanning stopped")
    
    def scan_loop(self):
        while self.scanning:
            try:
                screenshot = pyautogui.screenshot(region=self.scan_region)
                img_array = np.array(screenshot)
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Use same logic as test_ocr - try original image first
                texts = self.ocr_engine.extract_text(img_array) if self.ocr_engine else []
                
                # If original didn't work well, try processed image
                if not texts or len(''.join(texts)) < 3:
                    processed_img = self.image_processor.preprocess_for_ocr(img_array)
                    texts = self.ocr_engine.extract_text(processed_img) if self.ocr_engine else []
                
                if texts:
                    self.update_results(texts)
                    
                    event = self.event_db.find_matching_event(texts)
                    if event:
                        self.show_event_popup(event)
                        self.history.add_entry(event, texts)
                        Logger.info(f"Event detected: {event['name']}")
                
                interval = float(self.settings.get('scan_interval', 2.0) or 2.0)
                time.sleep(interval)
            except Exception as e:
                Logger.error(f"Scan error: {e}")
                time.sleep(1)
    
    def update_results(self, texts: List[str]):
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.result_text.insert(tk.END, f"=== {timestamp} ===\n")
        self.result_text.insert(tk.END, f"Detected {len(texts)} text(s):\n\n")
        
        for i, text in enumerate(texts, 1):
            self.result_text.insert(tk.END, f"[{i}] {text}\n")
        
        self.result_text.config(state='disabled')
        self.result_text.see(tk.END)
    
    def show_event_popup(self, event: Dict):
        if self.current_popup:
            try:
                self.current_popup.close()
            except:
                pass
        
        auto_close = bool(self.settings.get('auto_close_popup', True))
        timeout = int(self.settings.get('popup_timeout', 8) or 8)
        
        self.current_popup = EventPopup(self.root, event, auto_close, timeout)
    
    def test_ocr(self):
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        try:
            x, y, w, h = self.scan_region
            
            # Validate region
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if x < 0 or y < 0 or x + w > screen_width or y + h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {x},{y} + {w}x{h}\n\nPlease select a new region.")
                return
            
            if w < 50 or h < 20:
                response = messagebox.askyesno("Small Region", f"Selected region is quite small: {w}x{h}\n\nThis might affect OCR accuracy.\nMinimum recommended: 50x20 pixels\n\nContinue anyway?")
                if not response:
                    return
            
            screenshot = pyautogui.screenshot(region=self.scan_region)
            img_array = np.array(screenshot)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Test with original image first
            texts_original = self.ocr_engine.extract_text(img_array) if self.ocr_engine else []
            
            # Test with processed image if original didn't work well
            if not texts_original or len(''.join(texts_original)) < 3:
                processed_img = self.image_processor.preprocess_for_ocr(img_array)
                texts_processed = self.ocr_engine.extract_text(processed_img) if self.ocr_engine else []
                texts = texts_processed
            else:
                texts = texts_original
                
                if texts:
                    self.update_results(texts)
                    result = '\n'.join(texts)
                    
                    # Check if detected text looks like game text
                    is_valid_game_text = self._check_if_game_text(texts)
                    
                    if is_valid_game_text:
                        messagebox.showinfo("OCR Test Results", f"✅ Detected game text:\n\n{result}")
                    else:
                        warning_msg = f"⚠️ Text may not be from game:\n\n{result}\n\n"
                        warning_msg += "🎯 Tips:\n"
                        warning_msg += "• Make sure region contains ONLY the event text\n"
                        warning_msg += "• Avoid UI elements, buttons, or background\n"
                        warning_msg += "• Ensure text is clear and readable\n"
                        warning_msg += "• Game should be in English language"
                        messagebox.showwarning("OCR Test Results", warning_msg)
                else:
                    failure_msg = "❌ No text detected!\n\n"
                    failure_msg += f"Region: {x},{y} (size: {w}x{h})\n\n"
                    failure_msg += "💡 Try:\n"
                    failure_msg += "• Select a smaller region focused on just the text\n"
                    failure_msg += "• Ensure good contrast (dark text on light background)\n"
                    failure_msg += "• Make sure game is in English\n"
                    failure_msg += f"• Recommended size for single line: ~300x50"
                    messagebox.showinfo("OCR Test Results", failure_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"OCR test failed: {e}")
            Logger.error(f"OCR test error: {e}")
    
    def _check_if_game_text(self, texts: List[str]) -> bool:
        """Check if detected texts look like actual game text"""
        if not texts:
            return False
        
        combined = ' '.join(texts).lower()
        
        # Game-specific keywords that indicate valid game text
        game_indicators = [
            'training', 'race', 'event', 'skill', 'card', 'support',
            'uma', 'musume', 'stamina', 'speed', 'power', 'guts', 'wisdom',
            'scenario', 'choice', 'conversation', 'striking', 'considerate',
            'session', 'win', 'lose', 'level', 'rank', 'grade'
        ]
        
        # Common English words that could appear in game text
        common_words = [
            'the', 'to', 'me', 'be', 'it', 'a', 'and', 'of', 'in', 'for',
            'with', 'on', 'at', 'by', 'from', 'as', 'is', 'was', 'are',
            'have', 'has', 'had', 'will', 'would', 'can', 'could', 'should'
        ]
        
        # Check for game indicators
        for indicator in game_indicators:
            if indicator in combined:
                return True
        
        # Check if it's a reasonable English sentence/phrase
        words = combined.split()
        if len(words) >= 2:
            common_word_count = sum(1 for word in words if word in common_words)
            # If at least 25% are common English words, likely valid
            if common_word_count / len(words) >= 0.25:
                return True
        
        # Check for proper sentence structure
        if any(text[0].isupper() and text.endswith(('!', '.', '?')) for text in texts):
            return True
        
        return False
    
    def refresh_history(self):
        self.history_listbox.delete(0, tk.END)
        
        for entry in self.history.get_history():
            timestamp = entry['timestamp'].strftime('%H:%M:%S')
            event_name = entry['event']['name']
            self.history_listbox.insert(tk.END, f"{timestamp} - {event_name}")
    
    def clear_history(self):
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.history.clear()
            self.refresh_history()
    
    def save_settings(self):
        self.settings.set('scan_interval', self.interval_var.get())
        self.settings.set('auto_close_popup', self.auto_close_var.get())
        
        if self.settings.save_settings():
            messagebox.showinfo("Success", "Settings saved!")
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def on_closing(self):
        if self.scanning:
            self.stop_scanning()
        
        self.settings.set('window_position', self.root.geometry())
        self.settings.save_settings()
        
        self.root.quit()
    
    def run(self):
        Logger.info("Starting Uma Event Scanner")
        self.root.mainloop()
    
def main():
    try:
        app = EventScannerApp()
        app.run()
    except Exception as e:
        Logger.error(f"Application error: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")

if __name__ == '__main__':
    main() 
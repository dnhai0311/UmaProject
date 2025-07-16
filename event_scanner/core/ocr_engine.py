"""
OCR Engine for Uma Event Scanner
Contains OCREngine class with GPU optimization and text processing
"""

import re
import time
from typing import List, Dict, Optional
import numpy as np
from event_scanner.utils import Logger
from event_scanner.core.image_processor import ImageProcessor

# Import OCR libraries
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    Logger.warning("EasyOCR not available")

# Import GPU configuration
try:
    from event_scanner.config import GPUConfig, EASYOCR_CONFIG, IMAGE_PROCESSING_CONFIG, PERFORMANCE_CONFIG
    GPU_CONFIG_AVAILABLE = True
except ImportError:
    GPU_CONFIG_AVAILABLE = False
    Logger.warning("GPU config not available - using default settings")

# Tesseract is no longer used
TESSERACT_AVAILABLE = False


class OCREngine:
    """Advanced OCR engine with GPU optimization for RTX 3050"""
    
    def __init__(self, language: str = 'eng'):
        self.language = language
        self.easyocr_reader = None
        self.use_easyocr = False
        self.gpu_available = False
        
        # Apply GPU optimizations if available
        if GPU_CONFIG_AVAILABLE:
            GPUConfig.optimize_for_rtx3050()
            Logger.info("GPU optimizations applied for RTX 3050")
            
            # Initialize performance monitoring
            if PERFORMANCE_CONFIG.get('enable_monitoring', False):
                self.operation_count = 0
                self.last_cache_clear = time.time()
        
        # Try to initialize EasyOCR with GPU optimization
        if EASYOCR_AVAILABLE:
            try:
                self.gpu_available = self._check_gpu_availability()
                
                if self.gpu_available:
                    try:
                        # Use optimized config for RTX 3050
                        if GPU_CONFIG_AVAILABLE:
                            self.easyocr_reader = easyocr.Reader(
                                ['en'], 
                                **EASYOCR_CONFIG
                            )
                        else:
                            # Fallback to basic GPU settings
                            self.easyocr_reader = easyocr.Reader(
                                ['en'], 
                                gpu=True, 
                                verbose=False,
                                model_storage_directory='./models',
                                download_enabled=True,
                                quantize=True
                            )
                        
                        self.use_easyocr = True
                        Logger.info("EasyOCR initialized with RTX 3050 GPU acceleration")
                        
                    except Exception as gpu_error:
                        Logger.error(f"GPU initialization failed: {gpu_error}")
                        self._fallback_to_cpu()
                else:
                    self._fallback_to_cpu()
                        
            except Exception as e:
                Logger.error(f"Failed to initialize EasyOCR: {e}")
                self._fallback_to_cpu()
        
        # Check if we have any OCR engine
        if not self.use_easyocr and not TESSERACT_AVAILABLE:
            raise ImportError("Neither EasyOCR nor Tesseract is available")
    
    def _fallback_to_cpu(self):
        """Fallback to CPU if GPU fails"""
        try:
            self.easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
            self.use_easyocr = True
            self.gpu_available = False
            Logger.info("EasyOCR initialized with CPU (GPU fallback)")
        except Exception as cpu_error:
            Logger.error(f"CPU initialization failed: {cpu_error}")
            self.use_easyocr = False
    
    def _check_gpu_availability(self) -> bool:
        """Check if GPU is available for processing"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                Logger.info(f"GPU detected: {gpu_name} (Count: {gpu_count}, Memory: {gpu_memory:.1f}GB)")
                
                # Check if it's RTX 3050 or similar
                if "3050" in gpu_name or "3060" in gpu_name or "3070" in gpu_name:
                    Logger.info("RTX 30 series detected - optimizing for performance")
                
                return True
            else:
                Logger.info("CUDA not available - will use CPU")
        except ImportError:
            Logger.info("PyTorch not available - will use CPU")
        return False
    
    def extract_text(self, image: np.ndarray) -> List[str]:
        """High-performance text extraction optimized for RTX 3050"""
        results = []
        
        if not self.use_easyocr or not self.easyocr_reader:
            return results
        
        try:
            # Strategy 1: Fast extraction from original image
            original_results = self._extract_with_easyocr_fast(image)
            results.extend(original_results)
            
            # Strategy 2: Enhanced extraction from preprocessed image (only if needed)
            if not results or len(''.join(results)) < 5:
                processed_image = ImageProcessor.preprocess_for_ocr(image)
                processed_results = self._extract_with_easyocr_fast(processed_image)
                results.extend(processed_results)
            
            # Strategy 3: Multi-scale extraction for better accuracy (only if GPU available)
            if not results and self.gpu_available:
                results.extend(self._multi_scale_extraction(image))
            
            # Remove duplicates and filter results
            unique_results = list(set(results))
            filtered_results = []
            
            for text in unique_results:
                if self._is_valid_text(text):
                    # Apply OCR corrections
                    corrected_text = self._correct_ocr_text(text)
                    # Apply special first character corrections
                    corrected_text = self._fix_first_character_misrecognition(corrected_text)
                    
                    # Add special characters detection for common patterns
                    corrected_text = self._detect_special_characters(corrected_text)
                    
                    if corrected_text and corrected_text not in filtered_results:
                        filtered_results.append(corrected_text)
            
            # Sort by quality score (length + game relevance)
            filtered_results.sort(key=lambda x: self._calculate_text_quality(x), reverse=True)
            
            # Use optimized max results if available
            max_results = IMAGE_PROCESSING_CONFIG.get('max_results', 3) if GPU_CONFIG_AVAILABLE else 3
            return filtered_results[:max_results]
            
        except Exception as e:
            Logger.error(f"Text extraction failed: {e}")
            return []
            
    def _extract_with_easyocr_fast(self, image: np.ndarray) -> List[str]:
        """Fast OCR extraction optimized for GPU"""
        results = []
        
        try:
            if not self.easyocr_reader:
                return results
            
            # Use adaptive confidence threshold
            if GPU_CONFIG_AVAILABLE:
                confidence_threshold = IMAGE_PROCESSING_CONFIG.get('confidence_threshold', 0.4)
            else:
                confidence_threshold = 0.4 if self.gpu_available else 0.3
            
            try:
                ocr_results = self.easyocr_reader.readtext(image, detail=1)
                
                for (bbox, text, confidence) in ocr_results:
                    conf_float = float(confidence) if isinstance(confidence, (str, int, float)) else 0.0
                    
                    if conf_float > confidence_threshold:
                        cleaned_text = text.strip()
                        if cleaned_text and len(cleaned_text) >= 2:
                            results.append(cleaned_text)
                
                # If no high-confidence results, try lower threshold
                if not results and self.gpu_available:
                    for (bbox, text, confidence) in ocr_results:
                        conf_float = float(confidence) if isinstance(confidence, (str, int, float)) else 0.0
                        if conf_float > 0.2:
                            cleaned_text = text.strip()
                            if cleaned_text and len(cleaned_text) >= 2:
                                results.append(cleaned_text)
                        
            except Exception as e:
                Logger.debug(f"Fast OCR extraction failed: {e}")
            
            # Clear GPU cache after processing
            if self.gpu_available:
                try:
                    import torch
                    torch.cuda.empty_cache()
                    
                    # Auto-clear cache based on performance config
                    if GPU_CONFIG_AVAILABLE and PERFORMANCE_CONFIG.get('auto_clear_cache', False):
                        self.operation_count += 1
                        if self.operation_count >= PERFORMANCE_CONFIG.get('clear_cache_interval', 10):
                            GPUConfig.clear_memory()
                            self.operation_count = 0
                            Logger.debug("Auto-cleared GPU cache")
                except:
                    pass
                    
        except Exception as e:
            Logger.error(f"Fast OCR extraction failed: {e}")
        
        return results
    
    def _multi_scale_extraction(self, image: np.ndarray) -> List[str]:
        """Extract text at multiple scales for better accuracy"""
        results = []
        
        try:
            h, w = image.shape[:2]
            
            # Use adaptive scales based on memory
            if GPU_CONFIG_AVAILABLE and IMAGE_PROCESSING_CONFIG.get('enable_multi_scale', True):
                scales = IMAGE_PROCESSING_CONFIG.get('scales', [0.8, 1.0, 1.2])
            else:
                scales = [0.8, 1.0, 1.2, 1.5] if self.gpu_available else [0.8, 1.0, 1.2]
            
            for scale in scales:
                try:
                    # Resize image
                    new_w = int(w * scale)
                    new_h = int(h * scale)
                    
                    if new_w < 20 or new_h < 10:  # Too small
                        continue
                    
                    import cv2
                    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
                    
                    # Extract text from resized image
                    scale_results = self._extract_with_easyocr_fast(resized)
                    results.extend(scale_results)
                    
                    # If we found good results, don't try more scales
                    if len(results) >= 2:
                        break
                        
                except Exception as e:
                    Logger.debug(f"Multi-scale extraction at scale {scale} failed: {e}")
                    continue
                    
        except Exception as e:
            Logger.debug(f"Multi-scale extraction failed: {e}")
        
        return results
    
    def _calculate_text_quality(self, text: str) -> float:
        """Calculate quality score for text"""
        if not text:
            return 0.0
        
        # Base score from length
        length_score = min(len(text) / 50.0, 1.0)
        
        # Game relevance score
        game_words = [
            'training', 'race', 'event', 'skill', 'card', 'support',
            'uma', 'musume', 'stamina', 'speed', 'power', 'guts', 'wisdom',
            'scenario', 'choice', 'conversation', 'striking', 'considerate',
            'session', 'win', 'lose', 'level', 'rank', 'grade', 'new', 'year'
        ]
        
        text_lower = text.lower()
        game_score = 0.0
        for word in game_words:
            if word in text_lower:
                game_score += 0.1
        
        game_score = min(game_score, 1.0)
        
        # Sentence structure score
        structure_score = 0.0
        if text[0].isupper() and text.endswith(('.', '!', '?')):
            structure_score = 0.5
        elif text[0].isupper():
            structure_score = 0.3
        
        # Combined score
        total_score = length_score * 0.4 + game_score * 0.4 + structure_score * 0.2
        
        return total_score

    def _is_valid_text(self, text: str) -> bool:
        """Check if extracted text is valid game text"""
        if not text or len(text) < 2:
            return False
        
        # Remove special characters for analysis but preserve common game symbols
        # Like music notes (♪), stars (★), arrows (→), etc.
        game_symbols = ['♪', '★', '☆', '→', '←', '↑', '↓', '♥', '❤', '!', '?', '(', ')', '[', ']', '{', '}']
        analysis_text = text
        
        # Temporarily replace game symbols with placeholder
        for symbol in game_symbols:
            analysis_text = analysis_text.replace(symbol, '')
        
        # Remove remaining special characters for analysis
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', analysis_text)
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
            
        return True

    def _correct_ocr_text(self, text: str) -> str:
        """Correct common OCR errors"""
        if not text:
            return text
        
        corrections = {
            # Common OCR errors
            'eave': 'Leave', 'eaves': 'Leave', 'toh': 'to', 'sto': 'to',
            'sidera': 'Considerate', 'ey': 'e!', 'Py': '', 'py': '',
            
            # I/T confusion fixes (capital I misrecognized as T)
            'T\'ve': 'I\'ve', 'T\'m': 'I\'m', 'T\'ll': 'I\'ll', 'T\'d': 'I\'d', 
            'Tve': 'I\'ve', 'Tm': 'I\'m', 'Tll': 'I\'ll', 'Td': 'I\'d',
            'T will': 'I will', 'T am': 'I am', 'T have': 'I have',
            'T was': 'I was', 'T want': 'I want', 'T need': 'I need',
            'T got': 'I got', 'T can': 'I can',
            'T would': 'I would', 'T could': 'I could', 'T should': 'I should',
            'T think': 'I think', 'T know': 'I know', 'T see': 'I see',
            'T like': 'I like', 'T love': 'I love',
            
            # I/F confusion (very common OCR error)
            'Fm ': 'I\'m ', 'F am ': 'I am ', 'F will ': 'I will ',
            'F can ': 'I can ', 'F have ': 'I have ', 'F had ': 'I had ',
            'F would ': 'I would ', 'F could ': 'I could ', 'F should ': 'I should ',
            'F think ': 'I think ', 'F know ': 'I know ', 'F see ': 'I see ',
            'F want ': 'I want ', 'F need ': 'I need ', 'F like ': 'I like ',
            'F love ': 'I love ', 'F hate ': 'I hate ', 'F feel ': 'I feel ',
            'F believe ': 'I believe ', 'F hope ': 'I hope ', 'F wish ': 'I wish ',
            'F guess ': 'I guess ', 'F mean ': 'I mean ', 'F say ': 'I say ',
            'F tell ': 'I tell ', 'F ask ': 'I ask ', 'I\'m ': 'I\'m ',
            
            # Exclamation mark confusion
            'l!': '!', 'l?': '?', 'l.': '.',
            'Afraidl': 'Afraid!', 'Afraid?': 'Afraid?', 'Afraid.': 'Afraid.',
            'Not Afraidl': 'Not Afraid!', 'Not Afraid?': 'Not Afraid?',
            
            # Special character corrections (for game-specific symbols)
            'Weather': 'Weather ♪',
            'Weather J': 'Weather ♪',
            'Weather!': 'Weather ♪',
            'Weather.': 'Weather ♪',
            'Training Weather': 'Training Weather ♪',
            'Lovely Training Weather': '(❯) Lovely Training Weather ♪',
            'Lovery Training Weather': '(❯) Lovely Training Weather ♪',
            
            # Common event names
            'Im Not Afraid': 'I\'m Not Afraid!',
            'I m Not Afraid': 'I\'m Not Afraid!',
            'Im Not Afraid!': '(❯) I\'m Not Afraid!',
            'I\'m Not Afraid': '(❯) I\'m Not Afraid!',
            'I\'m Not Afraid!': '(❯) I\'m Not Afraid!',
            'Ive Got This': 'I\'ve Got This!',
            'I ve Got This': 'I\'ve Got This!',
            'Ive Got This!': '(❯) I\'ve Got This!',
            'I\'ve Got This': '(❯) I\'ve Got This!',
            'I\'ve Got This!': '(❯) I\'ve Got This!',
            'Leave it to Me': 'Leave it to Me!',
            'Leave it to Me to Be Considerate': 'Leave it to Me to Be Considerate!'
        }
        
        # Apply corrections
        corrected = text
        for old, new in corrections.items():
            corrected = corrected.replace(old, new)
        
        # Special case handling
        if "not afraid" in corrected.lower() and not "i'm not afraid" in corrected.lower():
            corrected = "(❯) I'm Not Afraid!"
        
        if "got this" in corrected.lower() and not "i've got this" in corrected.lower():
            corrected = "(❯) I've Got This!"
        
        return corrected
    
    def _smart_text_corrections(self, text: str) -> str:
        """Apply smart text corrections based on context"""
        if not text:
            return text
        
        # Fix common OCR errors at word boundaries
        import re
        
        # Words that should not have 'l' replaced with '!'
        safe_words = {
            'will', 'well', 'all', 'call', 'fall', 'ball', 'small', 'tall',
            'wall', 'hall', 'full', 'pull', 'bull', 'dull', 'null', 'kill',
            'fill', 'hill', 'mill', 'pill', 'still', 'skill', 'drill', 'grill',
            'chill', 'spill', 'thrill', 'until', 'while', 'mile', 'file',
            'smile', 'style', 'tile', 'pile', 'vile', 'wile', 'bile', 'rile'
        }
        
        # Fix I/T confusion at start of sentences or words
        text = re.sub(r'\bT\b(?=\s+[a-z])', 'I', text)
        text = re.sub(r'\bT\'(?=[a-zA-Z])', 'I\'', text)  # Fix T'xx patterns like T've, T'll, T'm
        text = re.sub(r'\bT(?=\'[a-zA-Z])', 'I', text)    # Fix alternative apostrophe patterns
        
        # Fix I/F confusion at start of sentences (more specific)
        text = re.sub(r'\bF\b(?=\s+[a-z])', 'I', text)
        
        # Fix common word truncation
        text = re.sub(r'\bhap\b', 'happy', text)
        text = re.sub(r'\bhap\s', 'happy ', text)
        
        # Fix specific common patterns first
        text = re.sub(r'\bwill\s+do\s*$', 'will do!', text)
        text = re.sub(r'\bcan\s+do\s*$', 'can do!', text)
        text = re.sub(r'\bshould\s+do\s*$', 'should do!', text)
        
        # Fix exclamation marks at end of words (more specific)
        # Only fix if it's likely to be punctuation and not a safe word
        words = text.split()
        corrected_words = []
        
        for word in words:
            if word.endswith('l') and word.lower() not in safe_words:
                # Check if it looks like it should be punctuation
                if len(word) > 1 and word[-2].isalpha():
                    corrected_words.append(word[:-1] + '!')
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        text = ' '.join(corrected_words)
        
        # Fix common contractions
        text = re.sub(r'\bFm\b', 'I\'m', text)
        text = re.sub(r'\bFll\b', 'I\'ll', text)
        text = re.sub(r'\bFve\b', 'I\'ve', text)
        text = re.sub(r'\bFd\b', 'I\'d', text)
        text = re.sub(r'\bTm\b', 'I\'m', text)
        text = re.sub(r'\bTll\b', 'I\'ll', text)
        text = re.sub(r'\bTve\b', 'I\'ve', text)
        text = re.sub(r'\bTd\b', 'I\'d', text)
        
        # Handle case where "I've Got This" is detected
        if re.search(r'T\'ve\s+Got\s+This', text, re.IGNORECASE) or re.search(r'Tve\s+Got\s+This', text, re.IGNORECASE):
            text = re.sub(r'T\'ve\s+Got\s+This', 'I\'ve Got This!', text, flags=re.IGNORECASE)
            text = re.sub(r'Tve\s+Got\s+This', 'I\'ve Got This!', text, flags=re.IGNORECASE)
        
        # Fix common game text patterns
        if 'Afraid' in text and text.endswith('l'):
            text = text[:-1] + '!'
        
        return text 

    def _fix_first_character_misrecognition(self, text: str) -> str:
        """Fix common OCR errors for the first character of text, especially I vs T confusion"""
        if not text or len(text) < 2:
            return text
            
        # Common first character misrecognitions
        first_char_fixes = {
            # I-related fixes (most common)
            'T\'': 'I\'',    # T've, T'm, T'd, T'll -> I've, I'm, I'd, I'll
            'T ': 'I ',      # T will, T am, etc. -> I will, I am, etc.
            'Tv': 'I\'v',    # Tve -> I've (missing apostrophe)
            'Tm': 'I\'m',    # Tm -> I'm (missing apostrophe)
            'Tl': 'I\'l',    # Tll -> I'll (missing apostrophe)
            'Td': 'I\'d',    # Td -> I'd (missing apostrophe)
            'F\'': 'I\'',    # F've, F'm, etc. -> I've, I'm, etc.
            'F ': 'I ',      # F will, F am, etc. -> I will, I am, etc.
            
            # Other common first character fixes
            '0': 'O',        # 0h -> Oh
            '1': 'I',        # 1'm -> I'm
            '!': 'I',        # !t's -> It's
            'l\'': 'I\'',    # l've -> I've (lowercase L)
            'l ': 'I ',      # l will -> I will (lowercase L)
        }
        
        # Try to fix the beginning of the text
        for wrong, right in first_char_fixes.items():
            if text.startswith(wrong):
                text = right + text[len(wrong):]
                break
                
        # Special case for "I've Got This!" which is a common phrase
        if text.lower().startswith("t've got this") or text.lower().startswith("tve got this"):
            text = "I've Got This!"
            
        return text 

    def _detect_special_characters(self, text: str) -> str:
        """Detect and add missing special characters based on context"""
        # List of known event patterns with special characters
        special_patterns = {
            "Lovely Training Weather": "(❯) Lovely Training Weather ♪",
            "Perfect Weather": "(❯) Perfect Weather ♪",
            "Nice Weather": "(❯) Nice Weather ♪",
            "Good Weather": "(❯) Good Weather ♪",
            "Sunny Weather": "(❯) Sunny Weather ♪",
            "Rainy Weather": "(❯) Rainy Weather ♪",
            "Cloudy Weather": "(❯) Cloudy Weather ♪",
            "Hot Weather": "(❯) Hot Weather ♪",
            "Cold Weather": "(❯) Cold Weather ♪",
            "Leave it to Me": "Leave it to Me!",
            "I'm Not Afraid": "(❯) I'm Not Afraid!",
            "Im Not Afraid": "(❯) I'm Not Afraid!",
            "Not Afraid": "(❯) I'm Not Afraid!",
            "I've Got This": "(❯) I've Got This!",
            "Ive Got This": "(❯) I've Got This!",
            "Got This": "(❯) I've Got This!"
        }
        
        # Check if text exactly matches any pattern but doesn't have the special character
        for pattern, corrected in special_patterns.items():
            if text == pattern:
                return corrected
        
        # Check if text starts with any pattern
        for pattern, corrected in special_patterns.items():
            if text.startswith(pattern) and text != corrected:
                return corrected
                
        # Check if text contains any pattern (for partial matches)
        for pattern, corrected in special_patterns.items():
            if pattern in text and not corrected in text:
                # Only replace if we're sure this is the event title (not part of another text)
                words = text.split()
                if len(words) <= len(pattern.split()) + 2:  # Allow small variation
                    return corrected
                
        return text 
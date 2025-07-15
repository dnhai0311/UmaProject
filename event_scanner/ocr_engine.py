"""
OCR Engine for Uma Event Scanner
Contains OCREngine class with GPU optimization and text processing
"""

import re
import time
from typing import List, Dict, Optional
import numpy as np
from utils import Logger
from image_processor import ImageProcessor

# Import OCR libraries
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    Logger.warning("EasyOCR not available")

# Import GPU configuration
try:
    from gpu_config import GPUConfig, EASYOCR_CONFIG, IMAGE_PROCESSING_CONFIG, PERFORMANCE_CONFIG
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
                    corrected_text = self._correct_ocr_text(text)
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
        """Correct common OCR errors"""
        if not text:
            return text
        
        corrections = {
            # Common OCR errors
            'eave': 'Leave', 'eaves': 'Leave', 'toh': 'to', 'sto': 'to',
            'sidera': 'Considerate', 'ey': 'e!', 'Py': '', 'py': '',
            
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
            'Not Afraidl': 'Not Afraid!', 'Not Afraid?': 'Not Afraid?', 'Not Afraid.': 'Not Afraid.',
            
            # Common game text corrections
            'Not Afraidl': 'Not Afraid!', 'Not Afraid?': 'Not Afraid?',
            'I\'m Not Afraidl': 'I\'m Not Afraid!', 'I\'m Not Afraid?': 'I\'m Not Afraid?',
            'Fm Not Afraidl': 'I\'m Not Afraid!', 'Fm Not Afraid?': 'I\'m Not Afraid?',
            
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
        
        # Additional smart corrections
        corrected = self._smart_text_corrections(corrected)
        
        # Remove duplicate words
        words = corrected.split()
        final_words = []
        prev_word = ""
        
        for word in words:
            if word.lower() != prev_word.lower():
                final_words.append(word)
                prev_word = word
        
        return ' '.join(final_words)
    
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
        
        # Fix common game text patterns
        if 'Afraid' in text and text.endswith('l'):
            text = text[:-1] + '!'
        
        return text 
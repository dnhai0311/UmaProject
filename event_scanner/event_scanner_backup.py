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

# Import OCR libraries
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("EasyOCR not available")

# Import GPU configuration
try:
    from gpu_config import GPUConfig, EASYOCR_CONFIG, IMAGE_PROCESSING_CONFIG, PERFORMANCE_CONFIG
    GPU_CONFIG_AVAILABLE = True
except ImportError:
    GPU_CONFIG_AVAILABLE = False
    print("GPU config not available - using default settings")

# Tesseract is no longer used
TESSERACT_AVAILABLE = False

# Constants
DATA_FILE = '../scrape/data/all_training_events.json'

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
        """Enhanced preprocessing for better OCR accuracy with multiple methods"""
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
        
        # Try multiple preprocessing methods and pick the best
        methods = [
            ImageProcessor._method_adaptive_clahe,
            ImageProcessor._method_otsu_enhanced,
            ImageProcessor._method_edge_based,
            ImageProcessor._method_frequency_domain,
            ImageProcessor._method_morphological
        ]
        
        best_result = None
        best_score = -1
        
        for method in methods:
            try:
                result = method(gray)
                score = ImageProcessor._evaluate_preprocessing_quality(result)
                if score > best_score:
                    best_score = score
                    best_result = result
            except Exception as e:
                Logger.debug(f"Preprocessing method failed: {e}")
                continue
        
        return best_result if best_result is not None else gray
    
    @staticmethod
    def _method_adaptive_clahe(gray: np.ndarray) -> np.ndarray:
        """Method 1: Adaptive CLAHE with noise reduction"""
        # Apply bilateral filter to reduce noise while preserving edges
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Apply Gaussian blur for additional smoothing
        blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
        
        # Enhanced CLAHE with adaptive parameters
        clahe = cv2.createCLAHE(clipLimit=15.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 11
        )
        
        # Clean up with morphological operations
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        return ImageProcessor._ensure_black_text_on_white(binary)
    
    @staticmethod
    def _method_otsu_enhanced(gray: np.ndarray) -> np.ndarray:
        """Method 2: Enhanced Otsu with preprocessing"""
        # Apply median filter to remove salt-and-pepper noise
        median = cv2.medianBlur(gray, 5)
        
        # Apply unsharp masking to enhance edges
        gaussian = cv2.GaussianBlur(median, (0, 0), 2.0)
        unsharp = cv2.addWeighted(median, 1.5, gaussian, -0.5, 0)
        
        # Apply CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=8.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(unsharp)
        
        # Otsu's thresholding
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological cleanup
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        return ImageProcessor._ensure_black_text_on_white(binary)
    
    @staticmethod
    def _method_edge_based(gray: np.ndarray) -> np.ndarray:
        """Method 3: Edge-based text detection"""
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Dilate edges to connect text components
        kernel = np.ones((2, 2), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours and create mask
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Create mask for text regions
        mask = np.zeros_like(gray)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 50:  # Filter small noise
                cv2.fillPoly(mask, [contour], 255)
        
        # Apply mask to original image
        masked = cv2.bitwise_and(gray, mask)
        
        # Apply adaptive threshold to masked region
        binary = cv2.adaptiveThreshold(
            masked, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, 5
        )
        
        return ImageProcessor._ensure_black_text_on_white(binary)
    
    @staticmethod
    def _method_frequency_domain(gray: np.ndarray) -> np.ndarray:
        """Method 4: Frequency domain processing"""
        # Apply FFT
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        
        # Create high-pass filter
        rows, cols = gray.shape
        crow, ccol = rows // 2, cols // 2
        mask = np.ones((rows, cols), np.uint8)
        r = 30
        center = [crow, ccol]
        x, y = np.ogrid[:rows, :cols]
        mask_area = (x - center[0]) ** 2 + (y - center[1]) ** 2 <= r*r
        mask[mask_area] = 0
        
        # Apply filter
        f_shift_filtered = f_shift * mask
        f_ishift = np.fft.ifftshift(f_shift_filtered)
        img_back = np.fft.ifft2(f_ishift)
        img_back = np.abs(img_back)
        
        # Normalize and convert to uint8
        img_back = np.clip(img_back, 0, 255).astype(np.uint8)
        
        # Apply threshold
        _, binary = cv2.threshold(img_back, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return ImageProcessor._ensure_black_text_on_white(binary)
    
    @staticmethod
    def _method_morphological(gray: np.ndarray) -> np.ndarray:
        """Method 5: Advanced morphological processing"""
        # Apply top-hat transform to extract bright text on dark background
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        
        # Apply black-hat transform to extract dark text on bright background
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        
        # Combine both transforms
        combined = cv2.add(gray, tophat)
        combined = cv2.subtract(combined, blackhat)
        
        # Apply CLAHE
        clahe = cv2.createCLAHE(clipLimit=10.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(combined)
        
        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Advanced morphological operations
        # Remove small noise
        kernel_noise = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_noise, iterations=1)
        
        # Fill gaps in characters
        kernel_fill = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_fill, iterations=1)
        
        # Slight dilation to make text more readable
        kernel_dilate = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel_dilate, iterations=1)
        
        return ImageProcessor._ensure_black_text_on_white(binary)
    
    @staticmethod
    def _evaluate_preprocessing_quality(binary: np.ndarray) -> float:
        """Evaluate the quality of preprocessing result"""
        h, w = binary.shape
        
        # Calculate white pixel ratio
        white_pixels = np.sum(binary == 255)
        total_pixels = h * w
        white_ratio = white_pixels / total_pixels
        
        # Ideal ratio for text is around 70-85%
        if 0.65 <= white_ratio <= 0.90:
            ratio_score = 1.0 - abs(0.775 - white_ratio) / 0.125
        else:
            ratio_score = 0.0
        
        # Calculate edge density (text should have good edge content)
        edges = cv2.Canny(binary, 50, 150)
        edge_density = np.sum(edges > 0) / total_pixels
        edge_score = min(edge_density * 100, 1.0)
        
        # Calculate connected component analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        
        # Count reasonable text components (not too small, not too large)
        good_components = 0
        for i in range(1, num_labels):  # Skip background
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            
            # Text components should be reasonable size
            if 20 <= area <= 2000 and 3 <= width <= 200 and 5 <= height <= 100:
                good_components += 1
        
        component_score = min(good_components / 10.0, 1.0)  # Normalize
        
        # Combined score
        total_score = (ratio_score * 0.4 + edge_score * 0.3 + component_score * 0.3)
        
        return total_score
    
    @staticmethod
    def _ensure_black_text_on_white(binary: np.ndarray) -> np.ndarray:
        """Ensure text is black on white background"""
        black_pixels = np.sum(binary == 0)
        white_pixels = np.sum(binary == 255)
        
        if black_pixels > white_pixels:
            # More black than white, likely inverted
            binary = cv2.bitwise_not(binary)
        
        return binary
    
    @staticmethod
    def detect_text_regions(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect potential text regions in the image"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Apply contour detection for text regions (simpler alternative to MSER)
        # Apply adaptive threshold to find text regions
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and merge regions
        text_regions = []
        for contour in contours:
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by size (reasonable text size)
            if 20 <= w <= 300 and 10 <= h <= 100 and w * h >= 100:
                # Check aspect ratio (text should be wider than tall)
                aspect_ratio = w / h
                if 0.5 <= aspect_ratio <= 10:
                    text_regions.append((x, y, w, h))
        
        # Merge overlapping regions
        merged_regions = ImageProcessor._merge_overlapping_regions(text_regions)
        
        return merged_regions
    
    @staticmethod
    def _merge_overlapping_regions(regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Merge overlapping or nearby text regions"""
        if not regions:
            return []
        
        # Sort regions by x coordinate
        regions = sorted(regions, key=lambda r: r[0])
        
        merged = []
        current = list(regions[0])
        
        for region in regions[1:]:
            x, y, w, h = region
            
            # Check if regions overlap or are close
            if (x <= current[0] + current[2] + 10 and  # Within 10 pixels horizontally
                abs(y - current[1]) <= max(current[3], h) * 0.5):  # Within 50% of height vertically
                
                # Merge regions
                new_x = min(current[0], x)
                new_y = min(current[1], y)
                new_w = max(current[0] + current[2], x + w) - new_x
                new_h = max(current[1] + current[3], y + h) - new_y
                
                current = [new_x, new_y, new_w, new_h]
            else:
                merged.append(tuple(current))
                current = list(region)
        
        merged.append(tuple(current))
        return merged

class OCREngine:
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
        self.popup.title('🎯 Event Detected!')
        
        # Force popup to be on top with multiple methods
        self.popup.attributes('-topmost', True)
        self.popup.lift()  # Bring to front
        self.popup.focus_force()  # Force focus
        
        # Additional Windows-specific attributes for better z-order
        try:
            self.popup.attributes('-toolwindow', False)  # Ensure it's not a tool window
            self.popup.attributes('-alpha', 1.0)  # Ensure full opacity
        except:
            pass  # Some attributes might not be available on all platforms
        
        self.popup.resizable(True, True)  # Allow resizing
        
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        
        # Calculate optimal size based on content
        choices = self.event.get('choices', [])
        
        # Estimate height needed for each choice (including effects)
        choice_height_estimate = 0
        for choice in choices:
            if isinstance(choice, dict):
                text = choice.get('choice', str(choice))
                effect = choice.get('effect', '') or choice.get('effects', '')
                # Estimate lines needed for text and effect
                text_lines = max(1, len(text) // 50)  # ~50 chars per line
                effect_lines = max(1, len(effect) // 50) if effect else 0
                choice_height_estimate += (text_lines + effect_lines + 2) * 25 + 30  # 25px per line + padding
            else:
                choice_height_estimate += 70  # Default height for simple choices
        
        # Base height for header and buttons
        base_height = 200
        total_height = base_height + choice_height_estimate
        
        # Responsive width and height - limit height to prevent too large popup
        width = min(1000, screen_width - 100)  # Reasonable width
        max_height = min(screen_height - 100, 800)  # Max 800px height
        height = min(total_height, max_height)
        
        # Position popup at bottom right corner
        x = screen_width - width - 20  # 20px margin from right edge
        y = screen_height - height - 20  # 20px margin from bottom edge
        
        self.popup.geometry(f'{width}x{height}+{x}+{y}')
        self.popup.configure(bg='#2c3e50')
        
        # Add border and shadow effect
        self.popup.configure(relief='raised', bd=3)
        
        # Ensure popup stays on top after geometry is set
        self.popup.after(100, self._ensure_on_top)
        
        self.create_content()
        
        # Final check to ensure popup is visible
        self.popup.after(200, self._final_visibility_check)
    
    def _final_visibility_check(self):
        """Final check to ensure popup is visible and properly positioned"""
        try:
            # Force update and bring to front
            self.popup.update_idletasks()
            self.popup.lift()
            self.popup.attributes('-topmost', True)
            self.popup.focus_force()
            
            # Ensure window is not minimized
            self.popup.state('normal')
            
        except Exception as e:
            Logger.debug(f"Final visibility check failed: {e}")
    
    def _ensure_on_top(self):
        """Ensure popup stays on top after creation"""
        try:
            self.popup.lift()
            self.popup.attributes('-topmost', True)
            self.popup.focus_force()
            
            # Windows-specific: Force window to front using win32api if available
            try:
                import win32gui
                import win32con
                
                # Get the window handle
                hwnd = self.popup.winfo_id()
                
                # Set window to be always on top
                win32gui.SetWindowPos(
                    hwnd, 
                    win32con.HWND_TOPMOST, 
                    0, 0, 0, 0, 
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                )
                
                # Bring window to front
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
            except ImportError:
                # win32gui not available, use tkinter methods only
                pass
            except Exception as e:
                Logger.debug(f"Windows-specific window management failed: {e}")
                
        except Exception as e:
            Logger.error(f"Error ensuring popup is on top: {e}")
    
    def create_content(self):
        # Main container with scrollbar
        main_container = tk.Frame(self.popup, bg='#2c3e50')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)  # Less padding
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(main_container, bg='#2c3e50', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Header with icon
        header_frame = tk.Frame(scrollable_frame, bg='#e74c3c', padx=15, pady=10)  # Less padding
        header_frame.pack(fill='x', pady=(0, 15))  # Less spacing
        
        event_label = tk.Label(
            header_frame, 
            text=f"🎯 {self.event['name']}",
            font=('Arial', 14, 'bold'),  # Larger font
            fg='white',
            bg='#e74c3c',
            wraplength=950  # Smaller wrapping
        )
        event_label.pack()
        
        # Choices section
        choices = self.event.get('choices', [])
        if choices:
            choices_label = tk.Label(
                scrollable_frame,
                text="📋 Available Choices:",
                font=('Arial', 12, 'bold'),  # Larger font
                fg='#ecf0f1',
                bg='#2c3e50'
            )
            choices_label.pack(anchor='w', pady=(0, 10))  # Less spacing
            
            # Create choices container
            choices_container = tk.Frame(scrollable_frame, bg='#2c3e50')
            choices_container.pack(fill='x', expand=True)
            
            for i, choice in enumerate(choices):
                # Define vibrant colors for different options
                colors = [
                    '#3498db',  # Blue
                    '#e67e22',  # Orange  
                    '#9b59b6',  # Purple
                    '#f1c40f',  # Yellow
                    '#1abc9c',  # Turquoise
                    '#e74c3c',  # Red
                    '#2ecc71',  # Green
                    '#f39c12'   # Gold
                ]
                bg_color = colors[i % len(colors)]
                
                # Create choice frame with rounded corners effect
                choice_frame = tk.Frame(choices_container, bg=bg_color, padx=15, pady=10, relief='raised', bd=2)  # Less padding
                choice_frame.pack(fill='x', pady=5)  # Less spacing
                
                # Create choice text label
                if isinstance(choice, dict):
                    text = choice.get('choice', str(choice))
                    effect = choice.get('effect', '') or choice.get('effects', '')
                    
                    # Choice text
                    choice_label = tk.Label(
                        choice_frame,
                        text=f"{i+1}. {text}",
                        font=('Arial', 11, 'bold'),  # Larger font
                        fg='white',
                        bg=bg_color,
                        wraplength=950,  # Smaller wrapping
                        justify='left',
                        anchor='w'
                    )
                    choice_label.pack(anchor='w', pady=(0, 8))  # Less spacing
                    
                    # Effect text (if exists)
                    if effect:
                        effect_label = tk.Label(
                            choice_frame,
                            text=f"   💡 Effect: {effect}",
                            font=('Arial', 10),  # Larger font
                            fg='white',
                            bg=bg_color,
                            wraplength=950,  # Smaller wrapping
                            justify='left',
                            anchor='w'
                        )
                        effect_label.pack(anchor='w')
                else:
                    # Simple string choice
                    choice_label = tk.Label(
                        choice_frame,
                        text=f"{i+1}. {choice}",
                        font=('Arial', 11, 'bold'),  # Larger font
                        fg='white',
                        bg=bg_color,
                        wraplength=950,  # Smaller wrapping
                        justify='left',
                        anchor='w'
                    )
                    choice_label.pack(anchor='w')
        
        # Close button with better styling
        close_btn = tk.Button(
            scrollable_frame,
            text='✖ Close',
            command=self.close,
            bg='#34495e',
            fg='white',
            font=('Arial', 10, 'bold'),  # Larger font
            padx=25,  # Less padding
            pady=5,   # Less padding
            relief='raised',
            bd=2
        )
        close_btn.pack(pady=(20, 0))  # Less spacing
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel to canvas with proper error handling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas might be destroyed, ignore the error
                pass
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Unbind when popup is closed
        def _on_closing():
            try:
                canvas.unbind_all("<MouseWheel>")
            except:
                pass
            self.close()
        
        self.popup.protocol("WM_DELETE_WINDOW", _on_closing)
    
    def _format_choice(self, choice, index: int) -> str:
        if isinstance(choice, dict):
            text = choice.get('choice', str(choice))
            # Check for both 'effect' and 'effects' keys
            effect = choice.get('effect', '') or choice.get('effects', '')
            if effect:
                # Format with better spacing and wrapping
                return f"{index}. {text}\n\n   💡 Effect: {effect}"
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
        self.root.geometry("800x700")  # Larger size to prevent label cutting
        self.root.minsize(700, 600)
        
        # Set modern theme colors
        style = ttk.Style()
        style.theme_use('clam')  # Use clam theme for better appearance
        
        # Configure custom colors
        self.root.configure(bg='#f0f0f0')
        
        self.position_window()
        
        # Create main container
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)  # More padding
        
        # Title bar
        title_frame = tk.Frame(main_container, bg='#2c3e50', height=60)  # Slightly shorter
        title_frame.pack(fill='x', pady=(0, 15))  # More spacing
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎯 Uma Event Scanner",
            font=('Arial', 16, 'bold'),  # Slightly smaller font
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(expand=True)
        
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True, pady=(0, 15))  # More spacing
        
        self.create_scanner_tab()
        self.create_history_tab()
        self.create_settings_tab()
        
        # Status bar with better styling
        status_frame = tk.Frame(main_container, bg='#34495e', height=30)  # Slightly shorter
        status_frame.pack(fill='x')
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(
            status_frame, 
            textvariable=self.status_var, 
            relief='flat',
            bg='#34495e',
            fg='white',
            font=('Arial', 9)  # Slightly smaller font
        )
        self.status_bar.pack(side='left', padx=15, pady=6)  # Less padding
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def position_window(self):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # DEBUG: Print screen width/height
        print(f"[DEBUG] screen_width={screen_width}, screen_height={screen_height}")
        
        # Position window on the right side with new size
        x = screen_width - 800  # Adjusted for new width
        y = 10
        print(f"[DEBUG] Calculated x={x}, y={y}")
        geometry_str = f"800x700+{x}+{y}"  # Updated size
        print(f"[DEBUG] geometry: {geometry_str}")
        self.root.geometry(geometry_str)
        self.root.attributes('-topmost', True)
        # Force geometry after 100ms to ensure correct position
        self.root.after(100, lambda: self.root.geometry(geometry_str))

    def create_scanner_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Scanner")
        
        # Region selection with better styling
        region_frame = tk.LabelFrame(tab, text="📐 Scan Region", font=('Arial', 10, 'bold'))
        region_frame.pack(fill='x', padx=15, pady=10)
        
        region_inner = tk.Frame(region_frame, bg='#ecf0f1', padx=15, pady=10)
        region_inner.pack(fill='x')
        
        self.region_label = tk.Label(
            region_inner, 
            text=self.get_region_text(),
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.region_label.pack(side='left', padx=(0, 10))
        
        # Buttons with modern styling
        select_btn = tk.Button(
            region_inner, 
            text="🎯 Select Region", 
            command=self.select_region,
            bg='#3498db',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        select_btn.pack(side='left', padx=5)
        
        preview_btn = tk.Button(
            region_inner, 
            text="👁️ Preview", 
            command=self.preview_region,
            bg='#e67e22',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        preview_btn.pack(side='left', padx=5)
        
        # Controls with better styling
        control_frame = tk.LabelFrame(tab, text="🎮 Controls", font=('Arial', 10, 'bold'))
        control_frame.pack(fill='x', padx=15, pady=10)
        
        control_inner = tk.Frame(control_frame, bg='#ecf0f1', padx=15, pady=10)
        control_inner.pack(fill='x')
        
        self.start_btn = tk.Button(
            control_inner, 
            text="▶️ Start Scanning", 
            command=self.start_scanning,
            bg='#27ae60',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            bd=0
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            control_inner, 
            text="⏹️ Stop", 
            command=self.stop_scanning,
            state='disabled',
            bg='#e74c3c',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            bd=0
        )
        self.stop_btn.pack(side='left', padx=5)
        
        test_btn = tk.Button(
            control_inner, 
            text="🔍 Test OCR", 
            command=self.test_ocr,
            bg='#9b59b6',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        test_btn.pack(side='left', padx=5)
        
        test_json_btn = tk.Button(
            control_inner, 
            text="📄 Test JSON", 
            command=self.test_with_json_data,
            bg='#f39c12',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        test_json_btn.pack(side='left', padx=5)
        
        # Results with better styling
        result_frame = tk.LabelFrame(tab, text="📊 Results", font=('Arial', 10, 'bold'))
        result_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        result_inner = tk.Frame(result_frame, bg='#ecf0f1')
        result_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_frame = tk.Frame(result_inner)
        text_frame.pack(fill='both', expand=True)
        
        self.result_text = tk.Text(
            text_frame, 
            height=15, 
            state='disabled', 
            font=('Consolas', 10),
            bg='white',
            fg='#2c3e50',
            relief='flat',
            bd=1
        )
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_history_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="History")
        
        # Controls with better styling
        control_frame = tk.LabelFrame(tab, text="📋 History Controls", font=('Arial', 10, 'bold'))
        control_frame.pack(fill='x', padx=15, pady=10)
        
        control_inner = tk.Frame(control_frame, bg='#ecf0f1', padx=15, pady=10)
        control_inner.pack(fill='x')
        
        refresh_btn = tk.Button(
            control_inner, 
            text="🔄 Refresh", 
            command=self.refresh_history,
            bg='#3498db',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        refresh_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            control_inner, 
            text="🗑️ Clear", 
            command=self.clear_history,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        clear_btn.pack(side='left', padx=5)
        
        # History list with better styling
        list_frame = tk.LabelFrame(tab, text="📜 Event History", font=('Arial', 10, 'bold'))
        list_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        list_inner = tk.Frame(list_frame, bg='#ecf0f1')
        list_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.history_listbox = tk.Listbox(
            list_inner, 
            font=('Arial', 10),
            bg='white',
            fg='#2c3e50',
            relief='flat',
            bd=1,
            selectmode='single',
            activestyle='none'
        )
        hist_scrollbar = ttk.Scrollbar(list_inner, orient='vertical', command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hist_scrollbar.set)
        
        self.history_listbox.pack(side='left', fill='both', expand=True)
        hist_scrollbar.pack(side='right', fill='y')
        
        # Bind double-click to show event details
        self.history_listbox.bind('<Double-Button-1>', self.show_history_event)
        
        self.refresh_history()
    
    def create_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Scanner settings with better styling
        scanner_frame = tk.LabelFrame(tab, text="⚙️ Scanner Settings", font=('Arial', 10, 'bold'))
        scanner_frame.pack(fill='x', padx=15, pady=10)
        
        scanner_inner = tk.Frame(scanner_frame, bg='#ecf0f1', padx=15, pady=15)
        scanner_inner.pack(fill='x')
        
        # Scan interval setting
        interval_label = tk.Label(
            scanner_inner, 
            text="⏱️ Scan Interval (seconds):",
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        interval_label.grid(row=0, column=0, sticky='w', pady=5)
        
        self.interval_var = tk.DoubleVar(value=self.settings.get('scan_interval', 2.0))
        interval_entry = tk.Entry(
            scanner_inner, 
            textvariable=self.interval_var, 
            width=10,
            font=('Arial', 10),
            relief='flat',
            bd=1
        )
        interval_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Popup settings with better styling
        popup_frame = tk.LabelFrame(tab, text="🔔 Popup Settings", font=('Arial', 10, 'bold'))
        popup_frame.pack(fill='x', padx=15, pady=10)
        
        popup_inner = tk.Frame(popup_frame, bg='#ecf0f1', padx=15, pady=15)
        popup_inner.pack(fill='x')
        
        self.auto_close_var = tk.BooleanVar(value=self.settings.get('auto_close_popup', True))
        auto_close_check = tk.Checkbutton(
            popup_inner, 
            text="🔄 Auto-close popups",
            variable=self.auto_close_var,
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50',
            selectcolor='#3498db'
        )
        auto_close_check.grid(row=0, column=0, sticky='w', pady=5)
        
        # Save button with better styling
        save_btn = tk.Button(
            tab, 
            text="💾 Save Settings", 
            command=self.save_settings,
            bg='#27ae60',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=30,
            pady=10,
            relief='flat',
            bd=0
        )
        save_btn.pack(pady=20)
    
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
                
                # Apply image size optimization if available
                if GPU_CONFIG_AVAILABLE:
                    max_size = IMAGE_PROCESSING_CONFIG.get('max_image_size', (800, 600))
                    h, w = img_array.shape[:2]
                    if h > max_size[1] or w > max_size[0]:
                        scale = min(max_size[0] / w, max_size[1] / h)
                        new_w, new_h = int(w * scale), int(h * scale)
                        img_array = cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
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
        
        # Create popup and ensure it's properly displayed
        self.current_popup = EventPopup(self.root, event, auto_close, timeout)
        
        # Additional steps to ensure popup is on top
        try:
            # Force the popup to be visible and on top
            self.current_popup.popup.update_idletasks()
            self.current_popup.popup.lift()
            self.current_popup.popup.attributes('-topmost', True)
            self.current_popup.popup.focus_force()
            
            # Schedule another check after a short delay
            self.root.after(200, self._ensure_popup_visibility)
        except Exception as e:
            Logger.error(f"Error ensuring popup visibility: {e}")
    
    def _ensure_popup_visibility(self):
        """Additional check to ensure popup is visible and on top"""
        if self.current_popup:
            try:
                self.current_popup.popup.lift()
                self.current_popup.popup.attributes('-topmost', True)
                self.current_popup.popup.focus_force()
            except Exception as e:
                Logger.error(f"Error in popup visibility check: {e}")
    
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
    
    def test_with_json_data(self):
        """Test popup with sample JSON data to debug display issues"""
        # Create a test event with many choices
        test_event = {
            'name': 'Test Event with Many Choices - This is a very long event name to test wrapping and display issues',
            'choices': [
                {
                    'choice': 'First Choice - This is a very long choice text to test wrapping and display properly',
                    'effects': 'Speed +10, Stamina +5, Power +3, Guts +2, Wisdom +1'
                },
                {
                    'choice': 'Second Choice - Another long choice with different effects',
                    'effects': 'Power +15, Speed +5, Stamina +10'
                },
                {
                    'choice': 'Third Choice - This choice has a very long effect description that should wrap properly',
                    'effects': 'Guts +8, Wisdom +3, Speed +2, Power +2, Stamina +2'
                },
                {
                    'choice': 'Fourth Choice - Balanced approach',
                    'effects': 'Speed +5, Power +5, Stamina +5, Guts +5, Wisdom +5'
                },
                {
                    'choice': 'Fifth Choice - This choice has a very long effect description that should wrap properly and show multiple lines',
                    'effects': 'Speed +3, Power +3, Stamina +3, Guts +3, Wisdom +3, Special bonus: Get Hot Topic status'
                },
                {
                    'choice': 'Sixth Choice - Special effect',
                    'effects': 'Special effect: Gain unique skill'
                },
                {
                    'choice': 'Seventh Choice - Another special effect',
                    'effects': 'Another special effect with long description'
                },
                {
                    'choice': 'Eighth Choice - Final choice',
                    'effects': 'Yet another effect with multiple bonuses'
                }
            ]
        }
        
        # Show test popup
        auto_close = False
        self.current_popup = EventPopup(self.root, test_event, auto_close, 0)
        
        # Ensure test popup is also properly displayed
        try:
            self.current_popup.popup.update_idletasks()
            self.current_popup.popup.lift()
            self.current_popup.popup.attributes('-topmost', True)
            self.current_popup.popup.focus_force()
        except Exception as e:
            Logger.error(f"Error ensuring test popup visibility: {e}")
        
        Logger.info("Showing test popup with JSON data")
    
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
    
    def show_history_event(self, event):
        """Show event details when double-clicking on history item"""
        selection = self.history_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        history_entries = self.history.get_history()
        
        if index < len(history_entries):
            entry = history_entries[index]
            event_data = entry['event']
            
            # Show event popup
            auto_close = False  # Don't auto-close for history view
            self.current_popup = EventPopup(self.root, event_data, auto_close, 0)
            
            # Ensure history popup is also properly displayed
            try:
                self.current_popup.popup.update_idletasks()
                self.current_popup.popup.lift()
                self.current_popup.popup.attributes('-topmost', True)
                self.current_popup.popup.focus_force()
            except Exception as e:
                Logger.error(f"Error ensuring history popup visibility: {e}")
    
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
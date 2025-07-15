"""
Image processing utilities for Uma Event Scanner
Contains ImageProcessor class with various preprocessing methods
"""

import cv2
import numpy as np
from typing import List, Tuple
from utils import Logger


class ImageProcessor:
    """Advanced image processing for OCR optimization"""
    
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
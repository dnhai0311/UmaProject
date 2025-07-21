"""
Simplified Image Processor for Uma Event Scanner.

This module provides only the minimal preprocessing required for OCR.  All the
previous GPU-specific and experimental methods have been removed to keep the
codebase maintainable and fast.
"""

from typing import Any

import cv2
import numpy as np


class ImageProcessor:
    """Basic preprocessing utilities for OCR."""
    
    @staticmethod
    def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
        """Convert *image* to a form that is easier for OCR engines.

        Steps performed:
        1. Convert BGR images to grayscale.
        2. Apply a bilateral filter to reduce noise while preserving edges.
        3. Run Otsu thresholding to obtain a high-contrast binary image.
        """
        if image is None:
            return image

        # 1) Optional upscale (helps EasyOCR on small UI text)
        h, w = image.shape[:2]
        if max(h, w) < 100:  # heuristic: consider tiny banner
            image = cv2.resize(image, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

        # 2) Grayscale conversion
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

        # 3) Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 4) Light de-noising while keeping edges crisp
        gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)

        # 5) Try binary + Otsu; if text seems lost (mostly white), invert
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        white_ratio = np.mean(thresh == 255)
        if white_ratio > 0.90:  # too white ⇒ invert mode may be better
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        return thresh


__all__ = ["ImageProcessor"] 
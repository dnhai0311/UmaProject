"""
Simplified OCR Engine for Uma Event Scanner.

This new implementation keeps the public API of the original `OCREngine`
class but dramatically reduces its complexity.  It relies only on
EasyOCR and the basic `ImageProcessor` created alongside this module.
"""

from typing import List

import numpy as np

from event_scanner.utils import Logger
from event_scanner.core.image_processor import ImageProcessor

try:
    import easyocr
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "EasyOCR is required to run the OCR engine. Install it with 'pip install easyocr'."
    ) from exc


class OCREngine:
    """A minimal wrapper around EasyOCR."""

    def __init__(self, language: str = "eng", gpu: bool = False):
        """Create an EasyOCR reader.

        Parameters
        ----------
        language: str, default "eng"
            The ISO code of the language used by EasyOCR.
        gpu: bool, default False
            Whether to use a CUDA-enabled GPU (if available).
        """

        # EasyOCR uses the ISO-639-1 code 'en' for English, while our settings
        # may pass in 'eng' (ISO-639-2) or the literal string 'english'.
        lang_code = language.lower()
        if lang_code in {"eng", "english"}:
            lang_code = "en"

        self.language = lang_code
        self.gpu = gpu  # expose flag
        self.reader = easyocr.Reader([lang_code], gpu=gpu, verbose=False)
        Logger.info(f"EasyOCR reader initialised (gpu={gpu}).")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def extract_text(self, image: np.ndarray) -> List[str]:
        """Extract text from *image* and return a list of unique strings."""
        if image is None:
            return []
            
        # 1) Attempt OCR directly on the colour image first
        raw_texts = self.reader.readtext(image, detail=0)

        # 2) If nothing or too few characters detected, fall back to pre-processed image
        if not raw_texts or len("".join(raw_texts)) < 3:
            processed = ImageProcessor.preprocess_for_ocr(image)
            raw_texts = self.reader.readtext(processed, detail=0)

        # Clean & deduplicate results
        texts: List[str] = []
        for txt in raw_texts:
            txt = txt.strip()
            if txt and txt not in texts:
                texts.append(txt)

        Logger.debug(f"OCR extracted {len(texts)} unique text fragment(s).")
        return texts


__all__ = ["OCREngine"] 
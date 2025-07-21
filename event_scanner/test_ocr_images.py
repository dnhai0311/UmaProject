"""Batch OCR test utility for Uma Event Scanner.

Usage:
    python -m event_scanner.test_ocr_images [--gpu] [--lang ENG]

The script will iterate over every image file in *event_scanner/images*,
running EasyOCR through the `OCREngine` and printing both the raw OCR
results and the best-matching event (if any).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from event_scanner.core import OCREngine, EventDatabase, ImageProcessor
from event_scanner.utils import Logger

IMAGES_DIR = Path(__file__).resolve().parent / "images"
SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def list_images(directory: Path) -> Sequence[Path]:
    if not directory.exists():
        Logger.error(f"Images directory not found: {directory}")
        return []
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch OCR tester for Uma Event Scanner")
    parser.add_argument("--gpu", action="store_true", help="Use GPU if available")
    parser.add_argument("--lang", default="eng", help="OCR language (default: eng)")
    args = parser.parse_args()

    ocr = OCREngine(language=args.lang, gpu=args.gpu)
    db = EventDatabase()

    images = list_images(IMAGES_DIR)
    if not images:
        Logger.warning("No images found to process.")
        sys.exit(0)

    Logger.info(f"Processing {len(images)} image(s) from {IMAGES_DIR}…")

    for idx, img_path in enumerate(images, 1):
        print("\n" + "=" * 80)
        print(f"[{idx}/{len(images)}] File: {img_path.name}")

        img = cv2.imread(str(img_path))
        if img is None:
            Logger.error(f"Failed to read image: {img_path}")
            continue

        # Run OCR
        texts = ocr.extract_text(img)
        if texts:
            print("OCR Texts:")
            for t in texts:
                print(f"  · {t}")
        else:
            print("(No text detected)")

        # Attempt to match event
        event = db.find_matching_event(texts)
        if event:
            print("\nMatched Event:")
            print(f"  Name   : {event['name']}")
            if event.get("type"):
                print(f"  Type   : {event['type']}")
            if event.get("choices"):
                print(f"  Choices: {len(event['choices'])} option(s)")
        else:
            print("\n(No matching event found)")

    print("\nDone.")


if __name__ == "__main__":
    main() 
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from event_scanner.utils.paths import get_data_dir
from typing import Optional, List, Dict
import threading

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QImage, QIcon
from PyQt6.QtCore import Qt, QSize, pyqtSignal

DATA_DIR = get_data_dir()
CHAR_FILE = DATA_DIR / "uma_char.json"
# Create a cache directory for character images
CACHE_DIR = Path(__file__).resolve().parents[2] / "cache" / "characters"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class CharacterSelectDialog(QDialog):
    """Dialog to pick a character with search and image thumbnails."""
    
    # Signal to update item with image when loaded
    image_loaded_signal = pyqtSignal(int, QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Character")
        self.resize(400, 550)
        self.selected_character: Optional[dict] = None
        self._image_cache: Dict[str, QPixmap] = {}

        layout = QVBoxLayout(self)

        # Add status label to show loading progress
        self.status_label = QLabel("Loading characters...")
        layout.addWidget(self.status_label)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        layout.addWidget(self.search_bar)

        self.list_widget = QListWidget()
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.setIconSize(QSize(64, 80))
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        clear_btn = QPushButton("Clear Filter")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch(1)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(self.accept)
        clear_btn.clicked.connect(self._do_clear)
        cancel_btn.clicked.connect(self.reject)

        self.search_bar.textChanged.connect(self._on_search)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.accept())

        # Connect the signal to update UI when images are loaded
        self.image_loaded_signal.connect(self._update_item_icon)
        
        self._load_data()
        
        # Start a thread to populate the list to keep UI responsive
        threading.Thread(target=self._populate_list_async, daemon=True).start()

    # ---------------- internal ----------------
    def _load_data(self):
        try:
            with open(CHAR_FILE, "r", encoding="utf-8") as fh:
                self._characters: List[dict] = json.load(fh)
        except Exception:
            self._characters = []

    def _populate_list_async(self, filter_text: str = ""):
        """Populate the list in a background thread"""
        self.list_widget.clear()
        filter_text = filter_text.lower()
        
        # First pass: Add all items without images to show list quickly
        for i, char in enumerate(self._characters):
            if filter_text and filter_text not in char["name"].lower():
                continue
            
            item = QListWidgetItem(char["name"])
            item.setData(Qt.ItemDataRole.UserRole, char)
            self.list_widget.addItem(item)
        
        # Update status
        self.status_label.setText(f"Loading images for {self.list_widget.count()} characters...")
        
        # Second pass: Load images in background
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item:
                continue
            
            char = item.data(Qt.ItemDataRole.UserRole)
            if not char or not char.get("imageUrl"):
                continue
            
            # Start loading the image in background
            url = char.get("imageUrl", "")
            threading.Thread(target=self._load_and_update_image, args=(url, i), daemon=True).start()
        
        # Update status when complete
        self.status_label.setText("All characters loaded")

    def _load_and_update_image(self, url: str, item_index: int):
        """Load an image and emit signal to update UI when done"""
        pixmap = self._load_pixmap(url)
        if pixmap:
            self.image_loaded_signal.emit(item_index, pixmap)

    def _update_item_icon(self, index: int, pixmap: QPixmap):
        """Update list item with loaded image (called in UI thread)"""
        item = self.list_widget.item(index)
        if item:
            item.setIcon(QIcon(pixmap))

    def _populate_list(self, filter_text: str = ""):
        """Synchronous version for search filtering (uses cache)"""
        self.list_widget.clear()
        filter_text = filter_text.lower()
        for char in self._characters:
            if filter_text and filter_text not in char["name"].lower():
                continue
            item = QListWidgetItem(char["name"])
            
            # Use cached image if available
            url = char.get("imageUrl", "")
            if url in self._image_cache:
                item.setIcon(QIcon(self._image_cache[url]))
            
            item.setData(Qt.ItemDataRole.UserRole, char)
            self.list_widget.addItem(item)

    def _on_search(self, txt: str):
        """Handle search text change"""
        self._populate_list(txt)
        self.status_label.setText(f"Found {self.list_widget.count()} characters")

    def _load_pixmap(self, url: str) -> Optional[QPixmap]:
        """Load pixmap from URL with caching"""
        if not url:
            return None
        
        # Check memory cache first
        if url in self._image_cache:
            return self._image_cache[url]
        
        # Create a cache filename from URL
        cache_filename = url.split('/')[-1]
        cache_path = CACHE_DIR / cache_filename
        
        try:
            # Check disk cache
            if cache_path.exists():
                pixmap = QPixmap(str(cache_path))
                if not pixmap.isNull():
                    self._image_cache[url] = pixmap
                    return pixmap
            
            # Download if not cached
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = resp.read()
            
            # Save to disk cache
            img = QImage()
            if img.loadFromData(data):
                # Scale the image
                pixmap = QPixmap.fromImage(img).scaled(
                    64, 80, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Save to disk cache
                pixmap.save(str(cache_path))
                
                # Add to memory cache
                self._image_cache[url] = pixmap
                return pixmap
                
        except Exception:
            # Return None on failure but don't crash
            pass
        
        return None

    def _do_clear(self):
        """Clear selection and accept dialog"""
        self.selected_character = {"clear": True}
        super().accept()

    def accept(self):
        # Override accept to set selected_character when ok pressed
        if not self.selected_character:
            item = self.list_widget.currentItem()
            if item:
                self.selected_character = item.data(Qt.ItemDataRole.UserRole)
        super().accept()

    @staticmethod
    def get_character(parent=None) -> Optional[dict]:
        dlg = CharacterSelectDialog(parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.selected_character
        return None
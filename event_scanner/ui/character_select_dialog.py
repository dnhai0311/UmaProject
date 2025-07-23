from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QSize

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CHAR_FILE = DATA_DIR / "uma_char.json"


class CharacterSelectDialog(QDialog):
    """Dialog to pick a character with search and image thumbnails."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Character")
        self.resize(400, 550)
        self.selected_character: Optional[dict] = None

        layout = QVBoxLayout(self)

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

        self._load_data()
        self._populate_list()

    # ---------------- internal ----------------
    def _load_data(self):
        try:
            with open(CHAR_FILE, "r", encoding="utf-8") as fh:
                self._characters: List[dict] = json.load(fh)
        except Exception:
            self._characters = []

    def _populate_list(self, filter_text: str = ""):
        self.list_widget.clear()
        filter_text = filter_text.lower()
        for char in self._characters:
            if filter_text and filter_text not in char["name"].lower():
                continue
            item = QListWidgetItem(char["name"])
            pix = self._load_pixmap(char.get("imageUrl"))
            if pix is not None:
                item.setIcon(pix)
            item.setData(Qt.ItemDataRole.UserRole, char)
            self.list_widget.addItem(item)

    def _on_search(self, txt: str):
        self._populate_list(txt)

    def _load_pixmap(self, url: str) -> Optional[QPixmap]:
        if not url:
            return None
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()
            img = QImage()
            if img.loadFromData(data):
                return QPixmap.fromImage(img).scaled(64, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception:
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
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont


class UpdateDialog(QDialog):
    append_signal = pyqtSignal(str)
    enable_close_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating Data – Scraper Logs")
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_view)

        self.close_btn = QPushButton("Close")
        self.close_btn.setEnabled(False)
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)

        self.append_signal.connect(self._append)
        self.enable_close_signal.connect(self._enable_close)

    def _append(self, text: str):
        self.log_view.append(text)
        self.log_view.ensureCursorVisible()

    def _enable_close(self):
        self.close_btn.setEnabled(True) 
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class EventDisplay(QWidget):
    """Simple widget to show current event information inside main window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(4)

        title = QLabel("📌 Current Event")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label = title
        layout.addWidget(title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._container = QFrame()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    def show_event(self, event: dict|None):
        """Render event content; pass None to clear."""
        # clear
        while self._container_layout.count():
            child = self._container_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        if not event:
            lbl = QLabel("No event detected.")
            self._container_layout.addWidget(lbl)
            return
        name_label = QLabel(event.get('name', 'Unknown'))
        name_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._container_layout.addWidget(name_label)

        # choices
        for i, choice in enumerate(event.get('choices', []), 1):
            choice_lbl = QLabel(f"{i}. {choice.get('choice','')}")
            choice_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            self._container_layout.addWidget(choice_lbl)
            for seg in choice.get('effects', []):
                eff_lbl = QLabel(f"- {seg.get('raw','')}")
                self._container_layout.addWidget(eff_lbl) 
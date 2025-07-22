"""
EventPopup component for Uma Event Scanner using PyQt6
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer, QSize, QEvent, QPoint
from PyQt6.QtGui import QFont, QColor, QShowEvent
import sys
import os
import time
from typing import Dict, Optional, Union, Any
from event_scanner.utils import Logger


class EventPopup(QDialog):
    """Popup window for displaying event information using PyQt6"""
    
    def __init__(self, parent=None, event: Optional[Dict[str, Any]] = None, auto_close: bool = True, timeout: int = 8):
        # Use no parent for better window management
        super().__init__(None)
        self.event_data: Dict[str, Any] = event if event is not None else {}
        self.close_requested = False
        self.parent_window = parent  # Store parent reference
        
        # Use strong window flags to ensure popup stays on top
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Setup UI components
        self.setupUi()
        
        # Set window properties after UI setup
        self.setWindowTitle('🎯 Event Detected!')
        self.positionBelowMainWindow()
        
        # Ensure initial visibility
        self.ensure_visible()
        
        # Set auto-close timer if needed
        if auto_close and timeout > 0:
            QTimer.singleShot(timeout * 1000, self.close_popup)
        
        # Set a visibility timer
        QTimer.singleShot(100, self.ensure_visible)
    
    def ensure_visible(self) -> None:
        """Ensure the popup is visible and has focus"""
        # Skip if close has been requested
        if self.close_requested:
            return
            
        # Force window to be visible and active
        self.show()
        self.activateWindow()
        self.raise_()
        self.setFocus()
    
    def positionBelowMainWindow(self) -> None:
        """Position the popup at top-right and stretch height."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        screen_geometry = screen.availableGeometry()
        
        # Desired size
        desired_width = 800  # wider for readability (was 600)
        desired_height = screen_geometry.height() - 40  # leave small margin

        # Resize window
        self.resize(desired_width, desired_height)

        # Position: top-right with 20px margin
        x_pos = screen_geometry.width() - desired_width - 20
        y_pos = 20

        self.move(x_pos, y_pos)
        Logger.info(f"Positioned popup at {x_pos},{y_pos} (top-right)")
    
    def setupUi(self) -> None:
        """Setup the UI components"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header frame with event name
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #e74c3c; padding: 10px;")
        header_frame.setMinimumHeight(60)
        
        header_layout = QVBoxLayout(header_frame)
        
        event_name_label = QLabel(self.event_data.get('name', 'Unknown Event'))
        event_name_label.setStyleSheet("color: white; font-weight: bold;")
        event_name_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        event_name_label.setWordWrap(True)
        event_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(event_name_label)
        
        # Add event type if available
        event_type = self.event_data.get('type', '')
        if event_type:
            type_label = QLabel(f"📋 Type: {event_type}")
            type_label.setStyleSheet("color: white; font-size: 11px;")
            type_label.setFont(QFont("Arial", 11))
            type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(type_label)
        
        main_layout.addWidget(header_frame)
        
        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #2c3e50;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        choices = self.event_data.get('choices', [])
        
        if choices and len(choices) > 0:
            # Event has choices
            choices_label = QLabel("📋 Available Choices:")
            choices_label.setStyleSheet("color: #ecf0f1; font-weight: bold;")
            choices_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            content_layout.addWidget(choices_label)
            
            # Add choices
            bg_colors = ['#3498db', '#e67e22', '#9b59b6', '#f1c40f', 
                         '#1abc9c', '#e74c3c', '#2ecc71', '#f39c12']
            
            for i, choice in enumerate(choices):
                bg_color = bg_colors[i % len(bg_colors)]
                
                choice_frame = QFrame()
                choice_frame.setStyleSheet(f"background-color: {bg_color}; "
                                        f"border-radius: 5px; padding: 15px;")
                
                choice_layout = QVBoxLayout(choice_frame)
                choice_layout.setSpacing(0)
                
                if isinstance(choice, dict):
                    text = choice.get('choice', str(choice))
                    effect_data = choice.get('effects', '')

                    # Choice label
                    choice_label = QLabel(f"{i+1}. {text}")
                    choice_label.setStyleSheet("color: white; font-weight: bold;")
                    choice_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
                    choice_label.setWordWrap(True)
                    choice_layout.addWidget(choice_label)

                    # Build effect string
                    effect_str = ""
                    if isinstance(effect_data, list):
                        lines = []
                        for seg in effect_data:
                            if not isinstance(seg, dict):
                                lines.append(str(seg))
                                continue
                            kind = seg.get('kind')
                            if kind in ('divider_or', 'random_header'):
                                lines.append(seg.get('raw', ''))
                            elif kind == 'stat':
                                lines.append(f"{seg.get('stat', '')} {seg.get('amount', ''):+}")
                            elif kind in ('skill', 'status'):
                                line = seg.get('raw', '')
                                if 'hint' in seg:
                                    line += f" (hint {seg['hint']:+})"
                                if seg.get('detail') and seg['detail'].get('effect'):
                                    line += f" — {seg['detail']['effect']}"
                                lines.append(line)
                            else:
                                lines.append(seg.get('raw', ''))
                        effect_str = "\n".join(lines)
                    else:
                        effect_str = str(effect_data) if effect_data else (choice.get('effect', '') or '')

                    if effect_str:
                        effect_label = QLabel(f"💡 Effect: {effect_str}")
                        effect_label.setStyleSheet("color: white;")
                        effect_label.setFont(QFont("Arial", 13))
                        effect_label.setWordWrap(True)
                        choice_layout.addWidget(effect_label)
                else:
                    # Simple string choice - INCREASED FONT SIZE
                    choice_text = QLabel(f"{i+1}. {choice}")
                    choice_text.setStyleSheet("color: white; font-weight: bold;")
                    choice_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # Increased from 11 to 14
                    choice_text.setWordWrap(True)
                    choice_layout.addWidget(choice_text)
                
                content_layout.addWidget(choice_frame)
        else:
            # No choices - show "No Choice" message
            no_choice_label = QLabel("🚫 No Choice Available")
            no_choice_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            no_choice_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # Increased from 12 to 14
            content_layout.addWidget(no_choice_label)
            
            # Check if there's an effect for no-choice events
            effect = self.event_data.get('effect', '') or self.event_data.get('effects', '')
            if effect:
                effect_frame = QFrame()
                effect_frame.setStyleSheet("background-color: #34495e; border-radius: 5px; padding: 15px;")
                
                effect_layout = QVBoxLayout(effect_frame)
                
                # For no-choice effect list
                segs_nc = self.event_data.get('effects', [])
                html_lines_nc = []
                for seg in segs_nc:
                    if seg.get('kind') in ('divider_or','random_header'):
                        html_lines_nc.append(f"<b>{seg.get('raw','')}</b>")
                    else:
                        html_lines_nc.append(seg.get('raw',''))
                effect_label = QLabel()
                effect_label.setTextFormat(Qt.TextFormat.RichText)
                effect_label.setText('<br>'.join(html_lines_nc))
                effect_label.setStyleSheet("color: white;")
                effect_label.setFont(QFont("Arial", 13))  # Increased from 10 to 13
                effect_label.setWordWrap(True)
                effect_layout.addWidget(effect_label)
                
                content_layout.addWidget(effect_frame)
        
        # Add spacer at the bottom
        content_layout.addStretch()
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Close button - MADE LARGER AND MORE PROMINENT
        close_btn = QPushButton("✖ CLOSE")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                font-size: 16px;
                padding: 12px 30px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a33025;
            }
        """)
        
        # Directly connect to close method
        close_btn.clicked.connect(self.close_popup)
        close_btn.setMinimumWidth(180)
        close_btn.setMinimumHeight(50)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
    
    def close_popup(self):
        """Custom close method to ensure proper cleanup"""
        if self.close_requested:
            return
            
        Logger.debug("Popup close requested")
        self.close_requested = True
        
        # Notify parent window immediately so scan loop skips redisplay
        if self.parent_window and hasattr(self.parent_window, 'dismissed_event_name'):
            try:
                self.parent_window.dismissed_event_name = self.event_data.get('name')
            except Exception:
                pass

        # Use accept() to reliably finish the dialog and emit finished signal
        self.accept()
        
        # If we have a parent, restore focus after a short delay
        if self.parent_window:
            QTimer.singleShot(100, self.restore_parent_focus)
    
    def closeEvent(self, event):
        """Override close event to ensure proper closing"""
        # Mark as closed first to prevent any callbacks from showing the window again
        self.close_requested = True
        Logger.debug("Popup closing")
        
        # Always accept the close event
        event.accept()
        
        # Restore parent focus
        if self.parent_window:
            try:
                QTimer.singleShot(100, lambda: self.restore_parent_focus())
            except:
                pass
    
    def restore_parent_focus(self):
        """Restore focus to parent window"""
        if self.parent_window:
            try:
                self.parent_window.activateWindow() 
                self.parent_window.raise_()
                QApplication.processEvents()
            except:
                pass
    
    def keyPressEvent(self, event):
        """Add keyboard shortcut for closing the popup"""
        # Close on Escape key press
        if event.key() == Qt.Key.Key_Escape:
            self.close_popup()
        # Close on Enter key press
        elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.close_popup()
        else:
            super().keyPressEvent(event)
    
    def showEvent(self, event: QShowEvent) -> None:
        """Override showEvent to ensure window is visible and on top"""
        super().showEvent(event)
        # Force window to be visible and on top
        if not self.close_requested:
            # Delay to ensure proper stacking
            QTimer.singleShot(50, self.ensure_visible)
    
    def sizeHint(self) -> QSize:
        """Suggested window size"""
        choices = self.event_data.get('choices', [])
        
        # Base size, adjust based on number of choices
        if choices:
            height = 300 + (len(choices) * 120)  # Increased from 100 to 120 for larger text
            return QSize(800, min(height, 700))
        else:
            return QSize(800, 400)


# For testing purposes
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    test_event = {
        'name': 'Test Event with Multiple Choices - This is a very long event name to test wrapping',
        'choices': [
            {
                'choice': 'First Choice - This is a very long choice text to test wrapping and display properly',
                'effects': [
                    {'kind': 'text', 'raw': 'Speed +10'},
                    {'kind': 'text', 'raw': 'Stamina +5'},
                    {'kind': 'text', 'raw': 'Power +3'},
                    {'kind': 'text', 'raw': 'Guts +2'},
                    {'kind': 'text', 'raw': 'Wisdom +1'}
                ]
            },
            {
                'choice': 'Second Choice - Another long choice with different effects',
                'effects': [
                    {'kind': 'text', 'raw': 'Power +15'},
                    {'kind': 'text', 'raw': 'Speed +5'},
                    {'kind': 'text', 'raw': 'Stamina +10'}
                ]
            },
            {
                'choice': 'Third Choice - Yet another choice option',
                'effects': [
                    {'kind': 'text', 'raw': 'Guts +8'},
                    {'kind': 'text', 'raw': 'Wisdom +3'}
                ]
            }
        ]
    }
    
    dialog = EventPopup(event=test_event, auto_close=False)
    dialog.show()
    
    sys.exit(app.exec()) 
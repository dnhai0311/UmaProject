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
        """Position the popup below the main window"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        # Get screen dimensions
        screen_geometry = screen.availableGeometry()
        
        # Find main window position
        main_window_pos = QPoint(0, 0)
        main_window_size = QSize(800, 600)  # Default size
        
        # If we have a parent window, use its position
        if self.parent_window:
            try:
                main_window_pos = self.parent_window.pos()
                main_window_size = self.parent_window.size()
            except:
                Logger.error("Could not get parent window position")
        
        # Adjust our size based on content
        self_size = self.sizeHint()
        self.resize(main_window_size.width(), self_size.height())
        
        # Position at the bottom of the main window or screen
        x_pos = main_window_pos.x()
        y_pos = main_window_pos.y() + main_window_size.height() - 20  # Overlap slightly for better visibility
        
        # Check if it would go off screen bottom
        if y_pos + self_size.height() > screen_geometry.height():
            # If it would go off bottom, position at screen bottom
            y_pos = screen_geometry.height() - self_size.height() - 20  # 20px margin
        
        # Ensure x position is on screen
        if x_pos < 0:
            x_pos = 0
        if x_pos + self_size.width() > screen_geometry.width():
            x_pos = screen_geometry.width() - self_size.width()
            
        # Set position
        self.move(x_pos, y_pos)
        Logger.info(f"Positioned popup at {x_pos},{y_pos} (below main window)")
    
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
                choice_layout.setSpacing(10)
                
                if isinstance(choice, dict):
                    text = choice.get('choice', str(choice))
                    effect = choice.get('effect', '') or choice.get('effects', '')
                    
                    # Choice text - INCREASED FONT SIZE
                    choice_text = QLabel(f"{i+1}. {text}")
                    choice_text.setStyleSheet("color: white; font-weight: bold;")
                    choice_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # Increased from 11 to 14
                    choice_text.setWordWrap(True)
                    choice_layout.addWidget(choice_text)
                    
                    # Effect text (if exists) - INCREASED FONT SIZE
                    if effect:
                        effect_text = QLabel(f"💡 Effect: {effect}")
                        effect_text.setStyleSheet("color: white;")
                        effect_text.setFont(QFont("Arial", 13))  # Increased from 10 to 13
                        effect_text.setWordWrap(True)
                        choice_layout.addWidget(effect_text)
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
                
                effect_label = QLabel(f"💡 Effect: {effect}")
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
        
        # Hide first for smoother transition
        self.hide()
        
        # Close the window
        self.close()
        
        # If we have a parent, make sure it gets proper focus
        if self.parent_window:
            try:
                self.parent_window.activateWindow()
                self.parent_window.raise_()
                QApplication.processEvents()
            except:
                pass
    
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
                'effect': 'Speed +10, Stamina +5, Power +3, Guts +2, Wisdom +1'
            },
            {
                'choice': 'Second Choice - Another long choice with different effects',
                'effect': 'Power +15, Speed +5, Stamina +10'
            },
            {
                'choice': 'Third Choice - Yet another choice option',
                'effect': 'Guts +8, Wisdom +3'
            }
        ]
    }
    
    dialog = EventPopup(event=test_event, auto_close=False)
    dialog.show()
    
    sys.exit(app.exec()) 
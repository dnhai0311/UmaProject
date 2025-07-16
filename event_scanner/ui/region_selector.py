"""
RegionSelector component for Uma Event Scanner using PyQt6
"""

import sys
import pyautogui
from typing import Callable, Optional, Tuple
import time

from PyQt6.QtWidgets import (
    QApplication, QDialog, QLabel, QVBoxLayout, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QRect, QTimer, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QGuiApplication

from event_scanner.utils import Logger


class SimpleRegionSelector(QDialog):
    """Simple fullscreen region selector without screenshot background"""
    
    def __init__(self, callback):
        super().__init__(None)
        self.callback = callback
        self.start_point = None
        self.current_point = None
        self.is_selecting = False
        
        # Set window properties
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Get screen dimensions and set window size
        screen = QGuiApplication.primaryScreen()
        if screen:
            self.screen_rect = screen.geometry()
            self.setGeometry(self.screen_rect)
        else:
            self.screen_rect = QRect(0, 0, 1920, 1080)
            self.setGeometry(0, 0, 1920, 1080)
        
        # Instructions label
        self.instructions = QLabel("Click and drag to select a region. Press ESC to cancel.", self)
        self.instructions.setStyleSheet("""
            background-color: rgba(0, 0, 0, 200);
            color: white;
            padding: 20px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
        """)
        self.instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Position the instructions at the top center
        layout = QVBoxLayout(self)
        layout.addWidget(self.instructions, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.setContentsMargins(0, 30, 0, 0)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Show fullscreen
        self.showFullScreen()
    
    def paintEvent(self, event):
        """Paint the overlay and selection rectangle"""
        painter = QPainter(self)
        
        # Semi-transparent dark overlay over the entire screen
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        
        # Draw selection rectangle if we're selecting
        if self.is_selecting and self.start_point and self.current_point:
            # Calculate rectangle coordinates
            x = min(self.start_point.x(), self.current_point.x())
            y = min(self.start_point.y(), self.current_point.y())
            width = abs(self.start_point.x() - self.current_point.x())
            height = abs(self.start_point.y() - self.current_point.y())
            
            # Clear the selection area (make it more transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, width, height, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Draw bright red border around selection
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.drawRect(x, y, width, height)
            
            # Show selection dimensions
            size_text = f"{width} x {height} pixels"
            painter.fillRect(x, y - 25, 150, 20, QColor(0, 0, 0, 200))
            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(x + 5, y - 10, size_text)
    
    def mousePressEvent(self, event):
        """Handle mouse press to start selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.current_point = event.pos()
            self.is_selecting = True
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement to update selection"""
        if self.is_selecting:
            self.current_point = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to finalize selection"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.current_point = event.pos()
            self.is_selecting = False
            self.update()
            self.process_selection()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
    
    def process_selection(self):
        """Process the selected region"""
        if not self.start_point or not self.current_point:
            self.reject()
            return
        
        # Calculate screen coordinates for the screenshot
        x = min(self.start_point.x(), self.current_point.x())
        y = min(self.start_point.y(), self.current_point.y())
        width = abs(self.start_point.x() - self.current_point.x())
        height = abs(self.start_point.y() - self.current_point.y())
        
        # Validate selection size
        if width < 50 or height < 20:
            QMessageBox.warning(
                None, "Region Too Small", 
                f"Selected region is too small: {width}x{height}\n\n"
                f"Minimum size: 50x20 pixels\n\n"
                f"Please select a larger area."
            )
            return
        
        # Return the selected region with screen coordinates
        final_region = (x, y, width, height)
        Logger.info(f"Final region coordinates: {final_region}")
        
        if self.callback:
            self.callback(final_region)
        self.accept()


class RegionSelector:
    """Manager for screen region selection"""
    
    def __init__(self, parent=None, callback: Optional[Callable] = None):
        self.parent = parent
        self.callback = callback
        self.region = None
    
    def select_region(self):
        """Start the region selection process"""
        if self.parent:
            # Hide the parent window during selection
            self.parent.hide()
            QApplication.processEvents()
        
        try:
            # Create and show the dialog
            dialog = SimpleRegionSelector(self._on_region_selected)
            result = dialog.exec()
            
            # Ensure the parent window is properly shown
            if self.parent:
                self.parent.show()
                self.parent.activateWindow()
                self.parent.raise_()
                QApplication.processEvents()
            
        except Exception as e:
            Logger.error(f"Failed to create region selector: {e}")
            QMessageBox.critical(None, "Error", f"Failed to create region selector: {e}")
            if self.parent:
                self.parent.show()
                self.parent.activateWindow()
                self.parent.raise_()
    
    def _on_region_selected(self, region):
        """Handle region selection"""
        self.region = region
        
        if self.parent:
            # Show parent window again
            self.parent.show()
            self.parent.activateWindow()
            self.parent.raise_()
        
        # Call the callback function
        if self.callback:
            self.callback(region)


# For testing purposes
if __name__ == '__main__':
    def on_region_selected(region):
        print(f"Selected region: {region}")
    
    app = QApplication(sys.argv)
    selector = RegionSelector(callback=on_region_selected)
    selector.select_region()
    
    # Keep the application running after selection
    print("Application still running. Press Ctrl+C to exit.")
    sys.exit(app.exec()) 
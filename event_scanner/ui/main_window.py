"""
Main Window for Uma Event Scanner using PyQt6
"""

import sys
import threading
import time
import cv2
import numpy as np
import pyautogui
from datetime import datetime
from typing import Tuple, Optional, Dict, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTabWidget, QFrame, QTextEdit, QListWidget,
    QMessageBox, QDoubleSpinBox, QCheckBox, QGroupBox, QScrollArea,
    QSplitter, QComboBox, QFileDialog, QApplication, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage

from event_scanner.core import ImageProcessor, EventDatabase, OCREngine
from event_scanner.services import SettingsManager, HistoryManager
from event_scanner.ui import EventPopup, RegionSelector, StatRecommendationsTab
# from event_scanner.ui.ai_learning_dialog import AILearningDialog  # Removed AI feature
from event_scanner.ui.training_events_tab import TrainingEventsTab
from event_scanner.utils import Logger

# Import GPU configuration if available
try:
    from event_scanner.config import GPUConfig, IMAGE_PROCESSING_CONFIG
    GPU_CONFIG_AVAILABLE = True
except ImportError:
    GPU_CONFIG_AVAILABLE = False
    Logger.warning("GPU config not available - using default settings")


class MainWindow(QMainWindow):
    """Main window for Uma Event Scanner"""
    
    # Custom signals for thread-safe operations
    update_results_signal = pyqtSignal(list)
    # Accepts either a dict (event data) or None to indicate no event
    event_detected_signal = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.settings = SettingsManager()
        self.history = HistoryManager()
        self.event_db = EventDatabase()
        # Apply user-defined threshold at startup
        from event_scanner.core.event_database import EventDatabase as _EDB
        _EDB.THRESHOLD_SCORE = int(self.settings.get('match_threshold', 85) or 85)
        # Track the last event name currently displayed to avoid reopening same popup
        self.last_event_name: Optional[str] = None
        # Track an event name that the user manually dismissed so we don't immediately reopen it
        self.dismissed_event_name: Optional[str] = None
        self.ocr_engine = None
        self.image_processor = ImageProcessor()
        
        from collections import Counter
        self.source_freq = Counter()

        self.scanning = False
        self.scan_region = self.settings.get('last_region')
        self.current_popup = None
        self.scan_thread = None
        
        # Set window flags to ensure main window stays active and on top
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        self.init_ocr()
        self.setup_ui()
        self.connect_signals()
        
        # Setup window properties
        self.setWindowTitle("Uma Event Scanner")
        self.resize(800, 700)
        self.setMinimumSize(700, 600)
        self.position_window()
    
    def init_ocr(self):
        """Initialize OCR engine"""
        try:
            language = self.settings.get('ocr_language', 'eng') or 'eng'
            use_gpu = bool(self.settings.get('use_gpu', False))
            self.ocr_engine = OCREngine(language, gpu=use_gpu)
            Logger.info("OCR engine initialized")
        except Exception as e:
            Logger.error(f"Failed to initialize OCR: {e}")
            QMessageBox.critical(self, "Error", "Failed to initialize OCR engine")
            sys.exit(1)
    
    def setup_ui(self):
        """Set up the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title bar
        title_frame = QFrame()
        title_frame.setStyleSheet("background-color: #2c3e50; color: white;")
        title_frame.setMinimumHeight(60)
        
        title_layout = QVBoxLayout(title_frame)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title_label = QLabel("🎯 Uma Event Scanner")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title_label)
        
        main_layout.addWidget(title_frame)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        self.setup_scanner_tab()
        self.setup_training_events_tab()
        self.setup_stat_recommendations_tab()
        self.setup_history_tab()
        self.setup_settings_tab()
        # self.setup_ai_tab()  # AI tab disabled
        
        # Status bar
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #34495e; color: white;")
        status_frame.setFixedHeight(30)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 0, 15, 0)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 9))
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(status_frame)
    
    def setup_training_events_tab(self):
        """Set up the training events tab"""
        self.training_events_tab = TrainingEventsTab()
        self.tab_widget.addTab(self.training_events_tab, "🎴 Training Events")
    
    def setup_stat_recommendations_tab(self):
        """Set up the stat recommendations tab"""
        self.stat_recommendations_tab = StatRecommendationsTab()
        self.tab_widget.addTab(self.stat_recommendations_tab, "📊 Stat Recommendations")
    
    def setup_scanner_tab(self):
        """Set up the scanner tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(10)
        
        # Region selection group
        region_group = QGroupBox("📐 Scan Region")
        region_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        region_layout = QHBoxLayout(region_group)
        region_layout.setContentsMargins(15, 15, 15, 15)
        
        self.region_label = QLabel(self.get_region_text())
        region_layout.addWidget(self.region_label, 1)
        
        select_btn = QPushButton("🎯 Select Region")
        select_btn.clicked.connect(self.select_region)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; 
                color: white; 
                font-weight: bold; 
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
                border: 2px solid #0d4e77;
            }
        """)
        region_layout.addWidget(select_btn)
        
        preview_btn = QPushButton("👁️ Preview")
        preview_btn.clicked.connect(self.preview_region)
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22; 
                color: white; 
                font-weight: bold; 
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #a04000;
                border: 2px solid #783000;
            }
        """)
        region_layout.addWidget(preview_btn)

        # Button to clear the last/dismissed event so pop-up can re-appear
        clear_event_btn = QPushButton("🧹 Clear Event")
        clear_event_btn.clicked.connect(self.clear_last_event)
        clear_event_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d; 
                color: white; 
                font-weight: bold; 
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #707b7c;
            }
            QPushButton:pressed {
                background-color: #5d6d7e;
                border: 2px solid #4d565e;
            }
        """)
        region_layout.addWidget(clear_event_btn)
        
        tab_layout.addWidget(region_group)
        
        # Control group
        self.control_group = QGroupBox("🎮 Controls")
        self.control_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        control_layout = QHBoxLayout(self.control_group)
        control_layout.setContentsMargins(15, 15, 15, 15)
        
        self.start_btn = QPushButton("▶️ Start Scanning")
        self.start_btn.clicked.connect(self.start_scanning)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; 
                color: white; 
                font-weight: bold; 
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed, QPushButton:disabled {
                background-color: #1e8449;
                border: 2px solid #145a32;
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 180);
            }
        """)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_scanning)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; 
                color: white; 
                font-weight: bold; 
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed, QPushButton:disabled {
                background-color: #a93226;
                border: 2px solid #7b241c;
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 180);
            }
        """)
        control_layout.addWidget(self.stop_btn)
        
        # --- đã xoá nút Test JSON và hàm test_with_json_data để loại bỏ code test ---
        
        tab_layout.addWidget(self.control_group)
        
        # Results group
        results_group = QGroupBox("📊 Results")
        results_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(10, 15, 10, 15)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        results_layout.addWidget(self.result_text)
        
        tab_layout.addWidget(results_group)
        tab_layout.setStretch(2, 1)  # Make results group stretch
        
        self.tab_widget.addTab(tab, "Scanner")
    
    def setup_history_tab(self):
        """Set up the history tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(10)
        
        # Controls group
        controls_group = QGroupBox("📋 History Controls")
        controls_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        controls_layout = QHBoxLayout(controls_group)
        controls_layout.setContentsMargins(15, 15, 15, 15)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_history)
        refresh_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; padding: 5px 15px;")
        controls_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_history)
        clear_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; padding: 5px 15px;")
        controls_layout.addWidget(clear_btn)
        
        controls_layout.addStretch(1)
        
        tab_layout.addWidget(controls_group)
        
        # History list group
        history_group = QGroupBox("📜 Event History")
        history_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(10, 15, 10, 15)
        
        self.history_list = QListWidget()
        self.history_list.setFont(QFont("Arial", 10))
        self.history_list.itemDoubleClicked.connect(self.show_history_event)
        history_layout.addWidget(self.history_list)
        
        tab_layout.addWidget(history_group)
        tab_layout.setStretch(1, 1)  # Make history list stretch
        
        self.tab_widget.addTab(tab, "History")
        
        # Initialize history display
        self.refresh_history()
    
    def setup_settings_tab(self):
        """Set up the settings tab"""
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setSpacing(15)
        
        # Scanner settings group
        scanner_group = QGroupBox("⚙️ Scanner Settings")
        scanner_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        scanner_layout = QVBoxLayout(scanner_group)
        scanner_layout.setContentsMargins(15, 15, 15, 15)
        scanner_layout.setSpacing(10)
        
        # Scan interval setting
        interval_layout = QHBoxLayout()
        interval_label = QLabel("⏱️ Scan Interval (seconds):")
        interval_layout.addWidget(interval_label)
        
        self.interval_spinbox = QDoubleSpinBox()
        self.interval_spinbox.setMinimum(0.5)
        self.interval_spinbox.setMaximum(10.0)
        self.interval_spinbox.setSingleStep(0.1)
        interval_value = self.settings.get('scan_interval', 2.0)
        self.interval_spinbox.setValue(float(interval_value) if interval_value is not None else 2.0)
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch(1)
        
        scanner_layout.addLayout(interval_layout)

        # Match threshold setting
        threshold_layout = QHBoxLayout()
        threshold_label = QLabel("🎯 Match Threshold (%):")
        threshold_layout.addWidget(threshold_label)

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(50, 100)
        threshold_value = self.settings.get('match_threshold', 85)
        self.threshold_spinbox.setValue(int(threshold_value) if threshold_value is not None else 85)
        threshold_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addStretch(1)

        scanner_layout.addLayout(threshold_layout)

        # Use GPU checkbox
        gpu_layout = QHBoxLayout()
        self.gpu_checkbox = QCheckBox("⚡ Use GPU (CUDA) if available")
        self.gpu_checkbox.setChecked(bool(self.settings.get('use_gpu', False)))
        gpu_layout.addWidget(self.gpu_checkbox)
        gpu_layout.addStretch(1)

        scanner_layout.addLayout(gpu_layout)
        
        tab_layout.addWidget(scanner_group)
        
        # Popup settings group
        popup_group = QGroupBox("🔔 Popup Settings")
        popup_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        popup_layout = QVBoxLayout(popup_group)
        popup_layout.setContentsMargins(15, 15, 15, 15)
        popup_layout.setSpacing(10)
        
        # Auto-close setting
        auto_close_layout = QHBoxLayout()
        auto_close_value = self.settings.get('auto_close_popup', True)
        self.auto_close_checkbox = QCheckBox("🔄 Auto-close popups")
        self.auto_close_checkbox.setChecked(bool(auto_close_value) if auto_close_value is not None else True)
        auto_close_layout.addWidget(self.auto_close_checkbox)
        auto_close_layout.addStretch(1)
        
        popup_layout.addLayout(auto_close_layout)

        # Popup timeout setting
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("⏲️ Popup Timeout (s):")
        timeout_layout.addWidget(timeout_label)

        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 30)
        self.timeout_spinbox.setValue(int(self.settings.get('popup_timeout', 8)))
        timeout_layout.addWidget(self.timeout_spinbox)
        timeout_layout.addStretch(1)

        popup_layout.addLayout(timeout_layout)

        # Add popup group to main settings tab layout (was accidentally removed)
        tab_layout.addWidget(popup_group)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setStyleSheet("""
            background-color: #27ae60;
            color: white;
            font-weight: bold;
            padding: 10px 30px;
            border: none;
            border-radius: 4px;
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch(1)
        
        tab_layout.addLayout(btn_layout)
        tab_layout.addStretch(1)
        
        self.tab_widget.addTab(tab, "Settings")
    
    def connect_signals(self):
        """Connect signals to slots"""
        self.update_results_signal.connect(self.update_results)
        self.event_detected_signal.connect(self.show_event_popup)
    
    def position_window(self):
        """Position the window on the screen"""
        screen = QApplication.primaryScreen()
        if not screen:
            return
            
        screen_geometry = screen.geometry()
        
        # Position on the right side of the screen
        x = screen_geometry.width() - self.width() - 20
        y = 20
        self.move(x, y)
    
    def get_region_text(self) -> str:
        """Get formatted text describing the selected region"""
        if self.scan_region:
            x, y, w, h = self.scan_region
            return f"Region: {x},{y} ({w}x{h})"
        return "No region selected"
    
    def select_region(self):
        """Select a region of the screen"""
        # Ensure proper window state before starting selection
        self.setWindowState(Qt.WindowState.WindowActive)
        self.activateWindow()
        QApplication.processEvents()
        
        # Log the state
        Logger.info("Starting region selection process")
        
        # Hide any existing popup
        if hasattr(self, 'current_popup') and self.current_popup:
            try:
                self.current_popup.close()
                self.current_popup = None
                Logger.debug("Closed existing popup before region selection")
            except Exception as e:
                Logger.error(f"Failed to close popup: {e}")
        
        # Make sure we're not already scanning
        if self.scanning:
            self.stop_scanning()
            Logger.debug("Stopped scanning before region selection")
        
        # Create and run the region selector
        selector = RegionSelector(self, self.on_region_selected)
        
        # Start selection process
        selector.select_region()
    
    def on_region_selected(self, region):
        """Handle region selection"""
        self.scan_region = region
        self.settings.set('last_region', region)
        self.settings.save_settings()
        self.region_label.setText(self.get_region_text())
        Logger.info(f"Region selected: {region}")
    
    def preview_region(self):
        """Preview the selected region"""
        if not self.scan_region:
            QMessageBox.warning(self, "Warning", "Please select a region first")
            return
        
        try:
            x, y, w, h = self.scan_region
            
            # Validate region
            screen = QApplication.primaryScreen()
            if not screen:
                QMessageBox.critical(self, "Error", "Could not get screen information")
                return
                
            screen_geometry = screen.geometry()
            
            if x < 0 or y < 0 or x + w > screen_geometry.width() or y + h > screen_geometry.height():
                QMessageBox.critical(
                    self, "Invalid Region", 
                    f"Selected region is outside screen bounds!\n\n"
                    f"Screen: {screen_geometry.width()}x{screen_geometry.height()}\n"
                    f"Region: {x},{y} + {w}x{h}\n\n"
                    f"Please select a new region."
                )
                return
            
            # Take screenshot of the region
            screenshot = pyautogui.screenshot(region=self.scan_region)
            
            # Create a preview dialog
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout
            
            preview = QDialog(self)
            preview.setWindowTitle(f"Region Preview - {w}x{h} at ({x},{y})")
            preview.setFixedSize(min(w + 40, 800), min(h + 100, 600))
            
            layout = QVBoxLayout(preview)
            
            # Info label with detailed coordinates
            info_text = f"Region: {x},{y} | Size: {w}x{h}\n"
            info_text += f"Screen: {screen_geometry.width()}x{screen_geometry.height()}\n"
            info_text += f"Screenshot size: {screenshot.width}x{screenshot.height}"
            info_label = QLabel(info_text)
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(info_label)
            
            # Image
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Convert PIL Image to QPixmap
            qimg = QPixmap.fromImage(screenshot.toqimage())
            img_label.setPixmap(qimg)
            
            layout.addWidget(img_label)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(preview.close)
            btn_layout.addWidget(close_btn)

            select_new_btn = QPushButton("Select New Region")
            select_new_btn.clicked.connect(lambda: [preview.close(), self.select_region()])
            btn_layout.addWidget(select_new_btn)
            
            layout.addLayout(btn_layout)
            
            preview.exec()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error", 
                f"Failed to preview region: {e}\n\n"
                f"This might indicate the region is invalid.\n"
                f"Please select a new region."
            )
    
    def start_scanning(self):
        """Start the scanning process"""
        if not self.scan_region:
            QMessageBox.warning(self, "Warning", "Please select a region first")
            return
        
        if not self.ocr_engine:
            QMessageBox.critical(self, "Error", "OCR engine not initialized")
            return
        
        self.scanning = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Update UI to show active scanning state
        self.status_label.setText("🔄 Scanning active...")
        self.status_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        
        # Change window title to indicate scanning is active
        self.setWindowTitle("Uma Event Scanner - [SCANNING ACTIVE]")
        
        # Highlight the control group to indicate active scanning
        self.control_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                color: #27ae60;
                font-weight: bold;
            }
        """)
        
        # Start scanning thread
        self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
        self.scan_thread.start()
        
        Logger.info("Scanning started")
    
    def stop_scanning(self):
        """Stop the scanning process"""
        self.scanning = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Update UI to show stopped state
        self.status_label.setText("⏹️ Scanning stopped")
        self.status_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # Reset window title
        self.setWindowTitle("Uma Event Scanner")
        
        # Reset control group style
        self.control_group.setStyleSheet("")
        
        Logger.info("Scanning stopped")
    
    def scan_loop(self):
        """Main scanning loop running in a separate thread"""
        while self.scanning:
            try:
                screenshot = pyautogui.screenshot(region=self.scan_region)
                img_array = np.array(screenshot)
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Apply image size optimization if available
                if GPU_CONFIG_AVAILABLE:
                    max_size = IMAGE_PROCESSING_CONFIG.get('max_image_size', (800, 600))
                    h, w = img_array.shape[:2]
                    if h > max_size[1] or w > max_size[0]:
                        scale = min(max_size[0] / w, max_size[1] / h)
                        new_w, new_h = int(w * scale), int(h * scale)
                        img_array = cv2.resize(img_array, (new_w, new_h), interpolation=cv2.INTER_AREA)
                
                # Extract text
                texts = self.ocr_engine.extract_text(img_array) if self.ocr_engine else []
                
                # If original didn't work well, try processed image
                if not texts or len(''.join(texts)) < 3:
                    processed_img = self.image_processor.preprocess_for_ocr(img_array)
                    texts = self.ocr_engine.extract_text(processed_img) if self.ocr_engine else []
                
                if texts:
                    # Emit signal to update UI in main thread
                    self.update_results_signal.emit(texts)
                    
                    # Check if the texts match an event
                    event = self.event_db.find_matching_event(texts)
                    if event:
                        # Skip if this event was recently dismissed by the user
                        if self.dismissed_event_name == event['name']:
                            # Still update last_event_name to current event for future comparison
                            self.last_event_name = event['name']
                            # Do not show the popup again until the event disappears
                        else:
                            # Only emit if new or changed event
                            if event['name'] != self.last_event_name:
                                self.last_event_name = event['name']
                            # update source frequency
                            for src in event.get('sources', []):
                                self.event_db.increment_source(src['name'])
                            self.event_detected_signal.emit(event)
                            # Add to history
                            self.history.add_entry(event, texts)
                            Logger.info(f"Event detected: {event['name']}")
                    else:
                        # No matching event detected – close existing popup if needed
                        if self.last_event_name is not None or self.current_popup:
                            self.last_event_name = None
                            self.dismissed_event_name = None
                            self.event_detected_signal.emit(None)
                else:
                    # No OCR text at all – ensure popup is closed
                    if self.last_event_name is not None or self.current_popup:
                        self.last_event_name = None
                        self.dismissed_event_name = None
                        self.event_detected_signal.emit(None)
                
                # Get scan interval from settings
                interval = float(self.settings.get('scan_interval', 2.0) or 2.0)
                time.sleep(interval)
                
            except Exception as e:
                Logger.error(f"Scan error: {e}")
                time.sleep(1)
    
    def update_results(self, texts: List[str]):
        """Update results display (called in main thread)"""
        self.result_text.clear()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.result_text.append(f"=== {timestamp} ===")
        self.result_text.append(f"Detected {len(texts)} text(s):\n")
        
        for i, text in enumerate(texts, 1):
            self.result_text.append(f"[{i}] {text}")
    
    def show_event_popup(self, event: Optional[Dict]):
        """Show event popup (called in main thread)"""
        # If event is None ⇒ hide any existing popup
        if not event:
            if hasattr(self, 'current_popup') and self.current_popup:
                try:
                    self.current_popup.close()
                    self.current_popup = None
                except Exception as e:
                    Logger.error(f"Failed to close popup: {e}")
            return
            
        # Log event details for debugging
        Logger.debug(f"Showing event popup. Event data: {str(event)}")
            
        if hasattr(self, 'current_popup') and self.current_popup:
            # If the same event is already displayed, just ensure visible and return
            try:
                if self.current_popup.event_data.get('name') == event.get('name'):
                    self.ensure_popup_visible()
                    return
                else:
                    self.current_popup.close()
                    self.current_popup = None
            except Exception as e:
                Logger.error(f"Failed to handle existing popup: {e}")
        
        # Keep popup visible while event is still detected ⇒ disable auto_close
        auto_close = self.auto_close_checkbox.isChecked()
        timeout = self.settings.get('popup_timeout', 8)
        
        try:
            # Ensure main window is active first
            self.activateWindow()
            self.raise_()
            QApplication.processEvents()
            
            # Kiểm tra và đảm bảo event có các trường cần thiết
            if 'name' not in event:
                Logger.warning(f"Event missing 'name' field: {str(event)}")
                event['name'] = "Unknown Event"
                
            if 'choices' not in event or not isinstance(event['choices'], list):
                Logger.warning(f"Event missing 'choices' field or invalid format: {str(event)}")
                event['choices'] = []
            
            # Create new popup with self as parent for proper positioning
            self.current_popup = EventPopup(self, event, auto_close, timeout)
            
            # Connect close signal
            self.current_popup.finished.connect(self.on_popup_closed)
            
            # Display the popup (this should make it appear)
            self.current_popup.show()
            self.current_popup.activateWindow()
            self.current_popup.raise_()
            
            # Ensure popup is visible with timer
            QTimer.singleShot(100, lambda: self.ensure_popup_visible())
            QTimer.singleShot(500, lambda: self.ensure_popup_visible())  # Additional check after 500ms
            
            # Log success
            Logger.info(f"Event popup shown: {event.get('name', 'Unknown Event')}")
        except Exception as e:
            Logger.error(f"Failed to show event popup: {e}")
            QMessageBox.critical(self, "Error", f"Failed to show event popup: {e}")
    
    def ensure_popup_visible(self):
        """Make sure popup is visible"""
        if self.current_popup and hasattr(self.current_popup, 'ensure_visible'):
            self.current_popup.ensure_visible()
        else:
            Logger.debug("Cannot ensure popup visibility - popup not available")
    
    def on_popup_closed(self):
        """Handle popup being closed"""
        self.current_popup = None
        # Remember which event was dismissed so we don't reopen it immediately
        self.dismissed_event_name = self.last_event_name
        # Make sure main window gets focus back
        self.activateWindow()
        self.raise_()
        QApplication.processEvents()
        Logger.debug("Popup was closed, main window focus restored")
    
    def refresh_history(self):
        """Refresh history display"""
        self.history_list.clear()
        
        for entry in self.history.get_history():
            timestamp = entry['timestamp'].strftime('%H:%M:%S')
            event_name = entry['event']['name']
            self.history_list.addItem(f"{timestamp} - {event_name}")
    
    def clear_history(self):
        """Clear all history"""
        reply = QMessageBox.question(
            self, "Confirm", "Clear all history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.refresh_history()
    
    def show_history_event(self, item):
        """Show event details when double-clicking on history item"""
        index = self.history_list.currentRow()
        history_entries = self.history.get_history()
        
        if 0 <= index < len(history_entries):
            entry = history_entries[index]
            event_data = entry['event']
            
            # Show event popup
            self.current_popup = EventPopup(self, event_data, False, 0)
            self.current_popup.show()
            self.current_popup.raise_()
            self.current_popup.activateWindow()
    
    def clear_last_event(self):
        """Clear the last event name and any dismissed event name, closing any current popup."""
        self.last_event_name = None
        self.dismissed_event_name = None
        if self.current_popup:
            self.current_popup.close()
            self.current_popup = None
        Logger.info("Last event name and dismissed event name cleared.")
    
    def save_settings(self):
        """Save application settings"""
        self.settings.set('scan_interval', self.interval_spinbox.value())
        self.settings.set('auto_close_popup', self.auto_close_checkbox.isChecked())
        self.settings.set('match_threshold', self.threshold_spinbox.value())
        self.settings.set('popup_timeout', self.timeout_spinbox.value())
        self.settings.set('use_gpu', self.gpu_checkbox.isChecked())

        # Apply threshold immediately
        from event_scanner.core.event_database import EventDatabase
        EventDatabase.THRESHOLD_SCORE = self.threshold_spinbox.value()
        
        # Reinitialize OCR engine if GPU flag changed
        previous_gpu = getattr(self.ocr_engine, 'gpu', None) if self.ocr_engine else None
        new_gpu = self.gpu_checkbox.isChecked()

        if self.settings.save_settings():
            QMessageBox.information(self, "Success", "Settings saved!")
            # Re-init OCR if GPU setting changed
            if previous_gpu != new_gpu:
                if self.scanning:
                    self.stop_scanning()
                self.init_ocr()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings")
    
    def closeEvent(self, event):
        """Handle application closing"""
        if self.scanning:
            self.stop_scanning()
        
        window_geometry = f"{self.width()}x{self.height()}+{self.x()}+{self.y()}"
        self.settings.set('window_position', window_geometry)
        self.settings.save_settings()
        
        event.accept()


# For testing purposes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 
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
    QSplitter, QComboBox, QFileDialog, QApplication, QSpinBox,
    QTreeWidget, QTreeWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap, QImage, QIcon

from event_scanner.core import ImageProcessor, EventDatabase, OCREngine
from event_scanner.services import SettingsManager, HistoryManager
from event_scanner.ui import RegionSelector, StatRecommendationsTab
from event_scanner.ui.character_select_dialog import CharacterSelectDialog
# from event_scanner.ui.ai_learning_dialog import AILearningDialog  # Removed AI feature
from event_scanner.ui.training_events_tab import TrainingEventsTab
from event_scanner.utils import Logger
import os, sys
import subprocess
from event_scanner.utils.paths import get_base_dir
from event_scanner.ui.update_dialog import UpdateDialog
import pathlib

# Import GPU configuration if available
try:
    from event_scanner.config import GPUConfig, IMAGE_PROCESSING_CONFIG
    GPU_CONFIG_AVAILABLE = True
except ImportError:
    GPU_CONFIG_AVAILABLE = False
    Logger.warning("GPU config not available - using default settings")

STAT_COLORS = {
    "Speed": "#3498DB",       # Blue sky
    "Stamina": "#E74C3C",     # Red (toned)
    "Power": "#F1C40F",       # Warm yellow
    "Guts": "#E67E22",        # Warm orange
    "Wisdom": "#1ABC9C",      # Teal
}

EFFECT_COLORS = {
    "skill": "#8E44AD",  # Purple (darker)
    "bond": "#FF6BB5",   # Pink stronger
    "status": "#9B59B6",  # Default for dark; will change per theme
}

DETAIL_FONT_PT = 13  # Font size for detail panel (pt)

# Summary panel style
SUMMARY_FONT_PT = 13
SUMMARY_NAME_COLOR = '#F39C12'   # Orange-gold
SUMMARY_TYPE_COLOR = '#9B59B6'   # Purple
SUMMARY_OWNER_COLOR = '#16A085'  # Teal

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
        self.selected_character_name: Optional[str] = None
        self.selected_character_id: Optional[str] = None
        self.image_processor = ImageProcessor()
        
        from collections import Counter
        self.source_freq = Counter()

        self.scanning = False
        self.scan_region = self.settings.get('last_region')
        self.current_popup = None
        self.scan_thread = None
        
        # Set window flags to ensure main window stays active and on top
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        
        # Remove default status bar to avoid gray background
        try:
            self.setStatusBar(None)
        except Exception:
            pass

        self.init_ocr()
        self.setup_ui()

        # Completely disable default status bar (remove gray area with 'Ready')
        from PyQt6.QtWidgets import QStatusBar
        empty_sb = QStatusBar()
        empty_sb.setSizeGripEnabled(False)
        empty_sb.setFixedHeight(0)
        empty_sb.setStyleSheet("QStatusBar{background:transparent;border:none;}")
        self.setStatusBar(empty_sb)

        icon_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'icon.ico'))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # Apply theme from settings (dark default)
        theme_name = self.settings.get('theme', 'dark')
        self.apply_theme(theme_name)
        self.connect_signals()
        
        # Setup window properties
        self.setWindowTitle("Uma Event Scanner")
        self.resize(560, 700)
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
        
        # (Removed title bar for more compact UI)
        
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
        status_frame.setObjectName("statusBar")
        status_frame.setFixedHeight(30)
        
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 9))
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(status_frame)
    
    def setup_training_events_tab(self):
        """Set up the training events tab"""
        self.training_events_tab = TrainingEventsTab()
        self.tab_widget.addTab(self.training_events_tab, "📚 Training")
    
    def setup_stat_recommendations_tab(self):
        """Set up the stat recommendations tab"""
        self.stat_recommendations_tab = StatRecommendationsTab()
        self.tab_widget.addTab(self.stat_recommendations_tab, "📊 Stats")
    
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
        
        preview_btn = QPushButton("👁️ Preview")
        preview_btn.clicked.connect(self.preview_region)

        # Button to pick character filter
        select_char_btn = QPushButton("🧑‍🎤 Select Uma")
        select_char_btn.clicked.connect(self.choose_character)

        # Add buttons to layout
        region_layout.addWidget(select_btn)
        region_layout.addWidget(preview_btn)
        region_layout.addWidget(select_char_btn)
        # add group to tab
        tab_layout.addWidget(region_group)
        
        # Control group
        self.control_group = QGroupBox("🎮 Controls")
        self.control_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        control_layout = QHBoxLayout(self.control_group)
        control_layout.setContentsMargins(15, 15, 15, 15)
        
        self.start_btn = QPushButton("▶️ Start Scanning")
        self.start_btn.clicked.connect(self.start_scanning)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_scanning)
        self.stop_btn.setEnabled(False)

        # Add buttons to control layout
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        
        # --- đã xoá nút Test JSON và hàm test_with_json_data để loại bỏ code test ---
        
        tab_layout.addWidget(self.control_group)
        
        # Results group
        results_group = QGroupBox("📊 Results")
        results_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(10, 15, 10, 15)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #555; }")
        self.result_splitter = splitter

        # Event summary (centered labels)
        self.summary_widget = QWidget()
        self.summary_widget.setMaximumWidth(230)
        sum_layout = QVBoxLayout(self.summary_widget)
        sum_layout.addStretch(1)
        self.lbl_name = QLabel()
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setWordWrap(True)
        self.lbl_type = QLabel()
        self.lbl_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_owner = QLabel()
        self.lbl_owner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_owner.setWordWrap(True)
        sum_layout.addWidget(self.lbl_name)
        sum_layout.addWidget(self.lbl_type)
        sum_layout.addWidget(self.lbl_owner)
        sum_layout.addStretch(1)
        splitter.addWidget(self.summary_widget)

        # Detail panel with scroll
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        detail_layout.addStretch(1)
        self.detail_layout = detail_layout  # keep for update
        detail_layout.addStretch(1)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(self.detail_widget)
        splitter.addWidget(scroll_area)

        # Hidden log text to maintain update_results without refactor
        from PyQt6.QtWidgets import QTextEdit
        self.result_text = QTextEdit()
        # Keep for logging but not added to layout to avoid extra splitter handle
        self.result_text.hide()

        # Restore splitter sizes from settings if available
        saved_sizes = self.settings.get('splitter_sizes')
        if saved_sizes and isinstance(saved_sizes, list) and len(saved_sizes)==2:
            splitter.setSizes([int(saved_sizes[0]), int(saved_sizes[1])])
        else:
            splitter.setSizes([200, 400])

        results_layout.addWidget(splitter)

        tab_layout.addWidget(results_group)
        tab_layout.setStretch(2, 1)  # Make results group stretch
        
        self.tab_widget.addTab(tab, "🖥️ Scanner")
    
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

        choose_btn = QPushButton("🔍 Chọn")
        choose_btn.clicked.connect(self.choose_character)

        controls_layout.addStretch(1)
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(choose_btn)
        
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
        
        self.tab_widget.addTab(tab, "📜 History")
        
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

        update_group = QGroupBox("🔄 Data Update")
        update_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        update_layout = QHBoxLayout(update_group)
        self.update_btn = QPushButton("🔄 Update")
        self.update_btn.clicked.connect(self.on_update_data)
        update_layout.addWidget(self.update_btn)
        update_layout.addStretch(1)
        tab_layout.addWidget(update_group)
        
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

        # Theme toggle
        theme_layout = QHBoxLayout()
        self.theme_checkbox = QCheckBox("🌙 Dark Theme")
        is_dark = (self.settings.get('theme', 'dark') == 'dark')
        self.theme_checkbox.setChecked(is_dark)
        def _on_theme_toggle(checked):
            self.apply_theme('dark' if checked else 'light')
            # persist immediately
            self.settings.set('theme', 'dark' if checked else 'light')
            self.settings.save_settings()
        self.theme_checkbox.toggled.connect(_on_theme_toggle)
        theme_layout.addWidget(self.theme_checkbox)
        theme_layout.addStretch(1)
        popup_layout.addLayout(theme_layout)
        
        # Add popup group to main settings tab layout (was accidentally removed)
        tab_layout.addWidget(popup_group)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_settings)
        tab_layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)
        tab_layout.addStretch(1)
        
        self.tab_widget.addTab(tab, "⚙️ Settings")
    
    def connect_signals(self):
        """Connect signals to slots"""
        self.update_results_signal.connect(self.update_results)
        self.event_detected_signal.connect(self.display_event_in_results)
    
    def position_window(self):
        """Position the window on the screen"""
        saved = self.settings.get('window_position')

        screen = QApplication.primaryScreen()
        if not screen:
            return

        if saved and isinstance(saved, str) and 'x' in saved and '+' in saved:
            try:
                dims, pos = saved.split('+', 1)
                w, h = map(int, dims.split('x'))
                x, y = map(int, pos.split('+')) if '+' in pos else (0, 0)

                # Validate within current screen bounds
                sg = screen.geometry()
                if 50 <= w <= sg.width() and 50 <= h <= sg.height():
                    self.resize(w, h)
                if 0 <= x <= sg.width() - 50 and 0 <= y <= sg.height() - 50:
                    self.move(x, y)
                    return  # successfully restored
            except Exception:
                pass  # fall back if parsing fails

        # Default position: right-top corner
        self.resize(560, self.height())
        sg = screen.geometry()
        x = sg.width() - self.width() - 20
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
        self.status_label.setProperty("state","running")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
        # Change window title to indicate scanning is active
        self.setWindowTitle("Uma Event Scanner - [SCANNING ACTIVE]")
        
        # Highlight the control group to indicate active scanning
        self.control_group.setProperty("active", True)
        self.control_group.style().unpolish(self.control_group)
        self.control_group.style().polish(self.control_group)
        
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
        self.status_label.setProperty("state","stopped")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        
        # Reset window title
        self.setWindowTitle("Uma Event Scanner")
        
        # Reset control group style
        self.control_group.setProperty("active", False)
        self.control_group.style().unpolish(self.control_group)
        self.control_group.style().polish(self.control_group)
        
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
                    
                    # Check if texts match an event, considering selected character id
                    event = self.event_db.find_matching_event(texts, self.selected_character_id)
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
                                src_name = src.get('name')
                                if src_name:
                                    self.event_db.increment_source(src_name)
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
    
    def display_event_in_results(self, event):
        """Append event details to result_text viewer."""
        if event is None:
            self.result_text.append("No event matched.\n")
            return

        # No skipping here – database already preferred variant; just show

        src_list = event.get('sources', []) or []
        match_selected = False
        if self.selected_character_id:
            match_selected = any(str(s.get('id')) == self.selected_character_id for s in src_list)

        if match_selected:
            owners = self.selected_character_name or "?"
        else:
            owners = ", ".join(s.get('name','') for s in src_list if s.get('name')) or "?"

        # Do not skip on name mismatch; database already handled preference

        # Apply colored, larger text for summary labels
        self.lbl_name.setText(
            f"<span style='color:{SUMMARY_NAME_COLOR}; font-size:{SUMMARY_FONT_PT}pt;'><b>{event.get('name','Unknown')}</b></span>"
        )
        self.lbl_name.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_name.setFont(QFont('Arial', SUMMARY_FONT_PT, QFont.Weight.Bold))

        self.lbl_type.setText(
            f"<span style='color:{SUMMARY_TYPE_COLOR}; font-size:{SUMMARY_FONT_PT}pt;'><i>{event.get('type','')}</i></span>"
        )
        self.lbl_type.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_type.setFont(QFont('Arial', SUMMARY_FONT_PT))

        self.lbl_owner.setText(
            f"<span style='color:{SUMMARY_OWNER_COLOR}; font-size:{SUMMARY_FONT_PT}pt;'><b>{owners}</b></span>"
        )
        self.lbl_owner.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_owner.setFont(QFont('Arial', SUMMARY_FONT_PT))

        self.show_event_details(event)

    def on_event_item_clicked(self, *args):
        return

    def show_event_details(self, event: dict):
        # Clear previous detail
        # remove all widgets between stretches (index 1 .. count-2)
        while self.detail_layout.count() > 2:
            item = self.detail_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Build labels
        choices = event.get('choices',[])
        if choices:
            for idx, ch in enumerate(choices):
                lbl_choice = QLabel(f"<b>{ch.get('choice','')}</b>")
                lbl_choice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                lbl_choice.setWordWrap(True)
                lbl_choice.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_choice.setTextFormat(Qt.TextFormat.RichText)
                lbl_choice.setFont(QFont("Arial", DETAIL_FONT_PT, QFont.Weight.Bold))
                self.detail_layout.insertWidget(self.detail_layout.count()-1, lbl_choice)

                for seg in ch.get('effects', []):
                    raw_text = seg.get('raw', '')
                    color = None
                    kind_raw = str(seg.get('kind', '')).lower()
                    if kind_raw == 'stat':
                        stat_name = seg.get('stat', '')
                        if 'bond' in stat_name.lower():
                            color = EFFECT_COLORS['bond']
                        else:
                            color = STAT_COLORS.get(stat_name)
                    elif 'skill' in kind_raw:
                        color = EFFECT_COLORS['skill']
                    elif 'bond' in kind_raw:
                        color = EFFECT_COLORS['bond']
                    elif kind_raw == 'status':
                        color = EFFECT_COLORS['status']
                    if color:
                        html = f"<span style='color:{color}; font-size:{DETAIL_FONT_PT}pt;'>{raw_text}</span>"
                    else:
                        html = f"<span style='font-size:{DETAIL_FONT_PT}pt;'>{raw_text}</span>"
                    eff = QLabel(html)
                    eff.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    eff.setWordWrap(True)
                    eff.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    eff.setTextFormat(Qt.TextFormat.RichText)
                    eff.setFont(QFont("Arial", DETAIL_FONT_PT))
                    self.detail_layout.insertWidget(self.detail_layout.count()-1, eff)

                    # Show detail under skill/status
                    if kind_raw in {"skill", "status"} and seg.get("detail"):
                        det = seg["detail"].get("effect") or ", ".join(str(v) for v in seg["detail"].values())
                        det_html = f"<span style='color:#95A5A6; font-style:italic; font-size:{DETAIL_FONT_PT - 1}pt;'>{det}</span>"
                        det_lbl = QLabel(det_html)
                        det_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                        det_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        det_lbl.setTextFormat(Qt.TextFormat.RichText)
                        det_lbl.setWordWrap(True)
                        det_font = QFont("Arial", DETAIL_FONT_PT - 1)
                        det_font.setItalic(True)
                        det_lbl.setFont(det_font)
                        self.detail_layout.insertWidget(self.detail_layout.count()-1, det_lbl)

                # Insert separator between choices (except after last)
                if idx < len(choices) - 1:
                    sep = QLabel("<span style='color:#666;'>──────────────</span>")
                    sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    sep.setTextFormat(Qt.TextFormat.RichText)
                    sep.setFont(QFont("Arial", DETAIL_FONT_PT))
                    self.detail_layout.insertWidget(self.detail_layout.count()-1, sep)

    # Event popup removed – no-op
    def show_event_popup(self, *args, **kwargs):
        return
    
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
            
            # Display event in panels instead of popup
            self.display_event_in_results(event_data)
            owners = ", ".join(s.get('name','') for s in event_data.get('sources', []) if s.get('name')) or "?"
            self.lbl_name.setText(f"<b>{event_data.get('name','Unknown')}</b>")
            self.lbl_type.setText(f"<i>{event_data.get('type','')}</i>")
            self.lbl_owner.setText(f"<b>{owners}</b>")
    
    def clear_last_event(self):
        """Clear the last event name and any dismissed event name, closing any current popup."""
        self.last_event_name = None
        self.dismissed_event_name = None
        # No popup now – nothing to close
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
    
    def on_update_data(self):
        """Handle update button click – run scraping tasks"""
        self.update_btn.setEnabled(False)
        self.status_label.setText("🔄 Updating data…")

        dlg = UpdateDialog(self)
        dlg.show()

        thread = threading.Thread(target=self.run_update_scripts, args=(dlg,), daemon=True)
        thread.start()

    def run_update_scripts(self, dialog: 'UpdateDialog'):
        """Worker thread: run Node.js scraper scripts sequentially and log output"""
        scripts = [
            ("Skills", "skill-scrape.js"),
            ("Uma Characters", "uma-scrape.js"),
            ("Support Cards", "support-scrape.js"),
            ("Events", "event-scrape.js"),
        ]
        scrape_dir = os.path.join(get_base_dir(), "scrape")

        portable_node = pathlib.Path(get_base_dir()) / "runtime" / "node.exe"
        node_cmd = str(portable_node) if portable_node.exists() else "node"

        for name, file_name in scripts:
            dialog.append_signal.emit(f"Running {name} scraper…")
            cmd_path = os.path.join(scrape_dir, file_name)
            if not os.path.exists(cmd_path):
                dialog.append_signal.emit(f"⚠️  Script not found: {cmd_path}\n")
                continue
            try:
                cmd_list = [node_cmd, cmd_path]
                work_dir = pathlib.Path(sys.executable).parent if getattr(sys, "frozen", False) else get_base_dir()
                proc = subprocess.Popen(cmd_list, cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
                if proc.stdout:
                    for line in proc.stdout:
                        dialog.append_signal.emit(line.rstrip())
                proc.wait()
                dialog.append_signal.emit(f"{name} scraping completed with exit code {proc.returncode}\n")
            except Exception as e:
                dialog.append_signal.emit(f"Error running {name} scraper: {e}\n")

        dialog.append_signal.emit("All scraping tasks completed.")
        dialog.enable_close_signal.emit()

        QTimer.singleShot(0, lambda: [self.update_btn.setEnabled(True), self.status_label.setText("Ready")])
    
    def closeEvent(self, event):
        """Handle application closing"""
        if self.scanning:
            self.stop_scanning()
        
        window_geometry = f"{self.width()}x{self.height()}+{self.x()}+{self.y()}"
        self.settings.set('window_position', window_geometry)
        # Save splitter sizes
        try:
            self.settings.set('splitter_sizes', self.result_splitter.sizes())
        except Exception:
            pass
        self.settings.save_settings()
        
        event.accept()

    # ---------------- Theme helper ----------------
    def apply_theme(self, theme_name: str):
        """Load stylesheet by theme name ('dark' or 'light')."""
        import os
        file_name = 'style.qss' if theme_name == 'dark' else 'style_light.qss'
        qss_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'resources', file_name))
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as fh:
                QApplication.instance().setStyleSheet(fh.read())
        else:
            QApplication.instance().setStyleSheet("")

        # Update status color for current theme
        global EFFECT_COLORS
        if theme_name == 'dark':
            EFFECT_COLORS['status'] = '#9B59B6'  # Lavender-dark
        else:
            EFFECT_COLORS['status'] = '#5D8AA8'  # Steel blue-light

    def choose_character(self):
        """Open dialog to select character filter."""
        char = CharacterSelectDialog.get_character(self)
        if not char:
            return

        if char.get("clear"):
            # Clear filter
            self.selected_character_name = None
            self.selected_character_id = None
            self.status_label.setText("Filter cleared")
            Logger.info("Character filter cleared")
            QMessageBox.information(self, "Cleared", "Character filter cleared.")
            return

        # Normal selection
        self.selected_character_name = char["name"].split("(")[0].strip()
        self.selected_character_id = str(char.get("id"))
        self.status_label.setText(f"Filtering: {self.selected_character_name}")
        QMessageBox.information(self, "Selected", f"Selected character: {self.selected_character_name}")
        Logger.info(f"Character filter set to '{self.selected_character_name}' (id={self.selected_character_id})")


# For testing purposes
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 
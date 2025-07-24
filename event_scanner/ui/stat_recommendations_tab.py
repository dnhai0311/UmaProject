"""
Stat Recommendations Tab for Uma Event Scanner
Displays recommended stats for different race types
"""

import json
import os
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGroupBox, QGridLayout, QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from event_scanner.utils import Logger
from event_scanner.utils.paths import get_data_dir


class StatRecommendationsTab(QWidget):
    """Tab for displaying stat recommendations"""
    
    def __init__(self):
        super().__init__()
        self.recommendations_data = {}
        self.setup_ui()
        self.load_recommendations()
    
    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Tab widget for different race types
        self.race_tabs = QTabWidget()
        self.race_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #404040;
                background-color: #1a1a1a;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #007bff;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #404040;
            }
        """)
        
        layout.addWidget(self.race_tabs)
    
    def load_recommendations(self):
        """Load recommendations from JSON file"""
        try:
            # Get the path to the recommendations file
            file_path = os.path.join(get_data_dir(), "stat_recommendations.json")
            
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.recommendations_data = json.load(f)
                self.display_recommendations()
                Logger.info("Stat recommendations loaded successfully")
            else:
                self.show_error_message(f"File not found: {file_path}")
                Logger.error(f"Stat recommendations file not found: {file_path}")
                
        except Exception as e:
            self.show_error_message(f"Failed to load recommendations: {e}")
            Logger.error(f"Failed to load stat recommendations: {e}")
    
    def display_recommendations(self):
        """Display the recommendations in the UI"""
        # Clear existing tabs
        self.race_tabs.clear()
        
        if not self.recommendations_data:
            self.show_error_message("No recommendations data available")
            return
        
        # Create tab for each race type
        for race_type, stats in self.recommendations_data.items():
            tab = self.create_race_tab(race_type, stats)
            self.race_tabs.addTab(tab, race_type)
    
    def create_race_tab(self, race_type: str, stats: Dict[str, str]) -> QWidget:
        """Create a tab widget for a specific race type"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #404040;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #555555;
            }
        """)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Create stats card
        stats_card = self.create_stats_card(stats)
        content_layout.addWidget(stats_card)
        
        # Add tips
        tips = self.get_race_tips(race_type)
        if tips:
            tips_card = self.create_tips_card(tips)
            content_layout.addWidget(tips_card)
        
        # Add stretch to push content to top
        content_layout.addStretch(1)
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_stats_card(self, stats: Dict[str, str]) -> QFrame:
        """Create a card widget for stats display"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("📊 Recommended Stats")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Stats grid
        stats_layout = QGridLayout()
        stats_layout.setSpacing(12)
        
        # Define stat colors and icons with softer colors
        stat_configs = {
            'SPD': {'color': '#dc3545', 'icon': '🏃', 'name': 'Speed'},
            'STA': {'color': '#28a745', 'icon': '💚', 'name': 'Stamina'},
            'PWR': {'color': '#fd7e14', 'icon': '💪', 'name': 'Power'},
            'WIT': {'color': '#6f42c1', 'icon': '🧠', 'name': 'Wisdom'}
        }
        
        row = 0
        for stat_code, stat_value in stats.items():
            if stat_code in stat_configs:
                config = stat_configs[stat_code]
                
                # Stat icon and name
                stat_label = QLabel(f"{config['icon']} {config['name']}")
                stat_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                stat_label.setStyleSheet(f"color: {config['color']};")
                stats_layout.addWidget(stat_label, row, 0)
                
                # Stat value
                value_label = QLabel(stat_value)
                value_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
                value_label.setStyleSheet(f"""
                    color: white;
                    background-color: {config['color']};
                    padding: 8px 15px;
                    border-radius: 6px;
                    border: none;
                """)
                value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                stats_layout.addWidget(value_label, row, 1)
                
                row += 1
        
        layout.addLayout(stats_layout)
        return card
    
    def create_tips_card(self, tips: str) -> QFrame:
        """Create a card widget for tips"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e3a5f;
                border: 1px solid #2d5a8b;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        # Tips title
        tips_title = QLabel("💡 Tips")
        tips_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        tips_title.setStyleSheet("color: #64b5f6;")
        layout.addWidget(tips_title)
        
        # Tips content
        tips_label = QLabel(tips)
        tips_label.setFont(QFont("Arial", 10))
        tips_label.setStyleSheet("color: #e0e0e0; line-height: 1.4;")
        tips_label.setWordWrap(True)
        layout.addWidget(tips_label)
        
        return card
    
    def get_race_tips(self, race_type: str) -> str:
        """Get tips for specific race type"""
        tips = {
            "Sprint/Mile": "Focus on Speed and Power. Stamina is less critical for short races.",
            "Medium": "Balanced approach with emphasis on Speed and Stamina. Power helps with acceleration.",
            "Long": "Stamina is crucial. Speed and Power are still important but Stamina should be prioritized."
        }
        return tips.get(race_type, "")
    
    def show_error_message(self, message: str):
        """Show error message in the UI"""
        error_label = QLabel(f"❌ {message}")
        error_label.setFont(QFont("Arial", 12))
        error_label.setStyleSheet("color: #dc3545; padding: 20px; text-align: center;")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Add to the first tab if available, otherwise create a new tab
        if self.race_tabs.count() > 0:
            first_tab = self.race_tabs.widget(0)
            if hasattr(first_tab, 'layout'):
                first_tab.layout().addWidget(error_label)
        else:
            # Create a temporary tab for error
            error_tab = QWidget()
            error_layout = QVBoxLayout(error_tab)
            error_layout.addWidget(error_label)
            self.race_tabs.addTab(error_tab, "Error")
    
    def refresh_data(self):
        """Refresh the recommendations data"""
        self.load_recommendations() 
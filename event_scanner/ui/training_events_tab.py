import json
import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QPushButton, QComboBox, QScrollArea, QFrame, QGroupBox,
    QTextEdit, QSplitter, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QCheckBox, QLineEdit, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QIcon
import requests
from typing import Dict, List, Optional, Any

class TrainingEventsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_file = "data/events.json"
        self.training_data = None
        self.filtered_events = []
        self.selected_event_type = None
        self.selected_character = None
        self.selected_scenario = None
        self.selected_cards = []
        
        # Will be populated from actual data
        self.event_types = []
        self.characters = []
        self.scenarios = []
        self.support_cards = []
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QHBoxLayout()
        
        # Left panel - Selection controls
        left_panel = self.create_selection_panel()
        
        # Right panel - Events display
        right_panel = self.create_events_panel()
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([550, 750])  # Adjusted splitter ratio
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
    def create_selection_panel(self):
        """Create the left panel with selection controls"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Training Events Helper")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Selection Group
        selection_group = QGroupBox("🔍 Tiêu chí lựa chọn")
        selection_grid = QGridLayout()
        selection_grid.setColumnStretch(1, 1)

        # Event Type Selection
        self.type_btn = QPushButton("📋 Chọn loại Event")
        self.type_btn.clicked.connect(self.open_type_selection)
        self.current_type_label = QLabel("Chưa chọn")
        self.current_type_label.setStyleSheet("color: #3498db; font-weight: bold;")
        selection_grid.addWidget(self.type_btn, 0, 0)
        selection_grid.addWidget(self.current_type_label, 0, 1)
        
        # Character Selection
        self.char_btn = QPushButton("👤 Chọn nhân vật")
        self.char_btn.clicked.connect(self.open_character_selection)
        self.current_char_label = QLabel("Chưa chọn")
        self.current_char_label.setStyleSheet("color: #e67e22; font-weight: bold;")
        selection_grid.addWidget(self.char_btn, 1, 0)
        selection_grid.addWidget(self.current_char_label, 1, 1)
        
        # Scenario Selection
        self.scenario_btn = QPushButton("📖 Chọn kịch bản")
        self.scenario_btn.clicked.connect(self.open_scenario_selection)
        self.current_scenario_label = QLabel("Chưa chọn")
        self.current_scenario_label.setStyleSheet("color: #9b59b6; font-weight: bold;")
        selection_grid.addWidget(self.scenario_btn, 2, 0)
        selection_grid.addWidget(self.current_scenario_label, 2, 1)
        
        # Support Cards Selection
        self.cards_btn = QPushButton("🎴 Chọn thẻ hỗ trợ")
        self.cards_btn.clicked.connect(self.open_cards_selection)
        self.current_cards_label = QLabel("Chưa chọn (0/6)")
        self.current_cards_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        selection_grid.addWidget(self.cards_btn, 3, 0)
        selection_grid.addWidget(self.current_cards_label, 3, 1)

        selection_group.setLayout(selection_grid)
        layout.addWidget(selection_group)

        # Filter Controls
        filter_group = QGroupBox("📊 Bộ lọc (Tự động cập nhật)")
        filter_layout = QVBoxLayout()
        self.show_type_events = QCheckBox("Lọc theo loại Event")
        self.show_type_events.setChecked(True)
        self.show_type_events.toggled.connect(self.apply_filters)
        
        self.show_character_events = QCheckBox("Lọc theo nhân vật")
        self.show_character_events.setChecked(True)
        self.show_character_events.toggled.connect(self.apply_filters)
        
        self.show_scenario_events = QCheckBox("Lọc theo kịch bản")
        self.show_scenario_events.setChecked(True)
        self.show_scenario_events.toggled.connect(self.apply_filters)
        
        self.show_card_events = QCheckBox("Lọc theo thẻ hỗ trợ")
        self.show_card_events.setChecked(True)
        self.show_card_events.toggled.connect(self.apply_filters)
        
        filter_layout.addWidget(self.show_type_events)
        filter_layout.addWidget(self.show_character_events)
        filter_layout.addWidget(self.show_scenario_events)
        filter_layout.addWidget(self.show_card_events)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Actions Group
        actions_group = QGroupBox("🚀 Hành động")
        actions_layout = QHBoxLayout()
        self.search_btn = QPushButton("🔍 Tìm kiếm thủ công")
        self.search_btn.clicked.connect(self.search_events)
        self.search_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 10px;")
        actions_layout.addWidget(self.search_btn)

        clear_all_btn = QPushButton("🗑️ Xóa tất cả")
        clear_all_btn.clicked.connect(self.clear_all_selections)
        clear_all_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        actions_layout.addWidget(clear_all_btn)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Status Label
        self.status_label = QLabel("Sẵn sàng")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("padding: 5px; background-color: #ecf0f1; border-radius: 3px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        panel.setLayout(layout)
        return panel
        
    def create_events_panel(self):
        """Create the right panel for displaying events"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📜 Kết quả Event")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Events count
        self.events_count = QLabel("Chưa tìm thấy event. Hãy lựa chọn và tìm kiếm.")
        self.events_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.events_count)
        
        # Events display
        self.events_display = QTextEdit()
        self.events_display.setReadOnly(True)
        self.events_display.setFont(QFont("Consolas", 10))
        layout.addWidget(self.events_display)
        
        panel.setLayout(layout)
        return panel
        
    def load_data(self):
        """Load training events data from JSON file and extract real data"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.training_data = json.load(f)
                
                self.extract_real_data()
                self.populate_selections()
                
                total_events = len(self.training_data.get('events', []))
                total_types = len(self.event_types)
                total_characters = len(self.characters)
                total_scenarios = len(self.scenarios)
                
                status_text = f"Đã tải {total_events} events, {total_types} loại, {total_characters} nhân vật, {total_scenarios} kịch bản."
                self.status_label.setText(status_text)
                self.display_events()
            else:
                self.status_label.setText(f"Không tìm thấy tệp dữ liệu: {self.data_file}")
                QMessageBox.warning(self, "Không tìm thấy dữ liệu", f"Không tìm thấy tệp dữ liệu training events:\n{self.data_file}")
        except Exception as e:
            self.status_label.setText(f"Lỗi khi tải dữ liệu: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tải dữ liệu: {e}")
            
    def extract_real_data(self):
        """Extract real event types, characters, and support cards from the data"""
        if not self.training_data:
            return
            
        events = self.training_data.get('events', [])
        characters = self.training_data.get('characters', [])
        support_cards = self.training_data.get('supportCards', [])
        scenarios_data = self.training_data.get('scenarios', [])

        # Existing lists
        self.event_types = sorted(list(set(event.get('type', 'Unknown') for event in events)))
        self.characters = sorted(list(set(char.get('name', '').replace(' (Original)', '') for char in characters if char.get('name'))))
        self.support_cards = sorted(list(set(card.get('name', '') for card in support_cards if card.get('name'))))

        # Scenario list extracted from dedicated section
        self.scenarios = sorted([scn.get('id', '') for scn in scenarios_data if scn.get('id')])

        # Build scenario -> eventIds map for quick filtering
        scenario_event_map = {}
        for scn in scenarios_data:
            scn_id = scn.get('id', '')
            if not scn_id:
                continue
            event_ids = [eid for group in scn.get('eventGroups', []) for eid in group.get('eventIds', [])]
            scenario_event_map[scn_id] = event_ids

        # Store helper lists/maps into training_data without overwriting original structures
        self.training_data['event_types'] = self.event_types
        self.training_data['character_names'] = self.characters  # keep original 'characters' intact
        self.training_data['scenario_ids'] = self.scenarios      # keep original 'scenarios' intact
        self.training_data['support_card_names'] = self.support_cards
        self.training_data['scenario_event_map'] = scenario_event_map
            
    def populate_selections(self):
        """Populate selection data for popup dialogs"""
        self.update_button_texts()
        
    def update_button_texts(self):
        """Update button texts and labels to show current selections"""
        self.current_type_label.setText(self.selected_event_type or 'Chưa chọn')
        self.current_char_label.setText(self.selected_character or 'Chưa chọn')
        self.current_scenario_label.setText(self.selected_scenario or 'Chưa chọn')
        
        if self.selected_cards:
            cards_text = ", ".join(self.selected_cards[:2])
            if len(self.selected_cards) > 2:
                cards_text += f"..."
            self.current_cards_label.setText(f"{cards_text} ({len(self.selected_cards)}/6)")
        else:
            self.current_cards_label.setText("Chưa chọn (0/6)")

    def apply_filters(self):
        """Apply current filters and refresh display"""
        # Only re-run search if there's an active selection to prevent running on startup
        has_selection = any([self.selected_event_type, self.selected_character, self.selected_scenario, self.selected_cards])
        if has_selection:
            self.search_events()
        
    def search_events(self):
        """Search for events based on current selections using real data"""
        if not self.training_data:
            QMessageBox.warning(self, "Không có dữ liệu", "Dữ liệu training chưa được tải.")
            return
            
        self.filtered_events = []
        all_events = self.training_data.get('events', [])
        characters_data = self.training_data.get('characters', [])
        support_cards_data = self.training_data.get('supportCards', [])
        scenario_event_map = self.training_data.get('scenario_event_map', {})

        # Build maps for faster lookups
        char_event_map = {char.get('name', '').replace(' (Original)', ''): [eid for group in char.get('eventGroups', []) for eid in group.get('eventIds', [])] for char in characters_data}
        card_event_map = {card.get('name', ''): [eid for group in card.get('eventGroups', []) for eid in group.get('eventIds', [])] for card in support_cards_data}

        has_selection = any([self.selected_event_type, self.selected_character, self.selected_scenario, self.selected_cards])
        if not has_selection:
            self.display_events()
            return
        
        seen_ids = set()  # track event IDs we've already added
        for event in all_events:
            event_id = event.get('id', '')
            event_type = event.get('type', 'Unknown')
            
            # Use a set to gather reasons for inclusion to avoid duplicate checks
            include_reasons = set()

            # Check type
            if self.show_type_events.isChecked() and self.selected_event_type and event_type == self.selected_event_type:
                include_reasons.add('type')

            # Check character
            if self.show_character_events.isChecked() and self.selected_character and event_id in char_event_map.get(self.selected_character, []):
                include_reasons.add('character')

            # Check scenario
            if self.show_scenario_events.isChecked() and self.selected_scenario and event_id in scenario_event_map.get(self.selected_scenario, []):
                include_reasons.add('scenario')

            # Check support cards
            if self.show_card_events.isChecked() and self.selected_cards:
                for card_name in self.selected_cards:
                    if event_id in card_event_map.get(card_name, []):
                        include_reasons.add('card')
                        break # No need to check other cards if one matches
            
            if include_reasons and event_id not in seen_ids:
                self.filtered_events.append(event)
                seen_ids.add(event_id)
                
        self.display_events()

    def display_events(self):
        """Display filtered events in the text area"""
        if not self.filtered_events:
            self.events_count.setText("Không tìm thấy event nào phù hợp.")
            self.events_display.setText("Vui lòng điều chỉnh tiêu chí lựa chọn và tìm kiếm lại.")
            return
            
        self.events_count.setText(f"Tìm thấy {len(self.filtered_events)} event duy nhất")
        display_text = ""
        events_by_type = {}
        for event in self.filtered_events:
            event_type = event.get('type', 'Unknown')
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
            
        for event_type, events in sorted(events_by_type.items()):
            display_text += f"\n{'='*70}\n"
            display_text += f"📋 {event_type.upper()} ({len(events)} events)\n"
            display_text += f"{'='*70}\n\n"
            
            for i, event in enumerate(events, 1):
                display_text += f"Event: {event.get('event', 'Unknown Event')}\n"
                choices = event.get('choices', [])
                if choices:
                    display_text += "  Lựa chọn:\n"
                    for j, choice in enumerate(choices, 1):
                        display_text += f"    {j}. {choice.get('choice', 'Không có mô tả')}\n"
                        raw_lines = []
                        segs = choice.get('effects', [])
                        if isinstance(segs, list):
                            for seg in segs:
                                if seg.get('kind') == 'divider_or':
                                    raw_lines.append('or')
                                else:
                                    raw_lines.append(seg.get('raw', ''))
                        for line in raw_lines:
                            if line.strip():
                                display_text += f"       → {line.strip()}\n"
                display_text += "-"*30 + "\n"
                
        self.events_display.setText(display_text)

    def open_type_selection(self):
        """Open popup dialog for event type selection"""
        dialog = SelectionDialog("Chọn loại Event", self.event_types, self.selected_event_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_event_type = dialog.selected_item
            self.update_button_texts()
            self.search_events()
            
    def open_character_selection(self):
        """Open popup dialog for character selection"""
        dialog = SelectionDialog("Chọn nhân vật", self.characters, self.selected_character, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_character = dialog.selected_item
            self.update_button_texts()
            self.search_events()
            
    def open_scenario_selection(self):
        """Open popup dialog for scenario selection"""
        dialog = SelectionDialog("Chọn kịch bản", self.scenarios, self.selected_scenario, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_scenario = dialog.selected_item
            self.update_button_texts()
            self.search_events()
            
    def open_cards_selection(self):
        """Open popup dialog for support cards selection"""
        dialog = MultiSelectionDialog("Chọn thẻ hỗ trợ", self.support_cards, self.selected_cards, 6, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_cards = dialog.selected_items
            self.update_button_texts()
            self.search_events()
            
    def clear_all_selections(self):
        """Clear all current selections"""
        self.selected_event_type = None
        self.selected_character = None
        self.selected_scenario = None
        self.selected_cards = []
        self.filtered_events = []
        self.update_button_texts()
        self.display_events()
        self.status_label.setText("Đã xóa lựa chọn. Sẵn sàng cho lần tìm kiếm mới.")


class SelectionDialog(QDialog):
    """Dialog for single item selection"""
    
    def __init__(self, title, items, current_selection, parent=None):
        super().__init__(parent)
        self.items = items
        self.selected_item = current_selection
        self.setup_ui(title)
        
    def setup_ui(self, title):
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Tìm kiếm...")
        self.search_edit.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_edit)
        
        # List widget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Xóa lựa chọn")
        clear_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Populate list
        self.populate_list()
        
    def populate_list(self):
        self.list_widget.clear()
        for item in self.items:
            list_item = QListWidgetItem(item)
            if item == self.selected_item:
                list_item.setSelected(True)
                self.list_widget.scrollToItem(list_item)
            self.list_widget.addItem(list_item)
            
    def filter_items(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setHidden(text.lower() not in item.text().lower())
            
    def clear_selection(self):
        self.selected_item = None
        self.accept()
        
    def accept(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            self.selected_item = selected_items[0].text()
        else: # Handle case where nothing is selected but OK is clicked
            self.selected_item = self.selected_item 
        super().accept()


class MultiSelectionDialog(QDialog):
    """Dialog for multiple item selection"""
    
    def __init__(self, title, items, current_selections, max_selections, parent=None):
        super().__init__(parent)
        self.items = items
        self.selected_items = current_selections.copy()
        self.max_selections = max_selections
        self.setup_ui(title)
        
    def setup_ui(self, title):
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(f"{title} (Tối đa {self.max_selections})")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Tìm kiếm...")
        self.search_edit.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_edit)
        
        # List widget with checkboxes
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.list_widget)
        
        # Selection info
        self.info_label = QLabel(f"Đã chọn: {len(self.selected_items)}/{self.max_selections}")
        self.info_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
        layout.addWidget(self.info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Xóa tất cả")
        clear_btn.clicked.connect(self.clear_selection)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        
        # Populate list
        self.populate_list()
        
    def populate_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for item in self.items:
            list_item = QListWidgetItem(item)
            list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if item in self.selected_items:
                list_item.setCheckState(Qt.CheckState.Checked)
            else:
                list_item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(list_item)
        self.list_widget.blockSignals(False)
        self.update_info()
        
    def filter_items(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setHidden(text.lower() not in item.text().lower())
            
    def on_item_changed(self, changed_item):
        if changed_item.checkState() == Qt.CheckState.Checked:
            if len(self.selected_items) >= self.max_selections:
                changed_item.setCheckState(Qt.CheckState.Unchecked)
                QMessageBox.warning(self, "Đã đạt giới hạn", f"Bạn chỉ có thể chọn tối đa {self.max_selections} thẻ.")
                return
            if changed_item.text() not in self.selected_items:
                self.selected_items.append(changed_item.text())
        else:
            if changed_item.text() in self.selected_items:
                self.selected_items.remove(changed_item.text())
            
        self.update_info()
        
    def update_info(self):
        self.info_label.setText(f"Đã chọn: {len(self.selected_items)}/{self.max_selections}")
        
    def clear_selection(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self.selected_items = []
        self.update_info() 
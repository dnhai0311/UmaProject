"""
Main Application for Uma Event Scanner
Contains the main EventScannerApp class with GUI and scanning logic
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
import pyautogui
import threading
import time
import re
from datetime import datetime
from PIL import Image, ImageTk
from typing import List, Dict, Optional

# Import our modules
from utils import Logger
from image_processor import ImageProcessor
from ocr_engine import OCREngine
from event_database import EventDatabase
from managers import SettingsManager, HistoryManager
from gui_components import EventPopup, RegionSelector

# Import GPU configuration
try:
    from gpu_config import GPUConfig, IMAGE_PROCESSING_CONFIG
    GPU_CONFIG_AVAILABLE = True
except ImportError:
    GPU_CONFIG_AVAILABLE = False
    Logger.warning("GPU config not available - using default settings")


class EventScannerApp:
    """Main application class for Uma Event Scanner"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.settings = SettingsManager()
        self.history = HistoryManager()
        self.event_db = EventDatabase()
        self.ocr_engine = None
        self.image_processor = ImageProcessor()
        
        self.scanning = False
        self.scan_region = self.settings.get('last_region')
        self.current_popup = None
        
        self.init_ocr()
        self.setup_gui()
    
    def init_ocr(self):
        """Initialize OCR engine"""
        try:
            language = self.settings.get('ocr_language', 'eng') or 'eng'
            self.ocr_engine = OCREngine(language)
            Logger.info("OCR engine initialized")
        except Exception as e:
            Logger.error(f"Failed to initialize OCR: {e}")
            messagebox.showerror("Error", "Failed to initialize OCR engine")
            self.root.quit()
    
    def setup_gui(self):
        """Setup the main GUI"""
        self.root.title("Uma Event Scanner")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        
        # Set modern theme colors
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom colors
        self.root.configure(bg='#f0f0f0')
        
        self.position_window()
        
        # Create main container
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Title bar
        title_frame = tk.Frame(main_container, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', pady=(0, 15))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="🎯 Uma Event Scanner",
            font=('Arial', 16, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(expand=True)
        
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True, pady=(0, 15))
        
        self.create_scanner_tab()
        self.create_history_tab()
        self.create_settings_tab()
        
        # Status bar with better styling
        status_frame = tk.Frame(main_container, bg='#34495e', height=30)
        status_frame.pack(fill='x')
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(
            status_frame, 
            textvariable=self.status_var, 
            relief='flat',
            bg='#34495e',
            fg='white',
            font=('Arial', 9)
        )
        self.status_bar.pack(side='left', padx=15, pady=6)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def position_window(self):
        """Position the window on screen"""
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Position window on the right side
        x = screen_width - 800
        y = 10
        geometry_str = f"800x700+{x}+{y}"
        self.root.geometry(geometry_str)
        self.root.attributes('-topmost', True)
        # Force geometry after 100ms to ensure correct position
        self.root.after(100, lambda: self.root.geometry(geometry_str))

    def create_scanner_tab(self):
        """Create the scanner tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Scanner")
        
        # Region selection
        region_frame = tk.LabelFrame(tab, text="📐 Scan Region", font=('Arial', 10, 'bold'))
        region_frame.pack(fill='x', padx=15, pady=10)
        
        region_inner = tk.Frame(region_frame, bg='#ecf0f1', padx=15, pady=10)
        region_inner.pack(fill='x')
        
        self.region_label = tk.Label(
            region_inner, 
            text=self.get_region_text(),
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        self.region_label.pack(side='left', padx=(0, 10))
        
        # Buttons
        select_btn = tk.Button(
            region_inner, 
            text="🎯 Select Region", 
            command=self.select_region,
            bg='#3498db',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        select_btn.pack(side='left', padx=5)
        
        preview_btn = tk.Button(
            region_inner, 
            text="👁️ Preview", 
            command=self.preview_region,
            bg='#e67e22',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        preview_btn.pack(side='left', padx=5)
        
        # Controls
        control_frame = tk.LabelFrame(tab, text="🎮 Controls", font=('Arial', 10, 'bold'))
        control_frame.pack(fill='x', padx=15, pady=10)
        
        control_inner = tk.Frame(control_frame, bg='#ecf0f1', padx=15, pady=10)
        control_inner.pack(fill='x')
        
        self.start_btn = tk.Button(
            control_inner, 
            text="▶️ Start Scanning", 
            command=self.start_scanning,
            bg='#27ae60',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            bd=0
        )
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = tk.Button(
            control_inner, 
            text="⏹️ Stop", 
            command=self.stop_scanning,
            state='disabled',
            bg='#e74c3c',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=8,
            relief='flat',
            bd=0
        )
        self.stop_btn.pack(side='left', padx=5)
        
        test_btn = tk.Button(
            control_inner, 
            text="🔍 Test OCR", 
            command=self.test_ocr,
            bg='#9b59b6',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        test_btn.pack(side='left', padx=5)
        
        test_json_btn = tk.Button(
            control_inner, 
            text="📄 Test JSON", 
            command=self.test_with_json_data,
            bg='#f39c12',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        test_json_btn.pack(side='left', padx=5)
        
        test_no_choice_btn = tk.Button(
            control_inner, 
            text="🚫 Test No Choice", 
            command=self.test_no_choice_event,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        test_no_choice_btn.pack(side='left', padx=5)
        
        # Results
        result_frame = tk.LabelFrame(tab, text="📊 Results", font=('Arial', 10, 'bold'))
        result_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        result_inner = tk.Frame(result_frame, bg='#ecf0f1')
        result_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        text_frame = tk.Frame(result_inner)
        text_frame.pack(fill='both', expand=True)
        
        self.result_text = tk.Text(
            text_frame, 
            height=15, 
            state='disabled', 
            font=('Consolas', 10),
            bg='white',
            fg='#2c3e50',
            relief='flat',
            bd=1
        )
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def create_history_tab(self):
        """Create the history tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="History")
        
        # Controls
        control_frame = tk.LabelFrame(tab, text="📋 History Controls", font=('Arial', 10, 'bold'))
        control_frame.pack(fill='x', padx=15, pady=10)
        
        control_inner = tk.Frame(control_frame, bg='#ecf0f1', padx=15, pady=10)
        control_inner.pack(fill='x')
        
        refresh_btn = tk.Button(
            control_inner, 
            text="🔄 Refresh", 
            command=self.refresh_history,
            bg='#3498db',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        refresh_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            control_inner, 
            text="🗑️ Clear", 
            command=self.clear_history,
            bg='#e74c3c',
            fg='white',
            font=('Arial', 9, 'bold'),
            padx=15,
            pady=5,
            relief='flat',
            bd=0
        )
        clear_btn.pack(side='left', padx=5)
        
        # History list
        list_frame = tk.LabelFrame(tab, text="📜 Event History", font=('Arial', 10, 'bold'))
        list_frame.pack(fill='both', expand=True, padx=15, pady=10)
        
        list_inner = tk.Frame(list_frame, bg='#ecf0f1')
        list_inner.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.history_listbox = tk.Listbox(
            list_inner, 
            font=('Arial', 10),
            bg='white',
            fg='#2c3e50',
            relief='flat',
            bd=1,
            selectmode='single',
            activestyle='none'
        )
        hist_scrollbar = ttk.Scrollbar(list_inner, orient='vertical', command=self.history_listbox.yview)
        self.history_listbox.configure(yscrollcommand=hist_scrollbar.set)
        
        self.history_listbox.pack(side='left', fill='both', expand=True)
        hist_scrollbar.pack(side='right', fill='y')
        
        # Bind double-click to show event details
        self.history_listbox.bind('<Double-Button-1>', self.show_history_event)
        
        self.refresh_history()
    
    def create_settings_tab(self):
        """Create the settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Scanner settings
        scanner_frame = tk.LabelFrame(tab, text="⚙️ Scanner Settings", font=('Arial', 10, 'bold'))
        scanner_frame.pack(fill='x', padx=15, pady=10)
        
        scanner_inner = tk.Frame(scanner_frame, bg='#ecf0f1', padx=15, pady=15)
        scanner_inner.pack(fill='x')
        
        # Scan interval setting
        interval_label = tk.Label(
            scanner_inner, 
            text="⏱️ Scan Interval (seconds):",
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50'
        )
        interval_label.grid(row=0, column=0, sticky='w', pady=5)
        
        self.interval_var = tk.DoubleVar(value=self.settings.get('scan_interval', 2.0))
        interval_entry = tk.Entry(
            scanner_inner, 
            textvariable=self.interval_var, 
            width=10,
            font=('Arial', 10),
            relief='flat',
            bd=1
        )
        interval_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Popup settings
        popup_frame = tk.LabelFrame(tab, text="🔔 Popup Settings", font=('Arial', 10, 'bold'))
        popup_frame.pack(fill='x', padx=15, pady=10)
        
        popup_inner = tk.Frame(popup_frame, bg='#ecf0f1', padx=15, pady=15)
        popup_inner.pack(fill='x')
        
        self.auto_close_var = tk.BooleanVar(value=self.settings.get('auto_close_popup', True))
        auto_close_check = tk.Checkbutton(
            popup_inner, 
            text="🔄 Auto-close popups",
            variable=self.auto_close_var,
            font=('Arial', 10),
            bg='#ecf0f1',
            fg='#2c3e50',
            selectcolor='#3498db'
        )
        auto_close_check.grid(row=0, column=0, sticky='w', pady=5)
        
        # Save button
        save_btn = tk.Button(
            tab, 
            text="💾 Save Settings", 
            command=self.save_settings,
            bg='#27ae60',
            fg='white',
            font=('Arial', 11, 'bold'),
            padx=30,
            pady=10,
            relief='flat',
            bd=0
        )
        save_btn.pack(pady=20)
    
    def get_region_text(self) -> str:
        """Get region text for display"""
        if self.scan_region:
            x, y, w, h = self.scan_region
            return f"Region: {x},{y} ({w}x{h})"
        return "No region selected"
    
    def select_region(self):
        """Select scan region"""
        selector = RegionSelector(self.root, self.on_region_selected)
        selector.select_region()
    
    def on_region_selected(self, region):
        """Handle region selection"""
        self.scan_region = region
        self.settings.set('last_region', region)
        self.settings.save_settings()
        self.region_label.config(text=self.get_region_text())
        Logger.info(f"Region selected: {region}")
    
    def preview_region(self):
        """Preview the selected region"""
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        try:
            x, y, w, h = self.scan_region
            
            # Validate region
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if x < 0 or y < 0 or x + w > screen_width or y + h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {x},{y} + {w}x{h}\n\nPlease select a new region.")
                return
            
            screenshot = pyautogui.screenshot(region=self.scan_region)
            
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"Region Preview - {w}x{h} at ({x},{y})")
            preview_window.resizable(False, False)
            
            img = screenshot.copy()
            
            # Scale image for display if needed
            max_display_size = (800, 600)
            if img.width > max_display_size[0] or img.height > max_display_size[1]:
                img.thumbnail(max_display_size)
            
            img_tk = ImageTk.PhotoImage(img)
            
            # Create frame for image and info
            main_frame = tk.Frame(preview_window)
            main_frame.pack(padx=10, pady=10)
            
            # Info label
            info_text = f"Region: {x},{y} | Size: {w}x{h} | Display: {img.size}"
            info_label = tk.Label(main_frame, text=info_text, font=('Arial', 10))
            info_label.pack(pady=(0, 10))
            
            # Image label
            label = tk.Label(main_frame, image=img_tk, border=2, relief='solid')
            label.pack()
            setattr(label, 'img_ref', img_tk)
            
            # Buttons frame
            button_frame = tk.Frame(main_frame)
            button_frame.pack(pady=(10, 0))
            
            ttk.Button(button_frame, text="Close", command=preview_window.destroy).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Test OCR", command=lambda: [preview_window.destroy(), self.test_ocr()]).pack(side='left', padx=5)
            ttk.Button(button_frame, text="Select New Region", command=lambda: [preview_window.destroy(), self.select_region()]).pack(side='left', padx=5)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to preview region: {e}\n\nThis might indicate the region is invalid.\nPlease select a new region.")

    def start_scanning(self):
        """Start the scanning process"""
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        if not self.ocr_engine:
            messagebox.showerror("Error", "OCR engine not initialized")
            return
        
        self.scanning = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_var.set("Scanning...")
        
        threading.Thread(target=self.scan_loop, daemon=True).start()
        Logger.info("Scanning started")
    
    def stop_scanning(self):
        """Stop the scanning process"""
        self.scanning = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_var.set("Stopped")
        Logger.info("Scanning stopped")
    
    def scan_loop(self):
        """Main scanning loop"""
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
                    self.update_results(texts)
                    
                    event = self.event_db.find_matching_event(texts)
                    if event:
                        self.show_event_popup(event)
                        self.history.add_entry(event, texts)
                        Logger.info(f"Event detected: {event['name']}")
                
                interval = float(self.settings.get('scan_interval', 2.0) or 2.0)
                time.sleep(interval)
            except Exception as e:
                Logger.error(f"Scan error: {e}")
                time.sleep(1)
    
    def update_results(self, texts: List[str]):
        """Update results display"""
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.result_text.insert(tk.END, f"=== {timestamp} ===\n")
        self.result_text.insert(tk.END, f"Detected {len(texts)} text(s):\n\n")
        
        for i, text in enumerate(texts, 1):
            self.result_text.insert(tk.END, f"[{i}] {text}\n")
        
        self.result_text.config(state='disabled')
        self.result_text.see(tk.END)
    
    def show_event_popup(self, event: Dict):
        """Show event popup"""
        if self.current_popup:
            try:
                self.current_popup.close()
            except:
                pass
        
        auto_close = bool(self.settings.get('auto_close_popup', True))
        timeout = int(self.settings.get('popup_timeout', 8) or 8)
        
        self.current_popup = EventPopup(self.root, event, auto_close, timeout)
        
        # Additional steps to ensure popup is on top
        try:
            self.current_popup.popup.update_idletasks()
            self.current_popup.popup.lift()
            self.current_popup.popup.attributes('-topmost', True)
            self.current_popup.popup.focus_force()
            
            self.root.after(200, self._ensure_popup_visibility)
        except Exception as e:
            Logger.error(f"Error ensuring popup visibility: {e}")
    
    def _ensure_popup_visibility(self):
        """Additional check to ensure popup is visible and on top"""
        if self.current_popup:
            try:
                self.current_popup.popup.lift()
                self.current_popup.popup.attributes('-topmost', True)
                self.current_popup.popup.focus_force()
            except Exception as e:
                Logger.error(f"Error in popup visibility check: {e}")
    
    def test_ocr(self):
        """Test OCR on current region"""
        if not self.scan_region:
            messagebox.showwarning("Warning", "Please select a region first")
            return
        
        try:
            x, y, w, h = self.scan_region
            
            # Validate region
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if x < 0 or y < 0 or x + w > screen_width or y + h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {x},{y} + {w}x{h}\n\nPlease select a new region.")
                return
            
            screenshot = pyautogui.screenshot(region=self.scan_region)
            img_array = np.array(screenshot)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Test with original image first
            texts_original = self.ocr_engine.extract_text(img_array) if self.ocr_engine else []
            
            # Test with processed image if original didn't work well
            if not texts_original or len(''.join(texts_original)) < 3:
                processed_img = self.image_processor.preprocess_for_ocr(img_array)
                texts_processed = self.ocr_engine.extract_text(processed_img) if self.ocr_engine else []
                texts = texts_processed
            else:
                texts = texts_original
                
            if texts:
                self.update_results(texts)
                result = '\n'.join(texts)
                
                # Check if detected text looks like game text
                is_valid_game_text = self._check_if_game_text(texts)
                
                if is_valid_game_text:
                    messagebox.showinfo("OCR Test Results", f"✅ Detected game text:\n\n{result}")
                else:
                    warning_msg = f"⚠️ Text may not be from game:\n\n{result}\n\n"
                    warning_msg += "🎯 Tips:\n"
                    warning_msg += "• Make sure region contains ONLY the event text\n"
                    warning_msg += "• Avoid UI elements, buttons, or background\n"
                    warning_msg += "• Ensure text is clear and readable\n"
                    warning_msg += "• Game should be in English language"
                    messagebox.showwarning("OCR Test Results", warning_msg)
            else:
                failure_msg = "❌ No text detected!\n\n"
                failure_msg += f"Region: {x},{y} (size: {w}x{h})\n\n"
                failure_msg += "💡 Try:\n"
                failure_msg += "• Select a smaller region focused on just the text\n"
                failure_msg += "• Ensure good contrast (dark text on light background)\n"
                failure_msg += "• Make sure game is in English\n"
                failure_msg += f"• Recommended size for single line: ~300x50"
                messagebox.showinfo("OCR Test Results", failure_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"OCR test failed: {e}")
            Logger.error(f"OCR test error: {e}")
    
    def test_with_json_data(self):
        """Test popup with sample JSON data"""
        # Create a test event with many choices
        test_event = {
            'name': 'Test Event with Many Choices - This is a very long event name to test wrapping and display issues',
            'choices': [
                {
                    'choice': 'First Choice - This is a very long choice text to test wrapping and display properly',
                    'effects': 'Speed +10, Stamina +5, Power +3, Guts +2, Wisdom +1'
                },
                {
                    'choice': 'Second Choice - Another long choice with different effects',
                    'effects': 'Power +15, Speed +5, Stamina +10'
                },
                {
                    'choice': 'Third Choice - This choice has a very long effect description that should wrap properly',
                    'effects': 'Guts +8, Wisdom +3, Speed +2, Power +2, Stamina +2'
                },
                {
                    'choice': 'Fourth Choice - Balanced approach',
                    'effects': 'Speed +5, Power +5, Stamina +5, Guts +5, Wisdom +5'
                }
            ]
        }
        
        # Show test popup
        auto_close = False
        self.current_popup = EventPopup(self.root, test_event, auto_close, 0)
        
        try:
            self.current_popup.popup.update_idletasks()
            self.current_popup.popup.lift()
            self.current_popup.popup.attributes('-topmost', True)
            self.current_popup.popup.focus_force()
        except Exception as e:
            Logger.error(f"Error ensuring test popup visibility: {e}")
        
        Logger.info("Showing test popup with JSON data")
    
    def test_no_choice_event(self):
        """Test popup with no-choice event"""
        # Create a test event with no choices
        test_event = {
            'name': 'I\'m Not Afraid! - No Choice Event',
            'effect': 'Speed +10, Stamina +5, Power +3, Guts +2, Wisdom +1 - Event chain ended'
        }
        
        # Show test popup
        auto_close = False
        self.current_popup = EventPopup(self.root, test_event, auto_close, 0)
        
        try:
            self.current_popup.popup.update_idletasks()
            self.current_popup.popup.lift()
            self.current_popup.popup.attributes('-topmost', True)
            self.current_popup.popup.focus_force()
        except Exception as e:
            Logger.error(f"Error ensuring test popup visibility: {e}")
        
        Logger.info("Showing test popup with no-choice event")
    
    def _check_if_game_text(self, texts: List[str]) -> bool:
        """Check if detected texts look like actual game text"""
        if not texts:
            return False
        
        combined = ' '.join(texts).lower()
        
        # Game-specific keywords that indicate valid game text
        game_indicators = [
            'training', 'race', 'event', 'skill', 'card', 'support',
            'uma', 'musume', 'stamina', 'speed', 'power', 'guts', 'wisdom',
            'scenario', 'choice', 'conversation', 'striking', 'considerate',
            'session', 'win', 'lose', 'level', 'rank', 'grade'
        ]
        
        # Common English words that could appear in game text
        common_words = [
            'the', 'to', 'me', 'be', 'it', 'a', 'and', 'of', 'in', 'for',
            'with', 'on', 'at', 'by', 'from', 'as', 'is', 'was', 'are',
            'have', 'has', 'had', 'will', 'would', 'can', 'could', 'should'
        ]
        
        # Check for game indicators
        for indicator in game_indicators:
            if indicator in combined:
                return True
        
        # Check if it's a reasonable English sentence/phrase
        words = combined.split()
        if len(words) >= 2:
            common_word_count = sum(1 for word in words if word in common_words)
            # If at least 25% are common English words, likely valid
            if common_word_count / len(words) >= 0.25:
                return True
        
        # Check for proper sentence structure
        if any(text[0].isupper() and text.endswith(('!', '.', '?')) for text in texts):
            return True
        
        return False
    
    def refresh_history(self):
        """Refresh history display"""
        self.history_listbox.delete(0, tk.END)
        
        for entry in self.history.get_history():
            timestamp = entry['timestamp'].strftime('%H:%M:%S')
            event_name = entry['event']['name']
            self.history_listbox.insert(tk.END, f"{timestamp} - {event_name}")
    
    def clear_history(self):
        """Clear all history"""
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.history.clear()
            self.refresh_history()
    
    def show_history_event(self, event):
        """Show event details when double-clicking on history item"""
        selection = self.history_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        history_entries = self.history.get_history()
        
        if index < len(history_entries):
            entry = history_entries[index]
            event_data = entry['event']
            
            # Show event popup
            auto_close = False  # Don't auto-close for history view
            self.current_popup = EventPopup(self.root, event_data, auto_close, 0)
            
            try:
                self.current_popup.popup.update_idletasks()
                self.current_popup.popup.lift()
                self.current_popup.popup.attributes('-topmost', True)
                self.current_popup.popup.focus_force()
            except Exception as e:
                Logger.error(f"Error ensuring history popup visibility: {e}")
    
    def save_settings(self):
        """Save application settings"""
        self.settings.set('scan_interval', self.interval_var.get())
        self.settings.set('auto_close_popup', self.auto_close_var.get())
        
        if self.settings.save_settings():
            messagebox.showinfo("Success", "Settings saved!")
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def on_closing(self):
        """Handle application closing"""
        if self.scanning:
            self.stop_scanning()
        
        self.settings.set('window_position', self.root.geometry())
        self.settings.save_settings()
        
        self.root.quit()
    
    def run(self):
        """Run the application"""
        Logger.info("Starting Uma Event Scanner")
        self.root.mainloop() 
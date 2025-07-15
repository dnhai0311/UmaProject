"""
GUI Components for Uma Event Scanner
Contains EventPopup and RegionSelector classes
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import time
from typing import Dict, Callable, Optional, Tuple
from PIL import Image, ImageTk
from utils import Logger


class EventPopup:
    """Popup window for displaying event information"""
    
    def __init__(self, parent, event: Dict, auto_close: bool = True, timeout: int = 8):
        self.event = event
        self.popup = tk.Toplevel(parent)
        self.setup_popup()
        
        if auto_close:
            self.popup.after(timeout * 1000, self.close)
    
    def setup_popup(self):
        """Setup the popup window"""
        self.popup.title('🎯 Event Detected!')
        
        # Force popup to be on top with multiple methods
        self.popup.attributes('-topmost', True)
        self.popup.lift()  # Bring to front
        self.popup.focus_force()  # Force focus
        
        # Additional Windows-specific attributes for better z-order
        try:
            self.popup.attributes('-toolwindow', False)  # Ensure it's not a tool window
            self.popup.attributes('-alpha', 1.0)  # Ensure full opacity
        except:
            pass  # Some attributes might not be available on all platforms
        
        self.popup.resizable(True, True)  # Allow resizing
        
        screen_width = self.popup.winfo_screenwidth()
        screen_height = self.popup.winfo_screenheight()
        
        # Calculate optimal size based on content
        choices = self.event.get('choices', [])
        
        # Estimate height needed for each choice (including effects)
        choice_height_estimate = 0
        if choices and len(choices) > 0:
            for choice in choices:
                if isinstance(choice, dict):
                    text = choice.get('choice', str(choice))
                    effect = choice.get('effect', '') or choice.get('effects', '')
                    # Estimate lines needed for text and effect
                    text_lines = max(1, len(text) // 50)  # ~50 chars per line
                    effect_lines = max(1, len(effect) // 50) if effect else 0
                    choice_height_estimate += (text_lines + effect_lines + 2) * 25 + 30  # 25px per line + padding
                else:
                    choice_height_estimate += 70  # Default height for simple choices
        else:
            # No choice event - estimate height for "No Choice" message
            effect = self.event.get('effect', '') or self.event.get('effects', '')
            if effect:
                effect_lines = max(1, len(effect) // 50)
                choice_height_estimate = effect_lines * 25 + 50  # Height for effect display
            else:
                choice_height_estimate = 50  # Height for "No Choice" message only
        
        # Base height for header and buttons
        base_height = 200
        total_height = base_height + choice_height_estimate
        
        # Responsive width and height - limit height to prevent too large popup
        width = min(1000, screen_width - 100)  # Reasonable width
        max_height = min(screen_height - 100, 800)  # Max 800px height
        height = min(total_height, max_height)
        
        # Position popup at bottom right corner
        x = screen_width - width - 20  # 20px margin from right edge
        y = screen_height - height - 20  # 20px margin from bottom edge
        
        self.popup.geometry(f'{width}x{height}+{x}+{y}')
        self.popup.configure(bg='#2c3e50')
        
        # Add border and shadow effect
        self.popup.configure(relief='raised', bd=3)
        
        # Ensure popup stays on top after geometry is set
        self.popup.after(100, self._ensure_on_top)
        
        self.create_content()
        
        # Final check to ensure popup is visible
        self.popup.after(200, self._final_visibility_check)
    
    def _final_visibility_check(self):
        """Final check to ensure popup is visible and properly positioned"""
        try:
            # Force update and bring to front
            self.popup.update_idletasks()
            self.popup.lift()
            self.popup.attributes('-topmost', True)
            self.popup.focus_force()
            
            # Ensure window is not minimized
            self.popup.state('normal')
            
        except Exception as e:
            Logger.debug(f"Final visibility check failed: {e}")
    
    def _ensure_on_top(self):
        """Ensure popup stays on top after creation"""
        try:
            self.popup.lift()
            self.popup.attributes('-topmost', True)
            self.popup.focus_force()
            
            # Windows-specific: Force window to front using win32api if available
            try:
                import win32gui
                import win32con
                
                # Get the window handle
                hwnd = self.popup.winfo_id()
                
                # Set window to be always on top
                win32gui.SetWindowPos(
                    hwnd, 
                    win32con.HWND_TOPMOST, 
                    0, 0, 0, 0, 
                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
                )
                
                # Bring window to front
                win32gui.SetForegroundWindow(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                
            except ImportError:
                # win32gui not available, use tkinter methods only
                pass
            except Exception as e:
                Logger.debug(f"Windows-specific window management failed: {e}")
                
        except Exception as e:
            Logger.error(f"Error ensuring popup is on top: {e}")
    
    def create_content(self):
        """Create the content of the popup"""
        # Main container
        main_container = tk.Frame(self.popup, bg='#2c3e50')
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Header with icon (FIXED - not scrollable)
        header_frame = tk.Frame(main_container, bg='#e74c3c', padx=15, pady=10)
        header_frame.pack(fill='x', pady=(0, 15))
        
        event_label = tk.Label(
            header_frame, 
            text=f"🎯 {self.event['name']}",
            font=('Arial', 14, 'bold'),
            fg='white',
            bg='#e74c3c',
            wraplength=950
        )
        event_label.pack()
        
        # Content container with scrollbar (only for choices/effects)
        content_container = tk.Frame(main_container, bg='#2c3e50')
        content_container.pack(fill='both', expand=True)
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(content_container, bg='#2c3e50', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#2c3e50')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Choices section
        choices = self.event.get('choices', [])
        
        # Check if event has choices or is "No Choice" type
        if choices and len(choices) > 0:
            # Event has choices
            choices_label = tk.Label(
                scrollable_frame,
                text="📋 Available Choices:",
                font=('Arial', 12, 'bold'),
                fg='#ecf0f1',
                bg='#2c3e50'
            )
            choices_label.pack(anchor='w', pady=(0, 10))
            
            # Create choices container
            choices_container = tk.Frame(scrollable_frame, bg='#2c3e50')
            choices_container.pack(fill='both', expand=True)
            
            for i, choice in enumerate(choices):
                # Define vibrant colors for different options
                colors = [
                    '#3498db',  # Blue
                    '#e67e22',  # Orange  
                    '#9b59b6',  # Purple
                    '#f1c40f',  # Yellow
                    '#1abc9c',  # Turquoise
                    '#e74c3c',  # Red
                    '#2ecc71',  # Green
                    '#f39c12'   # Gold
                ]
                bg_color = colors[i % len(colors)]
                
                # Create choice frame with rounded corners effect
                choice_frame = tk.Frame(choices_container, bg=bg_color, padx=15, pady=10, relief='raised', bd=2)
                choice_frame.pack(fill='x', expand=True, pady=5)
                
                # Create choice text label
                if isinstance(choice, dict):
                    text = choice.get('choice', str(choice))
                    effect = choice.get('effect', '') or choice.get('effects', '')
                    
                    # Choice text
                    choice_label = tk.Label(
                        choice_frame,
                        text=f"{i+1}. {text}",
                        font=('Arial', 11, 'bold'),
                        fg='white',
                        bg=bg_color,
                        wraplength=950,
                        justify='left',
                        anchor='w'
                    )
                    choice_label.pack(fill='x', anchor='w', pady=(0, 8))
                    
                    # Effect text (if exists)
                    if effect:
                        effect_label = tk.Label(
                            choice_frame,
                            text=f"   💡 Effect: {effect}",
                            font=('Arial', 10),
                            fg='white',
                            bg=bg_color,
                            wraplength=950,
                            justify='left',
                            anchor='w'
                        )
                        effect_label.pack(fill='x', anchor='w')
                else:
                    # Simple string choice
                    choice_label = tk.Label(
                        choice_frame,
                        text=f"{i+1}. {choice}",
                        font=('Arial', 11, 'bold'),
                        fg='white',
                        bg=bg_color,
                        wraplength=950,
                        justify='left',
                        anchor='w'
                    )
                    choice_label.pack(fill='x', anchor='w')
        else:
            # No choices - show "No Choice" message
            no_choice_label = tk.Label(
                scrollable_frame,
                text="🚫 No Choice Available",
                font=('Arial', 12, 'bold'),
                fg='#e74c3c',
                bg='#2c3e50'
            )
            no_choice_label.pack(anchor='w', pady=(0, 10))
            
            # Check if there's an effect for no-choice events
            effect = self.event.get('effect', '') or self.event.get('effects', '')
            if effect:
                effect_frame = tk.Frame(scrollable_frame, bg='#34495e', padx=15, pady=10, relief='raised', bd=2)
                effect_frame.pack(fill='x', expand=True, pady=5)
                
                effect_label = tk.Label(
                    effect_frame,
                    text=f"💡 Effect: {effect}",
                    font=('Arial', 10),
                    fg='white',
                    bg='#34495e',
                    wraplength=950,
                    justify='left',
                    anchor='w'
                )
                effect_label.pack(fill='x', anchor='w')
        
        # Close button with better styling (FIXED - not scrollable)
        close_btn = tk.Button(
            main_container,
            text='✖ Close',
            command=self.close,
            bg='#34495e',
            fg='white',
            font=('Arial', 10, 'bold'),
            padx=25,
            pady=5,
            relief='raised',
            bd=2
        )
        close_btn.pack(pady=(20, 0))
        
        # Pack canvas and scrollbar with proper layout
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Update scroll region after content is created
        self.popup.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Bind mouse wheel to canvas with proper error handling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas might be destroyed, ignore the error
                pass
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Unbind when popup is closed
        def _on_closing():
            try:
                canvas.unbind_all("<MouseWheel>")
            except:
                pass
            self.close()
        
        self.popup.protocol("WM_DELETE_WINDOW", _on_closing)
    
    def close(self):
        """Close the popup"""
        try:
            self.popup.destroy()
        except:
            pass


class RegionSelector:
    """GUI component for selecting screen regions"""
    
    def __init__(self, parent, callback: Callable):
        self.parent = parent
        self.callback = callback
        self.region = None
        self.selection_window = None
        self.rect = None
        self.start_pos = [0, 0]
    
    def select_region(self):
        """Start region selection process"""
        self.parent.withdraw()
        time.sleep(0.3)
        
        try:
            screenshot = pyautogui.screenshot()
            self.create_selection_window(screenshot)
        except Exception as e:
            Logger.error(f"Failed to take screenshot: {e}")
            messagebox.showerror("Error", f"Failed to take screenshot: {e}")
            self.parent.deiconify()
    
    def create_selection_window(self, screenshot: Image.Image):
        """Create the selection window"""
        img = screenshot.copy()
        img.thumbnail((1200, 800))
        
        scale_x = screenshot.width / img.width
        scale_y = screenshot.height / img.height
        
        self.selection_window = tk.Toplevel()
        self.selection_window.title('Select Scan Region')
        self.selection_window.attributes('-topmost', True)
        
        img_tk = ImageTk.PhotoImage(img)
        canvas = tk.Canvas(self.selection_window, width=img.width, height=img.height)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
        setattr(canvas, 'img_ref', img_tk)
        
        self.rect = None
        self.start_pos = [0, 0]
        
        canvas.bind('<ButtonPress-1>', lambda e: self.on_press(e, scale_x, scale_y))
        canvas.bind('<B1-Motion>', lambda e: self.on_drag(e, canvas))
        canvas.bind('<ButtonRelease-1>', lambda e: self.on_release(e, scale_x, scale_y))
    
    def on_press(self, event, scale_x: float, scale_y: float):
        """Handle mouse press event"""
        self.start_pos = [event.x, event.y]
        if self.rect:
            event.widget.delete(self.rect)
        self.rect = event.widget.create_rectangle(
            event.x, event.y, event.x, event.y, 
            outline='red', width=2
        )
    
    def on_drag(self, event, canvas):
        """Handle mouse drag event"""
        if self.rect:
            canvas.coords(self.rect, self.start_pos[0], self.start_pos[1], event.x, event.y)
    
    def on_release(self, event, scale_x: float, scale_y: float):
        """Handle mouse release event"""
        x1, y1 = min(self.start_pos[0], event.x), min(self.start_pos[1], event.y)
        x2, y2 = max(self.start_pos[0], event.x), max(self.start_pos[1], event.y)
        
        selection_width = x2 - x1
        selection_height = y2 - y1
        
        if selection_width > 10 and selection_height > 10:
            # Convert preview coordinates to real screen coordinates
            real_x = int(x1 * scale_x)
            real_y = int(y1 * scale_y)
            real_w = int(selection_width * scale_x)
            real_h = int(selection_height * scale_y)
            
            # Validation checks
            if real_w < 50 or real_h < 20:
                messagebox.showwarning("Region Too Small", f"Selected region is too small: {real_w}x{real_h}\n\nMinimum size: 50x20 pixels\n\nPlease select a larger area containing the text.")
                if self.selection_window:
                    self.selection_window.destroy()
                self.parent.deiconify()
                return
            
            if real_w > 1000 or real_h > 200:
                response = messagebox.askyesno("Large Region", f"Selected region is very large: {real_w}x{real_h}\n\nThis might include unwanted elements.\n\nRecommended max: 1000x200 pixels\n\nContinue anyway?")
                if not response:
                    if self.selection_window:
                        self.selection_window.destroy()
                    self.parent.deiconify()
                    return
            
            # Get screen dimensions for validation
            if self.selection_window:
                screen_width = self.selection_window.winfo_screenwidth()
                screen_height = self.selection_window.winfo_screenheight()
            else:
                screen_width = 1920  # Default fallback
                screen_height = 1080
            
            if real_x < 0 or real_y < 0 or real_x + real_w > screen_width or real_y + real_h > screen_height:
                messagebox.showerror("Invalid Region", f"Selected region is outside screen bounds!\n\nScreen: {screen_width}x{screen_height}\nRegion: {real_x},{real_y} + {real_w}x{real_h}")
                if self.selection_window:
                    self.selection_window.destroy()
                self.parent.deiconify()
                return
            
            self.region = (real_x, real_y, real_w, real_h)
            self.callback(self.region)
        else:
            messagebox.showwarning("Selection Too Small", "Please drag to select a larger area")
        
        if self.selection_window:
            self.selection_window.destroy()
        self.parent.deiconify() 
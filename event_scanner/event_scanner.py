"""
Uma Musume Event Scanner - Modular Version
Entry point for the refactored application
"""

from main_app import EventScannerApp
from utils import Logger

    
def main():
    """Main entry point for the Uma Event Scanner application"""
    try:
        app = EventScannerApp()
        app.run()
    except Exception as e:
        Logger.error(f"Application error: {e}")
        import tkinter.messagebox as messagebox
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")


if __name__ == '__main__':
    main() 
"""
Uma Musume Event Scanner - PyQt6 Version
Entry point for the application
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from event_scanner.ui.main_window import MainWindow
from event_scanner.utils import Logger


def main():
    """Main entry point for the application"""
    try:
        # Create the application
        app = QApplication(sys.argv)
        
        # Set application name and organization
        app.setApplicationName("Uma Event Scanner")
        app.setOrganizationName("UmaEventScanner")
        
        # Create and show the main window
        main_window = MainWindow()
        main_window.show()
        
        # Run the application
        return app.exec()
        
    except Exception as e:
        Logger.error(f"Application error: {e}")
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Fatal Error", f"Application failed to start: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
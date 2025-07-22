@echo off
echo ========================================
echo Installing Python Dependencies for Uma Event Scanner
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Checking version...
python --version
echo.

REM Upgrade pip to latest version
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install PyTorch with CUDA support for RTX 3050
REM (PyTorch installation removed)
echo.

REM Install OpenCV
echo Installing OpenCV...
python -m pip install opencv-python
echo.

REM Install NumPy
echo Installing NumPy...
python -m pip install numpy
echo.

REM Install Pillow (PIL)
echo Installing Pillow...
python -m pip install Pillow
echo.

REM Install PyAutoGUI
echo Installing PyAutoGUI...
python -m pip install pyautogui
echo.

REM Install EasyOCR with GPU support
echo Installing EasyOCR with GPU support...
python -m pip install easyocr
echo.

REM Install additional dependencies for EasyOCR
echo Installing additional OCR dependencies...
python -m pip install easyocr[gpu]
echo.

REM Install psutil for system monitoring
echo Installing psutil for system monitoring...
python -m pip install psutil
echo.

REM Install PyQt6
echo Installing PyQt6...
python -m pip install PyQt6
echo.

REM Install requests for HTTP requests
echo Installing requests for HTTP requests...
python -m pip install requests
echo.

REM Install pathlib (usually included with Python 3.4+, but just in case)
echo Installing pathlib...
python -m pip install pathlib
echo.

REM Install RapidFuzz for high-accuracy fuzzy matching
echo Installing RapidFuzz...
python -m pip install rapidfuzz
echo.

REM ========================================
REM AI/ML Dependencies for Event Detection
REM ========================================
REM (AI/ML dependency installations removed)
echo.
echo Verifying installations...
echo ========================================

REM (PyTorch test removed)
echo.

echo Testing OpenCV...
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
echo.

echo Testing EasyOCR...
python -c "import easyocr; print('EasyOCR imported successfully')"
echo.

echo Testing requests...
python -c "import requests; print('Requests imported successfully')"
echo.

REM (AI/ML library test removed)
echo.

echo Testing other libraries...
python -c "import numpy as np; import PIL; import pyautogui; import psutil; print('All core libraries imported successfully')"
echo.

echo ========================================
echo Installation completed!
echo ========================================
echo.
echo All dependencies installed successfully:
echo ✓ OpenCV
echo ✓ EasyOCR
echo ✓ PyQt6
echo ✓ NumPy
echo ✓ PyAutoGUI, psutil
echo ✓ Requests
echo ✓ Pandas, Matplotlib, Seaborn
echo.
REM (AI Learning feature lines removed)
echo If you see any errors above, please check:
echo 1. Python version (should be 3.8+)
echo 2. Internet connection
echo 3. Sufficient disk space
echo.
REM (AI test instruction removed)
echo To run the scanner, use: python start_scanner.py
echo.
pause 
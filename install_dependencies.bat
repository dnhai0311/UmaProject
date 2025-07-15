@echo off
echo ========================================
echo Installing Python Dependencies for Uma Event Scanner
echo Optimized for RTX 3050 Laptop GPU
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
echo Installing PyTorch with CUDA support for RTX 3050...
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
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

REM Install pywin32 for Windows-specific features
echo Installing pywin32 for Windows features...
python -m pip install pywin32
echo.

REM Install psutil for system monitoring
echo Installing psutil for system monitoring...
python -m pip install psutil
echo.

REM Verify installations
echo.
echo ========================================
echo Verifying installations...
echo ========================================

echo Testing PyTorch CUDA...
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}'); print(f'GPU count: {torch.cuda.device_count()}'); print(f'GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
echo.

echo Testing OpenCV...
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
echo.

echo Testing EasyOCR...
python -c "import easyocr; print('EasyOCR imported successfully')"
echo.

echo Testing other libraries...
python -c "import numpy as np; import PIL; import pyautogui; print('All core libraries imported successfully')"
echo.

echo ========================================
echo Installation completed!
echo ========================================
echo.
echo If you see any errors above, please check:
echo 1. Python version (should be 3.8+)
echo 2. Internet connection
echo 3. Sufficient disk space
echo.
echo To run the scanner, use: python event_scanner/event_scanner.py
echo.
pause 
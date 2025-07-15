@echo off
echo ========================================
echo Uma Event Scanner - RTX 3050 Optimized
echo ========================================
echo.

echo Checking GPU availability...
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'GPU Count: {torch.cuda.device_count()}'); print(f'GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo.
echo Setting up GPU optimizations...

REM Set environment variables for GPU optimization
set CUDA_VISIBLE_DEVICES=0
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
set OMP_NUM_THREADS=4

echo.
echo Starting Uma Event Scanner...
echo.

REM Start the scanner with optimized settings
cd /d "%~dp0"
cd event_scanner
python event_scanner.py

echo.
echo Scanner stopped.
pause 
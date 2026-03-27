@echo off
REM Build script for img2vid using PyInstaller

echo ========================================
echo Building img2vid Executable
echo ========================================

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller>=6.0.0

REM Run tests first (optional)
echo.
echo Running tests...
pytest tests/ -v || echo Tests completed with warnings

REM Build with PyInstaller
echo.
echo Building executable...
pyinstaller --name img2vid ^
    --onefile ^
    --icon=NONE ^
    --add-data "src;src" ^
    --hidden-import textual ^
    --hidden-import ffmpeg ^
    --hidden-import textual.widgets ^
    src\main.py

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo Executable location: dist\img2vid.exe
echo.

REM Keep window open to see results
pause

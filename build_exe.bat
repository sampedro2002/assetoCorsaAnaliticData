@echo off
echo ========================================
echo  Building Executable
echo ========================================
echo.

REM Detect virtual environment
set VENV_PATH=
if exist "auto\Scripts\activate.bat" (
    set VENV_PATH=auto
) else if exist "asseto\Scripts\activate.bat" (
    set VENV_PATH=asseto
)

if "%VENV_PATH%"=="" (
    echo [ERROR] Virtual environment not found (checked 'auto' and 'asseto'^)
    echo Please run install.bat first
    pause
    exit /b 1
)

echo [VENV] Using virtual environment: %VENV_PATH%
call %VENV_PATH%\Scripts\activate.bat

REM Install PyInstaller if not already installed
echo [1/3] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo [2/3] Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build executable
echo [3/3] Building executable...
pyinstaller --clean AssettoCorsaAnalytic.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo ========================================
echo.
echo Executable created: dist\analisisAsseto.exe
echo.
echo This is a PORTABLE executable with a GUI.
echo - Choose your Assetto Corsa folder and browser in the launcher.
echo - No terminal will appear in the background.
echo.
pause
pause

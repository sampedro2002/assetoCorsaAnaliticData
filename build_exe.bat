@echo off
echo ========================================
echo  Building Executable
echo ========================================
echo.

REM Activate virtual environment
if not exist "asseto\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

call asseto\Scripts\activate.bat

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
pyinstaller --clean grupo4Analisis.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  BUILD COMPLETED SUCCESSFULLY
echo ========================================
echo.
echo Executable created: dist\AssettoCorsa_Telemetry_Launcher.exe
echo.
echo You can now distribute this .exe file along with:
echo   - backend/ folder
echo   - frontend/ folder
echo   - .env file
echo   - data/ folder (will be created automatically)
echo.
pause

@echo off
REM StampFly Ecosystem - Development Environment Setup (Windows)
REM Usage: setup_env.bat

setlocal enabledelayedexpansion

echo.
echo [INFO] Setting up StampFly development environment...
echo.

REM Discover python.exe in common install locations
set "PYTHON_DIR="
for %%d in (
    "%USERPROFILE%\.pyenv\pyenv-win\versions\3.13.7"
    "%USERPROFILE%\.pyenv\pyenv-win\versions\3.12.0"
    "%USERPROFILE%\.pyenv\pyenv-win\versions\3.11.0"
    "%USERPROFILE%\.pyenv\pyenv-win\versions\3.10.11"
    "%LOCALAPPDATA%\Programs\Python\Python313"
    "%LOCALAPPDATA%\Programs\Python\Python312"
    "%LOCALAPPDATA%\Programs\Python\Python311"
    "%LOCALAPPDATA%\Programs\Python\Python310"
    "C:\Python313"
    "C:\Python312"
    "C:\Python311"
    "C:\Python310"
    "%USERPROFILE%\scoop\apps\python\current"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
) do (
    if not defined PYTHON_DIR (
        if exist "%%~d\python.exe" set "PYTHON_DIR=%%~d"
    )
)

if defined PYTHON_DIR (
    set "PATH=!PYTHON_DIR!;!PATH!"
)

python.exe --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ first.
    echo   https://www.python.org/downloads/
    exit /b 1
)

set "DISCOVERED_PATH=!PATH!"
endlocal & set "PATH=%DISCOVERED_PATH%"

set "IDF_PATH=%USERPROFILE%\esp\esp-idf"
if not exist "%IDF_PATH%\export.bat" (
    echo [ERROR] ESP-IDF not found at %IDF_PATH%
    echo   Run install.bat first.
    exit /b 1
)

echo [INFO] Loading ESP-IDF environment...
call "%IDF_PATH%\export.bat"
if errorlevel 1 (
    echo [ERROR] Failed to load ESP-IDF environment.
    exit /b 1
)

echo.
echo [OK] StampFly development environment ready.
echo.
echo   sf doctor          Check environment
echo   sf build vehicle   Build vehicle firmware
echo   sf --help          Show all commands
echo.

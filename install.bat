@echo off
REM StampFly Ecosystem Installer (Windows)
REM Usage: install.bat [options]

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

echo.
echo ============================================================
echo  StampFly Ecosystem Installer
echo ============================================================
echo.

REM Check for git
echo [INFO] Checking git...
where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] git is not installed.
    echo.
    echo   Install Git from:
    echo     https://git-scm.com/download/win
    echo.
    echo   Or using winget:
    echo     winget install Git.Git
    echo.
    exit /b 1
)
echo [OK] git found
echo.

REM Discover python.exe in common install locations
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
    if exist "%%~d\python.exe" (
        set "PATH=%%~d;!PATH!"
    )
)

REM Check for Python
echo [INFO] Checking Python...

set "PYTHON_CMD="
set "PYTHON_VERSION="

REM Try different Python commands (validate version >= 3.10)
for %%p in (python3 python py) do (
    if not defined PYTHON_CMD (
        for /f "tokens=*" %%v in ('%%p -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
            set "ver=%%v"
        )
        if defined ver (
            for /f "tokens=1,2 delims=." %%a in ("!ver!") do (
                if %%a geq 3 if %%b geq 10 (
                    set "PYTHON_CMD=%%p"
                    set "PYTHON_VERSION=!ver!"
                )
            )
        )
        set "ver="
    )
)

if not defined PYTHON_CMD (
    echo [ERROR] Python 3.10+ is required but not found.
    echo.
    echo   Install Python from:
    echo     https://www.python.org/downloads/
    echo.
    echo   Or using winget:
    echo     winget install Python.Python.3.12
    echo.
    exit /b 1
)

echo [OK] Found Python %PYTHON_VERSION% (%PYTHON_CMD%)
echo.

REM Run Python installer
%PYTHON_CMD% -u "%SCRIPT_DIR%scripts\installer.py" %*

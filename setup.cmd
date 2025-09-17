@echo off
REM Lightspeed OAuth Helper - One-Time Setup Script

echo ===============================================
echo Lightspeed OAuth Helper - Setup
echo ===============================================
echo.

echo This script will help you set up the Lightspeed OAuth helper.
echo.

REM Check if .env already exists
if exist ".env" (
    echo .env file already exists.
    choice /c YN /m "Do you want to overwrite it"
    if errorlevel 2 goto :skip_env
    echo.
)

REM Check if env.example exists
if exist "env.example" (
    echo Found env.example file. Copying to .env...
    copy "env.example" ".env" >nul
    echo.
    echo Please edit .env file with your actual Lightspeed credentials:
    echo.
    echo   LIGHTSPEED_RETAIL_CLIENT_ID=your_client_id
    echo   LIGHTSPEED_RETAIL_CLIENT_SECRET=your_client_secret
    echo   LIGHTSPEED_RETAIL_REDIRECT_URI=https://localhost:8080/callback
    echo   LIGHTSPEED_RETAIL_SCOPE=employee:all
    echo.
    choice /c YN /m "Do you want to open .env file for editing now"
    if not errorlevel 2 notepad ".env"
) else (
    echo Creating .env file template...
    echo # Lightspeed Retail OAuth Configuration > ".env"
    echo LIGHTSPEED_RETAIL_CLIENT_ID=your_client_id_here >> ".env"
    echo LIGHTSPEED_RETAIL_CLIENT_SECRET=your_client_secret_here >> ".env"
    echo LIGHTSPEED_RETAIL_REDIRECT_URI=https://localhost:8080/callback >> ".env"
    echo LIGHTSPEED_RETAIL_SCOPE=employee:all >> ".env"
    echo.
    echo Created .env file with template.
    echo Please edit it with your actual Lightspeed credentials.
    echo.
    choice /c YN /m "Do you want to open .env file for editing now"
    if not errorlevel 2 notepad ".env"
)

:skip_env
echo.
echo ===============================================
echo Checking Python installation...
echo ===============================================

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10 or higher and try again.
    echo.
    pause
    exit /b 1
)

python --version
echo Python is installed!
echo.

echo ===============================================
echo Installing Lightspeed OAuth Helper...
echo ===============================================

pip install -e .
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Installation failed.
    echo Please check the error messages above and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo Testing installation...
echo ===============================================

lsr-auth --help >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Installation verification failed.
    echo The lsr-auth command is not available.
    echo.
    pause
    exit /b 1
)

echo Installation successful!
echo.

echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Next steps:
echo 1. Make sure your .env file has correct Lightspeed credentials
echo 2. Run 'lightspeed-login.cmd' to authenticate
echo 3. Run 'lightspeed-task.cmd' to start using the API
echo.
echo For help, see QUICK_START.md
echo.
pause

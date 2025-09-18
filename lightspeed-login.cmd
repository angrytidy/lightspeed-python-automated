@echo off
REM Lightspeed OAuth Helper - Easy Login Script
REM This script initializes OAuth authentication for Lightspeed Retail API

echo ===============================================
echo Lightspeed Retail API - OAuth Login
echo ===============================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please create a .env file with your Lightspeed credentials:
    echo   LIGHTSPEED_RETAIL_CLIENT_ID=your_client_id
    echo   LIGHTSPEED_RETAIL_CLIENT_SECRET=your_client_secret
    echo   LIGHTSPEED_RETAIL_REDIRECT_URI=https://oauth.pstmn.io/v1/callback
    echo   LIGHTSPEED_RETAIL_SCOPE=employee:all
    echo.
    echo You can copy from env.example and update with your credentials.
    echo.
    pause
    exit /b 1
)

echo Checking current authentication status...
lsr-auth info
echo.

REM Check if already authenticated
lsr-auth info 2>nul | find "Has Tokens" | find "Yes" >nul
if %errorlevel% == 0 (
    echo You are already authenticated!
    echo.
    choice /c YN /m "Do you want to re-authenticate"
    if errorlevel 2 goto :end
    echo.
    echo Clearing existing tokens...
    lsr-auth clear --yes 2>nul
    echo.
)

echo Starting OAuth authentication...
echo This will open your browser for Lightspeed authorization.
echo.
pause

REM Use manual login by default on Windows (more reliable)
echo Using manual login mode for better Windows compatibility...
echo.
echo INSTRUCTIONS:
echo 1. A browser will open with the Lightspeed authorization page
echo 2. Sign in to your Lightspeed account and click 'Authorize'
echo 3. After authorization, copy the FULL URL from your browser's address bar
echo 4. Paste that complete URL when prompted below
echo.
pause

lsr-auth init --manual

REM Check if login was successful
if %errorlevel% == 0 (
    echo.
    echo ===============================================
    echo SUCCESS! OAuth authentication completed.
    echo ===============================================
    echo.
    echo Testing API connection...
    lsr-auth call /API/V3/Account.json
    echo.
    echo You can now use 'lightspeed-task.cmd' to run API commands.
) else (
    echo.
    echo ===============================================
    echo FAILED! OAuth authentication was not successful.
    echo ===============================================
    echo.
    echo Common issues:
    echo - Make sure you copied the COMPLETE redirect URL from your browser
    echo - Verify your .env file has the correct credentials
    echo - Check that redirect URI matches your Lightspeed app settings
    echo.
    echo For troubleshooting, run: lsr-auth info
)

:end
echo.
pause

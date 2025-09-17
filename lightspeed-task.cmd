@echo off
REM Lightspeed OAuth Helper - Task Execution Script
REM This script provides easy access to common Lightspeed API tasks

setlocal enabledelayedexpansion

echo ===============================================
echo Lightspeed Retail API - Task Runner
echo ===============================================
echo.

REM Check if authenticated
lsr-auth info 2>nul | find "Has Tokens" | find "Yes" >nul
if %errorlevel% neq 0 (
    echo ERROR: Not authenticated!
    echo Please run 'lightspeed-login.cmd' first to authenticate.
    echo.
    pause
    exit /b 1
)

REM Show current authentication status
echo Current Authentication Status:
lsr-auth info
echo.

:menu
echo ===============================================
echo Select a task:
echo ===============================================
echo 1. Get Account Information
echo 2. List Items/Products
echo 3. Get Item Details (by ID)
echo 4. List Categories
echo 5. List Customers
echo 6. Get Shop Information
echo 7. List Vendors
echo 8. Custom API Call
echo 9. Refresh Authentication Token
echo 0. Exit
echo.

set /p choice="Enter your choice (0-9): "

if "%choice%"=="0" goto :end
if "%choice%"=="1" goto :account
if "%choice%"=="2" goto :items
if "%choice%"=="3" goto :item_details
if "%choice%"=="4" goto :categories
if "%choice%"=="5" goto :customers
if "%choice%"=="6" goto :shop
if "%choice%"=="7" goto :vendors
if "%choice%"=="8" goto :custom
if "%choice%"=="9" goto :refresh

echo Invalid choice. Please try again.
echo.
goto :menu

:account
echo.
echo ===============================================
echo Getting Account Information...
echo ===============================================
lsr-auth call /API/V3/Account.json
goto :continue

:items
echo.
echo ===============================================
echo Listing Items/Products...
echo ===============================================
echo Note: This will show the first page of items (default limit)
lsr-auth call "/API/V3/Item.json"
goto :continue

:item_details
echo.
set /p item_id="Enter Item ID: "
if "%item_id%"=="" (
    echo Item ID cannot be empty.
    goto :continue
)
echo.
echo ===============================================
echo Getting Item Details for ID: %item_id%
echo ===============================================
lsr-auth call "/API/V3/Item/%item_id%.json"
goto :continue

:categories
echo.
echo ===============================================
echo Listing Categories...
echo ===============================================
lsr-auth call "/API/V3/Category.json"
goto :continue

:customers
echo.
echo ===============================================
echo Listing Customers...
echo ===============================================
echo Note: This will show the first page of customers (default limit)
lsr-auth call "/API/V3/Customer.json"
goto :continue

:shop
echo.
echo ===============================================
echo Getting Shop Information...
echo ===============================================
lsr-auth call "/API/V3/Shop.json"
goto :continue

:vendors
echo.
echo ===============================================
echo Listing Vendors...
echo ===============================================
lsr-auth call "/API/V3/Vendor.json"
goto :continue

:custom
echo.
echo ===============================================
echo Custom API Call
echo ===============================================
echo Enter the API endpoint path (e.g., /API/V3/Item.json)
echo Or enter a full path with query parameters
echo Example: /API/V3/Item.json?limit=10
echo.
set /p api_path="API Path: "
if "%api_path%"=="" (
    echo API path cannot be empty.
    goto :continue
)

echo.
set /p method="HTTP Method [GET]: "
if "%method%"=="" set method=GET

echo.
echo ===============================================
echo Making %method% request to: %api_path%
echo ===============================================
lsr-auth call "%api_path%" --method %method%
goto :continue

:refresh
echo.
echo ===============================================
echo Refreshing Authentication Token...
echo ===============================================
lsr-auth refresh
if %errorlevel% == 0 (
    echo Token refreshed successfully!
) else (
    echo Token refresh failed. You may need to re-authenticate.
    echo Run 'lightspeed-login.cmd' to log in again.
)
goto :continue

:continue
echo.
echo ===============================================
choice /c YN /m "Do you want to perform another task"
if errorlevel 2 goto :end
echo.
goto :menu

:end
echo.
echo Thank you for using Lightspeed API Task Runner!
echo.
pause

@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo ViolaDocs Platform - Production Mode
echo ==========================================

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%"

REM Check if .env file exists
if not exist .env (
    echo [WARN] .env file not found!
    echo [INFO] Creating .env from .env.example...
    if exist .env.example (
        copy .env.example .env >nul
        echo [OK] Created .env file. Please edit it with your configuration.
        echo    IMPORTANT: Set DEBUG=false, configure domain and SSL before production use!
        echo    Then run this script again.
        exit /b 1
    ) else (
        echo [ERROR] .env.example not found! Please create .env file manually.
        exit /b 1
    )
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)

echo.
echo [START] Starting ViolaDocs Platform in PRODUCTION mode...
echo.
echo [NOTE] Note: Services will be accessible via Nginx reverse proxy
echo    Frontend: http://localhost (or your configured domain)
echo    Backend API: http://localhost/api/v1
echo.

REM Build and start all services with nginx
docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml up -d --build

echo.
echo [WAIT] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo [STATUS] Service Status:
docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml ps

echo.
echo [OK] ViolaDocs Platform is running in PRODUCTION mode!
echo.
echo [WEB] Access the application:
echo    Frontend: http://localhost
echo    Backend API: http://localhost/api/v1
echo    API Docs: http://localhost/api/v1/docs
echo.
echo [NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml logs -f
echo [STOP] Stop services: scripts\prod\stop.bat
echo.

endlocal


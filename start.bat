@echo off
setlocal enabledelayedexpansion

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo ViolaDocs Platform - Startup Script
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo [WARN] .env file not found!
    echo [INFO] Creating .env from .env.example...
    if exist .env.example (
        copy .env.example .env >nul
        echo [OK] Created .env file. Please edit it with your configuration.
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
echo [START] Starting ViolaDocs Platform...
echo.
echo Select mode:
echo   1) Development (direct ports, no nginx)
echo   2) Production (nginx reverse proxy)
echo.
set /p mode="Enter choice [1-2] (default: 2): "
if "%mode%"=="" set mode=2
if "%mode%"=="1" (
    echo.
    echo [NOTE] Starting in DEVELOPMENT mode...
    echo    Frontend: http://localhost:3000
    echo    Backend: http://localhost:8000
    echo.
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d --build
) else (
    echo.
    echo [NOTE] Starting in PRODUCTION mode...
    echo    Access via: http://localhost
    echo.
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml up -d --build
)

echo.
echo [WAIT] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo [STATUS] Service Status:
if "%mode%"=="1" (
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps
) else (
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml ps
)

echo.
echo [OK] ViolaDocs Platform is starting!
echo.
if "%mode%"=="1" (
    echo [WEB] Access the application:
    echo    Frontend: http://localhost:3000
    echo    Backend API: http://localhost:8000
    echo    API Docs: http://localhost:8000/api/v1/docs
    echo.
    echo [NOTE] View logs:" docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f
    echo [STOP] Stop services:" stop.bat or docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down
) else (
    echo [WEB] Access the application:
    echo    Frontend: http://localhost
    echo    Backend API: http://localhost/api/v1
    echo    API Docs: http://localhost/api/v1/docs
    echo.
    echo [NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml logs -f
    echo [STOP] Stop services: stop.bat or docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down
)
echo.

endlocal


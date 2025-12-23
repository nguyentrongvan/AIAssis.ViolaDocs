@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo ViolaDocs Platform - Startup Script
echo ==========================================

if not exist .env (
    call :ColorEcho Yellow "[WARN] .env file not found!"
    call :ColorEcho Cyan "[INFO] Creating .env from .env.example..."
    if exist .env.example (
        copy .env.example .env >nul
        if errorlevel 1 (
            call :ColorEcho Red "[ERROR] Failed to create .env file."
            exit /b 1
        )
        call :ColorEcho Green "[OK] Created .env file. Please edit it with your configuration."
        echo    Then run this script again.
        exit /b 1
    ) else (
        call :ColorEcho Red "[ERROR] .env.example not found!"
        exit /b 1
    )
)

docker info >nul 2>&1
if errorlevel 1 (
    call :ColorEcho Red "[ERROR] Docker is not running. Please start Docker and try again."
    exit /b 1
)
call :ColorEcho Green "[OK] Docker is running."

echo.
echo [START] Starting ViolaDocs Platform...
echo.
echo Select mode:
echo   1^) Development (direct ports, no nginx)
echo   2^) Production (nginx reverse proxy)
echo.
set /p mode="Enter choice [1-2] (default: 2): "
if "%mode%"=="" set mode=2

echo.
echo Build options:
echo   1^) Normal build (use cache)
echo   2^) Force rebuild (no cache - slower but ensures fresh build)
echo.
set /p build_option="Enter build option [1-2] (default: 1): "
if "%build_option%"=="" set build_option=1

set BUILD_FLAGS=--build
if "%build_option%"=="2" (
    set BUILD_FLAGS=--build --no-cache
    call :ColorEcho Yellow "[INFO] Force rebuild enabled (no cache)"
)

if "%mode%"=="1" (
    echo.
    call :ColorEcho Cyan "[NOTE] Starting in DEVELOPMENT mode..."
    call :ColorEcho Green "   Frontend: http://localhost:3000"
    call :ColorEcho Green "   Backend: http://localhost:8000"
    echo.
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d %BUILD_FLAGS%
    if errorlevel 1 (
        call :ColorEcho Red "[ERROR] Failed to start services."
        exit /b 1
    )
    call :ColorEcho Green "[OK] Services started successfully in DEVELOPMENT mode."
) else (
    echo.
    call :ColorEcho Cyan "[NOTE] Starting in PRODUCTION mode..."
    call :ColorEcho Green "   Access via: http://localhost"
    echo.
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml up -d %BUILD_FLAGS%
    if errorlevel 1 (
        call :ColorEcho Red "[ERROR] Failed to start services."
        exit /b 1
    )
    call :ColorEcho Green "[OK] Services started successfully in PRODUCTION mode."
)

echo.
echo [WAIT] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

echo.
echo [STATUS] Service Status:
if "%mode%"=="1" (
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps
) else (
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml ps
)

echo.
call :ColorEcho Green "[OK] ViolaDocs Platform is starting!"
echo.

if "%mode%"=="1" (
    call :ColorEcho Cyan "[WEB] Access the application:"
    call :ColorEcho Green "   Frontend: http://localhost:3000"
    call :ColorEcho Green "   Backend API: http://localhost:8000"
    call :ColorEcho Green "   API Docs: http://localhost:8000/api/v1/docs"
    echo.
    echo [NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f
    echo [STOP] Stop services: stop.bat
) else (
    call :ColorEcho Cyan "[WEB] Access the application:"
    call :ColorEcho Green "   Frontend: http://localhost"
    call :ColorEcho Green "   Backend API: http://localhost/api/v1"
    call :ColorEcho Green "   API Docs: http://localhost/api/v1/docs"
    echo.
    echo [NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml logs -f
    echo [STOP] Stop services: stop.bat
)
echo.

endlocal
exit /b 0

:ColorEcho
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b

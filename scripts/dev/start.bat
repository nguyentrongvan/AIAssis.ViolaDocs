@echo off
setlocal

echo ==========================================
echo ViolaDocs Platform - Development Mode
echo ==========================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%"

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
call :ColorEcho Magenta "[START] Starting ViolaDocs Platform in DEVELOPMENT mode..."
echo.
call :ColorEcho Cyan "[NOTE] Frontend and Backend will be accessible directly on their ports"
call :ColorEcho Green "   Frontend: http://localhost:3000"
call :ColorEcho Green "   Backend API: http://localhost:8000"
call :ColorEcho Green "   API Docs: http://localhost:8000/api/v1/docs"
echo.

docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml up -d --build
if errorlevel 1 (
    call :ColorEcho Red "[ERROR] Failed to start services in DEVELOPMENT mode."
    exit /b 1
)
call :ColorEcho Green "[OK] Services started successfully."

echo.
echo [WAIT] Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

echo.
echo [STATUS] Service Status:
docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml ps

echo.
call :ColorEcho Green "[OK] ViolaDocs Platform is running in DEVELOPMENT mode!"
echo.
call :ColorEcho Cyan "[WEB] Access the application:"
call :ColorEcho Green "   Frontend: http://localhost:3000"
call :ColorEcho Green "   Backend API: http://localhost:8000"
call :ColorEcho Green "   API Docs: http://localhost:8000/api/v1/docs"
echo.
echo [NOTE] View logs: docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml logs -f
echo [STOP] Stop services: scripts\dev\stop.bat
echo.

endlocal
exit /b 0

:ColorEcho
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b

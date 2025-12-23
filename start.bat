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
call :ColorEcho Cyan "[INFO] Checking Ollama models initialization..."
call :CheckOllamaModels

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

:CheckOllamaModels
setlocal enabledelayedexpansion
set "MAX_WAIT=600"
set "WAIT_COUNT=0"
set "MODELS_READY=0"
set "LAST_STATUS="
set "LAST_PROGRESS="
set "COMPOSE_FILE="
if "%mode%"=="1" (
    set "COMPOSE_FILE=docker/docker-compose.base.yml -f docker/dev/docker-compose.yml"
) else (
    set "COMPOSE_FILE=docker/docker-compose.base.yml -f docker/prod/docker-compose.yml"
)

call :ColorEcho Yellow "[OLLAMA] Monitoring model download progress..."
echo.

:CheckLoop
set /a WAIT_COUNT+=1
if !WAIT_COUNT! gtr !MAX_WAIT! (
    call :ColorEcho Red "[WARNING] Timeout waiting for Ollama models. They may still be downloading in background."
    goto :EndCheck
)

REM Get last 100 lines of backend logs and check for key messages
docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Initializing Ollama Models" >nul
if !errorlevel! equ 0 (
    if !MODELS_READY! equ 0 (
        call :ColorEcho Cyan "[OLLAMA] Model initialization started..."
        set "MODELS_READY=1"
    )
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Pulling model" >nul
if !errorlevel! equ 0 (
    if not "!LAST_STATUS!"=="PULLING" (
        call :ColorEcho Yellow "[OLLAMA] Downloading model..."
        set "LAST_STATUS=PULLING"
    )
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Status: Pulling manifest" >nul
if !errorlevel! equ 0 (
    if not "!LAST_STATUS!"=="MANIFEST" (
        call :ColorEcho Cyan "[OLLAMA]   - Pulling manifest..."
        set "LAST_STATUS=MANIFEST"
    )
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Status: Downloading" >nul
if !errorlevel! equ 0 (
    if not "!LAST_STATUS!"=="DOWNLOADING" (
        call :ColorEcho Cyan "[OLLAMA]   - Downloading layers..."
        set "LAST_STATUS=DOWNLOADING"
    )
)

REM Check for progress updates - simplified to avoid nested for loop issues
docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Progress:" >nul
if !errorlevel! equ 0 (
    for /f "tokens=*" %%p in ('docker-compose -f !COMPOSE_FILE! logs --tail=5 backend 2^>nul ^| findstr /i "Progress:"') do (
        set "PROGRESS_LINE=%%p"
        if not "!PROGRESS_LINE!"=="!LAST_PROGRESS!" (
            call :ColorEcho Green "[OLLAMA]   !PROGRESS_LINE!"
            set "LAST_PROGRESS=!PROGRESS_LINE!"
        )
    )
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Status: Verifying" >nul
if !errorlevel! equ 0 (
    if not "!LAST_STATUS!"=="VERIFYING" (
        call :ColorEcho Cyan "[OLLAMA]   - Verifying model..."
        set "LAST_STATUS=VERIFYING"
    )
)

REM Check for success messages
docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Model pulled successfully" >nul
if !errorlevel! equ 0 (
    if not "!LAST_STATUS!"=="SUCCESS" (
        call :ColorEcho Green "[OLLAMA]   Model downloaded successfully!"
        set "LAST_STATUS=SUCCESS"
    )
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"All required models are already available" >nul
if !errorlevel! equ 0 (
    call :ColorEcho Green "[OLLAMA] All models are ready!"
    set "MODELS_READY=2"
    goto :EndCheck
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Successfully pulled" >nul
if !errorlevel! equ 0 (
    call :ColorEcho Green "[OLLAMA] Models downloaded successfully!"
    set "MODELS_READY=2"
    goto :EndCheck
)

docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Ollama models initialization completed" >nul
if !errorlevel! equ 0 (
    call :ColorEcho Green "[OLLAMA] Model initialization completed!"
    set "MODELS_READY=2"
    goto :EndCheck
)

REM Check if backend has started (means models are done or skipped)
docker-compose -f !COMPOSE_FILE! logs --tail=100 backend 2>nul | findstr /i /c:"Starting ViolaDocs backend server" >nul
if !errorlevel! equ 0 (
    if !MODELS_READY! equ 1 (
        REM Models were being pulled, wait a bit more to ensure completion
        timeout /t 3 /nobreak >nul
    )
    set "MODELS_READY=2"
    goto :EndCheck
)

REM Wait before next check
timeout /t 2 /nobreak >nul
goto :CheckLoop

:EndCheck
if !MODELS_READY! equ 2 (
    call :ColorEcho Green "[OLLAMA] Models ready!"
) else if !MODELS_READY! equ 1 (
    call :ColorEcho Yellow "[OLLAMA] Models may still be downloading in background"
) else (
    call :ColorEcho Yellow "[OLLAMA] Could not determine model status"
)
echo.
endlocal
exit /b

:ColorEcho
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b

@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo ViolaDocs Platform - Stop Script
echo ==========================================

echo.
call :ColorEcho Red "[STOP] Stopping ViolaDocs Platform..."
echo.
echo Select mode to stop:
echo   1^) Development
echo   2^) Production
echo   3^) Both (all running containers)
echo.
set /p mode="Enter choice [1-3] (default: 3): "
if "%mode%"=="" set mode=3

if "%mode%"=="1" (
    call :ColorEcho Cyan "[INFO] Stopping Development mode..."
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down
    if errorlevel 1 (
        call :ColorEcho Red "[ERROR] Failed to stop Development services."
        exit /b 1
    )
    call :ColorEcho Green "[OK] Development services stopped successfully."
) else if "%mode%"=="2" (
    call :ColorEcho Cyan "[INFO] Stopping Production mode..."
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down
    if errorlevel 1 (
        call :ColorEcho Red "[ERROR] Failed to stop Production services."
        exit /b 1
    )
    call :ColorEcho Green "[OK] Production services stopped successfully."
) else (
    call :ColorEcho Cyan "[INFO] Stopping all containers..."
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down 2>nul
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down 2>nul
    call :ColorEcho Green "[OK] All services stopped successfully."
)

echo.
call :ColorEcho Green "[OK] All services stopped!"
echo.
call :ColorEcho Yellow "[TIP] To remove volumes (data will be lost):"
echo    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down -v
echo    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down -v
echo.

endlocal
exit /b 0

:ColorEcho
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b

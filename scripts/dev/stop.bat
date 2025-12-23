@echo off
setlocal

echo ==========================================
echo ViolaDocs Platform - Stop Development Mode
echo ==========================================

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%"

echo.
call :ColorEcho Red "[STOP] Stopping ViolaDocs Platform (Development mode)..."
echo.

docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down
if errorlevel 1 (
    call :ColorEcho Red "[ERROR] Failed to stop services."
    exit /b 1
)

echo.
call :ColorEcho Green "[OK] All services stopped!"
echo.

endlocal
exit /b 0

:ColorEcho
powershell -NoProfile -Command "Write-Host '%~2' -ForegroundColor %~1"
exit /b

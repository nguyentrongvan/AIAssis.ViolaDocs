@echo off
setlocal

echo ==========================================
echo ViolaDocs Platform - Stop Production Mode
echo ==========================================

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%"

echo.
echo [STOP] Stopping ViolaDocs Platform (Production mode)...
echo.

REM Stop all services
docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down

echo.
echo [OK] All services stopped!
echo.

endlocal


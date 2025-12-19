@echo off
setlocal enabledelayedexpansion

REM Get script directory and project root
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%"
cd /d "%PROJECT_ROOT%"

echo ==========================================
echo ViolaDocs Platform - Stop Script
echo ==========================================

echo.
echo [STOP] Stopping ViolaDocs Platform...
echo.
echo Select mode to stop:
echo   1) Development
echo   2) Production
echo   3) Both (all running containers)
echo.
set /p mode="Enter choice [1-3] (default: 3): "
if "%mode%"=="" set mode=3

if "%mode%"=="1" (
    echo Stopping Development mode...
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down
) else if "%mode%"=="2" (
    echo Stopping Production mode...
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down
) else (
    echo Stopping all containers...
    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down 2>nul
    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down 2>nul
)

echo.
echo [OK] All services stopped!
echo.
echo [TIP] To remove volumes (data will be lost):
echo    docker-compose -f docker/docker-compose.base.yml -f docker/dev/docker-compose.yml down -v
echo    docker-compose -f docker/docker-compose.base.yml -f docker/prod/docker-compose.yml down -v
echo.

endlocal


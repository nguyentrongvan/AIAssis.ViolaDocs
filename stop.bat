@echo off
setlocal

echo ==========================================
echo ViolaDocs Platform - Stop Script
echo ==========================================

echo.
echo 🛑 Stopping ViolaDocs Platform...
echo.

REM Stop all services
docker-compose down

echo.
echo ✅ All services stopped!
echo.
echo 💡 To remove volumes (data will be lost):
echo    docker-compose down -v
echo.

endlocal


@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo ViolaDocs Platform - Startup Script
echo ==========================================

REM Check if .env file exists
if not exist .env (
    echo ⚠️  .env file not found!
    echo 📋 Creating .env from .env.example...
    if exist .env.example (
        copy .env.example .env >nul
        echo ✅ Created .env file. Please edit it with your configuration.
        echo    Then run this script again.
        exit /b 1
    ) else (
        echo ❌ .env.example not found! Please create .env file manually.
        exit /b 1
    )
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker and try again.
    exit /b 1
)

echo.
echo 🚀 Starting ViolaDocs Platform...
echo.

REM Build and start all services
docker-compose up -d --build

echo.
echo ⏳ Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check service status
echo.
echo 📊 Service Status:
docker-compose ps

echo.
echo ✅ ViolaDocs Platform is starting!
echo.
echo 🌐 Access the application:
echo    Frontend: http://localhost
echo    Backend API: http://localhost/api/v1
echo    API Docs: http://localhost/api/v1/docs
echo.
echo 📝 View logs: docker-compose logs -f
echo 🛑 Stop services: stop.bat or docker-compose down
echo.

endlocal


@echo off
echo ============================================
echo   Assessment Engine — Full System Start
echo ============================================
echo.

:: Check Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not installed or not running.
    echo Please install Docker Desktop from https://docker.com
    pause
    exit /b 1
)

echo [1/3] Starting infrastructure (PostgreSQL + Redis — FAISS is local, no Qdrant)...
cd /d %~dp0docker
docker compose up -d
echo       Waiting 10 seconds for services to initialize...
timeout /t 10 /nobreak >nul

echo [2/3] Starting Backend API (FastAPI)...
start "Assessment Backend" cmd /k "cd /d %~dp0backend && call start.bat"

echo [3/3] Starting Frontend (Next.js)...
start "Assessment Frontend" cmd /k "cd /d %~dp0frontend && npm install && npm run dev"

echo.
echo ============================================
echo   System is starting!
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/api/docs
echo   Frontend: http://localhost:3000
echo   Vectors:  FAISS at backend/data/faiss (no Docker)
echo ============================================
echo.
pause

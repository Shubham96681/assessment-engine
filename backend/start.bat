@echo off
echo ============================================
echo   Assessment Engine — Backend Startup
echo ============================================

cd /d %~dp0

:: Install dependencies globally since venv fails
echo [1/2] Installing dependencies...
mkdir D:\temp 2>nul
mkdir D:\pip-cache 2>nul
set TMP=D:\temp
set TEMP=D:\temp
set PIP_CACHE_DIR=D:\pip-cache
python -m pip install -r requirements.txt --quiet

:: Start FastAPI
echo [2/2] Starting FastAPI server on http://localhost:8000
echo       API Docs: http://localhost:8000/api/docs
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

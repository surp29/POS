@echo off
REM PosPos Backend Startup Script - Windows
chcp 65001 >nul

echo.
echo ========================================
echo   PosPos Backend Server
echo ========================================
echo.

REM Add Docker to PATH
set PATH=%PATH%;C:\Program Files\Docker\Docker\resources\bin

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat. Tai tai: https://python.org
    pause & exit /b 1
)

REM Create venv if not exists
if not exist "venv" (
    echo [INFO] Tao virtual environment...
    python -m venv venv
    if errorlevel 1 (echo [ERROR] Khong the tao venv & pause & exit /b 1)
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install/update dependencies
echo [INFO] Kiem tra dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (echo [ERROR] Loi cai dat dependencies & pause & exit /b 1)

REM Copy .env if not exists
if not exist ".env" (
    echo [WARNING] File .env chua ton tai
    if exist "env.example" (
        copy env.example .env >nul
        echo [INFO] Da copy tu env.example sang .env
        echo [INFO] Hay mo file .env va dien thong tin PostgreSQL/Redis cua ban
        notepad .env
    )
)

REM Start Redis if Docker is available
docker ps >nul 2>&1
if not errorlevel 1 (
    docker ps --filter "name=redis-pos" --format "{{.Names}}" | findstr "redis-pos" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Khoi dong Redis...
        docker run -d --name redis-pos -p 6379:6379 redis:7-alpine >nul 2>&1
        echo [INFO] Redis da khoi dong
    ) else (
        docker start redis-pos >nul 2>&1
        echo [INFO] Redis dang chay
    )
) else (
    echo [WARNING] Docker khong kha dung - dam bao Redis dang chay thu cong
)

REM Setup database (tao bang neu chua co)
echo [INFO] Kiem tra database...
python setup_database.py
if errorlevel 1 (
    echo [ERROR] Loi setup database - kiem tra PostgreSQL va file .env
    pause & exit /b 1
)

REM Start server
echo.
echo [SUCCESS] Khoi dong FastAPI server...
echo [INFO] API:     http://localhost:5001
echo [INFO] Docs:    http://localhost:5001/docs
echo [INFO] Metrics: http://localhost:5001/metrics
echo [INFO] WS:      ws://localhost:5001/api/ws/orders
echo [INFO] Nhan Ctrl+C de dung server
echo.
python main.py

pause
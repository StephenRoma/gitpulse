@echo off
REM GitPulse startup script for Windows

SET SCRIPT_DIR=%~dp0

REM ── Check .env ─────────────────────────────────────────────────────
IF NOT EXIST "%SCRIPT_DIR%backend\.env" (
    echo [ERROR] No .env found in backend\
    echo Copy backend\.env.example to backend\.env and fill in your keys.
    pause
    exit /b 1
)

REM ── Backend ────────────────────────────────────────────────────────
cd "%SCRIPT_DIR%backend"

IF NOT EXIST "venv\" (
    echo Setting up Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo Starting FastAPI backend...
start "GitPulse Backend" cmd /k "venv\Scripts\activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

REM ── Frontend ───────────────────────────────────────────────────────
cd "%SCRIPT_DIR%frontend"

echo Installing frontend dependencies...
call npm install --silent

echo Starting Vite dev server...
start "GitPulse Frontend" cmd /k "npm run dev"

echo.
echo GitPulse is starting up!
echo Dashboard -^> http://localhost:5173
echo API docs  -^> http://localhost:8000/docs
echo.
echo Close the terminal windows to stop.
pause

@echo off
REM GitPulse — single-terminal startup
REM Backend runs silently (log → backend\backend.log); only Vite is shown here.

SET SCRIPT_DIR=%~dp0

REM ── Check .env ─────────────────────────────────────────────────────
IF NOT EXIST "%SCRIPT_DIR%backend\.env" (
    echo [ERROR] backend\.env not found.
    echo Copy backend\.env.example to backend\.env and fill in your API keys.
    pause
    exit /b 1
)

REM ── Backend venv + deps ────────────────────────────────────────────
cd /d "%SCRIPT_DIR%backend"

IF NOT EXIST "venv\" (
    echo Setting up Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

IF NOT EXIST "venv\Lib\site-packages\fastapi" (
    echo Installing Python dependencies...
    pip install -q -r requirements.txt
)

REM ── Start backend silently (log → backend\backend.log) ────────────
echo Starting backend on http://localhost:8000
start /min "GitPulse Backend" cmd /c "cd /d "%SCRIPT_DIR%backend" && call venv\Scripts\activate.bat && python -m uvicorn main:app --host 127.0.0.1 --port 8000 > backend.log 2>&1"

REM ── Frontend ───────────────────────────────────────────────────────
cd /d "%SCRIPT_DIR%frontend"

IF NOT EXIST "node_modules\" (
    echo Installing frontend dependencies...
    call npm install --silent
)

echo.
echo  GitPulse  →  http://localhost:5173
echo  API docs  →  http://localhost:8000/docs
echo  Backend log  →  backend\backend.log
echo.

npm run dev

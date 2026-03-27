#!/bin/bash
# GitPulse startup script — runs backend + frontend concurrently

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Check .env ────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/backend/.env" ]; then
  echo "❌  No .env found in backend/"
  echo "    Copy backend/.env.example → backend/.env and fill in your keys."
  exit 1
fi

# ── Backend ───────────────────────────────────────────────────────────
echo "🔧  Setting up Python environment..."
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo "🚀  Starting FastAPI backend on http://localhost:8000 ..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# ── Frontend ──────────────────────────────────────────────────────────
cd "$SCRIPT_DIR/frontend"

echo "📦  Installing frontend dependencies..."
npm install --silent

echo "⚡  Starting Vite dev server on http://localhost:5173 ..."
npm run dev &
FRONTEND_PID=$!

# ── Cleanup on exit ───────────────────────────────────────────────────
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

echo ""
echo "✅  GitPulse is running!"
echo "    Dashboard → http://localhost:5173"
echo "    API docs  → http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."
echo ""

wait

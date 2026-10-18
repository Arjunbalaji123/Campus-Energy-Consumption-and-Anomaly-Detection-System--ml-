#!/usr/bin/env bash
# ==============================================================================
# AI-Based Campus Energy Consumption & Anomaly Detection System (CIT Coimbatore)
# Quick Start Script: Runs Backend (FastAPI) and Frontend (Vite) simultaneously
# ==============================================================================

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
VENV_PYTHON="${BACKEND_DIR}/venv/bin/python"
VENV_UVICORN="${BACKEND_DIR}/venv/bin/uvicorn"

echo "================================================================================"
echo " Starting CIT Campus Energy & Anomaly Detection System"
echo "================================================================================"

# Verify Python virtualenv exists
if [ ! -f "${VENV_UVICORN}" ]; then
    echo "❌ Error: Virtualenv uvicorn binary not found at ${VENV_UVICORN}"
    exit 1
fi

# Ensure database is up to date
echo "📌 Running database migrations..."
cd "${BACKEND_DIR}"
"${BACKEND_DIR}/venv/bin/alembic" upgrade head

# Trap SIGINT and SIGTERM to kill background children cleanly
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $(jobs -p) 2>/dev/null || true
    wait $(jobs -p) 2>/dev/null || true
    echo "✓ Stopped all services cleanly."
}
trap cleanup SIGINT SIGTERM EXIT

# Start Backend
echo "🚀 Starting FastAPI backend on http://127.0.0.1:8000 ..."
cd "${BACKEND_DIR}"
"${VENV_UVICORN}" app.main:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

# Start Frontend
echo "🚀 Starting Vite frontend on http://localhost:5173 ..."
cd "${FRONTEND_DIR}"
npm run dev &
FRONTEND_PID=$!

echo "================================================================================"
echo " All services running!"
echo " 👉 Web Application: http://localhost:5173"
echo " 👉 API Swagger Docs: http://127.0.0.1:8000/docs"
echo " Press Ctrl+C in this terminal to stop both servers."
echo "================================================================================"

# Keep script running
wait


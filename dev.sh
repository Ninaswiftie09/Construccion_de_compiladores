#!/bin/bash

# Quick start script for development
# Start both frontend and backend in background

set -e

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null || true
  echo "✅ Cleanup complete"
}

trap cleanup EXIT INT TERM

echo "🚀 Compiscript Compiler - Development Start"
echo "==========================================="
echo ""

# Start backend
echo "Starting backend..."
cd backend
source venv/bin/activate 2>/dev/null || {
  echo "❌ Backend not set up. Run: ./setup.sh"
  exit 1
}
python server.py &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
sleep 2

# Start frontend
echo "Starting frontend..."
cd ../frontend
npm start &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
sleep 2

echo ""
echo "🎉 Ready to develop!"
echo "🌐 Frontend: http://localhost:3000"
echo "⚙️  Backend:  http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

wait

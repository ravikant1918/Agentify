#!/bin/bash

# Agentify Development Script
echo "🚀 Starting Agentify Development Environment"

# Kill any existing processes
echo "🔄 Cleaning up existing processes..."
pkill -f "uvicorn" || true
pkill -f "npm run dev" || true

# Wait a moment for cleanup
sleep 2

echo "📦 Building React app..."
cd frontend && npm run build && cd ..


echo "🔧 Starting backend server..."
cd backend && uvicorn app:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!
cd ..

echo "⚛️  Starting React development server..."
cd frontend && npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Development environment started!"
echo "🌐 Backend API: http://localhost:8001"
echo "⚛️  Frontend Dev: http://localhost:3000"
echo "📝 React app is also served from backend at http://localhost:8001"

echo ""
echo "📋 Quick Commands:"
echo "  - Kill all: pkill -f 'uvicorn|npm run dev'"
echo "  - Backend only: cd backend && uvicorn app:app --host 0.0.0.0 --port 8001 --reload"
echo "  - Frontend only: cd frontend && npm run dev"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap 'echo "🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait
#!/bin/bash

# Compiscript Compiler - Setup Script
# This script sets up both backend and frontend

set -e

echo "🚀 Compiscript Compiler Setup"
echo "=============================="
echo ""

# Backend Setup
echo "1️⃣  Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
  echo "   Creating virtual environment..."
  python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "   Installing Python dependencies..."
pip install -q -r requirements.txt

# Generate ANTLR files
echo "   Generating ANTLR parser..."
cd grammar
if ! command -v antlr4 &> /dev/null; then
  echo "   ⚠️  ANTLR not found. Please install it first:"
  echo "      brew install antlr (macOS)"
  echo "      sudo apt-get install antlr4 (Linux)"
  exit 1
fi
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4 -o .
cd ..

echo "   ✅ Backend ready!"
cd ..

echo ""

# Frontend Setup
echo "2️⃣  Setting up frontend..."
cd frontend

# Install dependencies
echo "   Installing Node.js dependencies..."
npm install -q

echo "   ✅ Frontend ready!"
cd ..

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the compiler:"
echo ""
echo "Terminal 1 (Backend):"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  python server.py"
echo ""
echo "Terminal 2 (Frontend):"
echo "  cd frontend"
echo "  npm start"
echo ""
echo "The IDE will be available at http://localhost:3000"

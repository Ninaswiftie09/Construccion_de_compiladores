#!/usr/bin/env python3
"""
Quick start script for the Compiscript Compiler

Usage:
  python quickstart.py              # Show help
  python quickstart.py backend      # Start backend server
  python quickstart.py frontend     # Start frontend server
  python quickstart.py both         # Start both servers
  python quickstart.py test         # Run tests
"""

import sys
import subprocess
import os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "backend":
        start_backend()
    elif command == "frontend":
        start_frontend()
    elif command == "both":
        print("Starting both servers...")
        print("Open 2 terminals and run:")
        print("  Terminal 1: python quickstart.py backend")
        print("  Terminal 2: python quickstart.py frontend")
        return
    elif command == "test":
        run_tests()
    elif command == "help" or command == "-h" or command == "--help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()
        sys.exit(1)

def show_help():
    print("""
╔════════════════════════════════════════════════════════════════╗
║  🧪 Compiscript Compiler - Quick Start                        ║
╚════════════════════════════════════════════════════════════════╝

COMMANDS:
  python quickstart.py backend    Start backend server
  python quickstart.py frontend   Start frontend server  
  python quickstart.py test       Run unit tests
  python quickstart.py help       Show this help message

FIRST TIME SETUP:
  1. Run: python quickstart.py setup
  2. Run: bash setup.sh  (Linux/macOS)
  3. Run: setup.bat      (Windows)

AFTER SETUP:
  Terminal 1:  python quickstart.py backend
  Terminal 2:  python quickstart.py frontend
  Then visit:  http://localhost:3000

REQUIREMENTS:
  ✓ Python 3.9+
  ✓ Node.js 16+
  ✓ ANTLR 4.14+

DOCUMENTATION:
  - README.md         - Project overview
  - docs/SETUP.md     - Detailed setup guide
  - docs/ARCHITECTURE.md - System design
""")

def start_backend():
    """Start the backend server"""
    backend_dir = Path(__file__).parent / "backend"
    
    # Check if virtual environment exists
    venv_path = backend_dir / "venv"
    if not venv_path.exists():
        print("❌ Virtual environment not found!")
        print("Run: python quickstart.py setup")
        sys.exit(1)
    
    # Check if ANTLR files exist
    grammar_dir = backend_dir / "grammar"
    if not (grammar_dir / "CompiscriptLexer.py").exists():
        print("⚠️  ANTLR files not generated!")
        print("Run: bash generate_parser.sh  (or generate_parser.bat on Windows)")
        sys.exit(1)
    
    print("🚀 Starting Backend Server...")
    print("📍 http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop\n")
    
    # Change to backend directory and run server
    os.chdir(backend_dir)
    
    # Activate venv and run server
    if sys.platform == "win32":
        subprocess.run([str(venv_path / "Scripts" / "python"), "server.py"])
    else:
        subprocess.run([str(venv_path / "bin" / "python"), "server.py"])

def start_frontend():
    """Start the frontend server"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("❌ Dependencies not installed!")
        print("Run: cd frontend && npm install")
        sys.exit(1)
    
    print("🚀 Starting Frontend Server...")
    print("📍 http://localhost:3000")
    print("Press Ctrl+C to stop\n")
    
    os.chdir(frontend_dir)
    subprocess.run(["npm", "start"])

def run_tests():
    """Run unit tests"""
    backend_dir = Path(__file__).parent / "backend"
    tests_dir = Path(__file__).parent / "tests"
    
    print("🧪 Running Tests...")
    print()
    
    # Run pytest
    os.chdir(tests_dir)
    subprocess.run(["python", "-m", "pytest", "test_*.py", "-v"])

if __name__ == "__main__":
    main()

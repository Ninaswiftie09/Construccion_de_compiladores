@echo off
REM Compiscript Compiler - Setup Script for Windows
REM This script sets up both backend and frontend

echo.
echo 🚀 Compiscript Compiler Setup
echo ==============================
echo.

REM Backend Setup
echo 1️⃣  Setting up backend...
cd backend

REM Create virtual environment
if not exist "venv" (
  echo    Creating virtual environment...
  python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo    Installing Python dependencies...
pip install -q -r requirements.txt

REM Generate ANTLR files
echo    Generating ANTLR parser...
cd grammar
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4
cd ..

echo    ✅ Backend ready!
cd ..

echo.

REM Frontend Setup
echo 2️⃣  Setting up frontend...
cd frontend

REM Install dependencies
echo    Installing Node.js dependencies...
call npm install

echo    ✅ Frontend ready!
cd ..

echo.
echo ✨ Setup complete!
echo.
echo To start the compiler:
echo.
echo PowerShell Terminal 1 ^(Backend^):
echo   cd backend
echo   .\venv\Scripts\Activate.ps1
echo   python server.py
echo.
echo PowerShell Terminal 2 ^(Frontend^):
echo   cd frontend
echo   npm start
echo.
echo The IDE will be available at http://localhost:3000
echo.
pause

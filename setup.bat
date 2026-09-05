@echo off
REM Compiscript Compiler - Setup Script for Windows
REM This script sets up both backend and frontend

echo.
echo 🚀 Compiscript Compiler Setup
echo ==============================
echo.

REM Prepara las dependencias de Python antes de generar el parser.
echo 1️⃣  Setting up backend...
cd backend

REM Aisla las dependencias del proyecto en un entorno virtual.
if not exist "venv" (
  echo    Creating virtual environment...
  python -m venv venv
)

REM Usa los ejecutables del entorno virtual en los siguientes pasos.
call venv\Scripts\activate.bat

REM Instala las dependencias declaradas por el proyecto.
echo    Installing Python dependencies...
pip install -q -r requirements.txt

REM Genera lexer, parser, visitor y listener desde la gramatica.
echo    Generating ANTLR parser...
cd grammar
set ANTLR4_TOOLS_ANTLR_VERSION=4.13.2
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4
cd ..

echo    ✅ Backend ready!
cd ..

echo.

REM Prepara las dependencias de la interfaz React.
echo 2️⃣  Setting up frontend...
cd frontend

REM Instala las dependencias declaradas por el proyecto.
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

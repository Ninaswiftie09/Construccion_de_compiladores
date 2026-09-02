@echo off
REM Generate ANTLR parser files for Compiscript
REM Usage: generate_parser.bat

setlocal enabledelayedexpansion

echo.
echo 🔨 Generating ANTLR Parser for Compiscript
echo ===========================================
echo.

cd /d "%~dp0\backend\grammar"

REM Check if antlr4 is installed
where antlr4 >nul 2>nul
if errorlevel 1 (
  echo ❌ Error: antlr4 not found
  echo.
  echo Please install ANTLR first:
  echo   1. Download antlr-4.14.0-complete.jar from https://www.antlr.org/download/
  echo   2. Add it to PATH or run: java -jar antlr-4.14.0-complete.jar
  exit /b 1
)

echo 📝 Grammar file: Compiscript.g4
echo 🎯 Target language: Python 3
echo.

echo Generating lexer, parser, visitor, and listener...
antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4

echo.
echo ✅ Parser generation complete!
echo.
echo Generated files:
dir *.py | find /C "Lexer" >nul && echo   - CompiscriptLexer.py
dir *.py | find /C "Parser" >nul && echo   - CompiscriptParser.py
dir *.py | find /C "Visitor" >nul && echo   - CompiscriptVisitor.py
dir *.py | find /C "Listener" >nul && echo   - CompiscriptListener.py

pause

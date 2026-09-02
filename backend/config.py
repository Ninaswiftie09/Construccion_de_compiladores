"""
Configuration and settings for the Compiscript Compiler
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
GRAMMAR_DIR = BACKEND_DIR / "grammar"
ANALYZER_DIR = BACKEND_DIR / "analyzer"

# Server settings
SERVER_HOST = os.getenv("COMPILER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("COMPILER_PORT", "8000"))
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Frontend settings
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# ANTLR settings
ANTLR_TARGET_LANGUAGE = "Python3"
ANTLR_GRAMMAR_FILE = GRAMMAR_DIR / "Compiscript.g4"

# Compiler settings
MAX_ERRORS_PER_PHASE = 100  # Limit errors to prevent spam
ENABLE_ERROR_RECOVERY = True

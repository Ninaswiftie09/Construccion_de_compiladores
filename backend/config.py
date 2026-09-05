"""
Valores de referencia para configurar el proyecto.
"""
import os
from pathlib import Path

# Las rutas se calculan desde el archivo para no depender de la terminal.
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
GRAMMAR_DIR = BACKEND_DIR / "grammar"
ANALYZER_DIR = BACKEND_DIR / "analyzer"

# Valores disponibles para consumidores que importen esta configuracion.
SERVER_HOST = os.getenv("COMPILER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("COMPILER_PORT", "8000"))
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Direccion local de referencia para la interfaz.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# La gramatica se genera como clases de Python.
ANTLR_TARGET_LANGUAGE = "Python3"
ANTLR_GRAMMAR_FILE = GRAMMAR_DIR / "Compiscript.g4"

# Valores de referencia; el orquestador aun no consume estas opciones.
MAX_ERRORS_PER_PHASE = 100  # Limite reservado para una futura configuracion del listener
ENABLE_ERROR_RECOVERY = True

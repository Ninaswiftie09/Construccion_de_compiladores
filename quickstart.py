#!/usr/bin/env python3
"""Atajos multiplataforma para preparar, iniciar y probar el proyecto."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def venv_python() -> Path:
    folder = "Scripts" if sys.platform == "win32" else "bin"
    executable = "python.exe" if sys.platform == "win32" else "python"
    return BACKEND / "venv" / folder / executable


def show_help():
    print(
        """Compiscript - comandos disponibles

  python quickstart.py setup       Instala y genera el parser
  python quickstart.py backend     Inicia la API en localhost:8000
  python quickstart.py frontend    Inicia el IDE en localhost:3000
  python quickstart.py test        Ejecuta toda la bateria de pruebas
"""
    )


def setup():
    script = ROOT / ("setup.bat" if sys.platform == "win32" else "setup.sh")
    subprocess.run([str(script)], cwd=ROOT, check=True, shell=sys.platform == "win32")


def start_backend():
    python = venv_python()
    if not python.exists():
        raise SystemExit("Falta el entorno virtual. Ejecuta: python quickstart.py setup")
    if not (BACKEND / "grammar" / "CompiscriptParser.py").exists():
        raise SystemExit("Falta el parser. Ejecuta generate_parser.bat o generate_parser.sh")
    subprocess.run([str(python), "server.py"], cwd=BACKEND, check=True)


def start_frontend():
    if not (FRONTEND / "node_modules").exists():
        raise SystemExit("Faltan dependencias. Ejecuta: python quickstart.py setup")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    subprocess.run([npm, "start"], cwd=FRONTEND, check=True)


def run_tests():
    python = venv_python() if venv_python().exists() else Path(sys.executable)
    subprocess.run([str(python), "-m", "pytest", "-v"], cwd=ROOT, check=True)


def main():
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    actions = {
        "setup": setup,
        "backend": start_backend,
        "frontend": start_frontend,
        "test": run_tests,
        "help": show_help,
        "-h": show_help,
        "--help": show_help,
    }
    action = actions.get(command)
    if action is None:
        show_help()
        raise SystemExit(f"Comando desconocido: {command}")
    action()


if __name__ == "__main__":
    main()

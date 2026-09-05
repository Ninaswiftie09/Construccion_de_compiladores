"""
Modelos de diagnosticos y tokens enviados a la interfaz.
"""
from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    """Identifica la fase que produjo el diagnostico."""
    LEXICAL = "lexical"
    SYNTACTIC = "syntactic"
    SEMANTIC = "semantic"


class CompilationError:
    """Guarda el mensaje y su ubicacion en el codigo fuente."""
    
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        line: int = 0,
        column: int = 0,
        context: Optional[str] = None
    ):
        self.error_type = error_type
        self.message = message
        self.line = line
        self.column = column
        self.context = context
    
    # Convierte el modelo a datos simples para enviarlos como JSON.
    def to_dict(self):
        return {
            "type": self.error_type.value,
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "context": self.context
        }
    
    def __str__(self):
        return f"[{self.error_type.value.upper()}] Line {self.line}:{self.column} - {self.message}"


class Token:
    """Conserva el tipo, lexema y posicion de un token."""
    
    def __init__(
        self,
        token_type: str,
        value: str,
        line: int = 0,
        column: int = 0
    ):
        self.token_type = token_type
        self.value = value
        self.line = line
        self.column = column
    
    # Convierte el modelo a datos simples para enviarlos como JSON.
    def to_dict(self):
        return {
            "type": self.token_type,
            "value": self.value,
            "line": self.line,
            "column": self.column
        }

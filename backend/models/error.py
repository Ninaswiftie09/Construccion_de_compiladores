"""
Error representation model for the Compiscript compiler
"""
from enum import Enum
from typing import Optional


class ErrorType(str, Enum):
    """Types of compilation errors"""
    LEXICAL = "lexical"
    SYNTACTIC = "syntactic"
    SEMANTIC = "semantic"


class CompilationError:
    """Represents a compilation error with location and message"""
    
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
    """Represents a lexical token"""
    
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
    
    def to_dict(self):
        return {
            "type": self.token_type,
            "value": self.value,
            "line": self.line,
            "column": self.column
        }

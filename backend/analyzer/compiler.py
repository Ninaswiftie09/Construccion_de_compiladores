"""
Compiler main module that orchestrates all analysis phases
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from antlr4 import InputStream, CommonTokenFactory, CommonTokenStream, ErrorListener
from antlr4.error.Errors import RecognitionException
from models.error import CompilationError, ErrorType


class CompilationResult:
    """Result of compilation process"""
    
    def __init__(self):
        self.lexical_errors: List[CompilationError] = []
        self.syntactic_errors: List[CompilationError] = []
        self.semantic_errors: List[CompilationError] = []
        self.tokens: List[Dict[str, Any]] = []
        self.ast = None
        self.symbol_table = None
    
    def get_all_errors(self) -> List[CompilationError]:
        """Get all errors from all phases"""
        return self.lexical_errors + self.syntactic_errors + self.semantic_errors
    
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.get_all_errors()) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": not self.has_errors(),
            "lexicalErrors": len(self.lexical_errors),
            "syntacticErrors": len(self.syntactic_errors),
            "semanticErrors": len(self.semantic_errors),
            "totalErrors": len(self.get_all_errors()),
            "errors": [e.to_dict() for e in self.get_all_errors()],
            "tokenCount": len(self.tokens)
        }


class CompilerErrorListener(ErrorListener):
    """Custom error listener for ANTLR that collects errors"""
    
    def __init__(self):
        super().__init__()
        self.errors: List[CompilationError] = []
    
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Called when a syntax error occurs"""
        error = CompilationError(
            ErrorType.SYNTACTIC,
            msg,
            line,
            column,
            str(offendingSymbol) if offendingSymbol else None
        )
        self.errors.append(error)


class Compiler:
    """
    Main compiler class that orchestrates lexical, syntactic, and semantic analysis
    """
    
    def __init__(self):
        self.result = None
    
    def compile(self, source_code: str) -> CompilationResult:
        """
        Compile source code through all analysis phases.
        Returns CompilationResult with all errors and analysis data.
        """
        self.result = CompilationResult()
        
        try:
            # Phase 1: Lexical Analysis
            self._lexical_analysis(source_code)
            
            # Phase 2: Syntactic Analysis
            self._syntactic_analysis(source_code)
            
            # Phase 3: Semantic Analysis (only if no critical errors)
            if len(self.result.syntactic_errors) < 5:  # Allow minor syntactic errors
                self._semantic_analysis(source_code)
        
        except Exception as e:
            self.result.semantic_errors.append(
                CompilationError(
                    ErrorType.SEMANTIC,
                    f"Internal compiler error: {str(e)}",
                    0, 0
                )
            )
        
        return self.result
    
    def _lexical_analysis(self, source_code: str):
        """Phase 1: Lexical Analysis"""
        try:
            from grammar.CompiscriptLexer import CompiscriptLexer
            from antlr4 import InputStream, CommonTokenStream
            
            input_stream = InputStream(source_code)
            lexer = CompiscriptLexer(input_stream)
            
            # Set custom error listener to capture errors
            lexer.removeErrorListeners()
            error_listener = CompilerErrorListener()
            lexer.addErrorListener(error_listener)
            
            # Tokenize
            tokens = lexer.getAllTokens()
            
            # Store tokens
            for token in tokens:
                self.result.tokens.append({
                    "type": lexer.symbolicNames[token.type] if token.type < len(lexer.symbolicNames) else token.type,
                    "value": token.text,
                    "line": token.line,
                    "column": token.column
                })
            
            # Store errors
            self.result.lexical_errors = error_listener.errors
        
        except ImportError:
            self.result.lexical_errors.append(
                CompilationError(
                    ErrorType.LEXICAL,
                    "ANTLR generated files not found. Run: cd grammar && antlr4 -Dlanguage=Python3 -visitor -listener Compiscript.g4",
                    0, 0
                )
            )
    
    def _syntactic_analysis(self, source_code: str):
        """Phase 2: Syntactic Analysis"""
        try:
            from grammar.CompiscriptLexer import CompiscriptLexer
            from grammar.CompiscriptParser import CompiscriptParser
            from antlr4 import InputStream, CommonTokenStream
            
            input_stream = InputStream(source_code)
            lexer = CompiscriptLexer(input_stream)
            stream = CommonTokenStream(lexer)
            parser = CompiscriptParser(stream)
            
            # Set custom error listener
            parser.removeErrorListeners()
            error_listener = CompilerErrorListener()
            parser.addErrorListener(error_listener)
            
            # Parse
            tree = parser.program()
            
            self.result.ast = tree
            self.result.syntactic_errors = error_listener.errors
        
        except ImportError:
            self.result.syntactic_errors.append(
                CompilationError(
                    ErrorType.SYNTACTIC,
                    "ANTLR generated files not found",
                    0, 0
                )
            )
        except Exception as e:
            self.result.syntactic_errors.append(
                CompilationError(
                    ErrorType.SYNTACTIC,
                    str(e),
                    0, 0
                )
            )
    
    def _semantic_analysis(self, source_code: str):
        """Phase 3: Semantic Analysis"""
        try:
            from analyzer.semantic import SemanticAnalyzer
            
            if not self.result.ast:
                return
            
            analyzer = SemanticAnalyzer()
            # TODO: Walk the AST and perform semantic analysis
            
            self.result.semantic_errors = analyzer.get_errors()
            self.result.symbol_table = analyzer.symbol_table
        
        except Exception as e:
            self.result.semantic_errors.append(
                CompilationError(
                    ErrorType.SEMANTIC,
                    f"Semantic analysis error: {str(e)}",
                    0, 0
                )
            )


def compile_file(file_path: str) -> CompilationResult:
    """Compile a file and return the result"""
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    compiler = Compiler()
    return compiler.compile(source_code)

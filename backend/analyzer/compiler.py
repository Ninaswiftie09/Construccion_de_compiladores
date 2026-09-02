"""Orquestador de las tres fases de analisis de Compiscript."""

from pathlib import Path
from typing import Any, Optional

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import TerminalNode

from models.error import CompilationError, ErrorType


class CompilationResult:
    """Resultado serializable de una compilacion."""

    def __init__(self):
        self.lexical_errors: list[CompilationError] = []
        self.syntactic_errors: list[CompilationError] = []
        self.semantic_errors: list[CompilationError] = []
        self.tokens: list[dict[str, Any]] = []
        self.ast: Optional[dict[str, Any]] = None
        self.symbol_table: Optional[dict[str, Any]] = None
        self._parse_tree = None

    def get_all_errors(self) -> list[CompilationError]:
        return self.lexical_errors + self.syntactic_errors + self.semantic_errors

    def has_errors(self) -> bool:
        return bool(self.get_all_errors())

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": not self.has_errors(),
            "lexicalErrors": len(self.lexical_errors),
            "syntacticErrors": len(self.syntactic_errors),
            "semanticErrors": len(self.semantic_errors),
            "totalErrors": len(self.get_all_errors()),
            "errors": [error.to_dict() for error in self.get_all_errors()],
            "tokenCount": len(self.tokens),
            "tokens": self.tokens,
            "ast": self.ast,
            "symbolTable": self.symbol_table,
        }


class CompilerErrorListener(ErrorListener):
    """Acumula errores sin detener al lexer ni al parser."""

    def __init__(self, error_type: ErrorType):
        super().__init__()
        self.error_type = error_type
        self.errors: list[CompilationError] = []
        self._keys: set[tuple] = set()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, error):
        context = getattr(offendingSymbol, "text", None)
        key = (line, column, msg, context)
        if key in self._keys:
            return
        self._keys.add(key)
        self.errors.append(CompilationError(self.error_type, msg, line, column, context))


class Compiler:
    """Ejecuta analisis lexico, sintactico y semantico."""

    def __init__(self):
        self.result: Optional[CompilationResult] = None

    def compile(self, source_code: str) -> CompilationResult:
        self.result = CompilationResult()
        self._lexical_analysis(source_code)
        self._syntactic_analysis(source_code)
        # El arbol recuperado todavia permite encontrar errores semanticos utiles.
        if self.result._parse_tree is not None:
            self._semantic_analysis()
        return self.result

    def _lexical_analysis(self, source_code: str):
        try:
            from grammar.CompiscriptLexer import CompiscriptLexer

            lexer = CompiscriptLexer(InputStream(source_code))
            listener = CompilerErrorListener(ErrorType.LEXICAL)
            lexer.removeErrorListeners()
            lexer.addErrorListener(listener)
            tokens = lexer.getAllTokens()
            for token in tokens:
                token_name = (
                    lexer.symbolicNames[token.type]
                    if 0 <= token.type < len(lexer.symbolicNames)
                    else str(token.type)
                )
                self.result.tokens.append(
                    {
                        "type": token_name or lexer.literalNames[token.type],
                        "value": token.text,
                        "line": token.line,
                        "column": token.column,
                    }
                )
            self.result.lexical_errors = listener.errors
        except ImportError:
            self.result.lexical_errors.append(
                CompilationError(
                    ErrorType.LEXICAL,
                    "No se encontro el lexer generado por ANTLR. Ejecuta generate_parser.bat o generate_parser.sh.",
                )
            )
        except Exception as error:
            self.result.lexical_errors.append(CompilationError(ErrorType.LEXICAL, f"Fallo del lexer: {error}"))

    def _syntactic_analysis(self, source_code: str):
        try:
            from grammar.CompiscriptLexer import CompiscriptLexer
            from grammar.CompiscriptParser import CompiscriptParser

            lexer = CompiscriptLexer(InputStream(source_code))
            lexer.removeErrorListeners()
            stream = CommonTokenStream(lexer)
            parser = CompiscriptParser(stream)
            listener = CompilerErrorListener(ErrorType.SYNTACTIC)
            parser.removeErrorListeners()
            parser.addErrorListener(listener)
            tree = parser.program()
            self.result._parse_tree = tree
            self.result.ast = self._tree_to_dict(tree, parser)
            self.result.syntactic_errors = listener.errors
        except ImportError:
            self.result.syntactic_errors.append(
                CompilationError(ErrorType.SYNTACTIC, "No se encontro el parser generado por ANTLR.")
            )
        except Exception as error:
            self.result.syntactic_errors.append(CompilationError(ErrorType.SYNTACTIC, f"Fallo del parser: {error}"))

    def _tree_to_dict(self, node, parser) -> dict[str, Any]:
        if isinstance(node, TerminalNode):
            token = node.getSymbol()
            return {
                "name": "token",
                "text": node.getText(),
                "line": getattr(token, "line", 0),
                "children": [],
            }
        rule_index = node.getRuleIndex() if hasattr(node, "getRuleIndex") else -1
        name = parser.ruleNames[rule_index] if 0 <= rule_index < len(parser.ruleNames) else type(node).__name__
        return {
            "name": name,
            "text": "",
            "line": getattr(getattr(node, "start", None), "line", 0),
            "children": [self._tree_to_dict(node.getChild(index), parser) for index in range(node.getChildCount())],
        }

    def _semantic_analysis(self):
        try:
            from analyzer.semantic import SemanticAnalyzer

            analyzer = SemanticAnalyzer()
            analyzer.visit(self.result._parse_tree)
            self.result.semantic_errors = analyzer.get_errors()
            self.result.symbol_table = analyzer.symbol_table.to_dict()
        except Exception as error:
            self.result.semantic_errors.append(
                CompilationError(ErrorType.SEMANTIC, f"Fallo interno del analisis semantico: {error}")
            )


def compile_file(file_path: str) -> CompilationResult:
    source_code = Path(file_path).read_text(encoding="utf-8")
    return Compiler().compile(source_code)

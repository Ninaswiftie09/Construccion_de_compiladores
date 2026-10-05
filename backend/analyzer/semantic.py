"""Recorrido semantico del arbol generado por ANTLR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from grammar.CompiscriptVisitor import CompiscriptVisitor
from models.error import CompilationError, ErrorType
from models.types import (
    DataType,
    NULL_TYPE,
    UNKNOWN_TYPE,
    VOID_TYPE,
    Symbol,
    TypeInfo,
    ensure_type_info,
)
from analyzer.symbol_table import SymbolTable


@dataclass
class ExprInfo:
    type_info: TypeInfo = UNKNOWN_TYPE
    symbol: Optional[Symbol] = None
    assignable: bool = False
    array_length: Optional[int] = None
    indexed: bool = False


class SemanticAnalyzer(CompiscriptVisitor):
    """Valida tipos, alcances, funciones, flujo, clases y arreglos."""

    def __init__(self):
        super().__init__()
        self.symbol_table = SymbolTable()
        self.errors: list[CompilationError] = []
        self._error_keys: set[tuple] = set()
        self._declaration_symbols: dict[int, Symbol] = {}
        self._classes: dict[int, Symbol] = {}
        self._function_stack: list[Symbol] = []
        self._class_stack: list[Symbol] = []
        self._class_scopes = {}
        self._field_declarations = {}
        self._resolving_fields = set()
        self._resolved_fields = set()

    # ----- Utilidades -----

    def visit(self, tree):
        # ANTLR puede dejar hijos ausentes al recuperar una sentencia incompleta.
        if tree is None:
            return ExprInfo()
        if hasattr(tree, "getRuleIndex") and not getattr(tree, "children", None):
            return ExprInfo()  # Regla incompleta durante la recuperacion de ANTLR.
        # Una declaracion sin nombre ya tiene diagnostico sintactico del parser.
        if type(tree).__name__ in ("VariableDeclarationContext", "ConstantDeclarationContext") and tree.Identifier() is None:
            return None
        previous = getattr(self.symbol_table, "context", None)
        self.symbol_table.context = tree
        try:
            result = super().visit(tree)
            if isinstance(result, ExprInfo) and result.symbol:
                tree._resolved_symbol = result.symbol
            return result
        finally:
            self.symbol_table.context = previous

    def visitChildren(self, node):
        # Pasamos cada hijo por visit para aplicar tambien la recuperacion local.
        result = self.defaultResult()
        for child in node.getChildren():
            if not self.shouldVisitNextChild(node, result):
                break
            result = self.aggregateResult(result, self.visit(child))
        return result

    def add_error(self, message: str, line: int = 0, column: int = 0, context: Optional[str] = None):
        # La llave evita repetir el mismo diagnostico durante la recuperacion.
        key = (message, line, column, context)
        if key in self._error_keys:
            return
        self._error_keys.add(key)
        self.errors.append(CompilationError(ErrorType.SEMANTIC, message, line, column, context))

    def _error(self, ctx, message: str, context: Optional[str] = None):
        token = getattr(ctx, "start", None)
        self.add_error(message, getattr(token, "line", 0), getattr(token, "column", 0), context)

    def get_errors(self) -> list[CompilationError]:
        return self.errors

    # Normaliza el resultado de los hijos para que todos usen ExprInfo.
    def _expr(self, value) -> ExprInfo:
        if isinstance(value, ExprInfo):
            return value
        if isinstance(value, TypeInfo):
            return ExprInfo(value)
        if isinstance(value, DataType):
            return ExprInfo(TypeInfo(value))
        return ExprInfo()

    # Separa el tipo base y la cantidad de dimensiones del arreglo.
    def _type_from_text(self, text: str) -> TypeInfo:
        dimensions = text.count("[]")
        base_name = text.replace("[]", "")
        builtins = {
            "integer": DataType.INTEGER,
            "float": DataType.FLOAT,
            "string": DataType.STRING,
            "boolean": DataType.BOOLEAN,
            "void": DataType.VOID,
        }
        result = TypeInfo(builtins[base_name]) if base_name in builtins else TypeInfo.object_of(base_name)
        for _ in range(dimensions):
            result = TypeInfo.array_of(result)
        return result

    def _type_from_annotation(self, annotation) -> TypeInfo:
        if annotation is None:
            return UNKNOWN_TYPE
        accessor = getattr(annotation, "type_", None) or getattr(annotation, "type", None)
        type_ctx = accessor() if accessor else annotation
        # No interpretar tokens sinteticos de recuperacion como nombres de clase.
        def damaged(node):
            if node is None:
                return True
            if hasattr(node, "getSymbol"):
                return node.getSymbol().tokenIndex < 0 or type(node).__name__ == "ErrorNodeImpl"
            return any(damaged(child) for child in node.getChildren())
        if type_ctx is None or not type_ctx.getText() or damaged(type_ctx):
            return UNKNOWN_TYPE
        result = self._type_from_text(type_ctx.getText())

        def resolve(value):
            if value.base == DataType.ARRAY:
                return TypeInfo.array_of(resolve(value.element_type))
            if value.base == DataType.OBJECT:
                symbol = self._lookup_class(value.class_name)
                if symbol is None:
                    self._error(annotation, f"La clase '{value.class_name}' no existe en este alcance")
                    return UNKNOWN_TYPE
                return symbol.data_type
            return value

        return resolve(result)

    # Conserva el orden de parametros para comparar argumentos por posicion.
    def _parameters(self, ctx) -> list[tuple[str, TypeInfo]]:
        parameters = ctx.parameters()
        if parameters is None:
            return []
        return [
            (parameter.Identifier().getText(), self._type_from_annotation(parameter.type_()))
            for parameter in parameters.parameter()
        ]

    # Guarda la firma antes del cuerpo para permitir llamadas recursivas.
    def _declare_function(self, ctx, owner: Optional[Symbol] = None) -> Symbol:
        name = ctx.Identifier().getText()
        return_type = self._type_from_annotation(ctx.type_()) if ctx.type_() else VOID_TYPE
        if name == "constructor":
            return_type = VOID_TYPE
        symbol = Symbol(name, "method" if owner else "function", return_type, ctx.start.line, ctx.start.column)
        symbol.parameters = self._parameters(ctx)
        symbol.return_type = return_type
        current = self.symbol_table.lookup_in_current_scope(name)
        if current:
            self._error(ctx, f"El identificador '{name}' ya fue declarado en este alcance")
        else:
            self.symbol_table.define_symbol(symbol)
        if owner:
            if name in owner.attributes:
                self._error(ctx, f"El miembro '{name}' ya fue declarado en la clase '{owner.name}'")
            else:
                owner.attributes[name] = symbol
        self._declaration_symbols[id(ctx)] = symbol
        return symbol

    # Registra el nombre y una identidad propia para esta clase.
    def _declare_class(self, ctx) -> Symbol:
        name = ctx.Identifier(0).getText()
        symbol = Symbol(name, "class", TypeInfo.object_of(name), ctx.start.line, ctx.start.column, is_initialized=True)
        symbol.data_type = TypeInfo.object_of(name, id(symbol))
        identifiers = ctx.Identifier()
        if len(identifiers) > 1:
            symbol.base_class = identifiers[1].getText()
        current = self.symbol_table.lookup_in_current_scope(name)
        if current:
            self._error(ctx, f"El identificador '{name}' ya fue declarado en este alcance")
        else:
            self.symbol_table.define_symbol(symbol)
            self._classes[id(symbol)] = symbol
        self._declaration_symbols[id(ctx)] = symbol
        return symbol

    def _predeclare(self, statements):
        # Primero las clases: las firmas pueden usar tipos declarados mas adelante.
        for statement in statements or []:
            declaration = statement.classDeclaration() if hasattr(statement, "classDeclaration") else None
            if declaration is not None and id(declaration) not in self._declaration_symbols:
                self._declare_class(declaration)
        for statement in statements or []:
            function = statement.functionDeclaration() if hasattr(statement, "functionDeclaration") else None
            class_decl = statement.classDeclaration() if hasattr(statement, "classDeclaration") else None
            if function is not None and id(function) not in self._declaration_symbols:
                self._declare_function(function)
            elif class_decl is not None and id(class_decl) not in self._declaration_symbols:
                self._declare_class(class_decl)
        # Cada enlace de herencia queda ligado al alcance de su declaracion.
        for statement in statements or []:
            declaration = statement.classDeclaration() if hasattr(statement, "classDeclaration") else None
            if declaration is not None:
                symbol = self._declaration_symbols[id(declaration)]
                symbol.base_symbol = self._lookup_class(symbol.base_class)
        # Las firmas y campos de TODAS las clases existen antes de los cuerpos.
        for statement in statements or []:
            declaration = statement.classDeclaration() if hasattr(statement, "classDeclaration") else None
            if declaration is not None:
                self._prepare_class(declaration)

    def _prepare_class(self, ctx):
        symbol = self._declaration_symbols[id(ctx)]
        if id(symbol) in self._class_scopes:
            return
        previous = getattr(self.symbol_table, "context", None)
        self.symbol_table.context = ctx
        scope = self.symbol_table.enter_scope("class", symbol.name)
        self.symbol_table.context = previous
        self._class_scopes[id(symbol)] = scope
        scope.class_symbol = symbol
        self.symbol_table.define_symbol(Symbol("this", "variable", symbol.data_type, is_initialized=True))
        try:
            for member in ctx.classMember():
                function = member.functionDeclaration()
                if function is not None:
                    self._declare_function(function, symbol)
                    continue
                variable, constant = member.variableDeclaration(), member.constantDeclaration()
                declaration = variable or constant
                if declaration is None or declaration.Identifier() is None:
                    continue
                name = declaration.Identifier().getText()
                field = Symbol(name, "attribute", self._type_from_annotation(declaration.typeAnnotation()),
                               declaration.start.line, declaration.start.column, constant is not None,
                               constant is not None or variable.initializer() is not None)
                if name in symbol.attributes:
                    self._error(declaration, f"El miembro '{name}' ya fue declarado en la clase '{symbol.name}'")
                else:
                    symbol.attributes[name] = field
                    self.symbol_table.define_symbol(field)
                self._declaration_symbols[id(declaration)] = field
                self._field_declarations[id(field)] = (declaration, symbol, scope)
        finally:
            self.symbol_table.exit_scope()

    def _resolve_field(self, field):
        entry = self._field_declarations.get(id(field))
        if entry is None or id(field) in self._resolved_fields:
            return
        declaration, owner, scope = entry
        if id(field) in self._resolving_fields:
            self._error(declaration, f"Inicializacion circular del atributo '{field.name}'")
            return
        self._resolving_fields.add(id(field))
        saved_scope = self.symbol_table.current_scope
        self.symbol_table.current_scope = scope
        self._class_stack.append(owner)
        try:
            self.visit(declaration)
            self._resolved_fields.add(id(field))
        finally:
            self._class_stack.pop()
            self.symbol_table.current_scope = saved_scope
            self._resolving_fields.remove(id(field))

    # Busca solamente la clase visible desde el alcance actual.
    def _lookup_value(self, name):
        scope = self.symbol_table.current_scope
        while scope is not None:
            symbol = scope.lookup_in_scope(name)
            if symbol is not None:
                return symbol
            owner = getattr(scope, "class_symbol", None)
            if owner is not None:
                inherited = self._lookup_member(owner.base_symbol, name)
                if inherited is not None:
                    return inherited
            scope = scope.parent
        return None

    def _lookup_class(self, name: Optional[str]) -> Optional[Symbol]:
        symbol = self.symbol_table.lookup_symbol(name or "")
        return symbol if symbol and symbol.symbol_type == "class" else None

    def _class_for_type(self, value: TypeInfo) -> Optional[Symbol]:
        # El tipo conserva su clase original aunque otro bloque oculte el nombre.
        return self._classes.get(value.class_id) if value.class_id else self._lookup_class(value.class_name)

    # Busca primero en la clase y despues en sus ancestros.
    def _lookup_member(self, class_symbol: Optional[Symbol], name: str) -> Optional[Symbol]:
        visited: set[int] = set()
        while class_symbol and id(class_symbol) not in visited:
            visited.add(id(class_symbol))
            if name in class_symbol.attributes:
                member = class_symbol.attributes[name]
                if member.symbol_type == "attribute" and member.data_type.is_unknown():
                    self._resolve_field(member)
                return member
            class_symbol = class_symbol.base_symbol
        return None

    # La compatibilidad considera tipos, arreglos y herencia.
    def _is_assignable(self, target: TypeInfo, value: TypeInfo) -> bool:
        if target.is_compatible_with(value):
            return True
        if target.base == DataType.OBJECT and value.base == DataType.OBJECT:
            current = self._class_for_type(value)
            visited = set()
            while current and current.base_symbol and id(current) not in visited:
                visited.add(id(current))
                if current.base_symbol.data_type == target:
                    return True
                current = current.base_symbol
        return False

    def _check_assignment(self, target: ExprInfo, value: ExprInfo, ctx):
        if target.type_info.is_unknown() and target.symbol is None:
            return  # Ya se reporto la causa; no agregamos errores derivados.
        if not target.assignable or target.symbol is None:
            self._error(ctx, "El lado izquierdo de la asignacion no es modificable")
            return
        if target.symbol.is_const:
            self._error(ctx, f"No se puede reasignar la constante '{target.symbol.name}'")
        if (getattr(target.symbol, "type_pending", False) and not target.indexed
                and not value.type_info.is_unknown() and value.type_info != NULL_TYPE):
            target.symbol.data_type = value.type_info
            target.symbol.type_pending = False
            target.type_info = value.type_info
        if not self._is_assignable(target.type_info, value.type_info):
            self._error(ctx, f"No se puede asignar {value.type_info} a {target.type_info}")
        target.symbol.is_initialized = True
        # Solo una asignacion al arreglo completo cambia su longitud conocida.
        if target.indexed:
            self._forget_lengths()
        elif target.type_info.base == DataType.ARRAY:
            self._forget_lengths()  # Una referencia compartida puede ser un alias.
            target.symbol.array_length = value.array_length

    # Compara cantidad y tipos de argumentos contra la firma guardada.
    def _check_call(self, symbol: Optional[Symbol], arguments: list[ExprInfo], ctx) -> ExprInfo:
        if symbol is None or symbol.symbol_type not in ("function", "method"):
            self._error(ctx, "La expresion invocada no es una funcion")
            return ExprInfo()
        if len(arguments) != len(symbol.parameters):
            self._error(ctx, f"La funcion '{symbol.name}' espera {len(symbol.parameters)} argumentos y recibio {len(arguments)}")
        for index, (argument, (_, expected)) in enumerate(zip(arguments, symbol.parameters), start=1):
            if not self._is_assignable(expected, argument.type_info):
                self._error(ctx, f"El argumento {index} de '{symbol.name}' debe ser {expected}, no {argument.type_info}")
        return ExprInfo(symbol.return_type)

    # Visita todos los argumentos, incluso si alguno tiene un error.
    def _arguments(self, ctx) -> list[ExprInfo]:
        if ctx is None:
            return []
        return [self._expr(self.visit(expression)) for expression in ctx.expression()]

    # Este recorrido combina operandos de izquierda a derecha.
    def _binary(self, ctx, validator) -> ExprInfo:
        left = self._expr(self.visit(ctx.getChild(0)))
        index = 1
        while index < ctx.getChildCount():
            operator = ctx.getChild(index).getText()
            right = self._expr(self.visit(ctx.getChild(index + 1)))
            left = validator(left, right, operator, ctx)
            index += 2
        return left

    # Sigue revisando sentencias aunque una anterior ya haya terminado el flujo.
    def _visit_statement_list(self, statements):
        self._predeclare(statements)
        terminated = False
        for statement in statements or []:
            if terminated:
                self._error(statement, "Codigo inalcanzable despues de una sentencia de salida")
            self.visit(statement)
            terminated = terminated or self._terminates(statement)

    def _terminates(self, node, returns_only=False):
        # Un if solo corta todos los caminos cuando ambas ramas terminan.
        if node is None:
            return False
        if hasattr(node, "returnStatement"):
            if node.returnStatement():
                return True
            if node.breakStatement() or node.continueStatement():
                return not returns_only
            if node.block():
                return self._terminates(node.block(), returns_only)
            branch = node.ifStatement()
            if branch:
                return len(branch.block()) == 2 and all(self._terminates(block, returns_only) for block in branch.block())
            guarded = node.tryCatchStatement()
            if guarded:
                return all(self._terminates(block, returns_only) for block in guarded.block())
        elif hasattr(node, "statement"):
            for statement in node.statement():
                if self._terminates(statement, returns_only):
                    return True
                if self._terminates(statement):
                    return False
        return False

    def _forget_lengths(self):
        # Sin ejecutar el programa, una rama o llamada puede cambiar un arreglo.
        def clear(scope):
            for symbol in scope.symbols.values():
                symbol.array_length = None
            for child in scope.child_scopes:
                clear(child)
        clear(self.symbol_table.global_scope)

    # ----- Programa y declaraciones -----

    # El programa empieza en el alcance global de la tabla.
    def visitProgram(self, ctx):
        self._visit_statement_list(ctx.statement())
        return None

    # Cada bloque crea un entorno y al salir recupera el anterior.
    def visitBlock(self, ctx):
        self.symbol_table.enter_scope("block")
        self._visit_statement_list(ctx.statement())
        self.symbol_table.exit_scope()
        return None

    # Usa la anotacion si existe; de lo contrario infiere el tipo inicial.
    def visitVariableDeclaration(self, ctx):
        name = ctx.Identifier().getText()
        initializer = ctx.initializer()
        value = self._expr(self.visit(initializer.expression())) if initializer else None
        declared = self._type_from_annotation(ctx.typeAnnotation())
        inferred = value.type_info if value else UNKNOWN_TYPE
        final_type = inferred if declared.is_unknown() else declared
        symbol = self._declaration_symbols.get(id(ctx))
        if symbol is None:
            symbol = Symbol(name, "variable", final_type, ctx.start.line, ctx.start.column, is_initialized=value is not None)
            if not self.symbol_table.define_symbol(symbol):
                self._error(ctx, f"La variable '{name}' ya fue declarada en este alcance")
                return None
        else:
            symbol.data_type = final_type
            symbol.is_initialized = value is not None
        symbol.type_pending = ctx.typeAnnotation() is None and final_type.is_unknown() and value is None
        if value and not self._is_assignable(final_type, value.type_info):
            self._error(ctx, f"La variable '{name}' es {final_type}, pero recibe {value.type_info}")
        symbol.array_length = value.array_length if value else None
        if value and value.symbol and final_type.base == DataType.ARRAY:
            self._forget_lengths()
        return None

    # Comprueba la inicializacion y registra que no se puede reasignar.
    def visitConstantDeclaration(self, ctx):
        name = ctx.Identifier().getText()
        value = self._expr(self.visit(ctx.expression()))
        if ctx.expression() is None:
            self._error(ctx, f"La constante '{name}' requiere un inicializador")
        declared = self._type_from_annotation(ctx.typeAnnotation())
        final_type = value.type_info if declared.is_unknown() else declared
        symbol = self._declaration_symbols.get(id(ctx))
        if symbol is None:
            symbol = Symbol(name, "constant", final_type, ctx.start.line, ctx.start.column, True, True)
            if not self.symbol_table.define_symbol(symbol):
                self._error(ctx, f"La constante '{name}' ya fue declarada en este alcance")
                return None
        else:
            symbol.data_type = final_type
            symbol.is_initialized = True
        if not self._is_assignable(final_type, value.type_info):
            self._error(ctx, f"La constante '{name}' es {final_type}, pero recibe {value.type_info}")
        symbol.array_length = value.array_length
        symbol.is_initialized = ctx.expression() is not None
        if value.symbol and final_type.base == DataType.ARRAY:
            self._forget_lengths()
        return None

    # Los parametros y retornos se validan dentro del entorno de la funcion.
    def visitFunctionDeclaration(self, ctx):
        self._forget_lengths()
        symbol = self._declaration_symbols.get(id(ctx)) or self._declare_function(ctx)
        self.symbol_table.enter_scope("function", symbol.name)
        self._function_stack.append(symbol)
        for name, data_type in symbol.parameters:
            parameter = Symbol(name, "parameter", data_type, ctx.start.line, ctx.start.column, is_initialized=True)
            if not self.symbol_table.define_symbol(parameter):
                self._error(ctx, f"El parametro '{name}' esta duplicado en '{symbol.name}'")
        self.visit(ctx.block())
        self._function_stack.pop()
        self.symbol_table.exit_scope()
        if symbol.return_type != VOID_TYPE and symbol.name != "constructor" and not self._terminates(ctx.block(), returns_only=True):
            self._error(ctx, f"La funcion '{symbol.name}' debe retornar {symbol.return_type}")
        self._forget_lengths()
        return None

    # Comprueba la herencia y registra atributos y metodos antes de sus cuerpos.
    def visitClassDeclaration(self, ctx):
        symbol = self._declaration_symbols.get(id(ctx)) or self._declare_class(ctx)
        if symbol.base_class:
            parent = symbol.base_symbol
            if parent is None:
                self._error(ctx, f"La clase base '{symbol.base_class}' no existe")
            elif parent is symbol:
                self._error(ctx, f"La clase '{symbol.name}' no puede heredarse a si misma")
            else:
                visited = {id(symbol)}
                while parent:
                    if id(parent) in visited:
                        self._error(ctx, f"Herencia circular en la clase '{symbol.name}'")
                        break
                    visited.add(id(parent))
                    parent = parent.base_symbol
        self._prepare_class(ctx)
        scope = self._class_scopes[id(symbol)]
        self.symbol_table.current_scope = scope
        self.symbol_table.scopes_stack.append(scope)
        self._class_stack.append(symbol)
        try:
            # Tipar campos antes de cuerpos; tambien admite campos posteriores al metodo.
            for member in ctx.classMember():
                declaration = member.variableDeclaration() or member.constantDeclaration()
                if declaration is not None and id(declaration) in self._declaration_symbols:
                    self._resolve_field(self._declaration_symbols[id(declaration)])
            for name, member in symbol.attributes.items():
                inherited = self._lookup_member(symbol.base_symbol, name)
                if inherited is None or name == "constructor":
                    continue
                if member.symbol_type != inherited.symbol_type:
                    self._error(ctx, f"El miembro '{name}' cambia la clase de miembro heredado")
                elif member.symbol_type == "method":
                    same_parameters = [t for _, t in member.parameters] == [t for _, t in inherited.parameters]
                    if not same_parameters or not self._is_assignable(inherited.return_type, member.return_type):
                        self._error(ctx, f"La sobrescritura de '{name}' tiene una firma incompatible con la clase base")
                elif member.data_type != inherited.data_type or member.is_const != inherited.is_const:
                    self._error(ctx, f"El atributo heredado '{name}' debe conservar su tipo y mutabilidad")
            for member in ctx.classMember():
                if member.functionDeclaration():
                    self.visit(member.functionDeclaration())
        finally:
            self._class_stack.pop()
            self.symbol_table.exit_scope()
        return None

    # ----- Sentencias -----

    # Resuelve el destino antes de comparar el tipo que recibe.
    def visitAssignment(self, ctx):
        expressions = ctx.expression()
        if len(expressions) == 1:
            name = ctx.Identifier().getText()
            symbol = self._lookup_value(name)
            if symbol is None:
                self._error(ctx, f"La variable '{name}' no fue declarada")
                target = ExprInfo()
            else:
                target = ExprInfo(symbol.data_type, symbol, symbol.symbol_type in ("variable", "constant", "parameter", "attribute"))
            value = self._expr(self.visit(expressions[0]))
        else:
            owner = self._expr(self.visit(expressions[0]))
            member_name = ctx.Identifier().getText()
            member = self._lookup_member(self._class_for_type(owner.type_info), member_name)
            if member is None and not owner.type_info.is_unknown():
                self._error(ctx, f"El objeto {owner.type_info} no tiene el miembro '{member_name}'")
            target = ExprInfo(member.data_type, member, member.symbol_type == "attribute") if member else ExprInfo()
            value = self._expr(self.visit(expressions[-1]))
        self._check_assignment(target, value, ctx)
        ctx._target_symbol = target.symbol
        return None

    # Una expresion aislada tambien puede contener llamadas o errores.
    def visitExpressionStatement(self, ctx):
        self.visit(ctx.expression())
        return None

    # Solo analiza el argumento; no ejecuta el print del programa fuente.
    def visitPrintStatement(self, ctx):
        self.visit(ctx.expression())
        return None

    # Las estructuras de control requieren una expresion booleana.
    def _check_condition(self, expression, ctx, owner: str):
        condition = self._expr(self.visit(expression))
        if condition.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"La condicion de '{owner}' debe ser boolean, no {condition.type_info}")

    # Revisa ambas ramas porque el analizador no ejecuta la condicion.
    def visitIfStatement(self, ctx):
        self._forget_lengths()
        self._check_condition(ctx.expression(), ctx, "if")
        for block in ctx.block():
            self.visit(block)
        self._forget_lengths()
        return None

    # El entorno del ciclo habilita break y continue dentro del cuerpo.
    def visitWhileStatement(self, ctx):
        self._forget_lengths()
        self._check_condition(ctx.expression(), ctx, "while")
        self.symbol_table.enter_scope("while")
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        self._forget_lengths()
        return None

    # El bloque tiene su propio alcance; la condicion se revisa fuera de el.
    def visitDoWhileStatement(self, ctx):
        self._forget_lengths()
        self.symbol_table.enter_scope("do-while")
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        self._check_condition(ctx.expression(), ctx, "do-while")
        self._forget_lengths()
        return None

    # La variable inicial solo es visible dentro de este for.
    def visitForStatement(self, ctx):
        self._forget_lengths()
        self.symbol_table.enter_scope("for")
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())
        # El ultimo punto y coma separa la condicion de la actualizacion opcional.
        # La posicion del hijo funciona incluso si ANTLR inserto un ';' sin tokenIndex.
        semicolons = [index for index, child in enumerate(ctx.children or [])
                      if hasattr(child, "symbol") and
                      0 <= child.symbol.type < len(ctx.parser.literalNames) and
                      ctx.parser.literalNames[child.symbol.type] == "';'"]
        boundary = semicolons[-1] if semicolons else None
        for expression in ctx.expression():
            if boundary is not None and ctx.children.index(expression) < boundary:
                self._check_condition(expression, ctx, "for")
            else:
                self.visit(expression)
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        self._forget_lengths()
        return None

    # El iterador toma el tipo de los elementos de la coleccion.
    def visitForeachStatement(self, ctx):
        self._forget_lengths()
        collection = self._expr(self.visit(ctx.expression()))
        if collection.type_info.base not in (DataType.ARRAY, DataType.UNKNOWN):
            self._error(ctx, f"foreach requiere un arreglo, no {collection.type_info}")
        item_type = collection.type_info.element_type or UNKNOWN_TYPE
        self.symbol_table.enter_scope("foreach")
        name = ctx.Identifier().getText()
        self.symbol_table.define_symbol(Symbol(name, "variable", item_type, ctx.start.line, ctx.start.column, is_initialized=True))
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        self._forget_lengths()
        return None

    # Consulta si hay un ciclo dentro de la misma funcion.
    def visitBreakStatement(self, ctx):
        if not self.symbol_table.is_in_breakable():
            self._error(ctx, "'break' solo puede usarse dentro de un ciclo o switch")
        return None

    # Continue necesita un ciclo accesible sin cruzar otra funcion.
    def visitContinueStatement(self, ctx):
        if not self.symbol_table.is_in_loop():
            self._error(ctx, "'continue' solo puede usarse dentro de un ciclo")
        return None

    # La cima de la pila indica a que funcion pertenece este retorno.
    def visitReturnStatement(self, ctx):
        if not self._function_stack:
            self._error(ctx, "'return' solo puede usarse dentro de una funcion")
            if ctx.expression():
                self.visit(ctx.expression())
            return None
        value = self._expr(self.visit(ctx.expression())) if ctx.expression() else ExprInfo(VOID_TYPE)
        expected = self._function_stack[-1].return_type
        if not self._is_assignable(expected, value.type_info):
            self._error(ctx, f"El retorno debe ser {expected}, no {value.type_info}")
        return None

    # El identificador del error solo existe dentro del catch.
    def visitTryCatchStatement(self, ctx):
        self._forget_lengths()
        self.visit(ctx.block(0))
        self.symbol_table.enter_scope("catch")
        if ctx.Identifier() is not None:
            name = ctx.Identifier().getText()
            self.symbol_table.define_symbol(Symbol(name, "variable", UNKNOWN_TYPE, ctx.start.line, ctx.start.column, is_initialized=True))
        self.visit(ctx.block(1))
        self.symbol_table.exit_scope()
        self._forget_lengths()
        return None

    # Cada case debe ser compatible con el valor del switch.
    def visitSwitchStatement(self, ctx):
        self._forget_lengths()
        switch_value = self._expr(self.visit(ctx.expression()))
        if switch_value.type_info.base not in (DataType.BOOLEAN, DataType.INTEGER, DataType.FLOAT, DataType.STRING, DataType.UNKNOWN):
            self._error(ctx, "La condicion de 'switch' debe ser un valor escalar")
        self.symbol_table.enter_scope("switch")
        for case in ctx.switchCase():
            case_type = self._expr(self.visit(case.expression())).type_info
            if not switch_value.type_info.is_comparable(case_type):
                self._error(case, f"El case {case_type} no es compatible con {switch_value.type_info}")
            self._visit_statement_list(case.statement())
        if ctx.defaultCase():
            self._visit_statement_list(ctx.defaultCase().statement())
        self.symbol_table.exit_scope()
        self._forget_lengths()
        return None

    # ----- Expresiones -----

    def visitExpression(self, ctx):
        return self._expr(self.visit(ctx.assignmentExpr()))

    # Una asignacion usada como expresion conserva el tipo del valor asignado.
    def visitAssignExpr(self, ctx):
        atom = ctx.lhs.primaryAtom()
        if not ctx.lhs.suffixOp() and type(atom).__name__ == "IdentifierExprContext":
            name = atom.Identifier().getText()
            symbol = self._lookup_value(name)
            if symbol is None:
                self._error(ctx, f"El identificador '{name}' no fue declarado")
                target = ExprInfo()
            else:
                ctx.lhs._resolved_symbol = symbol
                target = ExprInfo(symbol.data_type, symbol, symbol.symbol_type in ("variable", "constant", "parameter", "attribute"))
        else:
            target = self._expr(self.visit(ctx.lhs))
        value = self._expr(self.visit(ctx.assignmentExpr()))
        self._check_assignment(target, value, ctx)
        return value

    # Localiza el miembro y comprueba que sea un atributo modificable.
    def visitPropertyAssignExpr(self, ctx):
        owner = self._expr(self.visit(ctx.lhs))
        name = ctx.Identifier().getText()
        member = self._lookup_member(self._class_for_type(owner.type_info), name)
        if member is None and not owner.type_info.is_unknown():
            self._error(ctx, f"El objeto {owner.type_info} no tiene el miembro '{name}'")
        target = ExprInfo(member.data_type, member, member.symbol_type == "attribute") if member else ExprInfo()
        value = self._expr(self.visit(ctx.assignmentExpr()))
        self._check_assignment(target, value, ctx)
        return value

    # Delega en la siguiente regla de precedencia sin cambiar el tipo.
    def visitExprNoAssign(self, ctx):
        return self._expr(self.visit(ctx.conditionalExpr()))

    # Comprueba la condicion y busca un tipo compatible entre ambas ramas.
    def visitTernaryExpr(self, ctx):
        condition = self._expr(self.visit(ctx.logicalOrExpr()))
        branches = ctx.expression()
        if not branches:
            return condition
        if condition.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"La condicion ternaria debe ser boolean, no {condition.type_info}")
        when_true = self._expr(self.visit(branches[0]))
        when_false = self._expr(self.visit(branches[1]))
        if self._is_assignable(when_true.type_info, when_false.type_info):
            return when_true
        if self._is_assignable(when_false.type_info, when_true.type_info):
            return when_false
        self._error(ctx, f"Las ramas ternarias {when_true.type_info} y {when_false.type_info} no son compatibles")
        return ExprInfo()

    # Agrupa las operaciones OR en su nivel de precedencia.
    def visitLogicalOrExpr(self, ctx):
        return self._binary(ctx, self._logical_operation)

    # Agrupa las operaciones AND antes de resolver OR.
    def visitLogicalAndExpr(self, ctx):
        return self._binary(ctx, self._logical_operation)

    # Los dos operandos logicos deben ser booleanos.
    def _logical_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if left.type_info.is_unknown() or right.type_info.is_unknown():
            return ExprInfo()
        allowed = (DataType.BOOLEAN, DataType.UNKNOWN)
        if left.type_info.base not in allowed or right.type_info.base not in allowed:
            self._error(ctx, f"'{operator}' requiere boolean y recibio {left.type_info} y {right.type_info}")
            return ExprInfo()
        return ExprInfo(TypeInfo(DataType.BOOLEAN))

    # Valida igualdad y desigualdad con las mismas reglas de compatibilidad.
    def visitEqualityExpr(self, ctx):
        return self._binary(ctx, self._comparison)

    # Comprueba los tipos de los operandos de una comparacion.
    def visitRelationalExpr(self, ctx):
        return self._binary(ctx, self._comparison)

    # El resultado de una comparacion siempre tiene tipo boolean.
    def _comparison(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if left.type_info.is_unknown() or right.type_info.is_unknown():
            return ExprInfo()
        if not left.type_info.is_comparable(right.type_info):
            self._error(ctx, f"No se puede comparar {left.type_info} con {right.type_info} usando '{operator}'")
            return ExprInfo()
        return ExprInfo(TypeInfo(DataType.BOOLEAN))

    # Procesa suma y resta despues de las multiplicaciones.
    def visitAdditiveExpr(self, ctx):
        return self._binary(ctx, self._additive_operation)

    # Permite concatenar dos strings; el resto requiere numeros.
    def _additive_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if operator == "+" and left.type_info.base == right.type_info.base == DataType.STRING:
            return ExprInfo(TypeInfo(DataType.STRING))
        return self._arithmetic_operation(left, right, operator, ctx)

    # Procesa multiplicacion, division y modulo en orden.
    def visitMultiplicativeExpr(self, ctx):
        return self._binary(ctx, self._arithmetic_operation)

    # Promueve el resultado a float cuando algun operando es float.
    def _arithmetic_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if not left.type_info.is_numeric() or not right.type_info.is_numeric():
            if not left.type_info.is_unknown() and not right.type_info.is_unknown():
                self._error(ctx, f"'{operator}' requiere numeros y recibio {left.type_info} y {right.type_info}")
            return ExprInfo()
        result = DataType.FLOAT if DataType.FLOAT in (left.type_info.base, right.type_info.base) else DataType.INTEGER
        return ExprInfo(TypeInfo(result))

    # Distingue la negacion logica del signo negativo numerico.
    def visitUnaryExpr(self, ctx):
        if ctx.primaryExpr():
            return self._expr(self.visit(ctx.primaryExpr()))
        operand = self._expr(self.visit(ctx.unaryExpr()))
        operator = ctx.getChild(0).getText()
        if operand.type_info.is_unknown():
            return ExprInfo()
        if operator == "!" and operand.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"'!' requiere boolean, no {operand.type_info}")
            return ExprInfo()
        if operator == "-" and not operand.type_info.is_numeric() and not operand.type_info.is_unknown():
            self._error(ctx, f"'-' requiere un numero, no {operand.type_info}")
            return ExprInfo()
        return ExprInfo(TypeInfo(DataType.BOOLEAN)) if operator == "!" else operand

    # Los parentesis conservan el tipo de la expresion interna.
    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            return self._expr(self.visit(ctx.literalExpr()))
        if ctx.leftHandSide():
            return self._expr(self.visit(ctx.leftHandSide()))
        return self._expr(self.visit(ctx.expression()))

    # Determina el tipo a partir del literal, sin evaluar el programa.
    def visitLiteralExpr(self, ctx):
        if ctx.arrayLiteral():
            return self._expr(self.visit(ctx.arrayLiteral()))
        text = ctx.getText()
        if text in ("true", "false"):
            return ExprInfo(TypeInfo(DataType.BOOLEAN))
        if text == "null":
            return ExprInfo(NULL_TYPE)
        if text.startswith('"'):
            return ExprInfo(TypeInfo(DataType.STRING))
        return ExprInfo(TypeInfo(DataType.FLOAT if "." in text else DataType.INTEGER))

    # Compara los elementos y conserva la longitud literal conocida.
    def visitArrayLiteral(self, ctx):
        values = [self._expr(self.visit(expression)) for expression in ctx.expression()]
        if not values:
            return ExprInfo(TypeInfo.array_of(UNKNOWN_TYPE), array_length=0)
        element = values[0].type_info
        for value in values[1:]:
            if element.is_numeric() and value.type_info.is_numeric():
                if value.type_info.base == DataType.FLOAT:
                    element = value.type_info
            elif not element.is_compatible_with(value.type_info) or not value.type_info.is_compatible_with(element):
                self._error(ctx, f"El arreglo mezcla elementos {element} y {value.type_info}")
        return ExprInfo(TypeInfo.array_of(element), array_length=len(values))

    # Recupera el simbolo visible y distingue valores de funciones.
    def visitIdentifierExpr(self, ctx):
        name = ctx.Identifier().getText()
        symbol = self._lookup_value(name)
        if symbol is None:
            self._error(ctx, f"El identificador '{name}' no fue declarado")
            return ExprInfo()
        if symbol.symbol_type == "attribute" and symbol.data_type.is_unknown():
            self._resolve_field(symbol)
        if getattr(symbol, "type_pending", False):
            self._error(ctx, f"No se ha definido el tipo de '{name}'; asigna un valor o declara su tipo antes de usarlo")
            return ExprInfo()
        # Una funcion tiene identidad invocable; su retorno solo aparece al llamarla.
        data_type = TypeInfo(DataType.FUNCTION) if symbol.symbol_type in ("function", "method") else symbol.data_type
        if symbol.symbol_type == "class":
            data_type = TypeInfo(DataType.CLASS)
        return ExprInfo(data_type, symbol, symbol.symbol_type in ("variable", "constant", "parameter", "attribute"), symbol.array_length)

    # Verifica la clase y los argumentos del constructor sin crear objetos reales.
    def visitNewExpr(self, ctx):
        name = ctx.Identifier().getText()
        class_symbol = self._lookup_class(name)
        ctx._class_symbol = class_symbol
        arguments = self._arguments(ctx.arguments())
        if class_symbol is None:
            self._error(ctx, f"La clase '{name}' no existe")
            return ExprInfo()
        constructor = self._lookup_member(class_symbol, "constructor")
        if constructor:
            self._check_call(constructor, arguments, ctx)
        elif arguments:
            self._error(ctx, f"La clase '{name}' no define un constructor con argumentos")
        self._forget_lengths()
        return ExprInfo(class_symbol.data_type)

    # This se refiere a la clase cuyo cuerpo estamos analizando.
    def visitThisExpr(self, ctx):
        if not self._class_stack:
            self._error(ctx, "'this' solo puede usarse dentro de una clase")
            return ExprInfo()
        return ExprInfo(self._class_stack[-1].data_type)

    # Cada sufijo transforma el resultado: llamada, indice o propiedad.
    def visitLeftHandSide(self, ctx):
        current = self._expr(self.visit(ctx.primaryAtom()))
        for suffix in ctx.suffixOp():
            first = suffix.getChild(0).getText()
            if first == "(":
                arguments = self._arguments(suffix.arguments())
                if not (current.type_info.is_unknown() and current.symbol is None):
                    current = self._check_call(current.symbol, arguments, suffix)
                self._forget_lengths()
            elif first == "[":
                index = self._expr(self.visit(suffix.expression()))
                # Solo comprobamos limites que conocemos sin ejecutar expresiones.
                index_text = suffix.expression().getText()
                if index_text.lstrip("-").isdigit():
                    position = int(index_text)
                    if position < 0 or (current.array_length is not None and position >= current.array_length):
                        self._error(suffix, "El indice esta fuera de los limites del arreglo")
                if index.type_info.base not in (DataType.INTEGER, DataType.UNKNOWN):
                    self._error(suffix, f"El indice debe ser integer, no {index.type_info}")
                if current.type_info.base not in (DataType.ARRAY, DataType.UNKNOWN):
                    self._error(suffix, f"No se puede indexar un valor {current.type_info}")
                    current = ExprInfo()
                else:
                    current = ExprInfo(current.type_info.element_type or UNKNOWN_TYPE, current.symbol, True, indexed=True)
            elif first == ".":
                name = suffix.Identifier().getText()
                member = self._lookup_member(self._class_for_type(current.type_info), name)
                if member is None:
                    if not current.type_info.is_unknown():
                        self._error(suffix, f"El objeto {current.type_info} no tiene el miembro '{name}'")
                    current = ExprInfo()
                else:
                    member_type = TypeInfo(DataType.FUNCTION) if member.symbol_type == "method" else member.data_type
                    current = ExprInfo(member_type, member, member.symbol_type == "attribute")
        return current

    # ----- API auxiliar usada por pruebas unitarias -----

    # Esta entrada auxiliar permite probar declaraciones sin construir un arbol.
    def define_variable(self, name: str, data_type: DataType | TypeInfo, line: int = 0, column: int = 0, is_const: bool = False, is_initialized: bool = False) -> bool:
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(f"La variable '{name}' ya fue declarada en este alcance", line, column)
            return False
        return self.symbol_table.define_symbol(Symbol(name, "variable", data_type, line, column, is_const, is_initialized))

    # Reutiliza la busqueda jerarquica de la tabla de simbolos.
    def lookup_variable(self, name: str) -> Optional[Symbol]:
        return self.symbol_table.lookup_symbol(name)

    # Abre un entorno para las pruebas auxiliares del analizador.
    def enter_scope(self, scope_type: str):
        return self.symbol_table.enter_scope(scope_type)

    # Vuelve al entorno que contiene al actual.
    def exit_scope(self):
        return self.symbol_table.exit_scope()

    # Registra una firma desde las pruebas unitarias.
    def define_function(self, name: str, return_type: DataType | TypeInfo, parameters: list[tuple], line: int = 0, column: int = 0) -> bool:
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(f"La funcion '{name}' ya fue declarada", line, column)
            return False
        symbol = Symbol(name, "function", return_type, line, column)
        symbol.parameters = [(param_name, ensure_type_info(param_type)) for param_name, param_type in parameters]
        symbol.return_type = ensure_type_info(return_type)
        return self.symbol_table.define_symbol(symbol)

    # Reporta un identificador ausente y devuelve el tipo cuando existe.
    def validate_variable_used(self, name: str, line: int = 0, column: int = 0) -> Optional[DataType]:
        symbol = self.lookup_variable(name)
        if symbol is None:
            self.add_error(f"La variable '{name}' no fue declarada", line, column)
            return None
        return symbol.data_type.base

    # Reutiliza la misma validacion de llamadas que el visitor.
    def validate_function_call(self, name: str, args: list[DataType | TypeInfo], line: int = 0, column: int = 0) -> Optional[DataType]:
        symbol = self.lookup_variable(name)
        if symbol is None or symbol.symbol_type != "function":
            self.add_error(f"La funcion '{name}' no fue declarada", line, column)
            return None
        before = len(self.errors)
        result = self._check_call(symbol, [ExprInfo(ensure_type_info(arg)) for arg in args], _Location(line, column))
        return None if len(self.errors) > before else result.type_info.base

    # Permite probar la regla de break sin depender del parser.
    def validate_break_statement(self, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_loop():
            self.add_error("'break' solo puede usarse dentro de un ciclo", line, column)
            return False
        return True

    # Permite probar la regla de continue sin depender del parser.
    def validate_continue_statement(self, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_loop():
            self.add_error("'continue' solo puede usarse dentro de un ciclo", line, column)
            return False
        return True

    # Comprueba el contexto de return; el visitor valida su tipo.
    def validate_return_statement(self, return_type: Optional[DataType] = None, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_function():
            self.add_error("'return' solo puede usarse dentro de una funcion", line, column)
            return False
        return True

    # Expone la regla booleana para las pruebas unitarias.
    def validate_condition_is_boolean(self, condition_type: DataType | TypeInfo, statement_type: str, line: int = 0, column: int = 0) -> bool:
        if ensure_type_info(condition_type).base != DataType.BOOLEAN:
            self.add_error(f"La condicion de '{statement_type}' debe ser boolean", line, column)
            return False
        return True

    # Valida operandos numericos desde las pruebas auxiliares.
    def check_arithmetic_operation(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        left, right = ensure_type_info(left_type), ensure_type_info(right_type)
        if not left.is_numeric() or not right.is_numeric():
            self.add_error(f"'{operator}' requiere tipos numericos", line, column)
            return DataType.NULL
        return DataType.FLOAT if DataType.FLOAT in (left.base, right.base) else DataType.INTEGER

    # Valida operandos booleanos desde las pruebas auxiliares.
    def check_logical_operation(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        left, right = ensure_type_info(left_type), ensure_type_info(right_type)
        if left.base != DataType.BOOLEAN or right.base != DataType.BOOLEAN:
            self.add_error(f"'{operator}' requiere tipos boolean", line, column)
            return DataType.NULL
        return DataType.BOOLEAN

    # Reutiliza la compatibilidad de tipos para comparar.
    def check_comparison(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        if not ensure_type_info(left_type).is_comparable(ensure_type_info(right_type)):
            self.add_error(f"No se pueden comparar {left_type} y {right_type}", line, column)
            return DataType.NULL
        return DataType.BOOLEAN

    # Devuelve si el tipo destino acepta el valor recibido.
    def check_assignment(self, target_type: DataType | TypeInfo, value_type: DataType | TypeInfo, target_name: str = "", line: int = 0, column: int = 0) -> bool:
        valid = self._is_assignable(ensure_type_info(target_type), ensure_type_info(value_type))
        if not valid:
            self.add_error(f"No se puede asignar {value_type} a {target_type} {target_name}".strip(), line, column)
        return valid

    # Agrupa errores y alcances para inspeccionar el analizador.
    def get_summary(self) -> dict:
        return {
            "errors": len(self.errors),
            "scopes": self.symbol_table.to_dict(),
            "global_symbols": len(self.symbol_table.get_global_symbols()),
        }


class _Location:
    """Contexto minimo para reutilizar validaciones en pruebas unitarias."""

    def __init__(self, line: int, column: int):
        self.start = type("TokenLocation", (), {"line": line, "column": column})()

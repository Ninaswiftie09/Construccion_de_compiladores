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


class SemanticAnalyzer(CompiscriptVisitor):
    """Valida tipos, alcances, funciones, flujo, clases y arreglos."""

    def __init__(self):
        super().__init__()
        self.symbol_table = SymbolTable()
        self.errors: list[CompilationError] = []
        self._error_keys: set[tuple] = set()
        self._declaration_symbols: dict[int, Symbol] = {}
        self._classes: dict[str, Symbol] = {}
        self._function_stack: list[Symbol] = []
        self._function_has_return: list[bool] = []
        self._class_stack: list[Symbol] = []

    # ----- Utilidades -----

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

    def _expr(self, value) -> ExprInfo:
        if isinstance(value, ExprInfo):
            return value
        if isinstance(value, TypeInfo):
            return ExprInfo(value)
        if isinstance(value, DataType):
            return ExprInfo(TypeInfo(value))
        return ExprInfo()

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
        return self._type_from_text(type_ctx.getText())

    def _parameters(self, ctx) -> list[tuple[str, TypeInfo]]:
        parameters = ctx.parameters()
        if parameters is None:
            return []
        return [
            (parameter.Identifier().getText(), self._type_from_annotation(parameter.type_()))
            for parameter in parameters.parameter()
        ]

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

    def _declare_class(self, ctx) -> Symbol:
        name = ctx.Identifier(0).getText()
        symbol = Symbol(name, "class", TypeInfo.object_of(name), ctx.start.line, ctx.start.column, is_initialized=True)
        identifiers = ctx.Identifier()
        if len(identifiers) > 1:
            symbol.base_class = identifiers[1].getText()
        current = self.symbol_table.lookup_in_current_scope(name)
        if current:
            self._error(ctx, f"El identificador '{name}' ya fue declarado en este alcance")
        else:
            self.symbol_table.define_symbol(symbol)
            self._classes[name] = symbol
        self._declaration_symbols[id(ctx)] = symbol
        return symbol

    def _predeclare(self, statements):
        # Funciones y clases se registran antes para permitir recursion.
        for statement in statements or []:
            function = statement.functionDeclaration() if hasattr(statement, "functionDeclaration") else None
            class_decl = statement.classDeclaration() if hasattr(statement, "classDeclaration") else None
            if function is not None and id(function) not in self._declaration_symbols:
                self._declare_function(function)
            elif class_decl is not None and id(class_decl) not in self._declaration_symbols:
                self._declare_class(class_decl)

    def _lookup_class(self, name: Optional[str]) -> Optional[Symbol]:
        return self._classes.get(name or "")

    def _lookup_member(self, class_symbol: Optional[Symbol], name: str) -> Optional[Symbol]:
        visited: set[str] = set()
        while class_symbol and class_symbol.name not in visited:
            visited.add(class_symbol.name)
            if name in class_symbol.attributes:
                return class_symbol.attributes[name]
            class_symbol = self._lookup_class(class_symbol.base_class)
        return None

    def _is_assignable(self, target: TypeInfo, value: TypeInfo) -> bool:
        if target.is_compatible_with(value):
            return True
        if target.base == DataType.OBJECT and value.base == DataType.OBJECT:
            current = self._lookup_class(value.class_name)
            while current and current.base_class:
                if current.base_class == target.class_name:
                    return True
                current = self._lookup_class(current.base_class)
        return False

    def _check_assignment(self, target: ExprInfo, value: ExprInfo, ctx):
        if not target.assignable or target.symbol is None:
            self._error(ctx, "El lado izquierdo de la asignacion no es modificable")
            return
        if target.symbol.is_const:
            self._error(ctx, f"No se puede reasignar la constante '{target.symbol.name}'")
        if not self._is_assignable(target.type_info, value.type_info):
            self._error(ctx, f"No se puede asignar {value.type_info} a {target.type_info}")
        target.symbol.is_initialized = True

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

    def _arguments(self, ctx) -> list[ExprInfo]:
        if ctx is None:
            return []
        return [self._expr(self.visit(expression)) for expression in ctx.expression()]

    def _binary(self, ctx, validator) -> ExprInfo:
        left = self._expr(self.visit(ctx.getChild(0)))
        index = 1
        while index < ctx.getChildCount():
            operator = ctx.getChild(index).getText()
            right = self._expr(self.visit(ctx.getChild(index + 1)))
            left = validator(left, right, operator, ctx)
            index += 2
        return left

    def _visit_statement_list(self, statements):
        self._predeclare(statements)
        terminated = False
        for statement in statements or []:
            if terminated:
                self._error(statement, "Codigo inalcanzable despues de una sentencia de salida")
            self.visit(statement)
            terminated = terminated or bool(
                statement.returnStatement()
                or statement.breakStatement()
                or statement.continueStatement()
            ) if hasattr(statement, "returnStatement") else False

    # ----- Programa y declaraciones -----

    def visitProgram(self, ctx):
        self._visit_statement_list(ctx.statement())
        return None

    def visitBlock(self, ctx):
        self.symbol_table.enter_scope("block")
        self._visit_statement_list(ctx.statement())
        self.symbol_table.exit_scope()
        return None

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
        if value and not self._is_assignable(final_type, value.type_info):
            self._error(ctx, f"La variable '{name}' es {final_type}, pero recibe {value.type_info}")
        return None

    def visitConstantDeclaration(self, ctx):
        name = ctx.Identifier().getText()
        value = self._expr(self.visit(ctx.expression()))
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
        return None

    def visitFunctionDeclaration(self, ctx):
        symbol = self._declaration_symbols.get(id(ctx)) or self._declare_function(ctx)
        self.symbol_table.enter_scope("function", symbol.name)
        self._function_stack.append(symbol)
        self._function_has_return.append(False)
        for name, data_type in symbol.parameters:
            parameter = Symbol(name, "parameter", data_type, ctx.start.line, ctx.start.column, is_initialized=True)
            if not self.symbol_table.define_symbol(parameter):
                self._error(ctx, f"El parametro '{name}' esta duplicado en '{symbol.name}'")
        self.visit(ctx.block())
        has_return = self._function_has_return.pop()
        self._function_stack.pop()
        self.symbol_table.exit_scope()
        if symbol.return_type != VOID_TYPE and symbol.name != "constructor" and not has_return:
            self._error(ctx, f"La funcion '{symbol.name}' debe retornar {symbol.return_type}")
        return None

    def visitClassDeclaration(self, ctx):
        symbol = self._declaration_symbols.get(id(ctx)) or self._declare_class(ctx)
        if symbol.base_class:
            parent = self._lookup_class(symbol.base_class)
            if parent is None:
                self._error(ctx, f"La clase base '{symbol.base_class}' no existe")
            elif parent is symbol:
                self._error(ctx, f"La clase '{symbol.name}' no puede heredarse a si misma")
        self.symbol_table.enter_scope("class", symbol.name)
        self._class_stack.append(symbol)
        self.symbol_table.define_symbol(Symbol("this", "variable", symbol.data_type, is_initialized=True))

        # Se registran todos los miembros antes de analizar los metodos.
        for member in ctx.classMember():
            function = member.functionDeclaration()
            variable = member.variableDeclaration()
            constant = member.constantDeclaration()
            if function is not None:
                self._declare_function(function, symbol)
                continue
            declaration = variable or constant
            name = declaration.Identifier().getText()
            data_type = self._type_from_annotation(declaration.typeAnnotation())
            field = Symbol(
                name,
                "attribute",
                data_type,
                declaration.start.line,
                declaration.start.column,
                constant is not None,
                declaration.initializer() is not None if variable is not None else True,
            )
            if name in symbol.attributes:
                self._error(declaration, f"El miembro '{name}' ya fue declarado en la clase '{symbol.name}'")
            else:
                symbol.attributes[name] = field
            if not self.symbol_table.define_symbol(field):
                self._error(declaration, f"El identificador '{name}' ya fue declarado en este alcance")
            self._declaration_symbols[id(declaration)] = field

        for member in ctx.classMember():
            self.visit(member)
        self._class_stack.pop()
        self.symbol_table.exit_scope()
        return None

    # ----- Sentencias -----

    def visitAssignment(self, ctx):
        expressions = ctx.expression()
        if len(expressions) == 1:
            name = ctx.Identifier().getText()
            symbol = self.symbol_table.lookup_symbol(name)
            if symbol is None:
                self._error(ctx, f"La variable '{name}' no fue declarada")
                target = ExprInfo()
            else:
                target = ExprInfo(symbol.data_type, symbol, True)
            value = self._expr(self.visit(expressions[0]))
        else:
            owner = self._expr(self.visit(expressions[0]))
            member_name = ctx.Identifier().getText()
            member = self._lookup_member(self._lookup_class(owner.type_info.class_name), member_name)
            if member is None:
                self._error(ctx, f"El objeto {owner.type_info} no tiene el miembro '{member_name}'")
            target = ExprInfo(member.data_type, member, True) if member else ExprInfo()
            value = self._expr(self.visit(expressions[-1]))
        self._check_assignment(target, value, ctx)
        return None

    def visitExpressionStatement(self, ctx):
        self.visit(ctx.expression())
        return None

    def visitPrintStatement(self, ctx):
        self.visit(ctx.expression())
        return None

    def _check_condition(self, expression, ctx, owner: str):
        condition = self._expr(self.visit(expression))
        if condition.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"La condicion de '{owner}' debe ser boolean, no {condition.type_info}")

    def visitIfStatement(self, ctx):
        self._check_condition(ctx.expression(), ctx, "if")
        for block in ctx.block():
            self.visit(block)
        return None

    def visitWhileStatement(self, ctx):
        self._check_condition(ctx.expression(), ctx, "while")
        self.symbol_table.enter_scope("while")
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        return None

    def visitDoWhileStatement(self, ctx):
        self.symbol_table.enter_scope("do-while")
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        self._check_condition(ctx.expression(), ctx, "do-while")
        return None

    def visitForStatement(self, ctx):
        self.symbol_table.enter_scope("for")
        if ctx.variableDeclaration():
            self.visit(ctx.variableDeclaration())
        elif ctx.assignment():
            self.visit(ctx.assignment())
        expressions = ctx.expression()
        if expressions:
            self._check_condition(expressions[0], ctx, "for")
        if len(expressions) > 1:
            self.visit(expressions[1])
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        return None

    def visitForeachStatement(self, ctx):
        collection = self._expr(self.visit(ctx.expression()))
        if collection.type_info.base not in (DataType.ARRAY, DataType.UNKNOWN):
            self._error(ctx, f"foreach requiere un arreglo, no {collection.type_info}")
        item_type = collection.type_info.element_type or UNKNOWN_TYPE
        self.symbol_table.enter_scope("foreach")
        name = ctx.Identifier().getText()
        self.symbol_table.define_symbol(Symbol(name, "variable", item_type, ctx.start.line, ctx.start.column, is_initialized=True))
        self.visit(ctx.block())
        self.symbol_table.exit_scope()
        return None

    def visitBreakStatement(self, ctx):
        if not self.symbol_table.is_in_loop():
            self._error(ctx, "'break' solo puede usarse dentro de un ciclo")
        return None

    def visitContinueStatement(self, ctx):
        if not self.symbol_table.is_in_loop():
            self._error(ctx, "'continue' solo puede usarse dentro de un ciclo")
        return None

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
        self._function_has_return[-1] = True
        return None

    def visitTryCatchStatement(self, ctx):
        self.visit(ctx.block(0))
        self.symbol_table.enter_scope("catch")
        name = ctx.Identifier().getText()
        self.symbol_table.define_symbol(Symbol(name, "variable", UNKNOWN_TYPE, ctx.start.line, ctx.start.column, is_initialized=True))
        self.visit(ctx.block(1))
        self.symbol_table.exit_scope()
        return None

    def visitSwitchStatement(self, ctx):
        switch_value = self._expr(self.visit(ctx.expression()))
        if switch_value.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"La condicion de 'switch' debe ser boolean, no {switch_value.type_info}")
        self.symbol_table.enter_scope("switch")
        for case in ctx.switchCase():
            case_type = self._expr(self.visit(case.expression())).type_info
            if not switch_value.type_info.is_comparable(case_type):
                self._error(case, f"El case {case_type} no es compatible con {switch_value.type_info}")
            self._visit_statement_list(case.statement())
        if ctx.defaultCase():
            self._visit_statement_list(ctx.defaultCase().statement())
        self.symbol_table.exit_scope()
        return None

    # ----- Expresiones -----

    def visitExpression(self, ctx):
        return self._expr(self.visit(ctx.assignmentExpr()))

    def visitAssignExpr(self, ctx):
        target = self._expr(self.visit(ctx.lhs))
        value = self._expr(self.visit(ctx.assignmentExpr()))
        self._check_assignment(target, value, ctx)
        return value

    def visitPropertyAssignExpr(self, ctx):
        owner = self._expr(self.visit(ctx.lhs))
        name = ctx.Identifier().getText()
        member = self._lookup_member(self._lookup_class(owner.type_info.class_name), name)
        if member is None:
            self._error(ctx, f"El objeto {owner.type_info} no tiene el miembro '{name}'")
        target = ExprInfo(member.data_type, member, True) if member else ExprInfo()
        value = self._expr(self.visit(ctx.assignmentExpr()))
        self._check_assignment(target, value, ctx)
        return value

    def visitExprNoAssign(self, ctx):
        return self._expr(self.visit(ctx.conditionalExpr()))

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

    def visitLogicalOrExpr(self, ctx):
        return self._binary(ctx, self._logical_operation)

    def visitLogicalAndExpr(self, ctx):
        return self._binary(ctx, self._logical_operation)

    def _logical_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        allowed = (DataType.BOOLEAN, DataType.UNKNOWN)
        if left.type_info.base not in allowed or right.type_info.base not in allowed:
            self._error(ctx, f"'{operator}' requiere boolean y recibio {left.type_info} y {right.type_info}")
        return ExprInfo(TypeInfo(DataType.BOOLEAN))

    def visitEqualityExpr(self, ctx):
        return self._binary(ctx, self._comparison)

    def visitRelationalExpr(self, ctx):
        return self._binary(ctx, self._comparison)

    def _comparison(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if not left.type_info.is_comparable(right.type_info):
            self._error(ctx, f"No se puede comparar {left.type_info} con {right.type_info} usando '{operator}'")
        return ExprInfo(TypeInfo(DataType.BOOLEAN))

    def visitAdditiveExpr(self, ctx):
        return self._binary(ctx, self._additive_operation)

    def _additive_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if operator == "+" and left.type_info.base == right.type_info.base == DataType.STRING:
            return ExprInfo(TypeInfo(DataType.STRING))
        return self._arithmetic_operation(left, right, operator, ctx)

    def visitMultiplicativeExpr(self, ctx):
        return self._binary(ctx, self._arithmetic_operation)

    def _arithmetic_operation(self, left: ExprInfo, right: ExprInfo, operator: str, ctx) -> ExprInfo:
        if not left.type_info.is_numeric() or not right.type_info.is_numeric():
            if not left.type_info.is_unknown() and not right.type_info.is_unknown():
                self._error(ctx, f"'{operator}' requiere numeros y recibio {left.type_info} y {right.type_info}")
            return ExprInfo()
        result = DataType.FLOAT if DataType.FLOAT in (left.type_info.base, right.type_info.base) else DataType.INTEGER
        return ExprInfo(TypeInfo(result))

    def visitUnaryExpr(self, ctx):
        if ctx.primaryExpr():
            return self._expr(self.visit(ctx.primaryExpr()))
        operand = self._expr(self.visit(ctx.unaryExpr()))
        operator = ctx.getChild(0).getText()
        if operator == "!" and operand.type_info.base not in (DataType.BOOLEAN, DataType.UNKNOWN):
            self._error(ctx, f"'!' requiere boolean, no {operand.type_info}")
        if operator == "-" and not operand.type_info.is_numeric() and not operand.type_info.is_unknown():
            self._error(ctx, f"'-' requiere un numero, no {operand.type_info}")
        return ExprInfo(TypeInfo(DataType.BOOLEAN)) if operator == "!" else operand

    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            return self._expr(self.visit(ctx.literalExpr()))
        if ctx.leftHandSide():
            return self._expr(self.visit(ctx.leftHandSide()))
        return self._expr(self.visit(ctx.expression()))

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

    def visitArrayLiteral(self, ctx):
        values = [self._expr(self.visit(expression)) for expression in ctx.expression()]
        if not values:
            return ExprInfo(TypeInfo.array_of(UNKNOWN_TYPE))
        element = values[0].type_info
        for value in values[1:]:
            if element.is_numeric() and value.type_info.is_numeric():
                if value.type_info.base == DataType.FLOAT:
                    element = value.type_info
            elif not element.is_compatible_with(value.type_info) or not value.type_info.is_compatible_with(element):
                self._error(ctx, f"El arreglo mezcla elementos {element} y {value.type_info}")
        return ExprInfo(TypeInfo.array_of(element))

    def visitIdentifierExpr(self, ctx):
        name = ctx.Identifier().getText()
        symbol = self.symbol_table.lookup_symbol(name)
        if symbol is None:
            self._error(ctx, f"El identificador '{name}' no fue declarado")
            return ExprInfo()
        return ExprInfo(symbol.data_type, symbol, symbol.symbol_type in ("variable", "parameter", "attribute"))

    def visitNewExpr(self, ctx):
        name = ctx.Identifier().getText()
        class_symbol = self._lookup_class(name)
        arguments = self._arguments(ctx.arguments())
        if class_symbol is None:
            self._error(ctx, f"La clase '{name}' no existe")
            return ExprInfo()
        constructor = self._lookup_member(class_symbol, "constructor")
        if constructor:
            self._check_call(constructor, arguments, ctx)
        elif arguments:
            self._error(ctx, f"La clase '{name}' no define un constructor con argumentos")
        return ExprInfo(TypeInfo.object_of(name))

    def visitThisExpr(self, ctx):
        if not self._class_stack:
            self._error(ctx, "'this' solo puede usarse dentro de una clase")
            return ExprInfo()
        return ExprInfo(self._class_stack[-1].data_type)

    def visitLeftHandSide(self, ctx):
        current = self._expr(self.visit(ctx.primaryAtom()))
        for suffix in ctx.suffixOp():
            first = suffix.getChild(0).getText()
            if first == "(":
                current = self._check_call(current.symbol, self._arguments(suffix.arguments()), suffix)
            elif first == "[":
                index = self._expr(self.visit(suffix.expression()))
                if index.type_info.base not in (DataType.INTEGER, DataType.UNKNOWN):
                    self._error(suffix, f"El indice debe ser integer, no {index.type_info}")
                if current.type_info.base not in (DataType.ARRAY, DataType.UNKNOWN):
                    self._error(suffix, f"No se puede indexar un valor {current.type_info}")
                    current = ExprInfo()
                else:
                    current = ExprInfo(current.type_info.element_type or UNKNOWN_TYPE, current.symbol, True)
            elif first == ".":
                name = suffix.Identifier().getText()
                member = self._lookup_member(self._lookup_class(current.type_info.class_name), name)
                if member is None:
                    self._error(suffix, f"El objeto {current.type_info} no tiene el miembro '{name}'")
                    current = ExprInfo()
                else:
                    current = ExprInfo(member.data_type, member, member.symbol_type == "attribute")
        return current

    # ----- API auxiliar usada por pruebas unitarias -----

    def define_variable(self, name: str, data_type: DataType | TypeInfo, line: int = 0, column: int = 0, is_const: bool = False, is_initialized: bool = False) -> bool:
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(f"La variable '{name}' ya fue declarada en este alcance", line, column)
            return False
        return self.symbol_table.define_symbol(Symbol(name, "variable", data_type, line, column, is_const, is_initialized))

    def lookup_variable(self, name: str) -> Optional[Symbol]:
        return self.symbol_table.lookup_symbol(name)

    def enter_scope(self, scope_type: str):
        return self.symbol_table.enter_scope(scope_type)

    def exit_scope(self):
        return self.symbol_table.exit_scope()

    def define_function(self, name: str, return_type: DataType | TypeInfo, parameters: list[tuple], line: int = 0, column: int = 0) -> bool:
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(f"La funcion '{name}' ya fue declarada", line, column)
            return False
        symbol = Symbol(name, "function", return_type, line, column)
        symbol.parameters = [(param_name, ensure_type_info(param_type)) for param_name, param_type in parameters]
        symbol.return_type = ensure_type_info(return_type)
        return self.symbol_table.define_symbol(symbol)

    def validate_variable_used(self, name: str, line: int = 0, column: int = 0) -> Optional[DataType]:
        symbol = self.lookup_variable(name)
        if symbol is None:
            self.add_error(f"La variable '{name}' no fue declarada", line, column)
            return None
        return symbol.data_type.base

    def validate_function_call(self, name: str, args: list[DataType | TypeInfo], line: int = 0, column: int = 0) -> Optional[DataType]:
        symbol = self.lookup_variable(name)
        if symbol is None or symbol.symbol_type != "function":
            self.add_error(f"La funcion '{name}' no fue declarada", line, column)
            return None
        before = len(self.errors)
        result = self._check_call(symbol, [ExprInfo(ensure_type_info(arg)) for arg in args], _Location(line, column))
        return None if len(self.errors) > before else result.type_info.base

    def validate_break_statement(self, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_loop():
            self.add_error("'break' solo puede usarse dentro de un ciclo", line, column)
            return False
        return True

    def validate_continue_statement(self, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_loop():
            self.add_error("'continue' solo puede usarse dentro de un ciclo", line, column)
            return False
        return True

    def validate_return_statement(self, return_type: Optional[DataType] = None, line: int = 0, column: int = 0) -> bool:
        if not self.symbol_table.is_in_function():
            self.add_error("'return' solo puede usarse dentro de una funcion", line, column)
            return False
        return True

    def validate_condition_is_boolean(self, condition_type: DataType | TypeInfo, statement_type: str, line: int = 0, column: int = 0) -> bool:
        if ensure_type_info(condition_type).base != DataType.BOOLEAN:
            self.add_error(f"La condicion de '{statement_type}' debe ser boolean", line, column)
            return False
        return True

    def check_arithmetic_operation(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        left, right = ensure_type_info(left_type), ensure_type_info(right_type)
        if not left.is_numeric() or not right.is_numeric():
            self.add_error(f"'{operator}' requiere tipos numericos", line, column)
            return DataType.NULL
        return DataType.FLOAT if DataType.FLOAT in (left.base, right.base) else DataType.INTEGER

    def check_logical_operation(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        left, right = ensure_type_info(left_type), ensure_type_info(right_type)
        if left.base != DataType.BOOLEAN or right.base != DataType.BOOLEAN:
            self.add_error(f"'{operator}' requiere tipos boolean", line, column)
            return DataType.NULL
        return DataType.BOOLEAN

    def check_comparison(self, left_type: DataType | TypeInfo, right_type: DataType | TypeInfo, operator: str, line: int = 0, column: int = 0) -> DataType:
        if not ensure_type_info(left_type).is_comparable(ensure_type_info(right_type)):
            self.add_error(f"No se pueden comparar {left_type} y {right_type}", line, column)
            return DataType.NULL
        return DataType.BOOLEAN

    def check_assignment(self, target_type: DataType | TypeInfo, value_type: DataType | TypeInfo, target_name: str = "", line: int = 0, column: int = 0) -> bool:
        valid = self._is_assignable(ensure_type_info(target_type), ensure_type_info(value_type))
        if not valid:
            self.add_error(f"No se puede asignar {value_type} a {target_type} {target_name}".strip(), line, column)
        return valid

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

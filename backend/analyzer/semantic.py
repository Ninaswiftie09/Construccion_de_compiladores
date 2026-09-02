"""
Semantic Analyzer for Compiscript
Performs type checking, scope validation, and semantic analysis
"""
from typing import Optional, List, Dict, Any
from antlr4 import ParseTreeListener
from models.error import CompilationError, ErrorType
from models.types import DataType, Symbol
from analyzer.symbol_table import SymbolTable


class SemanticAnalyzer(ParseTreeListener):
    """
    Semantic analyzer using visitor pattern.
    Validates types, scopes, and semantic rules.
    """
    
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[CompilationError] = []
        self.current_function = None  # Track current function for return type checking
        self.current_loop_depth = 0  # Track loop depth for break/continue validation
    
    def add_error(
        self,
        message: str,
        line: int = 0,
        column: int = 0,
        context: Optional[str] = None
    ):
        """Add a semantic error to the list"""
        error = CompilationError(
            ErrorType.SEMANTIC,
            message,
            line,
            column,
            context
        )
        self.errors.append(error)
    
    def get_errors(self) -> List[CompilationError]:
        """Get all semantic errors"""
        return self.errors
    
    # ===== Symbol Table Management =====
    
    def enter_scope(self, scope_type: str):
        """Enter a new scope"""
        self.symbol_table.enter_scope(scope_type)
    
    def exit_scope(self):
        """Exit current scope"""
        self.symbol_table.exit_scope()
    
    def define_variable(
        self,
        name: str,
        data_type: DataType,
        line: int = 0,
        column: int = 0,
        is_const: bool = False,
        is_initialized: bool = False
    ) -> bool:
        """Define a variable in current scope"""
        # Check if variable already exists in current scope
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(
                f"Variable '{name}' already declared in this scope",
                line,
                column
            )
            return False
        
        symbol = Symbol(
            name,
            "variable",
            data_type,
            line,
            column,
            is_const,
            is_initialized
        )
        return self.symbol_table.define_symbol(symbol)
    
    def define_function(
        self,
        name: str,
        return_type: DataType,
        parameters: List[tuple],
        line: int = 0,
        column: int = 0
    ) -> bool:
        """Define a function in current scope"""
        if self.symbol_table.lookup_in_current_scope(name):
            self.add_error(
                f"Function '{name}' already declared",
                line,
                column
            )
            return False
        
        symbol = Symbol(name, "function", return_type, line, column)
        symbol.parameters = parameters
        symbol.return_type = return_type
        return self.symbol_table.define_symbol(symbol)
    
    def lookup_variable(self, name: str) -> Optional[Symbol]:
        """Look up a variable"""
        return self.symbol_table.lookup_symbol(name)
    
    # ===== Type Checking =====
    
    def check_arithmetic_operation(
        self,
        left_type: DataType,
        right_type: DataType,
        operator: str,
        line: int = 0,
        column: int = 0
    ) -> DataType:
        """
        Check arithmetic operation type compatibility.
        Returns result type or None if error.
        """
        if not left_type.is_numeric() or not right_type.is_numeric():
            self.add_error(
                f"Arithmetic operation '{operator}' requires numeric types, "
                f"got {left_type} and {right_type}",
                line,
                column
            )
            return DataType.NULL
        
        # Float takes precedence
        if left_type == DataType.FLOAT or right_type == DataType.FLOAT:
            return DataType.FLOAT
        return DataType.INTEGER
    
    def check_logical_operation(
        self,
        left_type: DataType,
        right_type: DataType,
        operator: str,
        line: int = 0,
        column: int = 0
    ) -> DataType:
        """Check logical operation type compatibility"""
        if left_type != DataType.BOOLEAN or right_type != DataType.BOOLEAN:
            self.add_error(
                f"Logical operation '{operator}' requires boolean types, "
                f"got {left_type} and {right_type}",
                line,
                column
            )
            return DataType.NULL
        
        return DataType.BOOLEAN
    
    def check_comparison(
        self,
        left_type: DataType,
        right_type: DataType,
        operator: str,
        line: int = 0,
        column: int = 0
    ) -> DataType:
        """Check comparison operation type compatibility"""
        if not left_type.is_comparable(right_type):
            self.add_error(
                f"Cannot compare {left_type} and {right_type} with '{operator}'",
                line,
                column
            )
            return DataType.NULL
        
        return DataType.BOOLEAN
    
    def check_assignment(
        self,
        target_type: DataType,
        value_type: DataType,
        target_name: str = "",
        line: int = 0,
        column: int = 0
    ) -> bool:
        """Check assignment type compatibility"""
        if not target_type.is_compatible_with(value_type):
            self.add_error(
                f"Cannot assign {value_type} to {target_type} "
                f"{'(variable: ' + target_name + ')' if target_name else ''}",
                line,
                column
            )
            return False
        return True
    
    # ===== Semantic Validations =====
    
    def validate_variable_used(
        self,
        name: str,
        line: int = 0,
        column: int = 0
    ) -> Optional[DataType]:
        """
        Validate that a variable has been declared and return its type.
        """
        symbol = self.lookup_variable(name)
        if not symbol:
            self.add_error(
                f"Undeclared variable '{name}'",
                line,
                column
            )
            return None
        return symbol.data_type
    
    def validate_const_initialized(
        self,
        name: str,
        line: int = 0,
        column: int = 0
    ) -> bool:
        """Check that a const is initialized at declaration"""
        # This is handled during variable definition
        return True
    
    def validate_function_call(
        self,
        func_name: str,
        args: List[DataType],
        line: int = 0,
        column: int = 0
    ) -> Optional[DataType]:
        """
        Validate function call: check if function exists,
        and argument types match parameter types.
        """
        func_symbol = self.lookup_variable(func_name)
        if not func_symbol:
            self.add_error(
                f"Undeclared function '{func_name}'",
                line,
                column
            )
            return None
        
        if func_symbol.symbol_type != "function":
            self.add_error(
                f"'{func_name}' is not a function",
                line,
                column
            )
            return None
        
        # Check argument count
        if len(args) != len(func_symbol.parameters):
            self.add_error(
                f"Function '{func_name}' expects {len(func_symbol.parameters)} "
                f"arguments, got {len(args)}",
                line,
                column
            )
            return None
        
        # Check argument types
        for i, (arg_type, (param_name, param_type)) in enumerate(zip(args, func_symbol.parameters)):
            if not param_type.is_compatible_with(arg_type):
                self.add_error(
                    f"Argument {i + 1} of '{func_name}': expected {param_type}, "
                    f"got {arg_type}",
                    line,
                    column
                )
                return None
        
        return func_symbol.return_type
    
    def validate_break_statement(self, line: int = 0, column: int = 0) -> bool:
        """Validate that break is inside a loop"""
        if not self.symbol_table.is_in_loop():
            self.add_error(
                "break statement must be inside a loop",
                line,
                column
            )
            return False
        return True
    
    def validate_continue_statement(self, line: int = 0, column: int = 0) -> bool:
        """Validate that continue is inside a loop"""
        if not self.symbol_table.is_in_loop():
            self.add_error(
                "continue statement must be inside a loop",
                line,
                column
            )
            return False
        return True
    
    def validate_return_statement(
        self,
        return_type: Optional[DataType],
        line: int = 0,
        column: int = 0
    ) -> bool:
        """Validate return statement"""
        if not self.symbol_table.is_in_function():
            self.add_error(
                "return statement must be inside a function",
                line,
                column
            )
            return False
        
        # TODO: Check return type matches function return type
        
        return True
    
    def validate_condition_is_boolean(
        self,
        condition_type: DataType,
        statement_type: str,
        line: int = 0,
        column: int = 0
    ) -> bool:
        """Validate that a condition is boolean"""
        if condition_type != DataType.BOOLEAN:
            self.add_error(
                f"Condition in '{statement_type}' must be boolean, "
                f"got {condition_type}",
                line,
                column
            )
            return False
        return True
    
    def get_summary(self) -> Dict[str, Any]:
        """Get analysis summary"""
        return {
            "errors": len(self.errors),
            "scopes": self.symbol_table.get_scope_hierarchy(),
            "global_symbols": len(self.symbol_table.get_global_symbols())
        }

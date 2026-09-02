"""
Data types supported by Compiscript
"""
from enum import Enum


class DataType(Enum):
    """Basic data types in Compiscript"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    NULL = "null"
    VOID = "void"
    ARRAY = "array"
    OBJECT = "object"
    
    def is_numeric(self) -> bool:
        """Check if type is numeric"""
        return self in (DataType.INTEGER, DataType.FLOAT)
    
    def is_comparable(self, other: 'DataType') -> bool:
        """Check if two types can be compared"""
        if self == other:
            return True
        # Allow integer-float comparison
        if self.is_numeric() and other.is_numeric():
            return True
        return False
    
    def is_compatible_with(self, other: 'DataType') -> bool:
        """Check if type is compatible for assignment"""
        if self == other:
            return True
        # Allow NULL to be assigned to any type
        if other == DataType.NULL:
            return True
        # Allow int to float conversion
        if self == DataType.FLOAT and other == DataType.INTEGER:
            return True
        return False
    
    def __str__(self):
        return self.value


class Symbol:
    """Represents a symbol in the symbol table"""
    
    def __init__(
        self,
        name: str,
        symbol_type: str,  # 'variable', 'function', 'class', 'parameter'
        data_type: DataType,
        line: int = 0,
        column: int = 0,
        is_const: bool = False,
        is_initialized: bool = False
    ):
        self.name = name
        self.symbol_type = symbol_type
        self.data_type = data_type
        self.line = line
        self.column = column
        self.is_const = is_const
        self.is_initialized = is_initialized
        self.attributes = {}  # For class members
        self.parameters = []  # For functions
        self.return_type = None  # For functions
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.symbol_type,
            "dataType": str(self.data_type),
            "line": self.line,
            "column": self.column,
            "isConst": self.is_const,
            "isInitialized": self.is_initialized
        }


class Scope:
    """Represents a scope level in the scope hierarchy"""
    
    def __init__(self, scope_type: str, parent: 'Scope' = None):
        self.scope_type = scope_type  # 'global', 'function', 'class', 'block'
        self.parent = parent
        self.symbols: dict[str, Symbol] = {}
        self.child_scopes: list[Scope] = []
    
    def define_symbol(self, symbol: Symbol) -> bool:
        """Define a new symbol in this scope. Returns False if already exists"""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True
    
    def lookup_symbol(self, name: str) -> Symbol | None:
        """Look up symbol in this scope and parent scopes"""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup_symbol(name)
        return None
    
    def lookup_in_scope(self, name: str) -> Symbol | None:
        """Look up symbol only in this scope"""
        return self.symbols.get(name)
    
    def get_all_symbols(self) -> list[Symbol]:
        """Get all symbols in this scope"""
        return list(self.symbols.values())

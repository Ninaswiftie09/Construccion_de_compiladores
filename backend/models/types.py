"""Tipos y simbolos usados por el analizador semantico."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DataType(Enum):
    """Tipos base de Compiscript."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    NULL = "null"
    VOID = "void"
    ARRAY = "array"
    OBJECT = "object"
    UNKNOWN = "unknown"

    def is_numeric(self) -> bool:
        return self in (DataType.INTEGER, DataType.FLOAT)

    def is_comparable(self, other: "DataType") -> bool:
        if DataType.UNKNOWN in (self, other):
            return True
        return self == other or (self.is_numeric() and other.is_numeric())

    def is_compatible_with(self, other: "DataType") -> bool:
        if DataType.UNKNOWN in (self, other) or self == other:
            return True
        if other == DataType.NULL and self != DataType.VOID:
            return True
        return self == DataType.FLOAT and other == DataType.INTEGER

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, eq=False)
class TypeInfo:
    """Tipo completo; conserva clases y dimensiones de arreglos."""

    base: DataType
    class_name: Optional[str] = None
    element_type: Optional["TypeInfo"] = None

    @classmethod
    def array_of(cls, element_type: "TypeInfo") -> "TypeInfo":
        return cls(DataType.ARRAY, element_type=element_type)

    @classmethod
    def object_of(cls, class_name: str) -> "TypeInfo":
        return cls(DataType.OBJECT, class_name=class_name)

    def is_numeric(self) -> bool:
        return self.base.is_numeric()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DataType):
            return self.base == other and self.class_name is None and self.element_type is None
        if not isinstance(other, TypeInfo):
            return False
        return (self.base, self.class_name, self.element_type) == (other.base, other.class_name, other.element_type)

    def __hash__(self) -> int:
        return hash((self.base, self.class_name, self.element_type))

    def is_unknown(self) -> bool:
        return self.base == DataType.UNKNOWN

    def is_comparable(self, other: "TypeInfo") -> bool:
        if self.is_unknown() or other.is_unknown():
            return True
        if self.base == DataType.ARRAY or other.base == DataType.ARRAY:
            return self == other
        if self.base == DataType.OBJECT or other.base == DataType.OBJECT:
            return self == other or self.base == DataType.NULL or other.base == DataType.NULL
        return self.base.is_comparable(other.base)

    def is_compatible_with(self, other: "TypeInfo") -> bool:
        if self.is_unknown() or other.is_unknown() or self == other:
            return True
        if other.base == DataType.NULL and self.base != DataType.VOID:
            return True
        if self.base == DataType.FLOAT and other.base == DataType.INTEGER:
            return True
        if self.base == DataType.ARRAY and other.base == DataType.ARRAY:
            return bool(self.element_type and other.element_type and self.element_type.is_compatible_with(other.element_type))
        return False

    def __str__(self) -> str:
        if self.base == DataType.ARRAY:
            return f"{self.element_type or UNKNOWN_TYPE}[]"
        if self.base == DataType.OBJECT:
            return self.class_name or "object"
        return str(self.base)


UNKNOWN_TYPE = TypeInfo(DataType.UNKNOWN)
VOID_TYPE = TypeInfo(DataType.VOID)
NULL_TYPE = TypeInfo(DataType.NULL)


def ensure_type_info(data_type: DataType | TypeInfo) -> TypeInfo:
    return data_type if isinstance(data_type, TypeInfo) else TypeInfo(data_type)


class Symbol:
    """Entrada de la tabla de simbolos."""

    def __init__(
        self,
        name: str,
        symbol_type: str,
        data_type: DataType | TypeInfo,
        line: int = 0,
        column: int = 0,
        is_const: bool = False,
        is_initialized: bool = False,
    ):
        self.name = name
        self.symbol_type = symbol_type
        self.data_type = ensure_type_info(data_type)
        self.line = line
        self.column = column
        self.is_const = is_const
        self.is_initialized = is_initialized
        self.attributes: dict[str, Symbol] = {}
        self.parameters: list[tuple[str, TypeInfo]] = []
        self.return_type: TypeInfo = self.data_type
        self.base_class: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.symbol_type,
            "dataType": str(self.data_type),
            "line": self.line,
            "column": self.column,
            "isConst": self.is_const,
            "isInitialized": self.is_initialized,
            "parameters": [
                {"name": name, "type": str(param_type)}
                for name, param_type in self.parameters
            ],
            "returnType": str(self.return_type),
        }


class Scope:
    """Un alcance enlazado con su padre e hijos."""

    def __init__(self, scope_type: str, parent: Optional["Scope"] = None, name: str = ""):
        self.scope_type = scope_type
        self.name = name
        self.parent = parent
        self.symbols: dict[str, Symbol] = {}
        self.child_scopes: list[Scope] = []

    def define_symbol(self, symbol: Symbol) -> bool:
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        return self.parent.lookup_symbol(name) if self.parent else None

    def lookup_in_scope(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def get_all_symbols(self) -> list[Symbol]:
        return list(self.symbols.values())

    def to_dict(self) -> dict:
        return {
            "type": self.scope_type,
            "name": self.name,
            "symbols": [symbol.to_dict() for symbol in self.get_all_symbols()],
            "children": [scope.to_dict() for scope in self.child_scopes],
        }

"""Tabla de simbolos jerarquica de Compiscript."""

from typing import Optional

from models.types import Scope, Symbol


class SymbolTable:
    """Inserta, consulta y actualiza simbolos respetando alcances."""

    def __init__(self):
        self.global_scope = Scope("global", name="global")
        self.current_scope = self.global_scope
        self.scopes_stack: list[Scope] = [self.global_scope]

    def enter_scope(self, scope_type: str, name: str = "") -> Scope:
        # Cada bloque conserva el enlace al alcance que lo contiene.
        new_scope = Scope(scope_type, self.current_scope, name)
        self.current_scope.child_scopes.append(new_scope)
        self.current_scope = new_scope
        self.scopes_stack.append(new_scope)
        return new_scope

    def exit_scope(self) -> Optional[Scope]:
        if len(self.scopes_stack) == 1:
            return None
        self.scopes_stack.pop()
        self.current_scope = self.scopes_stack[-1]
        return self.current_scope

    def define_symbol(self, symbol: Symbol) -> bool:
        return self.current_scope.define_symbol(symbol)

    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_symbol(name)

    def lookup_in_current_scope(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_in_scope(name)

    def update_symbol(self, name: str, **changes) -> bool:
        """Actualiza la entrada visible mas cercana."""
        symbol = self.lookup_symbol(name)
        if symbol is None:
            return False
        for field, value in changes.items():
            if field != "name" and hasattr(symbol, field):
                setattr(symbol, field, value)
        return True

    def get_current_scope_type(self) -> str:
        return self.current_scope.scope_type

    def _has_scope(self, accepted: tuple[str, ...]) -> bool:
        scope: Optional[Scope] = self.current_scope
        while scope:
            if scope.scope_type in accepted:
                return True
            scope = scope.parent
        return False

    def is_in_loop(self) -> bool:
        return self._has_scope(("while", "do-while", "for", "foreach"))

    def is_in_function(self) -> bool:
        return self._has_scope(("function",))

    def is_in_class(self) -> bool:
        return self._has_scope(("class",))

    def get_global_symbols(self) -> list[Symbol]:
        return self.global_scope.get_all_symbols()

    def get_current_scope_symbols(self) -> list[Symbol]:
        return self.current_scope.get_all_symbols()

    def get_scope_hierarchy(self) -> list[str]:
        hierarchy = []
        scope: Optional[Scope] = self.current_scope
        while scope:
            hierarchy.insert(0, scope.scope_type)
            scope = scope.parent
        return hierarchy

    def to_dict(self) -> dict:
        return self.global_scope.to_dict()

    def debug_print_scopes(self):
        def print_scope(scope: Scope, indent: int = 0):
            prefix = "  " * indent
            print(f"{prefix}[{scope.scope_type}] {scope.name}")
            for symbol in scope.get_all_symbols():
                print(f"{prefix}  - {symbol.name}: {symbol.data_type}")
            for child in scope.child_scopes:
                print_scope(child, indent + 1)

        print_scope(self.global_scope)

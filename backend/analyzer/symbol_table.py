"""
Symbol Table implementation with scope management
"""
from typing import Optional
from models.types import Symbol, Scope, DataType


class SymbolTable:
    """
    Symbol table with hierarchical scope management.
    Supports global, function, class, and block scopes.
    """
    
    def __init__(self):
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.scopes_stack: list[Scope] = [self.global_scope]
    
    def enter_scope(self, scope_type: str) -> Scope:
        """Enter a new scope"""
        new_scope = Scope(scope_type, self.current_scope)
        self.current_scope.child_scopes.append(new_scope)
        self.current_scope = new_scope
        self.scopes_stack.append(new_scope)
        return new_scope
    
    def exit_scope(self) -> Optional[Scope]:
        """Exit current scope and return to parent"""
        if len(self.scopes_stack) > 1:
            self.scopes_stack.pop()
            self.current_scope = self.scopes_stack[-1]
            return self.current_scope
        return None
    
    def define_symbol(self, symbol: Symbol) -> bool:
        """Define a symbol in the current scope"""
        return self.current_scope.define_symbol(symbol)
    
    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        """Look up a symbol in current and parent scopes"""
        return self.current_scope.lookup_symbol(name)
    
    def lookup_in_current_scope(self, name: str) -> Optional[Symbol]:
        """Look up symbol only in current scope"""
        return self.current_scope.lookup_in_scope(name)
    
    def get_current_scope_type(self) -> str:
        """Get the type of current scope"""
        return self.current_scope.scope_type
    
    def is_in_loop(self) -> bool:
        """Check if we're currently inside a loop scope"""
        scope = self.current_scope
        while scope:
            if scope.scope_type in ("while", "do-while", "for", "foreach"):
                return True
            scope = scope.parent
        return False
    
    def is_in_function(self) -> bool:
        """Check if we're currently inside a function scope"""
        scope = self.current_scope
        while scope:
            if scope.scope_type == "function":
                return True
            scope = scope.parent
        return False
    
    def get_global_symbols(self) -> list[Symbol]:
        """Get all symbols in global scope"""
        return self.global_scope.get_all_symbols()
    
    def get_current_scope_symbols(self) -> list[Symbol]:
        """Get all symbols in current scope"""
        return self.current_scope.get_all_symbols()
    
    def get_scope_hierarchy(self) -> list[str]:
        """Get current scope hierarchy"""
        hierarchy = []
        scope = self.current_scope
        while scope:
            hierarchy.insert(0, f"{scope.scope_type}")
            scope = scope.parent
        return hierarchy
    
    def debug_print_scopes(self):
        """Print scope hierarchy for debugging"""
        def print_scope(scope: Scope, indent=0):
            prefix = "  " * indent
            print(f"{prefix}[{scope.scope_type}]")
            for symbol in scope.get_all_symbols():
                print(f"{prefix}  - {symbol.name}: {symbol.data_type}")
            for child in scope.child_scopes:
                print_scope(child, indent + 1)
        
        print_scope(self.global_scope)

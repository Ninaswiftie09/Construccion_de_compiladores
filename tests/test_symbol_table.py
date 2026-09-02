"""
Unit tests for Symbol Table
"""
import pytest
from models.types import DataType, Symbol, Scope
from analyzer.symbol_table import SymbolTable


class TestSymbolTable:
    
    def setup_method(self):
        """Setup for each test"""
        self.table = SymbolTable()
    
    def test_define_and_lookup_variable(self):
        """Test defining and looking up a variable"""
        symbol = Symbol("x", "variable", DataType.INTEGER)
        assert self.table.define_symbol(symbol)
        assert self.table.lookup_symbol("x") == symbol
    
    def test_duplicate_definition_fails(self):
        """Test that duplicate definitions in same scope fail"""
        symbol1 = Symbol("x", "variable", DataType.INTEGER)
        symbol2 = Symbol("x", "variable", DataType.STRING)
        
        assert self.table.define_symbol(symbol1)
        assert not self.table.define_symbol(symbol2)
    
    def test_scope_separation(self):
        """Test that symbols in different scopes don't conflict"""
        # Define in global scope
        symbol1 = Symbol("x", "variable", DataType.INTEGER)
        self.table.define_symbol(symbol1)
        
        # Enter new scope
        self.table.enter_scope("function")
        
        # Can define same name in new scope
        symbol2 = Symbol("x", "variable", DataType.STRING)
        assert self.table.define_symbol(symbol2)
        
        # Lookup returns the one in current scope
        assert self.table.lookup_symbol("x") == symbol2
    
    def test_scope_hierarchy(self):
        """Test scope hierarchy and lookup"""
        # Global scope
        global_var = Symbol("global_x", "variable", DataType.INTEGER)
        self.table.define_symbol(global_var)
        
        # Enter function scope
        self.table.enter_scope("function")
        
        # Can lookup global variable from function scope
        assert self.table.lookup_symbol("global_x") == global_var
        
        # Define local variable
        local_var = Symbol("local_x", "variable", DataType.STRING)
        self.table.define_symbol(local_var)
        
        # Exit function scope
        self.table.exit_scope()
        
        # Cannot lookup local variable from global scope
        assert self.table.lookup_symbol("local_x") is None
    
    def test_is_in_loop(self):
        """Test loop detection"""
        assert not self.table.is_in_loop()
        
        self.table.enter_scope("for")
        assert self.table.is_in_loop()
        
        self.table.exit_scope()
        assert not self.table.is_in_loop()
    
    def test_is_in_function(self):
        """Test function detection"""
        assert not self.table.is_in_function()
        
        self.table.enter_scope("function")
        assert self.table.is_in_function()
        
        # Nested block inside function
        self.table.enter_scope("block")
        assert self.table.is_in_function()
        
        self.table.exit_scope()
        self.table.exit_scope()
        assert not self.table.is_in_function()

    def test_update_visible_symbol(self):
        """Test updating information in the closest visible entry"""
        symbol = Symbol("counter", "variable", DataType.INTEGER)
        self.table.define_symbol(symbol)
        self.table.enter_scope("block")

        assert self.table.update_symbol("counter", is_initialized=True)
        assert symbol.is_initialized
        assert not self.table.update_symbol("missing", is_initialized=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

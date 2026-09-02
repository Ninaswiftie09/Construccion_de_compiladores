"""
Example test program demonstrating Compiscript features
"""

from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from analyzer.compiler import Compiler
from models.types import DataType

def test_program(name: str, code: str):
    """Test a program and display results"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    print("\nCode:")
    print("-" * 40)
    print(code)
    print("-" * 40)
    
    compiler = Compiler()
    result = compiler.compile(code)
    
    print("\nResults:")
    print(f"  Status: {'✅ SUCCESS' if result.has_errors() == False else '❌ ERRORS'}")
    print(f"  Total errors: {len(result.get_all_errors())}")
    print(f"  Lexical errors: {len(result.lexical_errors)}")
    print(f"  Syntactic errors: {len(result.syntactic_errors)}")
    print(f"  Semantic errors: {len(result.semantic_errors)}")
    print(f"  Tokens generated: {len(result.tokens)}")
    
    if result.get_all_errors():
        print("\nErrors:")
        for error in result.get_all_errors():
            print(f"  [{error.error_type.upper()}] Line {error.line}:{error.column} - {error.message}")
    else:
        print("\n✨ No errors found!")


if __name__ == "__main__":
    print("🧪 Compiscript Compiler - Test Suite")
    
    # Test 1: Valid arithmetic
    test_program(
        "Valid Arithmetic",
        """
let x: integer = 10;
let y: integer = 20;
let sum: integer = x + y;
print(sum);
""")
    
    # Test 2: Function declaration
    test_program(
        "Function Declaration",
        """
function add(a: integer, b: integer): integer {
    return a + b;
}

let result: integer = add(5, 3);
print(result);
""")
    
    # Test 3: Type error - string to integer
    test_program(
        "Type Mismatch Error",
        """
let x: integer = "hello";
print(x);
""")
    
    # Test 4: Undeclared variable
    test_program(
        "Undeclared Variable Error",
        """
print(undefined_var);
""")
    
    # Test 5: Syntax error - missing semicolon
    test_program(
        "Syntax Error",
        """
let x: integer = 10
let y: integer = 20;
""")
    
    print(f"\n{'='*60}")
    print("Test suite complete!")
    print(f"{'='*60}\n")

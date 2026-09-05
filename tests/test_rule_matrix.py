"""Cada fila demuestra una regla con un programa valido y otro invalido."""

import pytest

from analyzer.compiler import Compiler


# Los nombres de las filas permiten localizar rapidamente una regla en pytest.
RULES = [
    ("arithmetic", "let x = 2 + 3 * 4 / 2;", 'let x = "x" * 2;', "requiere numeros"),
    ("logic", "let x = true && !false || false;", "let x = 1 && false;", "requiere boolean"),
    ("comparison", "let x = 2 < 3;", 'let x = 2 < "3";', "comparar"),
    ("assignment", "let x: integer = 2; x = 3;", 'let x: integer = 2; x = "3";', "asignar"),
    ("constant", "const x: integer = 2; print(x);", "const x = 2; x = 3;", "constante"),
    ("lookup", "let x = 1; print(x);", "print(x);", "declarado"),
    ("duplicate_variable", "let x = 1; { let x = 2; }", "let x = 1; let x = 2;", "declarada"),
    ("block_scope", "let x = 1; { print(x); }", "{ let x = 1; } print(x);", "declarado"),
    ("arity", "function f(a: integer) {} f(1);", "function f(a: integer) {} f();", "argumentos"),
    ("argument_type", "function f(a: integer) {} f(1);", 'function f(a: integer) {} f("x");', "argumento 1"),
    ("return_type", "function f(): integer { return 1; }", 'function f(): integer { return "x"; }', "retorno"),
    ("recursion", "function f(n: integer): integer { if (n == 0) { return 0; } return f(n - 1); }", 'function f(n: integer): integer { return f("x"); }', "argumento 1"),
    ("closure", "function f(a: integer): integer { function g(): integer { return a; } return g(); }", "function f() { let a = 1; } function g(): integer { return a; }", "declarado"),
    ("duplicate_function", "function f() {} { function f() {} }", "function f() {} function f() {}", "declarado"),
    ("if", "if (true) {}", "if (1) {}", "condicion"),
    ("while", "while (false) {}", "while (1) {}", "condicion"),
    ("do_while", "do {} while (false);", "do {} while (1);", "condicion"),
    ("for", "for (; false;) {}", "for (; 1;) {}", "condicion"),
    ("switch", "switch (true) { case false: print(1); }", "switch (1) { case 1: print(1); }", "condicion"),
    ("break", "while (true) { break; }", "break;", "break"),
    ("continue", "while (false) { continue; }", "continue;", "continue"),
    ("return_scope", "function f() { return; }", "return;", "return"),
    ("member", "class A { let x: integer; } let a = new A(); print(a.x);", "class A {} let a = new A(); print(a.x);", "miembro"),
    ("constructor", "class A { function constructor(n: integer) {} } let a = new A(1);", 'class A { function constructor(n: integer) {} } let a = new A("x");', "argumento 1"),
    ("this", "class A { function f() { print(this); } }", "print(this);", "this"),
    ("array_elements", "let a = [1, 2];", 'let a = [1, "x"];', "mezcla"),
    ("array_index", "let a = [1]; print(a[0]);", "let a = [1]; print(a[true]);", "indice"),
    ("dead_code", "function f() { print(1); return; }", "function f() { return; print(1); }", "inalcanzable"),
    ("duplicate_parameter", "function f(a: integer, b: integer) {}", "function f(a: integer, a: integer) {}", "duplicado"),
]


@pytest.mark.parametrize("name, valid, invalid, message", RULES, ids=[row[0] for row in RULES])
def test_required_rule_has_positive_and_negative_examples(name, valid, invalid, message):
    assert Compiler().compile(valid).get_all_errors() == []
    result = Compiler().compile(invalid)
    # Evitamos que un error de sintaxis haga pasar una prueba semantica.
    assert not result.lexical_errors
    assert not result.syntactic_errors
    assert any(message in error.message for error in result.semantic_errors)
    assert not any("Fallo interno" in error.message for error in result.semantic_errors)

"""Casos que reproducen los fallos encontrados al revisar la rubrica."""

import subprocess
import sys

import pytest

from analyzer.compiler import Compiler


def analyze(code):
    # Todos estos ejemplos deben llegar al visitor sin errores de gramatica.
    result = Compiler().compile(code)
    assert not result.lexical_errors
    assert not result.syntactic_errors
    assert not any("Fallo interno" in error.message for error in result.semantic_errors)
    return result


@pytest.mark.parametrize("code, message", [
    ('function f(): integer { return 1; } let x = f * 2;', "requiere numeros"),
    ('function f(): integer { return 1; } f = 3;', "no es modificable"),
    ('function f(): integer { return 1; } let x: integer = f;', "recibe function"),
    ('while (true) { function f() { break; } }', "break"),
    ('while (true) { function f() { continue; } }', "continue"),
    ('{ class Hidden {} } let x = new Hidden();', "no existe"),
    ('let x: Missing;', "no existe"),
    ('let xs = [1, 2]; print(xs[-1]);', "limites"),
    ('let xs = [1, 2]; print(xs[2]);', "limites"),
    ('function f(b: boolean): integer { if (b) { return 1; } }', "debe retornar"),
    ('function f(b: boolean): integer { if (b) { return 1; } else { return 2; } print(3); }', "inalcanzable"),
    ('class A { function f(): integer { return 1; } } let a = new A(); let x = a.f * 2;', "requiere numeros"),
    ('class A {} { class A {} let x: A = new A(); }', None),
    ('class A {} let x = new A(); { class A {} let y: A = x; }', "recibe A"),
])
def test_review_regressions(code, message):
    found = [error.message for error in analyze(code).semantic_errors]
    assert any(message in error for error in found) if message else found == []


@pytest.mark.parametrize("code", [
    'let i = 0; for (; ; i = i + 1) { break; }',
    'let i = 0; for (; i < 2; ) { i = i + 1; }',
    'for (;;) { break; }',
    'function f(): integer { return 1; } let x = f() * 2;',
    'while (true) { function f() { while (true) { break; } } break; }',
    'let xs = [1, 2]; print(xs[0]); print(xs[1]);',
    'let xs = [1]; xs = [1, 2]; print(xs[1]);',
    'let xs = [1]; if (true) { xs = [1, 2]; } print(xs[1]);',
    'let xs = [1]; function grow() { xs = [1, 2]; } grow(); print(xs[1]);',
    'let xs = [[1], [2]]; xs[0] = [3]; print(xs[1]);',
    'function f(b: boolean): integer { if (b) { return 1; } else { return 2; } }',
    'class A { let x: integer; } let a = new A(); { class A {} print(a.x); }',
])
def test_valid_counterparts(code):
    assert analyze(code).get_all_errors() == []


def test_missing_initializer_does_not_stop_later_diagnostics():
    result = Compiler().compile('const x: integer; print(missing); let bad: integer = "x";')
    # El parser recupera la constante y el visitor sigue con las otras sentencias.
    assert result.syntactic_errors
    messages = [error.message for error in result.semantic_errors]
    assert any("missing" in message for message in messages)
    assert any("bad" in message for message in messages)
    assert not any("Fallo interno" in message for message in messages)
    assert result.symbol_table is not None


@pytest.mark.parametrize("broken", ["const ;", "class A { const ; }", "let ;", "if () {}", "let x = ( ;"])
def test_incomplete_nodes_keep_semantic_recovery(broken):
    result = Compiler().compile(broken + " print(missing);")
    assert result.syntactic_errors
    assert any("missing" in error.message for error in result.semantic_errors)
    assert not any("Fallo interno" in error.message for error in result.semantic_errors)


def test_unknown_values_do_not_create_cascading_errors():
    result = analyze('missing = 1; print(other.foo.bar); absent(unknown);')
    assert len(result.semantic_errors) == 4
    assert all("declarad" in error.message for error in result.semantic_errors)


def test_inheritance_cycle_finishes_and_reports_later_errors():
    # Un proceso separado impide que una regresion de ciclos congele pytest.
    source = 'class A : B {} class B : A {} class C {} let x: C = new A(); print(missing);'
    script = (
        "import sys; sys.path.insert(0, 'backend'); from analyzer.compiler import Compiler; "
        f"r = Compiler().compile({source!r}); print([e.message for e in r.semantic_errors])"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert "circular" in result.stdout
    assert "missing" in result.stdout


def test_tokens_use_the_generated_parser_vocabulary():
    result = analyze('let x: integer = 1;')
    assert [(token["value"], token["type"]) for token in result.tokens] == [
        ("let", "let"), ("x", "Identifier"), (":", ":"),
        ("integer", "integer"), ("=", "="), ("1", "Literal"), (";", ";"),
    ]

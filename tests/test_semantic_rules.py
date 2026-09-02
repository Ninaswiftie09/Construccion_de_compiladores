"""Cobertura adicional de las reglas solicitadas en el enunciado."""

import pytest

from analyzer.compiler import Compiler


def semantic_messages(code: str) -> list[str]:
    return [error.message for error in Compiler().compile(code).semantic_errors]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ('let value: integer = 1; let value: integer = 2;', "ya fue declarada"),
        ('const limit: integer = 3; limit = 4;', "constante"),
        ('if (1) { print(1); }', "condicion"),
        ('return 1;', "return"),
        ('continue;', "continue"),
        ('let values: integer[] = [1]; print(values["zero"]);', "indice"),
        ('foreach (item in 12) { print(item); }', "arreglo"),
        ('print(this);', "this"),
        ('function value(): integer { print(1); }', "debe retornar"),
    ],
)
def test_reports_individual_semantic_rules(code: str, expected: str):
    assert any(expected in message for message in semantic_messages(code))


def test_nested_function_captures_outer_variable():
    code = """
    function outer(base: integer): integer {
        function inner(value: integer): integer { return base + value; }
        return inner(2);
    }
    let result: integer = outer(4);
    """

    assert semantic_messages(code) == []


def test_inheritance_exposes_parent_members():
    code = """
    class Animal {
        let name: string;
        function constructor(name: string) { this.name = name; }
        function speak(): string { return this.name; }
    }
    class Dog : Animal {
        function label(): string { return this.name + " dog"; }
    }
    let dog: Animal = new Dog("Luna");
    """

    assert semantic_messages(code) == []


def test_dead_code_is_reported_after_return():
    found = semantic_messages(
        "function sample(): integer { return 1; print(2); let other: integer = 3; }"
    )

    assert sum("inalcanzable" in message for message in found) == 2

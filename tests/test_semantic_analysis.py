"""Pruebas integrales de las reglas semanticas principales."""

from analyzer.compiler import Compiler


def compile_code(code: str):
    return Compiler().compile(code)


def messages(result) -> list[str]:
    return [error.message for error in result.semantic_errors]


def test_valid_program_supports_recursion_arrays_and_scopes():
    result = compile_code(
        """
        function factorial(n: integer): integer {
            if (n <= 1) { return 1; }
            return n * factorial(n - 1);
        }
        let values: integer[] = [1, 2, 3];
        foreach (value in values) { print(factorial(value)); }
        """
    )

    assert result.get_all_errors() == []
    assert result.ast is not None
    assert result.symbol_table is not None


def test_reports_multiple_independent_semantic_errors():
    result = compile_code(
        """
        let count: integer = "wrong";
        print(missing);
        break;
        let flag: boolean = 1 && false;
        """
    )

    found = messages(result)
    assert len(found) >= 4
    assert any("count" in message for message in found)
    assert any("missing" in message for message in found)
    assert any("break" in message for message in found)
    assert any("boolean" in message for message in found)


def test_validates_function_arguments_and_return_types():
    result = compile_code(
        """
        function add(a: integer, b: integer): integer { return "bad"; }
        let value: integer = add(1, true);
        add(1);
        """
    )

    found = messages(result)
    assert any("retorno" in message for message in found)
    assert any("argumento 2" in message for message in found)
    assert any("espera 2 argumentos" in message for message in found)


def test_validates_classes_this_members_and_constructor():
    result = compile_code(
        """
        class Person {
            let name: string;
            function constructor(name: string) { this.name = name; }
            function label(): string { return this.name; }
        }
        let person: Person = new Person("Ada");
        print(person.label());
        print(person.unknown);
        """
    )

    found = messages(result)
    assert len(found) == 1
    assert "unknown" in found[0]


def test_validates_array_elements_and_indexes():
    result = compile_code(
        """
        let values: integer[] = [1, "two", 3];
        print(values[true]);
        """
    )

    found = messages(result)
    assert any("mezcla elementos" in message for message in found)
    assert any("indice" in message for message in found)


def test_lexer_and_parser_recover_after_errors():
    result = compile_code(
        """
        let first: integer = 1 @ 2;
        let second: integer = ;
        print(undeclared);
        """
    )

    assert result.lexical_errors
    assert result.syntactic_errors
    assert any("undeclared" in message for message in messages(result))

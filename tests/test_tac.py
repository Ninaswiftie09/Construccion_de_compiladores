"""Comprueba traducciones, efectos y casos invalidos del proyecto dos."""

import pytest
from analyzer.compiler import Compiler
from analyzer.tac import TemporaryPool


def translate(source):
    result = Compiler().compile(source)
    assert not result.has_errors(), [e.message for e in result.get_all_errors()]
    assert result.intermediate_code is not None
    return result.intermediate_code


CASES = [
    ("declarations", "let a: integer; const b = 3; a = b;", {"declare", "const", "copy"}),
    ("arithmetic", "let a = -(2 + 3) * 4 / 2 % 3;", {"+", "*", "/", "%", "neg"}),
    ("logic", "let a = !false && true || false;", {"not", "if_false", "if_true"}),
    ("arrays", "let a = [[1, 2], [3, 4]]; a[0][1] = 5; print(a[1][0]);", {"array", "load_index", "copy"}),
    ("if_else", "if (true) { print(1); } else { print(2); }", {"if_false", "goto", "print"}),
    ("while", "let i = 0; while (i < 4) { i = i + 1; if (i == 2) { continue; } if (i == 3) { break; } }", {"<", "==", "goto"}),
    ("do_while", "let i = 0; do { i = i + 1; } while (i < 2);", {"if_true", "+"}),
    ("for", "for (let i = 0; i < 3; i = i + 1) { print(i); }", {"if_false", "+"}),
    ("foreach", "let a = [1, 2]; foreach (x in a) { print(x); }", {"length", "load_index", "if_false"}),
    ("switch", 'switch (2) { case 1: print(1); break; case 2: print(2); break; default: print(3); }', {"==", "if_true", "goto"}),
    ("functions", "function add(a: integer, b: integer): integer { return a + b; } let x = add(1, 2);", {"receive", "param", "call", "return", "closure"}),
    ("recursion", "function f(n: integer): integer { if (n <= 1) { return 1; } return n * f(n - 1); } print(f(5));", {"closure", "call", "*", "return"}),
    ("closure", "function outer(a: integer): integer { function inner(): integer { return a; } return inner(); } print(outer(4));", {"closure", "call", "receive"}),
    ("classes", "class A { let x = 1; function constructor(x: integer) { this.x = x; } function f(): integer { return this.x; } } let a = new A(2); print(a.f());", {"class", "method", "new", "init_object", "bind", "member"}),
    ("inheritance", "class A { let x = 1; function f(): integer { return this.x; } } class B : A { function f(): integer { return this.x + 1; } } let b: A = new B(); print(b.f());", {"class", "method", "init_object", "member"}),
    ("try_catch", "let a = [1]; let i = 2; try { print(a[i]); } catch (err) { print(err); }", {"try_begin", "try_end", "catch", "load_index"}),
    ("ternary", "let a = true ? 1 + 2 : 3 + 4;", {"if_false", "goto", "copy"}),
]


@pytest.mark.parametrize("name,source,operations", CASES, ids=[c[0] for c in CASES])
def test_rubric_translations(name, source, operations):
    code = translate(source)
    assert operations <= {i["op"] for i in code["instructions"]}
    labels = [i["result"] for i in code["instructions"] if i["op"] == "label"]
    assert len(labels) == len(set(labels))
    for instruction in code["instructions"]:
        if instruction["op"] in ("goto", "if_true", "if_false", "try_begin"):
            assert instruction["result"] in labels


@pytest.mark.parametrize("source", [
    "let x = @ 1;", "let x = ; print( );", 'let x: integer = "bad";',
    "const x = 1; x = 2;", "break; continue; print(missing);",
    "let a = [1]; print(a[3]);", "class A : B {} class B : A {}",
    "function f(n: integer): integer { return f(true); }",
    "class A {} let a = new A(1);", "switch (1) { case true: print(1); }",
    "try { print(missing); } catch (e) { print(other); }",
])
def test_any_error_blocks_all_intermediate_code(source):
    result = Compiler().compile(source)
    assert result.has_errors()
    assert result.intermediate_code is None
    assert result.to_dict()["intermediateCode"] is None


def test_temporary_pool_does_not_reuse_live_values():
    pool = TemporaryPool()
    first, second = pool.acquire(), pool.acquire()
    pool.release(first)
    third = pool.acquire()
    assert third.name == first.name
    assert third.name != second.name
    assert pool.created == 2 and pool.reused == 1 and pool.peak == 2


def test_arithmetic_recycles_between_statements_and_bounds_storage():
    code = translate("".join(f"let x{i} = (1 + 2) * (3 + 4);" for i in range(40)))
    stats = code["temporaries"][-1]
    assert stats["created"] <= 4
    assert stats["reused"] > 100
    assert stats["peakLive"] <= 4


def test_arithmetic_order_and_associativity():
    instructions = translate("let x = 10 - 3 - 2 * 4;")["instructions"]
    math = [i for i in instructions if i["op"] in ("-", "*")]
    assert [i["op"] for i in math] == ["-", "*", "-"]
    assert (math[0]["arg1"], math[0]["arg2"]) == ("10", "3")
    assert (math[1]["arg1"], math[1]["arg2"]) == ("2", "4")
    assert math[2]["arg1"] == math[0]["result"]
    assert math[2]["arg2"] == math[1]["result"]


@pytest.mark.parametrize("operator,branch", [("&&", "if_false"), ("||", "if_true")])
def test_short_circuit_skips_right_side_call(operator, branch):
    code = translate(f"function f(): boolean {{ return true; }} let x = false {operator} f();")
    instructions = code["instructions"]
    call_index = next(i for i, row in enumerate(instructions) if row["op"] == "call")
    jumps = [row for row in instructions[:call_index] if row["op"] == branch]
    assert jumps
    label_index = next(i for i, row in enumerate(instructions) if row["op"] == "label" and row["result"] == jumps[-1]["result"])
    assert label_index > call_index


def test_values_are_preserved_before_side_effects():
    rows = translate("let x = 1; let y = x + (x = 5);")["instructions"]
    snapshot = next(i for i, row in enumerate(rows) if row["op"] == "copy" and row["arg1"].endswith(".x"))
    overwrite = next(i for i, row in enumerate(rows) if row["op"] == "copy" and row["arg1"] == "5")
    addition = next(row for row in rows if row["op"] == "+")
    assert snapshot < overwrite
    assert addition["arg1"] == rows[snapshot]["result"]


def test_nested_call_arguments_are_not_interleaved():
    rows = translate("function f(a: integer, b: integer): integer { return a + b; } print(f(1, f(2, 3)));")["instructions"]
    calls = [i for i, row in enumerate(rows) if row["op"] == "call"]
    assert len(calls) == 2
    assert [row["arg1"] for row in rows[calls[0] - 2:calls[0]]] == ["2", "3"]
    assert rows[calls[1] - 2]["arg1"] == "1"
    assert rows[calls[1] - 1]["arg1"] == rows[calls[0]]["result"]


def test_shadowing_preserves_symbol_selected_during_semantics():
    rows = translate("let x = 1; { print(x); x = 3; let x = 2; print(x); }")["instructions"]
    prints = [row["arg1"] for row in rows if row["op"] == "print"]
    assert prints == ["s1.x", "s2.x"]
    assert any(row["op"] == "copy" and row["result"] == "s1.x" and row["arg1"] == "3" for row in rows)


def test_frame_offsets_and_static_links():
    code = translate("function outer(a: integer): integer { let b = 1; function inner(): integer { return a + b; } return inner(); } print(outer(2));")
    frames = code["frames"]
    outer = next(f for f in frames if f["name"] == "outer")
    inner = next(f for f in frames if f["name"] == "inner")
    assert inner["lexicalParent"] == outer["id"]
    assert outer["header"] == {"returnAddress": 0, "dynamicLink": 8, "staticLink": 16, "receiver": 24}
    offsets = [s["offset"] for s in outer["slots"]]
    assert len(offsets) == len(set(offsets)) and min(offsets) >= 32
    assert outer["temporaryOffset"] == max(offsets) + 8
    assert outer["size"] == outer["temporaryOffset"] + outer["temporarySlots"] * 8


def test_inherited_layout_and_virtual_override():
    code = translate("class A { let x = 1; function f(): integer { return this.x; } } class B : A { let y = 2; function f(): integer { return this.y; } } let b: A = new B(); print(b.f());")
    parent, child = code["classes"]
    assert child["base"] == parent["label"]
    assert child["layout"]["fields"] == [{"name": "x", "offset": 8, "type": "integer"}, {"name": "y", "offset": 16, "type": "integer"}]
    assert child["layout"]["size"] == 24
    assert child["layout"]["methods"]["f"] != parent["layout"]["methods"]["f"]


def test_exception_handlers_are_unwound_before_return():
    rows = translate("function f(): integer { try { return 1; } catch (e) { return 2; } } print(f());")["instructions"]
    index = next(i for i, row in enumerate(rows) if row["op"] == "return" and row["arg1"] == "1")
    assert rows[index - 1]["op"] == "try_end"


def test_continue_in_switch_targets_enclosing_loop():
    rows = translate("let i = 0; while (i < 3) { switch (i) { case 1: i = i + 1; continue; default: print(i); } i = i + 1; }")["instructions"]
    assert any(row["op"] == "goto" for row in rows)
    assert all(row["result"] for row in rows if row["op"] == "goto")


def test_repeat_compile_has_clean_labels_frames_and_temporaries():
    compiler = Compiler()
    source = "let x = (1 + 2) * 3;"
    first = compiler.compile(source).intermediate_code
    compiler.compile("print(missing);")
    assert compiler.compile(source).intermediate_code == first

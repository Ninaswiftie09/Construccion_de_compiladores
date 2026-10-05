"""Regresiones del compilador. Ejecutar: python -m unittest discover -s tests -v."""
import json
from pathlib import Path
import unittest
from analyzer.compiler import Compiler
from antlr4 import InputStream
from grammar.CompiscriptLexer import CompiscriptLexer


CASES = json.loads((Path(__file__).parent / "regression_cases.json").read_text(encoding="utf-8"))


class CompilerRegressionTests(unittest.TestCase):
    def compile_ok(self, source):
        result = Compiler().compile(source).to_dict()
        self.assertTrue(result["success"], result["errors"])
        self.assertIsNotNone(result["intermediateCode"])
        return result

    def test_language_cases_and_error_gating(self):
        for name, case in CASES.items():
            with self.subTest(name=name):
                result = Compiler().compile(case["source"]).to_dict()
                self.assertEqual(result["success"], case["success"], result["errors"])
                self.assertEqual(result["intermediateCode"] is not None, case["success"])
                self.assertFalse(any("Fallo interno" in e["message"] for e in result["errors"]), result["errors"])
                keys = [(e["type"], e["line"], e["column"], e["message"]) for e in result["errors"]]
                self.assertEqual(len(keys), len(set(keys)))
                for expected in case.get("messages", []):
                    self.assertTrue(any(expected in e["message"] for e in result["errors"]), result["errors"])

    def test_recovery_keeps_later_errors(self):
        r = Compiler().compile('@ let a: = 1; # let b: boolean = 2; print(missing);').to_dict()
        self.assertEqual(r["lexicalErrors"], 2)
        self.assertGreaterEqual(r["syntacticErrors"], 1)
        self.assertTrue(any("missing" in e["message"] for e in r["errors"]))
        self.assertTrue(any("recibe integer" in e["message"] for e in r["errors"]))
        self.assertFalse(any("clase ''" in e["message"] for e in r["errors"]))
        self.assertIsNone(r["intermediateCode"])

    def test_temporaries_recycled_and_reserved_in_frame(self):
        code = self.compile_ok('let x=(1+2)*(3+4); let y=(5+6)*(7+8);')["intermediateCode"]
        stats = code["temporaries"][0]
        self.assertGreater(stats["reused"], 0)
        self.assertEqual(stats["created"], stats["peakLive"])
        frame = next(f for f in code["frames"] if f["id"] == stats["frame"])
        self.assertEqual(frame["temporarySlots"], stats["created"])
        self.assertEqual(frame["size"], frame["temporaryOffset"] + 8 * stats["created"])

    def test_short_circuit_guards_rhs_call(self):
        code = self.compile_ok('function f(): boolean { return true; } let x=false && f();')["intermediateCode"]
        ins = code["instructions"]
        jump = next(i for i in ins if i["op"] == "if_false")
        call = next(i for i in ins if i["op"] == "call")
        destination = next(i for i in ins if i["op"] == "label" and i["result"] == jump["result"])
        self.assertLess(jump["index"], call["index"])
        self.assertLess(call["index"], destination["index"])

    def test_labels_and_layout_for_all_valid_cases(self):
        for name, case in CASES.items():
            if not case["success"]:
                continue
            with self.subTest(name=name):
                code = self.compile_ok(case["source"])["intermediateCode"]
                labels = [i["result"] for i in code["instructions"] if i["op"] == "label"]
                self.assertEqual(len(labels), len(set(labels)))
                for i in code["instructions"]:
                    if i["op"] in ("goto", "if_true", "if_false", "try_begin"):
                        self.assertIn(i["result"], labels)
                for frame in code["frames"]:
                    offsets = [slot["offset"] for slot in frame["slots"]]
                    self.assertEqual(len(offsets), len(set(offsets)))
                    self.assertTrue(all(offset >= 32 and offset < frame["size"] for offset in offsets))

    def test_inheritance_preserves_offsets_and_dispatch(self):
        code = self.compile_ok('class B:A { let y=2; function f():integer{return 2;} } class A { let x=1; function f():integer{return 1;} }')["intermediateCode"]
        base = next(c for c in code["classes"] if c["base"] is None)
        child = next(c for c in code["classes"] if c["base"] is not None)
        self.assertEqual(child["base"], base["label"])
        self.assertEqual(child["layout"]["fields"][0], base["layout"]["fields"][0])
        self.assertNotEqual(child["layout"]["methods"]["f"], base["layout"]["methods"]["f"])
        self.assertGreater(child["layout"]["size"], base["layout"]["size"])

    def test_recursion_has_call_and_distinct_frame(self):
        code = self.compile_ok(CASES["recursion"]["source"])["intermediateCode"]
        self.assertEqual(len([f for f in code["frames"] if f["kind"] == "function"]), 1)
        self.assertGreaterEqual(len([i for i in code["instructions"] if i["op"] == "call"]), 2)
        self.assertTrue(any(i["op"] == "receive" for i in code["instructions"]))

    def test_shadowed_identifier_keeps_original_binding(self):
        code = self.compile_ok('let x=1; {print(x); let x=2; print(x);}')["intermediateCode"]
        prints = [i["arg1"] for i in code["instructions"] if i["op"] == "print"]
        self.assertNotEqual(prints[0], prints[1])

    def test_assignment_expression_fixes_type(self):
        r = self.compile_ok('let x; print(x=1); print(x+1);')
        x = next(s for s in r["symbolTable"]["symbols"] if s["name"] == "x")
        self.assertEqual(x["dataType"], "integer")

    def test_compiler_reuse_does_not_keep_errors(self):
        compiler = Compiler()
        self.assertTrue(compiler.compile('print(missing);').has_errors())
        self.assertFalse(compiler.compile('let x=1;').has_errors())

    def test_recovery_with_deleted_tokens(self):
        seeds = [
            'function f(x:integer):integer {if(x>0){return x;}else{return 0;}} print(missing);',
            'class A {let x=1; function f():integer{return this.x;}} let a=new A(); print(missing);',
            'for(let i=0;i<3;i=i+1){print(i);} print(missing);',
            'try{let x=1;}catch(e){print(e);} print(missing);',
            'let a=[1,2]; a[0]=3; print(missing);',
        ]
        for source in seeds:
            for token in CompiscriptLexer(InputStream(source)).getAllTokens():
                mutated = source[:token.start] + source[token.stop + 1:]
                with self.subTest(source=mutated):
                    result = Compiler().compile(mutated).to_dict()
                    self.assertFalse(any('Fallo interno' in e['message'] for e in result['errors']), result['errors'])
                    if result['errors']:
                        self.assertIsNone(result['intermediateCode'])

    def test_incomplete_constructs_keep_following_diagnostics(self):
        fragments = ['if (1 >) {}', 'for(let i=;i<3;i=i+1){}',
                     'for(let i=0;i<;i=i+1){}', 'for(let i=0;i<3i=i+1){}',
                     'for(let i=0;i<3;i=i+){}', 'try{}catche){}']
        for fragment in fragments:
            with self.subTest(fragment=fragment):
                result = Compiler().compile(fragment + ' print(missing);').to_dict()
                self.assertGreater(result['syntacticErrors'], 0)
                self.assertTrue(any("'missing' no fue declarado" in e['message'] for e in result['errors']), result['errors'])
                self.assertIsNone(result['intermediateCode'])


if __name__ == "__main__":
    unittest.main()

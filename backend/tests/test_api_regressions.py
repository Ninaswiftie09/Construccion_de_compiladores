"""Contrato HTTP con FastAPI/TestClient, sin servidor ni ejecucion del TAC."""
import sys
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import analyzer.diagrams as diagrams
from server import app


class ApiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.output = patch.object(diagrams, "OUTPUT_DIR", Path(self.folder.name))
        self.output.start()
        # Graphviz es opcional; el contrato debe funcionar aunque no este instalado.
        self.dot = patch.object(diagrams.subprocess, "run", side_effect=FileNotFoundError("dot"))
        self.dot.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.dot.stop()
        self.output.stop()
        self.folder.cleanup()

    def test_compile_response_and_graphviz_fallback(self):
        response = self.client.post("/compile", json={"code": "let x=1+2;"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertIsNotNone(body["intermediateCode"])
        self.assertTrue(body["diagramWarnings"])
        self.assertTrue(list(Path(self.folder.name).rglob("program.tac")))

    def test_invalid_source_has_no_tac_file(self):
        response = self.client.post("/compile", json={"code": 'let x; x=1; x="s";'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIsNone(response.json()["intermediateCode"])
        self.assertFalse(list(Path(self.folder.name).rglob("program.tac")))

    def test_upload_file(self):
        response = self.client.post("/compile/file", files={"file": ("test.cps", b"print(1);", "text/plain")})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_invalid_extension(self):
        response = self.client.post("/compile/file", files={"file": ("test.txt", b"print(1);", "text/plain")})
        self.assertEqual(response.status_code, 400)

    def test_invalid_encoding(self):
        response = self.client.post("/compile/file", files={"file": ("test.cps", b"\xff", "text/plain")})
        self.assertEqual(response.status_code, 400)

    def test_missing_generated_parser_is_diagnostic(self):
        with patch.dict(sys.modules, {"grammar.CompiscriptLexer": None}):
            response = self.client.post("/compile", json={"code": "let x=1;"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["success"])
        self.assertIsNone(response.json()["intermediateCode"])

    @unittest.skipUnless(shutil.which("dot"), "Graphviz es opcional")
    def test_real_graphviz_outputs(self):
        self.dot.stop()
        response = self.client.post("/compile", json={"code": "let x=1; while(x<3){x=x+1;}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["diagramWarnings"], [])
        self.assertEqual(set(response.json()["diagrams"]), {"ast", "symbols", "tac"})
        files = list(Path(self.folder.name).rglob("*.png"))
        self.assertEqual(len(files), 3)
        for file in files:
            self.assertTrue(file.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()

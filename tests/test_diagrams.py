"""Verifica archivos de imagen y la respuesta usada por el IDE."""

import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from analyzer.compiler import Compiler
from analyzer import diagrams
from server import app


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz no instalado")
def test_images_and_tac_are_saved_inside_project_and_served():
    client = TestClient(app)
    response = client.post("/compile", json={"code": "let a = 1 + 2; if (a > 0) { print(a); }"})
    payload = response.json()
    assert response.status_code == 200 and payload["success"]
    assert payload["diagramWarnings"] == []
    assert set(payload["diagrams"]) == {"ast", "symbols", "tac"}
    for diagram in payload["diagrams"].values():
        path = Path(diagram["path"])
        assert path.resolve().is_relative_to(diagrams.OUTPUT_DIR.resolve())
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        svg = client.get(diagram["url"])
        assert svg.status_code == 200 and "<svg" in svg.text
        assert client.get(diagram["pngUrl"]).content == path.read_bytes()
    folder = Path(payload["diagrams"]["tac"]["path"]).parent
    assert (folder / "program.tac").read_text(encoding="utf-8") == payload["intermediateCode"]["text"]
    assert (folder / "program.json").exists()


def test_errors_do_not_create_tac_files(tmp_path, monkeypatch):
    monkeypatch.setattr(diagrams, "OUTPUT_DIR", tmp_path)
    result = Compiler().compile('let x: integer = "bad"; print(missing); break;')
    pictures, _ = diagrams.save_diagrams(result)
    assert result.has_errors() and result.intermediate_code is None
    assert "tac" not in pictures
    assert not list(tmp_path.rglob("program.tac"))
    assert not list(tmp_path.rglob("tac.dot"))
    assert len(result.get_all_errors()) >= 3


def test_missing_graphviz_is_reported_without_losing_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(diagrams, "OUTPUT_DIR", tmp_path)
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("dot")
    monkeypatch.setattr(diagrams.subprocess, "run", unavailable)
    result = Compiler().compile("let x = 1;")
    pictures, warnings = diagrams.save_diagrams(result)
    assert pictures == {} and len(warnings) == 3
    assert result.intermediate_code and not result.has_errors()
    assert list(tmp_path.rglob("program.tac"))


def test_control_graph_has_exception_edges_for_failing_operations():
    result = Compiler().compile("let a = [1]; let i = 3; try { print(a[i]); } catch (e) { print(e); }")
    graph = diagrams.control_graph(result.intermediate_code).source()
    assert graph.count('label="excepcion"') >= 2


def test_invalid_upload_never_returns_intermediate_code():
    client = TestClient(app)
    response = client.post("/compile/file", files={"file": ("error.cps", b"print(missing); break;", "text/plain")})
    payload = response.json()
    assert response.status_code == 200 and not payload["success"]
    assert payload["intermediateCode"] is None and "tac" not in payload["diagrams"]


def test_static_files_cannot_read_outside_diagram_folder():
    response = TestClient(app).get("/diagrams/%2e%2e/%2e%2e/backend/server.py")
    assert response.status_code == 404

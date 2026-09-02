"""Pruebas de los endpoints usados por el IDE."""

from fastapi.testclient import TestClient

from server import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_compile_returns_visualization_data():
    response = client.post("/compile", json={"code": "let value: integer = 2; print(value);"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["success"]
    assert payload["ast"]["name"] == "program"
    assert payload["symbolTable"]["type"] == "global"
    assert payload["tokens"]


def test_file_endpoint_accepts_only_utf8_cps_files():
    valid = client.post(
        "/compile/file",
        files={"file": ("valid.cps", b"let value: integer = 1;", "text/plain")},
    )
    invalid_extension = client.post(
        "/compile/file",
        files={"file": ("invalid.txt", b"let value = 1;", "text/plain")},
    )

    assert valid.status_code == 200
    assert invalid_extension.status_code == 400

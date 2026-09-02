"""Comprueba todos los archivos .cps entregados para calificación."""

from pathlib import Path

import pytest

from analyzer.compiler import compile_file


CASES = Path(__file__).parent / "test_cases"


@pytest.mark.parametrize("path", sorted(CASES.glob("valid_*.cps")), ids=lambda path: path.name)
def test_valid_case_files(path: Path):
    assert compile_file(str(path)).get_all_errors() == []


@pytest.mark.parametrize("path", sorted(CASES.glob("error_*.cps")), ids=lambda path: path.name)
def test_error_case_files(path: Path):
    assert compile_file(str(path)).get_all_errors()

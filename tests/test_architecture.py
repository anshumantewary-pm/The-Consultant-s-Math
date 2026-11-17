"""Enforce the import rules in docs/ARCHITECTURE.md: each layer imports only downward."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "casemath"

ALLOWED = {
    "core": {"core"},
    "calculators": {"core", "calculators"},
    "frameworks": {"core", "frameworks"},
    "analysis": {"core", "analysis"},
    "cases": {"core", "calculators", "frameworks", "analysis", "cases"},
}
# The CLI's built-in models wrap calculators by design.
EXCEPTIONS = {("analysis", "models.py"): {"calculators"}}


def casemath_imports(path: Path) -> set[str]:
    layers = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] == "casemath" and len(parts) > 1:
                layers.add(parts[1])
    return layers


@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_imports_only_downward(layer: str) -> None:
    for path in sorted((PACKAGE / layer).glob("*.py")):
        allowed = ALLOWED[layer] | EXCEPTIONS.get((layer, path.name), set())
        illegal = casemath_imports(path) - allowed
        assert not illegal, f"{layer}/{path.name} imports {sorted(illegal)}"


def test_every_layer_is_covered() -> None:
    packages = {p.name for p in PACKAGE.iterdir() if (p / "__init__.py").exists()}
    assert packages == set(ALLOWED)

"""Protect the modular-monolith dependency direction as the scaffold grows."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "factory_ops"
FORBIDDEN_INTERNAL = {
    "domain": {"api", "application", "infrastructure"},
    "application": {"api", "infrastructure"},
    "infrastructure": {"api"},
    "api": {"domain", "infrastructure"},
}


def imported_modules(path: Path) -> list[str]:
    package = "factory_ops." + ".".join(path.parent.relative_to(SOURCE).parts)
    modules = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                module = importlib.util.resolve_name("." * node.level + module, package)
            # Include imported names so `from factory_ops import infrastructure` is checked.
            modules.append(module)
            modules.extend(f"{module}.{alias.name}" for alias in node.names)
    return modules


@pytest.mark.parametrize("layer", FORBIDDEN_INTERNAL)
def test_layer_imports_obey_dependency_direction(layer: str) -> None:
    for path in (SOURCE / layer).rglob("*.py"):
        for module in imported_modules(path):
            parts = module.split(".")
            if parts[0] == "factory_ops":
                if layer == "domain":
                    assert len(parts) < 2 or parts[1] == "domain", (
                        f"{path}: Domain must not depend on {module}"
                    )
                assert len(parts) < 2 or parts[1] not in FORBIDDEN_INTERNAL[layer], (
                    f"{path}: {layer} must not depend on {module}"
                )
            elif layer == "domain":
                assert parts[0] in sys.stdlib_module_names, (
                    f"{path}: Domain must only use stdlib and Domain, found {module}"
                )

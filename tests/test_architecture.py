"""Architecture tests to enforce AGENTS.md rules."""

import ast
from pathlib import Path


def get_imports(file_path: Path) -> list[str]:
    """Parse a file and return a list of imported module names."""
    with open(file_path) as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_domain_is_framework_free():
    """Verify [AR1b] Domain is framework-free."""
    domain_path = Path("src/agent_loop/domain")
    if not domain_path.exists():
        return

    forbidden_modules = [
        "fastapi",
        "weave",
        "langgraph",
        "openai",
        "requests",
        "httpx",
    ]

    # Exceptions: langgraph types/messages are allowed primitives if pure data
    # But strictly, [AR1b] says: "Exception: langchain_core messages/runnables are allowed primitives"

    errors = []

    for py_file in domain_path.rglob("*.py"):
        imports = get_imports(py_file)
        for imp in imports:
            for forbidden in forbidden_modules:
                if imp.startswith(forbidden):
                    errors.append(f"{py_file}: Imports '{imp}' (Forbidden: {forbidden})")

    assert not errors, "\n".join(errors)


def test_file_line_counts():
    """Verify [LC1a] No file > 350 lines."""
    src_path = Path("src")
    max_lines = 350
    errors = []

    for py_file in src_path.rglob("*.py"):
        with open(py_file) as f:
            count = sum(1 for _ in f)
            if count > max_lines:
                errors.append(f"{py_file}: {count} lines (Max: {max_lines})")

    assert not errors, "\n".join(errors)

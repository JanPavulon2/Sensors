#!/usr/bin/env python3
"""
WebSocket Endpoint Validator

Detects missing type hints on FastAPI WebSocket handlers to prevent HTTP 403 errors.
This validator ensures all @app.websocket() and @router.websocket() decorators have
properly typed WebSocket parameters.

Usage:
    From Python:
        from tools.websocket_validator import validate_websocket_handlers
        errors = validate_websocket_handlers()
        if errors:
            sys.exit(1)

    From command line:
        python tools/websocket_validator.py

    As pre-commit hook:
        Add to .git/hooks/pre-commit:
        python tools/websocket_validator.py
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


class WebSocketHandlerValidator(ast.NodeVisitor):
    """AST visitor that finds WebSocket decorators and checks for type hints."""

    def __init__(self, filename: str):
        self.filename = filename
        self.errors: List[Tuple[int, str]] = []
        self.in_websocket_decorator = False
        self.pending_function = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check if function has @app.websocket() or @router.websocket() decorator."""
        for decorator in node.decorator_list:
            # Check for @app.websocket(...) or @router.websocket(...)
            if self._is_websocket_decorator(decorator):
                self._check_websocket_handler(node)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async functions with WebSocket decorators."""
        for decorator in node.decorator_list:
            if self._is_websocket_decorator(decorator):
                self._check_websocket_handler(node)

        self.generic_visit(node)

    def _is_websocket_decorator(self, decorator: ast.expr) -> bool:
        """Check if decorator is a WebSocket endpoint."""
        # Handle @app.websocket(...) or @router.websocket(...)
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute) and func.attr == "websocket":
                return True
        return False

    def _check_websocket_handler(
        self, node: ast.AsyncFunctionDef | ast.FunctionDef
    ) -> None:
        """Verify WebSocket handler has properly typed parameters."""
        if not node.args.args:
            self.errors.append(
                (
                    node.lineno,
                    f"WebSocket handler '{node.name}' has no parameters (expected 'websocket: WebSocket')",
                )
            )
            return

        # First parameter should be 'websocket'
        first_param = node.args.args[0]
        if first_param.arg != "websocket":
            self.errors.append(
                (
                    node.lineno,
                    f"WebSocket handler '{node.name}' first parameter should be 'websocket', got '{first_param.arg}'",
                )
            )
            return

        # Check for type hint
        if first_param.annotation is None:
            self.errors.append(
                (
                    node.lineno,
                    f"WebSocket handler '{node.name}' missing type hint on 'websocket' parameter. "
                    f"Must be: 'websocket: WebSocket'",
                )
            )
            return

        # Verify type hint is 'WebSocket'
        type_hint = self._get_type_hint_name(first_param.annotation)
        if type_hint != "WebSocket":
            self.errors.append(
                (
                    node.lineno,
                    f"WebSocket handler '{node.name}' has incorrect type hint: '{type_hint}'. "
                    f"Must be 'WebSocket'",
                )
            )

    def _get_type_hint_name(self, annotation: ast.expr) -> str:
        """Extract the type name from annotation AST node."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        else:
            return "Unknown"


def validate_websocket_handlers(
    path: str | Path = None, verbose: bool = False
) -> List[Tuple[str, int, str]]:
    """
    Validate all WebSocket handlers in the codebase.

    Args:
        path: Directory to search (default: src/api)
        verbose: Print progress information

    Returns:
        List of (filename, line_number, error_message) tuples
    """
    if path is None:
        # Default to src/api directory
        project_root = Path(__file__).parent.parent
        path = project_root / "src" / "api"
    else:
        path = Path(path)

    if not path.exists():
        print(f"ERROR: Path does not exist: {path}")
        return []

    errors = []

    # Find all Python files
    python_files = list(path.rglob("*.py"))

    if verbose:
        print(f"Scanning {len(python_files)} Python files for WebSocket handlers...")

    for filepath in python_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source, filename=str(filepath))
            validator = WebSocketHandlerValidator(str(filepath))
            validator.visit(tree)

            for line_num, error_msg in validator.errors:
                # Get relative path from project root
                project_root = Path(__file__).parent.parent
                relative_path = filepath.relative_to(project_root)
                errors.append((str(relative_path), line_num, error_msg))
                if verbose:
                    print(f"  {relative_path}:{line_num} - {error_msg}")

        except SyntaxError as e:
            if verbose:
                print(f"  SYNTAX ERROR in {filepath}: {e}")
        except Exception as e:
            if verbose:
                print(f"  ERROR scanning {filepath}: {e}")

    return errors


def main() -> int:
    """Command-line interface for WebSocket validator."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate WebSocket endpoint type hints")
    parser.add_argument(
        "--path",
        default=None,
        help="Path to scan (default: src/api)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )

    args = parser.parse_args()

    errors = validate_websocket_handlers(path=args.path, verbose=True)

    if errors:
        print(f"\n❌ Found {len(errors)} WebSocket validation error(s):\n")
        for filename, line_num, error_msg in errors:
            print(f"  {filename}:{line_num}")
            print(f"    {error_msg}\n")
        return 1
    else:
        print("✅ All WebSocket handlers have proper type hints!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

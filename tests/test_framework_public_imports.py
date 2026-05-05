from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / 'src' / 'somevar_ui_playground'

FORBIDDEN_IMPORTS = {
    'somevar_ui.core.runtime_state': 'use somevar_ui.core',
    'somevar_ui.ui.base': 'use somevar_ui.ui.kit.core',
    'somevar_ui.ui.lists': 'use somevar_ui.ui.kit.widgets',
    'somevar_ui.ui.search_select': 'use somevar_ui.ui.kit.widgets',
    'somevar_ui.ui.shell.titlebar': 'use somevar_ui.ui.shell',
}

FORBIDDEN_LOCAL_FROM_IMPORTS = {
    'somevar_ui_playground.ui.playground_support': {
        'DataTableWidget': 'use somevar_ui.ui.kit.tables',
        'table_palette_for_theme': 'use somevar_ui.ui.kit.tables',
    },
}


def _iter_imported_modules(file_path: Path) -> list[str]:
    tree = ast.parse(file_path.read_text(encoding='utf-8'))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _iter_from_import_names(file_path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(file_path.read_text(encoding='utf-8'))
    imports: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.extend((node.module, alias.name) for alias in node.names)
    return imports


def test_playground_uses_public_framework_imports() -> None:
    violations: list[str] = []

    for file_path in SRC_ROOT.rglob('*.py'):
        rel = file_path.relative_to(SRC_ROOT).as_posix()
        for module in _iter_imported_modules(file_path):
            replacement = FORBIDDEN_IMPORTS.get(module)
            if replacement is not None:
                violations.append(f'{rel}: imports {module} ({replacement})')
        for module, name in _iter_from_import_names(file_path):
            replacement = FORBIDDEN_LOCAL_FROM_IMPORTS.get(module, {}).get(name)
            if replacement is not None:
                violations.append(f'{rel}: imports {name} from {module} ({replacement})')

    assert not violations, 'Internal framework imports:\n' + '\n'.join(sorted(violations))

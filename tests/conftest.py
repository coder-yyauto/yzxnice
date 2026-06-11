"""Project-root conftest: make `core`, `admin`, `pyq`, `config`, `database` importable from tests/.

The legacy test files in this directory were authored as run-scripts that expect
the project root on `sys.path` (their `from core.X import ...` imports assume so).
Pytest's default collection finds `tests/` on the path, not the repo root, so
we add it here. Without this, pytest fails at collection with
`ModuleNotFoundError: No module named 'core'`.

The tests themselves are still print/Playwright scripts — pytest will collect
their top-level code on import. Run them directly with `python tests/test_X.py`
when you want real verification, or accept that `pytest tests/ -v` just runs
the import-time side effects.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

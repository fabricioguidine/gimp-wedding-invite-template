"""Pytest setup: put the repo root (for `import tui`) and tests/ (for `_modules`)
on sys.path."""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
for _p in (str(_REPO), str(_HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

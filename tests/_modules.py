"""Shared test helpers: locate the repo and its active modules (no GIMP import)."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = REPO_ROOT / 'modules'
SRC = REPO_ROOT / 'src'
REQUIRED_FILES = ('build.py', 'content.yaml', 'layout.yaml')


def active_module_dirs():
    """Module dirs that have all three of build.py/content.yaml/layout.yaml."""
    if not MODULES_ROOT.exists():
        return []
    return sorted(
        (d for d in MODULES_ROOT.iterdir()
         if d.is_dir() and all((d / f).exists() for f in REQUIRED_FILES)),
        key=lambda d: d.name,
    )


def module_ids():
    return [d.name for d in active_module_dirs()]

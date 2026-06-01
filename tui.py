"""Interactive launcher for the wedding-stationery modules.

Flow:
  1. Pick a module (only those with build.py are listed as active).
  2. Type a run name (default = ISO timestamp).
  2b. Tick which variants to build (checklist; all by default) — or pass
      --variants pageboy,flowergirl to skip the prompt.
  3. Optionally provide a background-image path.
  4. For each leaf field in content.yaml, accept the default (just press Enter)
     or type a replacement. Nested structure preserved.
  5. The modified content is written to outputs/<run>/_content.yaml so
     it's reproducible later.
  6. The chosen module is built via gimp-console-3.2.exe + src/module_runner.py,
     and PNG + PDF are dropped beside the XCF.

Also runnable non-interactively:

    python tui.py --module wedding-invite --run-name my-run \
                  --bg "C:/path/to/bg.jpg" --non-interactive
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

try:
    import questionary
except ImportError:
    questionary = None  # falls back to plain input() if missing


REPO_ROOT = Path(__file__).resolve().parent
MODULES_ROOT = REPO_ROOT / 'modules'
SRC_DIR = REPO_ROOT / 'src'
GIMP_EXE = Path(r'C:\Users\fabri\AppData\Local\Programs\GIMP 3\bin\gimp-console-3.2.exe')


# ----------------------------------------------------------------- ui helpers
def _ask_text(message: str, default: str = '') -> str:
    if questionary is not None:
        return questionary.text(message, default=default).ask() or default
    raw = input('{} [{}]: '.format(message, default)).strip()
    return raw or default


def _ask_select(message: str, choices: list[str]) -> str:
    if questionary is not None:
        return questionary.select(message, choices=choices).ask() or choices[0]
    print(message)
    for i, c in enumerate(choices):
        print('  {}. {}'.format(i + 1, c))
    while True:
        raw = input('Pick [1-{}]: '.format(len(choices))).strip()
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass


def _ask_path(message: str, default: str = '') -> str:
    if questionary is not None:
        return questionary.path(message, default=default, only_directories=False).ask() or default
    return _ask_text(message, default)


def _ask_checkbox(message: str, choices: list[str]) -> list[str]:
    """Multi-select checklist. Returns the chosen subset (defaults to all)."""
    if questionary is not None:
        chosen = questionary.checkbox(
            message,
            choices=[questionary.Choice(c, checked=True) for c in choices],
        ).ask()
        return chosen if chosen else list(choices)
    print(message)
    for i, c in enumerate(choices):
        print('  {}. {}'.format(i + 1, c))
    raw = input('Pick (comma-separated numbers, Enter = all): ').strip()
    if not raw:
        return list(choices)
    picked = []
    for tok in raw.split(','):
        try:
            idx = int(tok) - 1
            if 0 <= idx < len(choices):
                picked.append(choices[idx])
        except ValueError:
            pass
    return picked or list(choices)


def _select_variants(content: dict[str, Any], requested: str | None,
                     interactive: bool) -> dict[str, Any]:
    """Filter content['variants'] to a chosen subset (checklist / --variants /
    all). The build engine skips variants absent from content['variants']."""
    variants = content.get('variants')
    if not isinstance(variants, dict) or len(variants) <= 1:
        return content
    keys = list(variants.keys())
    if requested:
        wanted = {v.strip() for v in requested.split(',') if v.strip()}
        chosen = [k for k in keys if k in wanted] or keys
    elif interactive:
        chosen = _ask_checkbox('Which variants to build? (space toggles, enter confirms)', keys)
    else:
        chosen = keys
    content = dict(content)
    content['variants'] = {k: variants[k] for k in keys if k in chosen}
    return content


# ------------------------------------------------------------------ discovery
def _list_modules() -> list[dict[str, Any]]:
    """Return [{name, dir, active}] for every modules/* dir."""
    out: list[dict[str, Any]] = []
    if not MODULES_ROOT.exists():
        return out
    for d in sorted(p for p in MODULES_ROOT.iterdir() if p.is_dir()):
        active = (d / 'build.py').exists() and (d / 'content.yaml').exists() \
            and (d / 'layout.yaml').exists()
        out.append({'name': d.name, 'dir': d, 'active': active})
    return out


# ------------------------------------------------------------------- editing
def _walk_and_prompt(obj: Any, path: str = '') -> Any:
    """Recursively walk a YAML-loaded structure prompting for every leaf.

    Scalar leaves (str, int, float, bool) become input prompts.
    Lists of scalars are joined with ' | ' and re-split on submit.
    Lists/dicts of complex items recurse.
    """
    if isinstance(obj, dict):
        return {k: _walk_and_prompt(v, _join(path, k)) for k, v in obj.items()}
    if isinstance(obj, list):
        if obj and all(isinstance(x, (str, int, float, bool)) for x in obj):
            joined = ' | '.join(str(x) for x in obj)
            raw = _ask_text('{} (separate items with " | ")'.format(path), default=joined)
            return [_coerce(x.strip()) for x in raw.split('|')] if raw else obj
        return [_walk_and_prompt(x, '{}[{}]'.format(path, i)) for i, x in enumerate(obj)]
    if obj is None:
        return obj
    if isinstance(obj, bool):
        return obj
    raw = _ask_text(path, default=str(obj))
    return _coerce(raw)


def _join(prefix: str, key: str) -> str:
    return key if not prefix else '{}.{}'.format(prefix, key)


def _coerce(raw: str) -> Any:
    """Best-effort: turn '42' into int, '3.14' into float, keep strings."""
    if raw == '':
        return raw
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# --------------------------------------------------------------------- build
def _yaml_to_json_file(yaml_obj: Any, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(yaml_obj, default=str, indent=2),
                        encoding='utf-8')


def _prepare_run(module: dict[str, Any], run_name: str,
                 content: dict[str, Any]) -> dict[str, str]:
    """Persist per-run content/layout (yaml + json); return a manifest entry."""
    module_dir: Path = module['dir']
    run_dir = module_dir / 'outputs' / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    # Persist the chosen content (reproducibility) + a layout copy.
    (run_dir / '_content.yaml').write_text(
        yaml.safe_dump(content, allow_unicode=True, sort_keys=False),
        encoding='utf-8',
    )
    layout = yaml.safe_load((module_dir / 'layout.yaml').read_text(encoding='utf-8'))
    shutil.copy(module_dir / 'layout.yaml', run_dir / '_layout.yaml')
    # Bridge YAML -> JSON for the GIMP-embedded Python (no pyyaml there).
    layout_json = run_dir / '_layout.json'
    content_json = run_dir / '_content.json'
    _yaml_to_json_file(layout, layout_json)
    _yaml_to_json_file(content, content_json)
    return {
        'name': module['name'], 'dir': str(module_dir),
        'layout_json': str(layout_json), 'content_json': str(content_json),
        'run_dir': str(run_dir),
    }


def _invoke_gimp(env: dict[str, str]) -> int:
    """Run gimp-console once with the module_runner batch; return its exit code."""
    if not GIMP_EXE.exists():
        print('ERR: gimp-console not found at {}'.format(GIMP_EXE), file=sys.stderr)
        return 2
    # Forward-slashes so backslashes don't get interpreted as escapes in the
    # GIMP batch interpreter string.
    src_for_batch = str(SRC_DIR).replace('\\', '/')
    batch = ("import sys; sys.path.insert(0, r'{}'); "
             "import module_runner".format(src_for_batch))
    proc = subprocess.run(
        [str(GIMP_EXE), '-i', '-d', '--quit',
         '--batch-interpreter=python-fu-eval', '-b', batch],
        env=env, check=False,
    )
    return proc.returncode


def _build(module: dict[str, Any], run_name: str, bg_path: str | None,
           content: dict[str, Any]) -> int:
    entry = _prepare_run(module, run_name, content)
    env = os.environ.copy()
    env.pop('WEDDING_MANIFEST', None)
    env.update({
        'WEDDING_MODULE': entry['name'],
        'WEDDING_MODULE_DIR': entry['dir'],
        'WEDDING_LAYOUT_JSON': entry['layout_json'],
        'WEDDING_CONTENT_JSON': entry['content_json'],
        'WEDDING_RUN_DIR': entry['run_dir'],
    })
    if bg_path:
        env['WEDDING_BG_PATH'] = bg_path

    print('\n[tui] invoking GIMP for module={} run={}'.format(entry['name'], run_name))
    rc = _invoke_gimp(env)
    if rc == 0:
        print('\n[tui] done. Artifacts: {}'.format(entry['run_dir']))
    else:
        print('GIMP exited with code {}'.format(rc), file=sys.stderr)
    return rc


def _build_all(modules: list[dict[str, Any]], run_name: str) -> int:
    """Build every given module in ONE GIMP session (defaults from each content.yaml)."""
    entries = [_prepare_run(m, run_name,
                            yaml.safe_load((m['dir'] / 'content.yaml').read_text(encoding='utf-8')))
               for m in modules]
    manifest = Path(tempfile.gettempdir()) / 'wedding_manifest_{}.json'.format(run_name)
    manifest.write_text(json.dumps(entries, default=str, indent=2), encoding='utf-8')
    env = os.environ.copy()
    env['WEDDING_MANIFEST'] = str(manifest)
    print('\n[tui] building {} modules in one GIMP session: {}'.format(
        len(entries), ', '.join(e['name'] for e in entries)))
    rc = _invoke_gimp(env)
    try:
        manifest.unlink()
    except OSError:
        pass
    if rc == 0:
        print('\n[tui] done. {} modules built.'.format(len(entries)))
    else:
        print('GIMP exited with code {}'.format(rc), file=sys.stderr)
    return rc


# ---------------------------------------------------------------------- main
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Wedding-stationery module launcher.')
    p.add_argument('--module', help='Skip module picker (e.g. wedding-invite).')
    p.add_argument('--variants', help='Comma-separated subset of variants to '
                   'build (e.g. "pageboy,flowergirl"). Default: all.')
    p.add_argument('--run-name', help='Skip run-name prompt.')
    p.add_argument('--bg', dest='bg', help='Background image path.')
    p.add_argument('--non-interactive', action='store_true',
                   help='Use defaults from content.yaml without prompting per field.')
    p.add_argument('--all', dest='build_all', action='store_true',
                   help='Build every active module in ONE GIMP session (content.yaml defaults).')
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    modules = _list_modules()
    if not modules:
        print('No modules found under {}'.format(MODULES_ROOT), file=sys.stderr)
        return 2

    active = [m for m in modules if m['active']]
    inactive = [m for m in modules if not m['active']]

    if args.build_all:
        if not active:
            print('No active modules to build.', file=sys.stderr)
            return 2
        run_name = (args.run_name or 'run-' + _dt.datetime.now().strftime('%Y%m%d-%H%M%S'))
        return _build_all(active, run_name.replace(' ', '-'))

    if args.module:
        match = next((m for m in modules if m['name'] == args.module), None)
        if not match or not match['active']:
            print('Module {!r} not found or not active.'.format(args.module),
                  file=sys.stderr)
            print('Active: {}'.format(', '.join(m['name'] for m in active)),
                  file=sys.stderr)
            return 2
        module = match
    else:
        labels = []
        for m in active:
            labels.append(m['name'])
        for m in inactive:
            labels.append('{}  (TODO — not yet implemented)'.format(m['name']))
        choice = _ask_select('Which module to build?', labels)
        chosen_name = choice.split()[0]
        module = next(m for m in modules if m['name'] == chosen_name)
        if not module['active']:
            print('{} is a stub — open its README.md.'.format(module['name']))
            return 0

    default_run = 'run-' + _dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    run_name = args.run_name or _ask_text('Run name (no spaces)', default=default_run)
    run_name = run_name.replace(' ', '-')

    bg_path = args.bg
    if bg_path is None and not args.non_interactive:
        raw = _ask_path('Background image path (Enter to skip)', default='')
        bg_path = raw.strip() or None
    if bg_path and not Path(bg_path).exists():
        print('warn: bg image not found at {} — proceeding without it.'.format(bg_path))
        bg_path = None

    content = yaml.safe_load(
        (module['dir'] / 'content.yaml').read_text(encoding='utf-8')
    )
    content = _select_variants(content, args.variants, not args.non_interactive)
    if not args.non_interactive:
        print('\nEdit each text field, or press Enter to keep the default.')
        print('Tip: keep replacement text a similar length to avoid border clipping.\n')
        content = _walk_and_prompt(content)

    return _build(module, run_name, bg_path, content)


if __name__ == '__main__':
    sys.exit(main())

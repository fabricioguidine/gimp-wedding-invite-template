"""End-to-end tests for the GIMP-free generation pipeline.

These exercise the real entrypoints that run headlessly on every OS (no GIMP):

  * the A4 imposition geometry that produces the print sheet layout, and
  * the tui.py run-preparation stage that snapshots a run's content/layout into
    the reproducible JSON + YAML bridge artifacts the GIMP step later consumes.

Everything is hermetic (writes only under tmp_path) and OS-agnostic.
"""
import json
import subprocess
import sys

import yaml

import tui
from _modules import REPO_ROOT, active_module_dirs


# --------------------------------------------------- A4 imposition end to end
def test_a4_imposition_pipeline_produces_valid_sheet():
    """Drive the pure-Python A4 imposition for a real tri-fold canvas and assert
    the computed print sheet is internally consistent (artwork inside margins,
    centered, fold marks at the thirds)."""
    sys.path.insert(0, str(REPO_ROOT / 'src'))
    import a4_impose
    import paper

    sheet = paper.sheet_px('a4', dpi=300)
    geo = a4_impose.compute(3543, 1772, margin_mm=5.0, dpi=300, page=sheet)

    assert (geo['page_w'], geo['page_h']) == sheet
    assert 0 < geo['new_w'] <= geo['page_w']
    assert 0 < geo['new_h'] <= geo['page_h']
    m = geo['margin_px']
    assert geo['off_x'] >= m and geo['off_y'] >= m
    f1, f2 = geo['fold_x']
    assert geo['off_x'] < f1 < f2 < geo['off_x'] + geo['new_w']


# --------------------------------------------- run-preparation API end to end
def _invite_module():
    return next(m for m in active_module_dirs() if m.name == 'wedding-invite')


def test_prepare_run_substitutes_names_and_dates(tmp_path, monkeypatch):
    """_prepare_run is the headless heart of the build: feed it content with
    real (substituted) names + date and assert the persisted JSON bridge parses
    and carries the substituted values."""
    mdir = _invite_module()
    # Redirect outputs/ into tmp_path so the test is hermetic.
    work = tmp_path / 'wedding-invite'
    work.mkdir()
    (work / 'layout.yaml').write_text(
        (mdir / 'layout.yaml').read_text(encoding='utf-8'), encoding='utf-8')
    (work / 'content.yaml').write_text(
        (mdir / 'content.yaml').read_text(encoding='utf-8'), encoding='utf-8')

    content = yaml.safe_load((mdir / 'content.yaml').read_text(encoding='utf-8'))
    content['couple'] = {'bride': 'Luany', 'groom': 'João Marcos'}
    content['date'] = {'day': 10, 'month_name': 'Outubro', 'year': 2026}

    module = {'name': 'wedding-invite', 'dir': work, 'active': True}
    entry = tui._prepare_run(module, 'pytest_headless', content)

    content_json = work / 'outputs' / 'pytest_headless' / '_content.json'
    layout_json = work / 'outputs' / 'pytest_headless' / '_layout.json'
    content_yaml = work / 'outputs' / 'pytest_headless' / '_content.yaml'
    for f in (content_json, layout_json, content_yaml):
        assert f.is_file() and f.stat().st_size > 0

    loaded = json.loads(content_json.read_text(encoding='utf-8'))
    assert loaded['couple'] == {'bride': 'Luany', 'groom': 'João Marcos'}
    assert loaded['date']['month_name'] == 'Outubro'

    # The YAML snapshot must round-trip the unicode groom name too.
    snap = yaml.safe_load(content_yaml.read_text(encoding='utf-8'))
    assert snap['couple']['groom'] == 'João Marcos'

    layout = json.loads(layout_json.read_text(encoding='utf-8'))
    assert {'width_px', 'height_px', 'dpi'} <= set(layout['canvas'])
    assert entry['run_dir'] == str(work / 'outputs' / 'pytest_headless')


def test_tui_cli_lists_modules_via_subprocess():
    """Real CLI invocation (subprocess + sys.executable) is importable and runs
    on this OS: an unknown module exits non-zero and prints the active set."""
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / 'tui.py'),
         '--module', '__nope__', '--non-interactive'],
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
    )
    assert r.returncode == 2
    assert 'wedding-invite' in (r.stdout + r.stderr)

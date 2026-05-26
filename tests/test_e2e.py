"""End-to-end build tests: run the real GIMP pipeline and assert artifacts.

Skipped automatically when gimp-console isn't installed (so the static suite
still runs anywhere). These are slow — each launches GIMP.
"""
import base64
import shutil
import subprocess
import sys

import pytest
import yaml

import tui
from _modules import active_module_dirs, module_ids, REPO_ROOT

pytestmark = pytest.mark.skipif(
    not tui.GIMP_EXE.exists(),
    reason='gimp-console not found at {} — e2e build skipped'.format(tui.GIMP_EXE),
)

MODS = active_module_dirs()
IDS = module_ids()

# 1x1 transparent PNG, enough to exercise an inputs/ override path.
_PNG_1x1 = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
    '+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')


def _run_tui(args):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / 'tui.py')] + args,
        cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=900,
    )


def _assert_artifacts(run_dir):
    xcfs = list(run_dir.glob('*.xcf'))
    assert xcfs, 'no XCF produced in {}'.format(run_dir)
    for x in xcfs:
        for ext in ('.png', '.pdf'):
            sib = x.with_suffix(ext)
            assert sib.exists() and sib.stat().st_size > 0, \
                'missing/empty {}'.format(sib.name)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_build_module(mdir):
    run_dir = mdir / 'outputs' / 'pytest_e2e'
    try:
        r = _run_tui(['--module', mdir.name, '--run-name', 'pytest_e2e',
                      '--non-interactive'])
        assert r.returncode == 0, r.stderr[-2000:]
        _assert_artifacts(run_dir)
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def test_build_all_one_session():
    try:
        r = _run_tui(['--all', '--run-name', 'pytest_all', '--non-interactive'])
        assert r.returncode == 0, r.stderr[-2000:]
        for mdir in MODS:
            _assert_artifacts(mdir / 'outputs' / 'pytest_all')
    finally:
        for mdir in MODS:
            shutil.rmtree(mdir / 'outputs' / 'pytest_all', ignore_errors=True)


def test_inputs_logo_override_builds():
    """A bridal module still builds when an inputs/logo.png override is present."""
    bridal = next(
        (m for m in MODS
         if (yaml.safe_load((m / 'content.yaml').read_text(encoding='utf-8')) or {}).get('variants')),
        None)
    if bridal is None:
        pytest.skip('no variant (bridal) module to test the logo override')
    logo = bridal / 'inputs' / 'logo.png'
    pre_existing = logo.exists()
    run_dir = bridal / 'outputs' / 'pytest_override'
    try:
        if not pre_existing:
            logo.write_bytes(_PNG_1x1)
        r = _run_tui(['--module', bridal.name, '--run-name', 'pytest_override',
                      '--non-interactive'])
        assert r.returncode == 0, r.stderr[-2000:]
        _assert_artifacts(run_dir)
    finally:
        if not pre_existing and logo.exists():
            logo.unlink()
        shutil.rmtree(run_dir, ignore_errors=True)

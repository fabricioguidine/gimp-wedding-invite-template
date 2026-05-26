"""Unit tests for the GIMP-free parts of tui.py (launcher logic)."""
import json

import tui


def test_coerce_types():
    assert tui._coerce('42') == 42
    assert tui._coerce('3.14') == 3.14
    assert tui._coerce('hello') == 'hello'
    assert tui._coerce('') == ''


def test_list_modules_marks_active():
    mods = tui._list_modules()
    by_name = {m['name']: m for m in mods}
    assert 'wedding-invite' in by_name
    assert by_name['wedding-invite']['active'] is True
    # wedding-menu ships as a stub (no build.py) -> inactive
    if 'wedding-menu' in by_name:
        assert by_name['wedding-menu']['active'] is False


def test_yaml_to_json_file(tmp_path):
    out = tmp_path / 'x.json'
    tui._yaml_to_json_file({'a': 1, 'b': [1, 2], 'c': {'d': 'e'}}, out)
    assert json.loads(out.read_text(encoding='utf-8')) == {'a': 1, 'b': [1, 2], 'c': {'d': 'e'}}


def test_prepare_run_writes_bridge_files(tmp_path):
    """_prepare_run should persist _content/_layout (yaml+json) and a manifest entry,
    without invoking GIMP."""
    mods = {m['name']: m for m in tui._list_modules() if m['active']}
    module = mods['wedding-invite']
    content = {'hello': 'world', 'n': 1}
    entry = tui._prepare_run(module, 'pytest_prepare', content)
    try:
        run_dir = module['dir'] / 'outputs' / 'pytest_prepare'
        assert (run_dir / '_content.json').is_file()
        assert (run_dir / '_layout.json').is_file()
        assert json.loads((run_dir / '_content.json').read_text(encoding='utf-8')) == content
        assert entry['name'] == 'wedding-invite'
        assert entry['run_dir'] == str(run_dir)
    finally:
        import shutil
        shutil.rmtree(module['dir'] / 'outputs' / 'pytest_prepare', ignore_errors=True)

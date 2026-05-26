"""Static validation of every active module (no GIMP needed)."""
import ast

import pytest
import yaml

from _modules import active_module_dirs, module_ids, REQUIRED_FILES

MODS = active_module_dirs()
IDS = module_ids()


def _content(mdir):
    return yaml.safe_load((mdir / 'content.yaml').read_text(encoding='utf-8'))


def _layout(mdir):
    return yaml.safe_load((mdir / 'layout.yaml').read_text(encoding='utf-8'))


def test_at_least_one_module():
    assert MODS, 'no active modules found under modules/'


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_required_files(mdir):
    for f in REQUIRED_FILES:
        assert (mdir / f).is_file(), '{} missing {}'.format(mdir.name, f)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_yaml_parses(mdir):
    assert isinstance(_content(mdir), dict) and _content(mdir)
    assert isinstance(_layout(mdir), dict) and _layout(mdir)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_build_defines_run(mdir):
    tree = ast.parse((mdir / 'build.py').read_text(encoding='utf-8'))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert 'run' in funcs, '{}/build.py must define a top-level run()'.format(mdir.name)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_layout_schema(mdir):
    layout = _layout(mdir)
    canvas = layout.get('canvas', {})
    for k in ('width_px', 'height_px', 'dpi'):
        assert k in canvas, '{} layout.canvas missing {}'.format(mdir.name, k)
    assert 'fonts' in layout, '{} layout missing fonts'.format(mdir.name)
    assert 'text_color' in layout, '{} layout missing text_color'.format(mdir.name)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_variant_modules_schema(mdir):
    content = _content(mdir)
    variants = content.get('variants')
    if not variants:
        pytest.skip('{} is not a variant (bridal-style) module'.format(mdir.name))
    for k in ('couple', 'date', 'tips'):
        assert k in content, '{} missing shared block {}'.format(mdir.name, k)
    for name, v in variants.items():
        assert 'cover' in v, '{}/{} missing cover'.format(mdir.name, name)
        assert ('role' in v) or ('roles' in v), \
            '{}/{} needs role or roles'.format(mdir.name, name)


@pytest.mark.parametrize('mdir', MODS, ids=IDS)
def test_palette_colors_match_names(mdir):
    """Each role's colors list lines up with its color_names list."""
    content = _content(mdir)
    for vname, v in (content.get('variants') or {}).items():
        roles = [v['role']] if 'role' in v else list(v.get('roles', {}).values())
        for role in roles:
            if isinstance(role, dict) and 'colors' in role:
                assert len(role['colors']) == len(role.get('color_names', [])), \
                    '{}/{}: colors vs color_names length mismatch'.format(mdir.name, vname)

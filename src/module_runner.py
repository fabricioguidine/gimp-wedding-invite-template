"""Generic per-module GIMP build dispatcher.

Each deliverable lives under ``modules/<name>/`` with its own ``layout.yaml``,
``content.yaml``, and ``build.py``. ``run.ps1`` (or ``tui.py``) invokes this
file inside ``gimp-console-3.2.exe``; the chosen module name + paths come in
through env vars so we don't have to parse argv inside the batch interpreter.

Expected env vars (set by run.ps1):
    WEDDING_MODULE        - e.g. 'wedding-invite'
    WEDDING_MODULE_DIR    - absolute path to that module's dir
    WEDDING_LAYOUT_JSON   - path to layout.yaml-converted-to-JSON
    WEDDING_CONTENT_JSON  - path to content.yaml-converted-to-JSON
    WEDDING_RUN_DIR       - absolute path to outputs/<run-name>/ (already mkdir-ed)
    WEDDING_BG_PATH       - optional absolute path to background image (or empty)

Module contract: every ``modules/<name>/build.py`` exports

    def run(layout, content, bg_path, output_dir, module_name) -> list[str]

returning a list of XCF paths it saved. The runner then exports each as
PNG and PDF next to the XCF.
"""

import json
import os
import sys
from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise RuntimeError("env var {} is not set".format(name))
    return v


def _load_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def _import_module_build(module_dir):
    """Import modules/<name>/build.py without clashing with any other build.py.

    Order matters: src/ (shared primitives) goes on sys.path FIRST so it's
    LATER in the import search order. Then module_dir goes on top so its
    build.py wins lookup. We also pop any previously-cached 'build' module
    to make subsequent imports clean (relevant for tests / repeated runs).
    """
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root / 'src'))
    sys.path.insert(0, str(module_dir))
    sys.modules.pop('build', None)
    import build as module_build  # noqa: E402
    return module_build


def _export(xcf_path):
    """Flatten the XCF and re-save it as PNG and PDF beside it."""
    xcf = Path(xcf_path)
    png = xcf.with_suffix('.png')
    pdf = xcf.with_suffix('.pdf')

    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                           Gio.File.new_for_path(str(xcf)))
    image.flatten()
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
                   Gio.File.new_for_path(str(png)), None)
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
                   Gio.File.new_for_path(str(pdf)), None)
    image.delete()
    return png, pdf


def main():
    Gegl.init(None)

    module_name = _env('WEDDING_MODULE')
    module_dir = Path(_env('WEDDING_MODULE_DIR'))
    layout = _load_json(_env('WEDDING_LAYOUT_JSON'))
    content = _load_json(_env('WEDDING_CONTENT_JSON'))
    run_dir = Path(_env('WEDDING_RUN_DIR'))
    bg_path = os.environ.get('WEDDING_BG_PATH') or None

    run_dir.mkdir(parents=True, exist_ok=True)

    module_build = _import_module_build(module_dir)

    xcf_paths = module_build.run(
        layout=layout,
        content=content,
        bg_path=bg_path,
        output_dir=str(run_dir),
        module_name=module_name,
    )
    if not xcf_paths:
        raise RuntimeError("module '{}' did not return any XCF paths".format(module_name))

    print('[module_runner] {} produced {} XCF(s):'.format(module_name, len(xcf_paths)))
    for xcf in xcf_paths:
        png, pdf = _export(xcf)
        print('  + {}'.format(Path(xcf).name))
        print('     -> {}'.format(Path(png).name))
        print('     -> {}'.format(Path(pdf).name))


main()

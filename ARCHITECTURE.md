# Architecture

This project generates print-ready wedding stationery. It is split into a
**host layer** (plain cross-platform Python that orchestrates and prepares
each run) and a **render layer** (GIMP 3 + its embedded Python, which actually
draws the artwork). Only the render layer needs GIMP; everything else runs and
is tested headlessly on Linux, macOS, and Windows.

## Layers

```
                 host Python (any OS)                 GIMP 3 embedded Python
  ┌───────────────────────────────────────┐   env    ┌──────────────────────────┐
  │ run.ps1 ─▶ tui.py                       │  vars /  │ src/module_runner.py      │
  │   discover modules/, prompt/override,   │  JSON    │   imports modules/<m>/    │
  │   snapshot content+layout to JSON ──────┼─────────▶│   build.py, composes from │
  │   then launch gimp-console              │  bridge  │   src/ primitives, saves  │
  └───────────────────────────────────────┘          │   XCF → PNG/PDF (+A4 PDF) │
                                                       └──────────────────────────┘
```

The host never imports `gi`; the render code imports `gi` at module top. They
communicate over: environment variables (`WEDDING_*`) and JSON files written
into `modules/<name>/outputs/<run>/` (`_content.json`, `_layout.json`). GIMP's
embedded Python has no `PyYAML`, so the host converts YAML→JSON for it.

## Component map

| Path | Layer | Imports GIMP? | Role |
|------|-------|---------------|------|
| `tui.py` | host | no | Interactive/CLI launcher; module discovery, per-field prompts, run preparation, GIMP invocation. |
| `run.ps1` | host | no | Windows convenience wrapper around `tui.py`. |
| `src/a4_impose.py` | shared (pure) | **no** | A4/imposition geometry: scale-to-fit, centering, fold positions. |
| `src/paper.py` | shared (pure) | **no** | Print-paper sizing (A4 / US Letter), name normalization. |
| `src/panels.py` | shared (pure) | **no** | Tri-fold panel rectangle layout. |
| `src/document.py` | render | yes | Canvas creation, color helpers, fold guides. |
| `src/a4_render.py` | render | yes | Draws the imposed sheet + fold marks (uses `a4_impose`). |
| `src/text_utils.py` | render | yes | Font resolution + text-layer placement. |
| `src/borders.py`, `src/calendar_panel.py`, `src/palette.py` | render | yes | Decorative borders, save-the-date calendar, palette swatches. |
| `src/trifold_blocks.py` | render | yes | Shared tri-fold leaflet engine (sponsors + juniors). |
| `src/module_runner.py` | render | yes | Per-run dispatcher inside `gimp-console`: imports the module `build.py`, exports XCF→PNG/PDF. |
| `modules/<name>/build.py` | render | yes | Module entrypoint `run(layout, content, bg_path, output_dir, module_name) -> [xcf_paths]`. |
| `modules/<name>/{content,layout}.yaml` | data | – | Text content and geometry per module. |
| `tools/yaml_to_json.py`, `tools/crop_logo.py`, `tools/canva_scrape.py` | host tools | no (PIL/Playwright) | Standalone host-side helpers. |
| `tools/export_*.py`, `tools/inspect_xcf.py` | render tools | yes | GIMP batch helpers. |

## Module contract

A directory under `modules/` is **active** when it has all three of `build.py`,
`content.yaml`, `layout.yaml`. Its `build.py` must define a top-level
`run(layout, content, bg_path, output_dir, module_name)` returning the list of
saved `.xcf` paths; `module_runner` then flattens each and writes PNG + PDF
beside it (plus an A4-landscape PDF for tri-fold modules).

## Cross-platform notes

- All filesystem paths use `pathlib`; text I/O is `encoding="utf-8"`, image I/O
  is binary. `tui.py` reconfigures stdout/stderr to UTF-8 (guarded).
- `gimp-console` is discovered via `WEDDING_GIMP_EXE` → `PATH` → per-OS default,
  so no Windows path is hardcoded.
- Pure modules never import `gi`, so they import and run on machines without
  GIMP — which is what the headless test suite and CI rely on.

## What CI cannot test

GIMP cannot run in CI (no display, heavy install, GObject-Introspection
stack). So the render layer (`gi`-importing modules and the full XCF→PNG/PDF
build) is **not** exercised in CI. Those builds live in `tests/test_e2e.py`,
marked `e2e` and deselected by default; run them locally with `pytest -m e2e`
on a machine with GIMP installed. CI runs only the pure-Python headless suite.

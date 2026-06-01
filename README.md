# gimp-wedding-invite-template

A YAML-driven GIMP 3 + Python generator for print-ready wedding stationery. Text lives in `content.yaml`, geometry in `layout.yaml`, and shared GIMP primitives in `src/`; an interactive TUI fills in the fields and renders PNG + PDF through GIMP's console.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/) [![GIMP 3](https://img.shields.io/badge/GIMP-3-5C5543.svg?logo=gimp&logoColor=white)](https://www.gimp.org/)

![wedding-invite sample](modules/wedding-invite/template/template.png)

## Features

- **YAML-driven content and layout** — words live in `content.yaml`, geometry in `layout.yaml`; both are merged and snapshotted per run for reproducibility.
- **Interactive TUI** — `tui.py` (wrapped by `run.ps1`) walks every field in `content.yaml`, prompting for each (Enter keeps the default), or runs `--non-interactive` from the defaults.
- **Multiple delivery modules** — a single-page invite plus tri-fold (Z-fold) sponsor and junior-attendant manuals, each auto-discovered under `modules/`.
- **Print-ready output** — every run emits an editable `.xcf`, a 300 DPI `.png` preview, and a native-size `.pdf`; tri-fold modules also emit a paper-imposed landscape PDF with equal 5 mm margins and fold marks.
- **Selectable paper** — set `paper: a4` or `paper: letter` in `content.yaml`; the canvas is sized to that sheet's printable area so margins and text wrap adapt.
- **Cormorant Garamond typography** with a Georgia fallback.

## Requirements

- GIMP 3 (developed against 3.2.4) — the console binary `gimp-console-3.2.exe` must be on PATH or at its default install location.
- Python 3.13 on the system PATH, with `pyyaml` (required) and `questionary` (optional; nicer TUI, falls back to plain `input()`).
- GIMP's embedded Python is invoked separately by the console and only needs the standard library plus `gi.repository.Gimp`.

```powershell
pip install pyyaml questionary
```

## How to run

```powershell
# Interactive: pick a module, fill in fields, supply a background image
.\run.ps1

# Build one module straight from its content.yaml defaults
.\run.ps1 wedding-invite

# List known modules
.\run.ps1 -List

# Non-interactive: accept defaults, no prompts
python tui.py --module wedding-invite --run-name my-run --non-interactive

# With a custom background image
python tui.py --module wedding-invite --run-name my-run --bg "C:/path/to/bg.jpg"

# Rebuild every active module in one GIMP session
python tui.py --all --non-interactive

# Build only some variants of a module
python tui.py --module wedding-juniors --variants pageboy --non-interactive
```

The TUI snapshots the merged content/layout to JSON, then dispatches into `gimp-console-3.2.exe -b`, where `src/module_runner.py` imports the chosen module's `build.py`, composes the panels, saves the `.xcf`, then flattens and exports PNG + PDF.

Output lands in `modules/<module>/outputs/<run-name>/`:

```
modules/wedding-invite/outputs/my-run/
├── _content.yaml   # exact content used (reproducible)
├── _layout.yaml    # layout snapshot
├── _content.json   # bridge into GIMP's embedded Python
├── _layout.json
├── wedding-invite.xcf   # editable GIMP source
├── wedding-invite.png   # 300 DPI preview
└── wedding-invite.pdf   # print-ready (native size)
```

Tri-fold modules additionally emit a paper-imposed PDF per side, named after the paper (`*_a4.pdf` / `*_letter.pdf`). Print those at landscape, actual size (not "fit to page").

## Content / YAML schema

Each module pairs a `content.yaml` (text) with a `layout.yaml` (geometry). For `wedding-invite`, the content fields are:

| Field | Type | Meaning |
|-------|------|---------|
| `verse.text` / `verse.reference` | string | Opening scripture line and its citation |
| `blessing` | string | Uppercase blessing line |
| `parents.bride[]` / `parents.groom[]` | list of strings | Two-column parents block (left / right) |
| `couple.bride` / `couple.groom` | string | The two first names |
| `invitation` | string | Uppercase invitation line |
| `day` | string | Weekday name |
| `date.day` / `date.month_name` / `date.year` | int / string / int | Ceremony date parts |
| `ceremony.time` / `ceremony.venue` / `ceremony.address` | string | Ceremony details |
| `reception.venue` / `reception.address` | string | Reception details |
| `rsvp.intro` / `rsvp.detail` | string | Bottom RSVP / registry lines |

Geometry lives in `layout.yaml`: `canvas` (width/height/DPI, background color), `text_color`, `fonts` (a `family` + `fallback` per role), `blocks` (each block's vertical center `y_pct`, font role, and pixel sizes at 300 DPI), and `background_layers` / `background_image` (composited below all text). Tri-fold modules add a `fold:` block and a `variants:` map; the runner uses `fold:` to emit the paper-imposed PDF.

```yaml
couple:
  bride: "Emily"
  groom: "James"
date:
  day: 10
  month_name: "October"
  year: 2026
ceremony:
  time: "At 5:30 PM hour"
  venue: "Our Lady of the Rosary Parish Church"
  address: "123 Sample Avenue, Suite 230"
```

The committed `template/template*.{png,pdf,xcf}` files carry English placeholders only (no real names or contact details); real content is supplied per run and never committed.

## Layout (tri-fold / Z-fold)

Tri-fold modules print on a single landscape sheet folded into three equal panels, with each side (`externo` / `interno`) rendered separately:

```
externo (outside, seen folded)        interno (inside, seen open)
┌─────────┬─────────┬─────────┐        ┌─────────┬─────────┬─────────┐
│  back   │  fold   │  front  │        │  left   │ center  │  right  │
│ monogram│  flap   │  cover  │        │ mission │  role   │  tips   │
└─────────┴─────────┴─────────┘        └─────────┴─────────┴─────────┘
       fold      fold                         fold      fold
```

The leaflet canvas is sized to the chosen paper's landscape printable area (sheet minus 5 mm on every side @ 300 DPI; A4 ≈ 28.7×20 cm, US Letter ≈ 26.9×20.6 cm), so the export sits with equal 5 mm margins and thin fold marks at the thirds. The single-page `wedding-invite` is one portrait panel (5×7" @ 300 DPI), shown above.

## Project structure

```
gimp-wedding-invite-template/
├── modules/
│   ├── wedding-invite/      # single portrait page (5×7")
│   │   ├── template/        # committed example PNG/PDF/XCF (English placeholders)
│   │   ├── inputs/          # user-supplied images (gitignored)
│   │   ├── outputs/<run>/   # PNG + PDF per run (gitignored)
│   │   ├── content.yaml     # text fields
│   │   ├── layout.yaml      # canvas, fonts, block positions
│   │   └── build.py         # run(layout, content, bg_path, output_dir, module_name)
│   ├── wedding-sponsors/    # tri-fold; bridesmaid / groomsman / couple variants
│   ├── wedding-juniors/     # tri-fold; page boy / flower girl variants
│   └── wedding-menu/         # TODO stub (README only)
├── src/                     # shared GIMP primitives + module_runner dispatcher
├── tools/                   # standalone utilities (fonts, export, inspect)
├── assets/                  # backgrounds, ornaments, palette references
├── tests/                   # structure / TUI / A4 imposition / e2e
├── tui.py                   # interactive launcher
├── run.ps1                  # PowerShell wrapper around tui.py
└── pytest.ini
```

A directory under `modules/` is auto-discovered as an active module when it has all three of `build.py`, `layout.yaml`, and `content.yaml`; one missing them (e.g. `wedding-menu`) is treated as a TODO stub and skipped by `--all`.

## Tests

```powershell
pip install pytest

# Static checks only (fast, no GIMP)
pytest tests/test_structure.py tests/test_tui.py

# Everything, including end-to-end GIMP builds (auto-skipped if GIMP is absent)
pytest
```

`tests/test_a4_impose.py` unit-tests the pure A4 imposition geometry without GIMP; `tests/test_e2e.py` builds each module for real and asserts the artifacts exist.

## License

[MIT](LICENSE)

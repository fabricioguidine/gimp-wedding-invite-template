# gimp-wedding-invite-template

Per-deliverable wedding-stationery generator using **GIMP 3.2 + Python
(GObject Introspection)**, driven by an interactive TUI.

Each *delivery module* under `modules/` owns its own layout, content, and
build script, and produces print-ready PNG + PDF artifacts via
`gimp-console-3.2.exe`.

## Modules

| Module               | Status | Output                                                                     |
|----------------------|--------|----------------------------------------------------------------------------|
| `wedding-invite`     | active | 1 portrait page (5×7" @ 300 DPI)                                           |
| `wedding-bridesmaid` | active | 3 tri-fold leaflet variants (madrinha / padrinho / casal), 2 sides → 6 XCFs (30×15 cm) |
| `wedding-menu`       | TODO   | reception menu card                                                        |
| `wedding-pages`      | active | 2 tri-fold leaflet variants (pajem / daminha), 2 sides → 4 XCFs (30×15 cm) |

The `wedding-bridesmaid` module builds all three bridal-party manuals
(`madrinha` / `padrinho` / `casal`) in a single run. They share the common
externo + mission + tips blocks via `src/bridal_party_blocks.py`; only the
middle interno panel differs per variant (single-role center for
madrinha/padrinho, split center for casal). Per-variant cover/role data lives
under `variants:` in `content.yaml`, and `layout.yaml` splits `interno.middle`
into `single:` / `split:` sub-maps.

`wedding-pages` reuses the same tri-fold (`src/bridal_party_blocks.py`) for the
kids — `pajem` / `daminha`, both single-role — in Portuguese with a playful
tone: a per-variant invite (`mission`, "Aceita ser nosso Pajem?"), an outfit
instruction (`role`), the Marsala & Azul palette, kid icons (teddy / car /
balloons), and an optional cover illustration slot at `assets/kids/<name>.png`.

Active modules produce a committed `template/template.{png,pdf,xcf}` rendered
with **English placeholder text** of similar letter-count to the Portuguese
original — so when real names/venues are plugged in via the TUI, the layout
stays stable.

## Quickstart

```powershell
# One-time: install Python deps
pip install pyyaml questionary

# Interactive run — pick a module, fill in text fields, supply bg image
.\run.ps1

# Non-interactive — accept defaults from content.yaml, no prompts
python tui.py --module wedding-invite --run-name my-run --non-interactive

# With a custom background image
python tui.py --module wedding-invite --run-name my-run --bg "C:/path/to/bg.jpg"

# Rebuild EVERY active module in ONE GIMP session (one startup instead of N)
python tui.py --all --non-interactive
```

Output lands in `modules/<module>/outputs/<run-name>/`:

```
modules/wedding-invite/outputs/my-run/
├── _content.yaml          # exact content used for this run (reproducible)
├── _layout.yaml           # snapshot of layout
├── _content.json          # bridge into GIMP's embedded Python
├── _layout.json
├── wedding-invite.xcf     # editable GIMP source
├── wedding-invite.png     # 300 DPI preview
└── wedding-invite.pdf     # print-ready
```

## Customizing

Everything text-based is editable per run through the TUI — it walks every field
in `content.yaml` and prompts for each (Enter keeps the default): couple names,
date, ceremony, tips, and per-variant cover title, invite (`mission`:
title / body / highlight / verse) and outfit (`role`: title / body / palette).

A few `content.yaml` knobs adjust the look without touching code:

- `background_color` — canvas colour (overrides `layout.yaml`).
- `images.logo_pct` / `images.cover_pct` — size of the override art (0–1 of the
  available area; `1.0` = as large as fits).
- `date.locale` — weekday-header language (`en` / `pt` / `es` / `fr` / `it` /
  `de`); the calendar day initials are filled automatically.

Image elements are swapped by dropping PNGs into a module's `inputs/` folder
(no code edit, no TUI):

- `inputs/logo.png` — back-cover monogram.
- `inputs/background.png` — full-bleed background image.
- `inputs/<variant>.png` — cover illustration (e.g. `inputs/pajem.png`).

## Architecture

```
gimp-wedding-invite-template/
├── modules/
│   ├── wedding-invite/
│   │   ├── template/          # committed example PNG/PDF (English placeholders)
│   │   ├── inputs/            # user-supplied bg images (gitignored)
│   │   ├── outputs/<run>/     # PNG + PDF per run (gitignored)
│   │   ├── content.yaml       # text fields, English placeholders
│   │   ├── layout.yaml        # canvas, fonts, block positions
│   │   └── build.py           # `run(layout, content, bg_path, output_dir, module_name)`
│   ├── wedding-bridesmaid/          # same shape, tri-fold; 3 variants → 6 XCFs
│   ├── wedding-menu/                # TODO stub
│   └── wedding-pages/               # pajem & daminha, tri-fold; 2 variants → 4 XCFs
├── src/                              # shared GIMP primitives
│   ├── document.py            # canvas + color helpers
│   ├── panels.py              # tri-fold rect math
│   ├── borders.py             # decorative stroke + path
│   ├── text_utils.py          # font resolution + text-layer creation + wrap
│   ├── palette.py             # color-circle row
│   ├── calendar_panel.py      # month grid + day highlight
│   ├── bridal_party_blocks.py # shared tri-fold engine: run_variants + cover/
│   │                          #   calendar/mission/role/split/tips/palette
│   └── module_runner.py       # dispatcher (single module, or --all via manifest)
├── tools/                            # standalone utilities (fonts, scraping, etc.)
├── assets/ornaments/                 # logo.png, icons/*.svg
├── tui.py                            # interactive launcher (questionary)
└── run.ps1                           # PowerShell wrapper around tui.py
```

### Module contract

Every `modules/<name>/build.py` exports a single function:

```python
def run(layout, content, bg_path, output_dir, module_name) -> list[str]:
    """Build the deliverable. Return list of saved .xcf paths.

    The generic runner re-loads each XCF, flattens it, and saves PNG + PDF
    alongside.
    """
```

A module that produces multiple files (e.g. `wedding-bridesmaid` builds three
variants × externo + interno sides) returns multiple XCF paths.

## Adding a new module

1. `cp -r modules/wedding-invite modules/wedding-<your-deliverable>`
2. Edit `layout.yaml` (canvas dimensions, block positions).
3. Edit `content.yaml` (English placeholders).
4. Rewrite `build.py` for the new design.
5. `python tui.py --module wedding-<your-deliverable> --run-name template --non-interactive`
6. Copy the result into `template/template.png` / `.pdf` and commit.

The TUI auto-discovers any module under `modules/` that has all three of
`build.py`, `layout.yaml`, `content.yaml`.

## Fonts

```powershell
.\tools\install_fonts.ps1
```

Installs **Cormorant Garamond** (regular/bold/italic/bold-italic) from
Google Fonts into the user font directory. The build falls back to
**Georgia** if Cormorant isn't found.

## Environment

- Windows 11, PowerShell 7
- GIMP 3.2.4 at `C:\Users\fabri\AppData\Local\Programs\GIMP 3\bin\`
- Python 3.13 on the system PATH (for `pyyaml`, `questionary`, and `tui.py`)
- The GIMP-embedded Python is invoked separately by `gimp-console-3.2.exe`
  and only needs the standard library + `gi.repository.Gimp`.

## Tests

```powershell
pip install pytest

# Static checks only (fast, no GIMP): module structure, YAML, schema, launcher
pytest tests/test_structure.py tests/test_tui.py

# Everything, including end-to-end GIMP builds (slow; auto-skipped if GIMP
# isn't installed — each test launches gimp-console)
pytest
```

`tests/test_e2e.py` builds each module (and `--all`) for real and asserts the
XCF/PNG/PDF artifacts exist, plus that a module still builds with an
`inputs/logo.png` override present.

## License

MIT.

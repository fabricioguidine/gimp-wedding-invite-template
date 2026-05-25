# gimp-wedding-invite-template

Per-deliverable wedding-stationery generator using **GIMP 3.2 + Python
(GObject Introspection)**, driven by an interactive TUI.

Each *delivery module* under `modules/` owns its own layout, content, and
build script, and produces print-ready PNG + PDF artifacts via
`gimp-console-3.2.exe`.

## Modules

| Module                          | Status   | Output                                  |
|---------------------------------|----------|-----------------------------------------|
| `wedding-invite`                | active   | 1 portrait page (5×7" @ 300 DPI)        |
| `wedding-bridesmaid-invite`     | active   | 2-side tri-fold leaflet (30×15 cm)      |
| `wedding-groomsman-invite`      | active   | 2-side tri-fold leaflet (groomsman variant) |
| `wedding-couple-invite`         | active   | 2-side tri-fold leaflet (couple variant — split center) |
| `wedding-menu`                  | TODO     | reception menu card                     |
| `wedding-pages-invite`          | TODO     | junior-attendant (flower girl + ring bearer + bear bearer) keepsake |

The three bridal-party manuals (`bridesmaid` / `groomsman` / `couple`) share
the common externo + mission + tips blocks via `src/bridal_party_blocks.py`.
Only the middle interno panel differs per role (single-role center for
bridesmaid/groomsman, split center for couple).

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
│   ├── wedding-bridesmaid-invite/   # same shape, tri-fold (produces 2 XCFs)
│   ├── wedding-menu/                # TODO stub
│   └── wedding-pages-invite/        # TODO stub
├── src/                              # shared GIMP primitives
│   ├── document.py            # canvas + color helpers
│   ├── panels.py              # tri-fold rect math
│   ├── borders.py             # decorative stroke + path
│   ├── text_utils.py          # font resolution + text-layer creation + wrap
│   ├── palette.py             # color-circle row
│   ├── calendar_panel.py      # month grid + day highlight
│   └── module_runner.py       # generic dispatcher invoked by GIMP
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

A module that produces multiple files (e.g. the bridesmaid leaflet has
externo + interno sides) returns multiple XCF paths.

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

## License

MIT.

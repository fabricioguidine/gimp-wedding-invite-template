# wedding-menu

**Status:** TODO — not implemented yet.

Planned deliverable: the reception menu card. Probably a single
portrait page like `wedding-invite`, with sections for:

- Couple monogram / heading
- Starter / entrada
- Main course / prato principal
- Dessert / sobremesa
- Drinks / bebidas
- Optional dietary notes

## When implementing

Mirror the structure of `wedding-invite/`:

```
modules/wedding-menu/
├── template/         # committed example PNG + PDF (English placeholders)
├── inputs/           # user-supplied bg image (gitignored)
├── outputs/<run>/    # PNG + PDF per run (gitignored)
├── content.yaml      # English placeholders matching Portuguese lengths
├── layout.yaml       # canvas, fonts, block positions
└── build.py          # exports `run(layout, content, bg_path, xcf_path)`
```

Add to `tui.py`'s active-modules list once `build.py` exists.

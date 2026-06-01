"""Print-paper geometry (landscape) — A4 and US Letter. Pure, no GIMP.

The tri-fold canvas is sized to the chosen paper's *printable area* (the sheet
minus an even margin on every side). Because the content is distributed
relative to the canvas, switching paper adapts the margins, text wrap and
vertical distribution automatically; the print export then sits with equal
margins on the full sheet.
"""

MM_PER_IN = 25.4

# Landscape dimensions (width >= height), in millimetres.
PAPERS = {
    'a4':     (297.0, 210.0),
    'letter': (279.4, 215.9),   # 11 x 8.5 in
}
DEFAULT_PAPER = 'a4'
DEFAULT_MARGIN_MM = 5.0


def normalize(name):
    """Map a user string ('A4', 'us-letter', 'Letter', ...) to a known key."""
    key = str(name or DEFAULT_PAPER).strip().lower().replace('-', '').replace(' ', '')
    if key in ('usletter', 'letterus', 'us'):
        key = 'letter'
    return key if key in PAPERS else DEFAULT_PAPER


def _px(mm, dpi):
    return int(round(mm / MM_PER_IN * dpi))


def sheet_px(name, dpi=300):
    """Full sheet size in px (landscape) for the print export."""
    w_mm, h_mm = PAPERS[normalize(name)]
    return _px(w_mm, dpi), _px(h_mm, dpi)


def printable_px(name, margin_mm=DEFAULT_MARGIN_MM, dpi=300):
    """Canvas size = sheet minus an even margin on all sides. Derived from
    sheet_px so canvas + 2*margin == sheet exactly (equal margins)."""
    sw, sh = sheet_px(name, dpi)
    m = _px(margin_mm, dpi)
    return sw - 2 * m, sh - 2 * m

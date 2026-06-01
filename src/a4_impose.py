"""Print imposition geometry (pure, no GIMP — testable anywhere).

Scales the tri-fold artwork to fit the chosen print sheet (landscape), keeping
its aspect ratio, and centers it inside an even margin. Here we only compute
the scale / offsets / fold positions; the drawing happens in a4_render (GIMP).
"""

MM_PER_IN = 25.4


def mm_to_px(mm, dpi=300):
    return int(round(mm / MM_PER_IN * dpi))


def a4_landscape_px(dpi=300):
    """A4 landscape (297x210 mm) in pixels at the given DPI."""
    return mm_to_px(297, dpi), mm_to_px(210, dpi)


def compute(src_w, src_h, margin_mm=5.0, dpi=300, page=None):
    """Scale-to-fit + center the artwork on the sheet.

    Returns a dict with page_w/page_h, scale, new_w/new_h, off_x/off_y and
    fold_x (the two absolute fold x-positions, at the thirds of the scaled art).
    """
    page_w, page_h = page if page is not None else a4_landscape_px(dpi)
    m = mm_to_px(margin_mm, dpi)
    avail_w = page_w - 2 * m
    avail_h = page_h - 2 * m
    scale = min(avail_w / float(src_w), avail_h / float(src_h))
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    off_x = (page_w - new_w) // 2
    off_y = (page_h - new_h) // 2
    fold_x = [off_x + int(round(new_w * i / 3.0)) for i in (1, 2)]
    return {
        'page_w': page_w, 'page_h': page_h, 'margin_px': m, 'scale': scale,
        'new_w': new_w, 'new_h': new_h, 'off_x': off_x, 'off_y': off_y,
        'fold_x': fold_x,
    }

"""Pure geometry tests for tri-fold panel layout (no GIMP)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import panels  # noqa: E402

LAYOUT = {
    'canvas': {'width_px': 3543, 'height_px': 1772},
    'fold': {'panel_order': ['left', 'middle', 'right']},
}


def test_three_panels_returned():
    rects = panels.compute_panel_rects(LAYOUT)
    assert set(rects) == {'left', 'middle', 'right'}


def test_panel_widths_sum_to_canvas():
    rects = panels.compute_panel_rects(LAYOUT)
    total = sum(w for (_x, _y, w, _h) in rects.values())
    assert total == LAYOUT['canvas']['width_px']


def test_panels_tile_left_to_right_full_height():
    rects = panels.compute_panel_rects(LAYOUT)
    h = LAYOUT['canvas']['height_px']
    xs = sorted((x, x + w) for (x, _y, w, _hh) in rects.values())
    assert xs[0][0] == 0
    assert xs[-1][1] == LAYOUT['canvas']['width_px']
    for (_x, y, _w, ph) in rects.values():
        assert y == 0 and ph == h
    # contiguous, no gaps/overlaps
    for (_s0, e0), (s1, _e1) in zip(xs, xs[1:]):
        assert e0 == s1

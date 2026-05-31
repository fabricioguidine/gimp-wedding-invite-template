"""Pure geometry tests for A4 imposition (no GIMP)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import a4_impose  # noqa: E402

# Tri-fold canvas: 3543x1772 px = 30x15 cm @ 300 DPI.
TRIFOLD = (3543, 1772)


def test_a4_landscape_dimensions():
    w, h = a4_impose.a4_landscape_px(300)
    assert (w, h) == (3508, 2480)            # 297x210 mm @ 300 DPI
    assert w > h                              # landscape


def test_trifold_fits_inside_margins():
    geo = a4_impose.compute(*TRIFOLD, margin_mm=5.0)
    m = geo['margin_px']
    assert geo['scale'] < 1.0                 # 30 cm shrinks to fit A4's 29.7 cm
    assert geo['off_x'] >= m
    assert geo['off_y'] >= m
    assert geo['off_x'] + geo['new_w'] <= geo['page_w'] - m
    assert geo['off_y'] + geo['new_h'] <= geo['page_h'] - m


def test_aspect_ratio_preserved():
    geo = a4_impose.compute(*TRIFOLD)
    src_ratio = TRIFOLD[0] / TRIFOLD[1]
    out_ratio = geo['new_w'] / geo['new_h']
    assert abs(src_ratio - out_ratio) < 0.01


def test_artwork_is_centered():
    geo = a4_impose.compute(*TRIFOLD)
    assert geo['off_x'] == (geo['page_w'] - geo['new_w']) // 2
    assert geo['off_y'] == (geo['page_h'] - geo['new_h']) // 2


def test_fold_lines_split_artwork_in_thirds():
    geo = a4_impose.compute(*TRIFOLD)
    f1, f2 = geo['fold_x']
    panel = geo['new_w'] / 3.0
    assert abs(f1 - (geo['off_x'] + panel)) <= 1
    assert abs(f2 - (geo['off_x'] + 2 * panel)) <= 1
    assert geo['off_x'] < f1 < f2 < geo['off_x'] + geo['new_w']


def test_smaller_margin_yields_larger_artwork():
    big = a4_impose.compute(*TRIFOLD, margin_mm=2.0)
    small = a4_impose.compute(*TRIFOLD, margin_mm=10.0)
    assert big['new_w'] > small['new_w']

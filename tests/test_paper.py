"""Pure geometry tests for print-paper sizing (no GIMP)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

import paper  # noqa: E402


def test_normalize_aliases():
    assert paper.normalize('A4') == 'a4'
    assert paper.normalize('Letter') == 'letter'
    assert paper.normalize('us-letter') == 'letter'
    assert paper.normalize('US') == 'letter'
    assert paper.normalize(None) == 'a4'
    assert paper.normalize('totally-unknown') == 'a4'


def test_sheet_px_a4_landscape():
    w, h = paper.sheet_px('a4', dpi=300)
    assert (w, h) == (3508, 2480)
    assert w > h


def test_sheet_px_letter_landscape():
    w, h = paper.sheet_px('letter', dpi=300)
    assert w > h


def test_printable_plus_margins_equals_sheet():
    for name in ('a4', 'letter'):
        sw, sh = paper.sheet_px(name, dpi=300)
        pw, ph = paper.printable_px(name, margin_mm=5.0, dpi=300)
        m = paper._px(5.0, 300)
        assert pw + 2 * m == sw
        assert ph + 2 * m == sh

"""Impose a tri-fold (XCF/PNG) onto a landscape print sheet, ready to print.

Unlike export_pdf (which saves at native size), this scales the artwork to fit
the chosen paper (a4 / letter), centers it, and marks the folds. Print at
landscape, 100% / actual size (NOT "fit to page").

Usage (same pattern as export_pdf, but add src/ to the path):
  gimp-console-3.2.exe -i -d --quit --batch-interpreter=python-fu-eval \
    -b "import sys; sys.path.insert(0, r'.../src'); sys.path.insert(0, r'.../tools'); import export_pdf_a4; export_pdf_a4.run(r'in.xcf', r'out.pdf')"
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl

import a4_render


def run(src_path, pdf_path, paper='a4', margin_mm=5.0, fold_marks=True):
    Gegl.init(None)
    a4_render.render_to_a4(src_path, pdf_path, paper, margin_mm, fold_marks)
    print('Print PDF saved to:', pdf_path)

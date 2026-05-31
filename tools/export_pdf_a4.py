"""Impõe um tri-fold (XCF/PNG) numa folha A4 paisagem, pronto pra imprimir.

Diferente do export_pdf (que salva no tamanho nativo 30x15 cm), este escala a
arte pra caber em A4, centraliza e marca as dobras. Imprima em A4 PAISAGEM,
escala 100% / tamanho real (NÃO "ajustar à página").

Uso (mesmo padrão do export_pdf, mas inclua src/ no path):
  gimp-console-3.2.exe -i -d --quit --batch-interpreter=python-fu-eval \
    -b "import sys; sys.path.insert(0, r'.../src'); sys.path.insert(0, r'.../tools'); import export_pdf_a4; export_pdf_a4.run(r'in.xcf', r'out_a4.pdf')"
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gegl

import a4_render


def run(src_path, pdf_path, margin_mm=5.0, fold_marks=True):
    Gegl.init(None)
    a4_render.render_to_a4(src_path, pdf_path, margin_mm, fold_marks)
    print('A4 PDF salvo em:', pdf_path)

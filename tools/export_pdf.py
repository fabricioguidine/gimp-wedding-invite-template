"""Exporta o .xcf gerado pra PDF (formato pra impressão).

Uso (mesmo padrão do export_png):
  gimp-console-3.2.exe -i -d --quit --batch-interpreter=python-fu-eval \
    -b "import sys; sys.path.insert(0, r'.../tools'); import export_pdf; export_pdf.run(r'.../arquivo.xcf', r'.../arquivo.pdf')"

GIMP 3 usa o plug-in file-pdf-save (deduzido pela extensão .pdf no path).
Mantém os 300 DPI definidos no XCF — o PDF resultante imprime no
tamanho físico correto (≈30×15 cm pro tri-fold).
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio


def run(xcf_path, pdf_path):
    Gegl.init(None)
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(xcf_path))
    image.flatten()
    Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE,
        image,
        Gio.File.new_for_path(pdf_path),
        None,
    )
    print('PDF salvo em:', pdf_path)
    image.delete()

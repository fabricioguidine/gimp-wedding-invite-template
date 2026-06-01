"""Export the generated .xcf to PDF (print format).

Usage (same pattern as export_png):
  gimp-console-3.2.exe -i -d --quit --batch-interpreter=python-fu-eval \
    -b "import sys; sys.path.insert(0, r'.../tools'); import export_pdf; export_pdf.run(r'.../file.xcf', r'.../file.pdf')"

GIMP 3 uses the file-pdf-save plug-in (inferred from the .pdf extension). Keeps
the 300 DPI set in the XCF, so the PDF prints at the correct physical size.
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
    print('PDF saved to:', pdf_path)
    image.delete()

"""Export the generated .xcf to PNG (a preview for visual inspection).

Usage:
  gimp-console-3.2.exe -i -d --quit --batch-interpreter=python-fu-eval \
    -b "import sys; sys.path.insert(0, r'.../tools'); import export_png; export_png.run(r'.../art.xcf', r'.../art.png')"
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio


def run(xcf_path, png_path, max_width=None):
    Gegl.init(None)
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(xcf_path))

    if max_width and image.get_width() > max_width:
        ratio = max_width / image.get_width()
        new_w = int(image.get_width() * ratio)
        new_h = int(image.get_height() * ratio)
        image.scale(new_w, new_h)

    image.flatten()
    Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE,
        image,
        Gio.File.new_for_path(png_path),
        None,
    )
    print('PNG saved to:', png_path)
    image.delete()

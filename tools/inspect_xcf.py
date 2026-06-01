"""Probe a generated .xcf: inspect dimensions, DPI, layers, and sample
the colour of a central pixel to validate the fill.

Usage (from the run helper):
    gimp-console-3.2.exe -i -d -f --batch-interpreter=python-fu-eval \
        -b "import sys; sys.path.insert(0, r'.../tools'); import inspect_xcf; inspect_xcf.run(r'.../convite.xcf')"
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio


def run(xcf_path):
    Gegl.init(None)
    gio_file = Gio.File.new_for_path(xcf_path)
    image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, gio_file)

    print('--- XCF INSPECTION ---')
    print('Path:        ', xcf_path)
    print('Dimensions:  ', image.get_width(), 'x', image.get_height())
    xres, yres = image.get_resolution().xresolution, image.get_resolution().yresolution
    print('DPI (x, y):  ', xres, yres)

    layers = image.get_layers()
    print('Layers (top -> bottom):')
    def _walk(layer_list, indent=0):
        for l in layer_list:
            kind = 'group' if l.is_group() else 'layer'
            print('{}- {} ({})'.format('  ' * (indent + 1), l.get_name(), kind))
            if l.is_group():
                _walk(l.get_children(), indent + 1)
    _walk(layers)

    # Sample a central pixel of the bg layer
    bg = next((l for l in layers if l.get_name() == 'bg'), None)
    if bg is not None:
        cx, cy = image.get_width() // 2, image.get_height() // 2
        color = bg.get_pixel(cx, cy)
        if hasattr(color, 'get_rgba'):
            print('bg @ center: RGBA =', color.get_rgba())
        else:
            print('bg @ center:', color)

    # Sample the 'borders' layer where the border should be
    bd = next((l for l in layers if l.get_name() == 'borders'), None)
    if bd is not None:
        # Inner margin ~118px; a pixel 118px from the canvas edge should sit
        # on the stroke (near the left line of the left-most panel).
        sx, sy = 118, image.get_height() // 2
        c = bd.get_pixel(sx, sy)
        if hasattr(c, 'get_rgba'):
            print('borders @ ({},{}): RGBA ='.format(sx, sy), c.get_rgba())
        else:
            print('borders @ ({},{}):'.format(sx, sy), c)

    # Paths (editable vectors)
    paths = image.get_paths()
    if paths:
        print('Paths:')
        for p in paths:
            n_strokes = len(p.get_strokes())
            print('  - {} ({} stroke(s))'.format(p.get_name(), n_strokes))
    else:
        print('Paths:        (none)')

    # Guides
    g = image.find_next_guide(0)
    guides = []
    while g != 0:
        pos = image.get_guide_position(g)
        orientation = image.get_guide_orientation(g)
        guides.append((pos, orientation))
        g = image.find_next_guide(g)
    print('Guides:      ', guides)

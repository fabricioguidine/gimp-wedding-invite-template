"""Base document creation in GIMP 3.

Responsible for: canvas with correct dimensions/DPI, background colour layer,
and vertical guides marking the tri-fold folds.

API: GIMP 3.x via GObject Introspection (gi.repository.Gimp). Not to be
confused with Python-Fu / gimpfu from GIMP 2.10 — function signatures and
class names changed a lot.
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl


def hex_to_rgb01(hex_color):
    """Convert '#RRGGBB' into an (r, g, b) tuple with components in [0, 1]."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def make_color(hex_color):
    """Build a Gegl.Color from a '#RRGGBB' string.

    In GIMP 3 the colour API goes through Gegl.Color (no longer gimpcolor).
    """
    color = Gegl.Color.new('white')
    r, g, b = hex_to_rgb01(hex_color)
    color.set_rgba(r, g, b, 1.0)
    return color


def create_canvas(layout, invite=None):
    """Create the base image with a background fill and vertical fold guides.

    Parameters:
        layout: dict loaded from layout.yaml (already converted to JSON).
        invite: dict loaded from content (unused here, kept in the signature).

    Returns: a Gimp.Image ready to be drawn on and saved.
    """
    canvas_cfg = layout['canvas']
    width = int(canvas_cfg['width_px'])
    height = int(canvas_cfg['height_px'])
    dpi = float(canvas_cfg['dpi'])
    bg_hex = canvas_cfg['background_color']

    # RGB image without alpha
    image = Gimp.Image.new(width, height, Gimp.ImageBaseType.RGB)
    image.set_resolution(dpi, dpi)

    # Paint the background on a dedicated layer (more flexible than Image fill)
    bg_layer = Gimp.Layer.new(
        image,
        'bg',
        width,
        height,
        Gimp.ImageType.RGB_IMAGE,
        100.0,                     # opacity
        Gimp.LayerMode.NORMAL,
    )
    # parent=None, position=0 -> top of the stack (only layer so far)
    image.insert_layer(bg_layer, None, 0)

    # Fill the layer with the background colour via context_set_foreground + fill
    Gimp.context_set_foreground(make_color(bg_hex))
    bg_layer.fill(Gimp.FillType.FOREGROUND)

    # Vertical guides at the folds (accordion / Z-fold)
    for pct in layout['fold']['guides_vertical_pct']:
        x = int(round(width * float(pct) / 100.0))
        image.add_vguide(x)

    return image

"""Decorative borders around each panel.

Always creates a single raster layer 'borders' with the stroke painted. If
layout.borders.as_paths == true (default), it also creates one Gimp.Path per
panel (visible in GIMP's "Paths" dialog) so the rectangles can be edited as
vectors — drag corners, resize — without touching pixels.
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp

from document import make_color


def draw_borders(image, layout, panel_rects):
    """Draw the borders. Returns the raster layer (or None if disabled).

    Reads from layout.borders:
      raster:    if True, paint the raster 'borders' layer (default True)
      as_paths:  if True, create editable Gimp.Path objects (default True)
    """
    cfg = layout['borders']
    margin = int(cfg['inner_margin_px'])

    raster_layer = None
    if cfg.get('raster', True):
        raster_layer = _draw_raster_borders(image, cfg, panel_rects, margin)

    if cfg.get('as_paths', True):
        _create_panel_paths(image, panel_rects, margin)

    return raster_layer


def _draw_raster_borders(image, cfg, panel_rects, margin):
    """Paint the rectangles as pixels on a single 'borders' layer."""
    stroke_width = float(cfg['stroke_width_px'])
    color = make_color(cfg['color'])
    canvas_w = image.get_width()
    canvas_h = image.get_height()

    borders_layer = Gimp.Layer.new(
        image, 'borders',
        canvas_w, canvas_h,
        Gimp.ImageType.RGBA_IMAGE,
        100.0,
        Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(borders_layer, None, 0)
    borders_layer.add_alpha()
    borders_layer.fill(Gimp.FillType.TRANSPARENT)

    Gimp.context_push()
    try:
        Gimp.context_set_foreground(color)
        # StrokeMethod.LINE avoids a brush dependency (important with -d).
        Gimp.context_set_stroke_method(Gimp.StrokeMethod.LINE)
        Gimp.context_set_line_width(stroke_width)
        Gimp.context_set_line_cap_style(Gimp.CapStyle.BUTT)
        Gimp.context_set_line_join_style(Gimp.JoinStyle.MITER)
        Gimp.context_set_antialias(True)

        for _name, (px, py, pw, ph) in panel_rects.items():
            ix = px + margin
            iy = py + margin
            iw = pw - 2 * margin
            ih = ph - 2 * margin
            image.select_rectangle(Gimp.ChannelOps.REPLACE, ix, iy, iw, ih)
            borders_layer.edit_stroke_selection()

        Gimp.Selection.none(image)
    finally:
        Gimp.context_pop()

    return borders_layer


def _create_panel_paths(image, panel_rects, margin):
    """Create one rectangular Gimp.Path per panel (editable vector).

    Each path has 4 anchors with coincident control points (square corners).
    Visible in GIMP's "Paths" dialog.
    """
    for name, (px, py, pw, ph) in panel_rects.items():
        x1 = px + margin
        y1 = py + margin
        x2 = px + pw - margin
        y2 = py + ph - margin

        path = Gimp.Path.new(image, 'border_{}'.format(name))
        image.insert_path(path, None, 0)

        # In GIMP 3, stroke_new_from_points for BEZIER expects a flat list of
        # doubles: [cp_in_x, cp_in_y, anchor_x, anchor_y, cp_out_x, cp_out_y]
        # per anchor. Square corners = control points equal to the anchor.
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        flat = []
        for ax, ay in corners:
            flat.extend([ax, ay, ax, ay, ax, ay])

        path.stroke_new_from_points(
            Gimp.PathStrokeType.BEZIER,
            flat,
            True,  # closed
        )

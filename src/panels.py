"""Geometry of the three tri-fold panels.

The total width is split equally into N panels (default 3). The panel order in
the open canvas comes from layout.yaml at fold.panel_order — for an accordion /
Z-fold the cover sits in the right-hand panel (index 2 when the order is
[back_cover, middle, front_cover]).
"""


def compute_panel_rects(layout):
    """Return a dict {panel_name: (x, y, w, h)} in pixels.

    Distributes the widths equally, adjusting rounding so the sum of the panel
    widths is exactly canvas.width_px.
    """
    canvas_w = int(layout['canvas']['width_px'])
    canvas_h = int(layout['canvas']['height_px'])
    order = layout['fold']['panel_order']
    n = len(order)

    rects = {}
    panel_w = canvas_w / n
    for i, name in enumerate(order):
        x = int(round(i * panel_w))
        next_x = canvas_w if i == n - 1 else int(round((i + 1) * panel_w))
        rects[name] = (x, 0, next_x - x, canvas_h)
    return rects

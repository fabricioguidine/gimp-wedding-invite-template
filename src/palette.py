"""Paleta de cores das madrinhas.

Desenha N círculos coloridos preenchidos, enfileirados horizontalmente,
centralizados no painel da madrinha. Cores em invite.madrinha.palette;
geometria (raio, espaçamento) em layout.panels.madrinha.palette.

Vai todo num único layer raster 'palette' dentro do grupo panel_madrinha.
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

from document import make_color


def compute_circle_centers(layout, panel_rects, panel_name, n_circles):
    """Retorna lista com X centers das N bolinhas com spacing fixo do
    layout.yaml, centralizadas no meio do painel (não estica até as bordas).
    """
    if panel_name not in panel_rects or n_circles == 0:
        return []
    px, py, pw, ph = panel_rects[panel_name]
    pal_cfg = layout['panels']['madrinha']['palette']
    radius = int(pal_cfg['circle_radius_px'])
    spacing = int(pal_cfg['circle_spacing_px'])
    diameter = radius * 2
    if n_circles == 1:
        return [px + pw // 2]
    total_w = n_circles * diameter + (n_circles - 1) * spacing
    start_cx = px + (pw - total_w) // 2 + radius
    return [int(start_cx + i * (diameter + spacing)) for i in range(n_circles)]


def draw_palette(image, layout, invite, panel_rects, panel_groups,
                 panel_name='madrinha', y_factor=0.78, layer_name='palette'):
    """Pinta os círculos da paleta dentro do painel indicado.

    panel_name: chave em panel_rects (default 'madrinha').
    y_factor:   posição vertical, fração da altura do painel (0..1).
    layer_name: nome da layer raster gerada.
    """
    if panel_name not in panel_rects:
        raise RuntimeError("Painel '{}' não está na ordem configurada".format(panel_name))

    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    pal_cfg = layout['panels']['madrinha']['palette']
    radius = int(pal_cfg['circle_radius_px'])
    diameter = radius * 2

    colors_hex = list(invite['madrinha']['palette'])
    n = len(colors_hex)
    if n == 0:
        return None

    circle_centers = compute_circle_centers(layout, panel_rects, panel_name, n)
    cy = py + int(ph * y_factor)
    canvas_w = image.get_width()
    canvas_h = image.get_height()

    layer = Gimp.Layer.new(
        image, layer_name,
        canvas_w, canvas_h,
        Gimp.ImageType.RGBA_IMAGE,
        100.0,
        Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(layer, parent, 0)
    layer.add_alpha()
    layer.fill(Gimp.FillType.TRANSPARENT)

    border_color = make_color(layout['borders']['color'])

    Gimp.context_push()
    try:
        Gimp.context_set_antialias(True)
        Gimp.context_set_stroke_method(Gimp.StrokeMethod.LINE)
        Gimp.context_set_line_width(1.5)
        Gimp.context_set_line_cap_style(Gimp.CapStyle.ROUND)
        Gimp.context_set_line_join_style(Gimp.JoinStyle.ROUND)

        for i, hex_color in enumerate(colors_hex):
            cx = circle_centers[i]
            x = cx - radius
            y = cy - radius
            image.select_ellipse(
                Gimp.ChannelOps.REPLACE, x, y, diameter, diameter,
            )
            # Preenche com a cor
            Gimp.context_set_foreground(make_color(hex_color))
            layer.edit_fill(Gimp.FillType.FOREGROUND)
            # Contorno fino — garante visibilidade do círculo branco no fundo creme
            Gimp.context_set_foreground(border_color)
            layer.edit_stroke_selection()

        Gimp.Selection.none(image)
    finally:
        Gimp.context_pop()

    return layer

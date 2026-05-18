"""Calendário do painel save_the_date.

Cria um grid 7 colunas (D S T Q Q S S) × N linhas com os dias do mês,
e desenha um círculo destacando o dia configurado em
invite.save_the_date.highlighted_day.

Tudo é inserido como sub-layers do grupo panel_save_the_date.
"""

import calendar as _cal

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at


def draw_calendar(image, layout, invite, panel_rects, panel_groups):
    """Desenha o calendário dentro do painel save_the_date."""
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        raise RuntimeError("Painel '{}' não está na ordem configurada".format(panel_name))

    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cal_cfg = layout['panels']['save_the_date']['calendar']
    cell = int(cal_cfg['cell_size_px'])
    header_size = int(cal_cfg['header_size_px'])
    day_size = int(cal_cfg['day_size_px'])
    weekday_labels = list(cal_cfg['weekday_labels'])  # [D, S, T, Q, Q, S, S]

    std = invite['save_the_date']
    year = int(std['year'])
    month = int(std['month'])
    highlighted_day = int(std['highlighted_day'])

    # Domingo como primeiro dia (padrão brasileiro)
    cal = _cal.Calendar(firstweekday=_cal.SUNDAY)
    weeks = cal.monthdayscalendar(year, month)  # 0 = célula vazia

    # Geometria do grid: 7 colunas, (1 + len(weeks)) linhas (header + semanas)
    cols = 7
    rows = 1 + len(weeks)
    grid_w = cols * cell
    grid_h = rows * cell

    # Centralizado horizontalmente; verticalmente um pouco abaixo do meio
    # (espaço acima vai virar título "Save the Date" na Fase 5)
    grid_x = px + (pw - grid_w) // 2
    grid_y = py + (ph - grid_h) // 2 + int(ph * 0.05)

    serif_font = resolve_font(layout, 'serif')
    text_color = make_color(layout['borders']['color'])

    # --- Linha de cabeçalho: dias da semana ---
    for col, label in enumerate(weekday_labels):
        cx = grid_x + col * cell + cell // 2
        cy = grid_y + cell // 2
        layer = make_text_layer(
            image, parent,
            'cal_wd_{}_{}'.format(col, label),
            label, serif_font, header_size, text_color,
        )
        center_layer_at(layer, cx, cy)

    # --- Linhas dos dias ---
    for row_idx, week in enumerate(weeks, start=1):
        for col, day in enumerate(week):
            if day == 0:
                continue  # célula vazia (mês não cobre)
            cx = grid_x + col * cell + cell // 2
            cy = grid_y + row_idx * cell + cell // 2
            layer = make_text_layer(
                image, parent,
                'cal_day_{:02d}'.format(day),
                str(day), serif_font, day_size, text_color,
            )
            center_layer_at(layer, cx, cy)

            # Guarda posição do dia destacado pra desenhar o círculo depois
            if day == highlighted_day:
                _draw_highlight_circle(
                    image, parent, cal_cfg,
                    cx, cy, text_color,
                )


def _draw_highlight_circle(image, parent, cal_cfg, cx, cy, color):
    """Desenha um círculo (raster) ao redor do dia destacado."""
    radius = int(cal_cfg['highlight_radius_px'])
    stroke = float(cal_cfg['highlight_stroke_px'])
    canvas_w = image.get_width()
    canvas_h = image.get_height()

    layer = Gimp.Layer.new(
        image, 'cal_highlight',
        canvas_w, canvas_h,
        Gimp.ImageType.RGBA_IMAGE,
        100.0,
        Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(layer, parent, 0)
    layer.add_alpha()
    layer.fill(Gimp.FillType.TRANSPARENT)

    Gimp.context_push()
    try:
        Gimp.context_set_foreground(color)
        Gimp.context_set_stroke_method(Gimp.StrokeMethod.LINE)
        Gimp.context_set_line_width(stroke)
        Gimp.context_set_line_cap_style(Gimp.CapStyle.ROUND)
        Gimp.context_set_line_join_style(Gimp.JoinStyle.ROUND)
        Gimp.context_set_antialias(True)

        x = cx - radius
        y = cy - radius
        d = radius * 2
        image.select_ellipse(Gimp.ChannelOps.REPLACE, x, y, d, d)
        layer.edit_stroke_selection()
        Gimp.Selection.none(image)
    finally:
        Gimp.context_pop()

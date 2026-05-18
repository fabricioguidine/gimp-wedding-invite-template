"""Textos dos três painéis: capa, save the date e madrinha.

Capa: monograma com nome da noiva, "&", nome do noivo (fonte script).
Save the date: título acima do calendário; venue/cidade/horário abaixo.
Madrinha: título no topo; corpo no miolo; paleta (Fase 4) já está embaixo.
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text


def draw_all_texts(image, layout, invite, panel_rects, panel_groups):
    draw_cover_text(image, layout, invite, panel_rects, panel_groups)
    draw_save_the_date_text(image, layout, invite, panel_rects, panel_groups)
    draw_madrinha_text(image, layout, invite, panel_rects, panel_groups)


# ---------------------------------------------------------------- capa
def draw_cover_text(image, layout, invite, panel_rects, panel_groups):
    panel_name = 'cover'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cover_cfg = layout['panels']['cover']
    font_kind = cover_cfg.get('monogram_font', 'script')
    base_size = int(cover_cfg['monogram_size_px'])
    color = _resolve_text_color(cover_cfg, layout)

    font = resolve_font(layout, font_kind)
    bride = invite['couple']['bride']
    groom = invite['couple']['groom']

    cx = px + pw // 2

    # Empilha verticalmente: noiva, "&" menor, noivo
    line_specs = [
        ('cover_bride', bride, base_size),
        ('cover_amp',   '&',   int(base_size * 0.55)),
        ('cover_groom', groom, base_size),
    ]
    layers = []
    total_h = 0
    for name, text, size in line_specs:
        layer = make_text_layer(image, parent, name, text, font, size, color)
        layers.append((layer, size))
        total_h += layer.get_height()

    # Espaçamento vertical proporcional
    gap = int(base_size * 0.05)
    block_h = total_h + gap * (len(layers) - 1)
    cy_top = py + (ph - block_h) // 2

    y_cursor = cy_top
    for layer, _size in layers:
        h = layer.get_height()
        center_layer_at(layer, cx, y_cursor + h // 2)
        y_cursor += h + gap


# ---------------------------------------------------- save the date
def draw_save_the_date_text(image, layout, invite, panel_rects, panel_groups):
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    std_cfg = layout['panels']['save_the_date']
    title_text = std_cfg.get('title_text', 'Save the Date')
    title_font = resolve_font(layout, std_cfg.get('title_font', 'script'))
    title_size = int(std_cfg['title_size_px'])
    body_font = resolve_font(layout, std_cfg.get('body_font', 'serif'))
    body_size = int(std_cfg['body_size_px'])
    color = _resolve_text_color(std_cfg, layout)

    cx = px + pw // 2

    # Título no topo (~10% da altura do painel a partir do topo da margem)
    title = make_text_layer(
        image, parent, 'std_title', title_text, title_font, title_size, color,
    )
    title_cy = py + int(ph * 0.13)
    center_layer_at(title, cx, title_cy)

    # Bloco de info abaixo do calendário
    ceremony = invite.get('ceremony', {})
    info_lines = []
    if ceremony.get('venue'):
        info_lines.append(ceremony['venue'])
    if ceremony.get('city'):
        info_lines.append(ceremony['city'])
    if ceremony.get('bridal_party_arrival'):
        info_lines.append('Chegada: {}'.format(ceremony['bridal_party_arrival']))

    if info_lines:
        info_text = '\n'.join(info_lines)
        info_layer = make_text_layer(
            image, parent, 'std_info', info_text, body_font, body_size, color,
        )
        info_cy = py + int(ph * 0.88)
        center_layer_at(info_layer, cx, info_cy)


# ---------------------------------------------------------- madrinha
def draw_madrinha_text(image, layout, invite, panel_rects, panel_groups):
    panel_name = 'madrinha'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    mad_cfg = layout['panels']['madrinha']
    title_font = resolve_font(layout, mad_cfg.get('title_font', 'script'))
    title_size = int(mad_cfg['title_size_px'])
    body_font = resolve_font(layout, mad_cfg.get('body_font', 'serif'))
    body_size = int(mad_cfg['body_size_px'])
    color = _resolve_text_color(mad_cfg, layout)

    title_text = invite['madrinha'].get('title', 'Madrinha')
    body_text = invite['madrinha'].get('body', '').strip()
    wrap_chars = int(mad_cfg.get('body_wrap_chars', 50))
    if body_text:
        body_text = wrap_text(body_text, wrap_chars)

    cx = px + pw // 2

    # Título no topo
    title = make_text_layer(
        image, parent, 'mad_title', title_text, title_font, title_size, color,
    )
    title_cy = py + int(ph * 0.13)
    center_layer_at(title, cx, title_cy)

    # Corpo entre título e paleta (paleta está em ~78% da altura)
    if body_text:
        body_layer = make_text_layer(
            image, parent, 'mad_body', body_text, body_font, body_size, color,
        )
        body_cy = py + int(ph * 0.48)
        center_layer_at(body_layer, cx, body_cy)


# ---------------------------------------------------------------- util
def _resolve_text_color(panel_cfg, layout):
    """Pega panel.text_color, ou cai pra layout.borders.color."""
    hex_str = panel_cfg.get('text_color') or layout['borders']['color']
    return make_color(hex_str)

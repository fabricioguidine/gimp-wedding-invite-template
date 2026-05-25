"""Shared drawing helpers for the three bridal-party manuals
(bridesmaid / groomsman / couple).

Each manual is a tri-fold leaflet with two sides:

    externo (visible when folded):
        back_cover     |  middle (calendar+info)  |  front_cover (title)

    interno (unfolded inside):
        back_cover (mission)  |  middle (role-specific)  |  front_cover (tips)

The externo + the back-cover-mission + front-cover-tips are identical across
all three manuals; only the middle interno panel varies (single-role center
for bridesmaid/groomsman, split center for couple). So those bits live here
and the role-specific draw_role_center stays in each module's build.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gio

from document import make_color, create_canvas
from panels import compute_panel_rects
from borders import draw_borders
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text
import palette as palette_module
import calendar_panel as calendar_module


_REPO_ROOT = Path(__file__).resolve().parent.parent
_ICONS_DIR = _REPO_ROOT / 'assets' / 'ornaments' / 'icons'
_LOGO_PATH = _REPO_ROOT / 'assets' / 'ornaments' / 'logo.png'


# ============================================================ canvas/setup
def build_canvas(layout, bg_path):
    image = create_canvas(layout, None)
    if bg_path:
        _place_background(image, layout, bg_path)
    return image


def _place_background(image, layout, bg_path):
    cfg = layout.get('background_image') or {}
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image,
            Gio.File.new_for_path(str(bg_path)),
        )
    except Exception as e:
        print('[bridal_party] could not load bg {}: {}'.format(bg_path, e))
        return
    image.insert_layer(layer, None, 0)
    layer.set_name('bg_image')
    cw, ch = image.get_width(), image.get_height()
    lw, lh = layer.get_width(), layer.get_height()
    if lw == 0 or lh == 0:
        return
    mode = cfg.get('scale_mode', 'cover')
    scale = (min if mode == 'fit' else max)(cw / float(lw), ch / float(lh))
    new_w, new_h = max(1, int(lw * scale)), max(1, int(lh * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets((cw - new_w) // 2, (ch - new_h) // 2)
    layer.set_opacity(max(0.0, min(100.0, float(cfg.get('opacity_pct', 20)))))


def create_panel_groups(image, panel_rects):
    groups = {}
    for name in panel_rects:
        g = Gimp.GroupLayer.new(image)
        g.set_name('panel_{}'.format(name))
        image.insert_layer(g, None, 0)
        groups[name] = g
    return groups


def prepare_image(layout, bg_path):
    """One-shot: canvas + bg + panels + borders + panel groups.

    Returns (image, panel_rects, panel_groups).
    """
    image = build_canvas(layout, bg_path)
    panel_rects = compute_panel_rects(layout)
    draw_borders(image, layout, panel_rects)
    panel_groups = create_panel_groups(image, panel_rects)
    return image, panel_rects, panel_groups


def save_xcf(image, path):
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
                   Gio.File.new_for_path(str(path)), None)
    image.delete()


# ============================================================ externo
def draw_externo(image, layout, content, panel_rects, panel_groups):
    """The folded-cover face. Same for all three manuals."""
    cfg = layout['externo']
    color = make_color(layout['text_color'])

    _draw_cover_title(image, layout, cfg['front_cover'], content,
                      panel_rects, panel_groups, color)
    _draw_couple_subtitle(image, layout, cfg['front_cover'], content,
                          panel_rects, panel_groups, color)
    _draw_calendar_with_info(image, layout, cfg['middle'], content,
                             panel_rects, panel_groups, color)
    _draw_back_cover_logo(image, layout, cfg['back_cover'],
                          panel_rects, panel_groups)


def _draw_cover_title(image, layout, cfg, content, panel_rects, panel_groups, color):
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    font = resolve_font(layout, 'script_bold')
    text = '\n'.join(content['cover']['title'].split())
    layer = make_text_layer(image, parent, 'cover_title', text, font,
                            int(cfg['title_size_px']), color)
    layer.set_justification(Gimp.TextJustification.CENTER)
    inner = int(layout['borders']['inner_margin_px'])
    top_y = py + inner + int(cfg['title_top_padding_px'])
    layer.set_offsets(px + (pw - layer.get_width()) // 2, top_y)


def _draw_couple_subtitle(image, layout, cfg, content, panel_rects, panel_groups, color):
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    font = resolve_font(layout, 'serif')
    text = '{} & {}'.format(content['couple']['bride'], content['couple']['groom'])
    layer = make_text_layer(image, parent, 'cover_subtitle', text, font,
                            int(cfg['subtitle_size_px']), color)
    center_layer_at(layer, px + pw // 2, py + int(ph * float(cfg['subtitle_y_factor'])))


def _draw_calendar_with_info(image, layout, cfg, content, panel_rects, panel_groups, color):
    panel = 'middle'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    shim_layout = _shim_calendar_layout(layout, cfg['calendar'])
    shim_invite = {
        'save_the_date': {
            'year': int(content['date']['year']),
            'month': int(content['date']['month']),
            'highlighted_day': int(content['date']['day']),
        },
    }
    shim_panel_rects = {'save_the_date': panel_rects[panel]}
    shim_panel_groups = {'save_the_date': panel_groups[panel]}
    calendar_module.draw_calendar(image, shim_layout, shim_invite,
                                  shim_panel_rects, shim_panel_groups)

    wd = make_text_layer(image, parent, 'cal_weekday', content['date']['weekday_name'],
                         title_font, int(cfg['weekday_size_px']), color)
    center_layer_at(wd, cx, py + int(ph * 0.12))

    date_text = '{} | {} | {}'.format(content['date']['day'],
                                       content['date']['month_name'],
                                       content['date']['year'])
    date = make_text_layer(image, parent, 'cal_date', date_text,
                           body_font, int(cfg['date_size_px']), color)
    center_layer_at(date, cx, py + int(ph * 0.21))

    y_pct = 0.74
    if content['ceremony'].get('arrival_time'):
        arr_text = '{}: {}'.format(content['ceremony']['arrival_label'],
                                    content['ceremony']['arrival_time'])
        arr = make_text_layer(image, parent, 'cal_arrival', arr_text,
                              body_font, int(cfg['arrival_size_px']), color)
        center_layer_at(arr, cx, py + int(ph * y_pct))
        y_pct += 0.06
    if content['ceremony'].get('venue'):
        venue = make_text_layer(image, parent, 'cal_venue',
                                wrap_text(content['ceremony']['venue'], 24),
                                body_font, int(cfg['venue_size_px']), color)
        venue.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(venue, cx, py + int(ph * y_pct))
        y_pct += 0.06
    if content['ceremony'].get('address'):
        addr = make_text_layer(image, parent, 'cal_addr',
                               wrap_text(content['ceremony']['address'], 26),
                               body_font, int(cfg['address_size_px']), color)
        addr.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(addr, cx, py + int(ph * y_pct))


def _shim_calendar_layout(layout, calendar_cfg):
    return {
        'panels': {'save_the_date': {'calendar': calendar_cfg}},
        'borders': layout['borders'],
        'fonts': layout['fonts'],
    }


def _draw_back_cover_logo(image, layout, cfg, panel_rects, panel_groups):
    panel = 'back_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    if not _LOGO_PATH.exists():
        return
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image,
            Gio.File.new_for_path(str(_LOGO_PATH)),
        )
    except Exception as e:
        print('[bridal_party] failed to load logo: {}'.format(e))
        return
    image.insert_layer(layer, parent, 0)
    layer.set_name('back_cover_logo')
    pad = int(cfg.get('logo_padding_px', 50))
    target_w, target_h = pw - 2 * pad, ph - 2 * pad
    cur_w, cur_h = layer.get_width(), layer.get_height()
    if cur_w == 0 or cur_h == 0:
        return
    scale = min(target_w / float(cur_w), target_h / float(cur_h))
    new_w, new_h = max(1, int(cur_w * scale)), max(1, int(cur_h * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets(px + (pw - new_w) // 2, py + (ph - new_h) // 2)


# ============================================================ interno blocks
def draw_mission_block(image, layout, content, panel_rects, panel_groups):
    cfg = layout['interno']['back_cover']
    panel = 'back_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    script_font = resolve_font(layout, 'script')
    body_font = resolve_font(layout, 'serif')

    mission = content['mission']

    title = make_text_layer(image, parent, 'mission_title', mission['title'],
                            title_font, int(cfg['title_size_px']), color)
    center_layer_at(title, cx, py + int(ph * 0.10))

    body_top = py + int(ph * 0.20)
    body_bottom = body_top
    body_text = (mission.get('body') or '').strip()
    if body_text:
        body = make_text_layer(image, parent, 'mission_body',
                               wrap_text(body_text, int(cfg['body_wrap_chars'])),
                               body_font, int(cfg['body_size_px']), color)
        body.set_justification(Gimp.TextJustification.CENTER)
        body.set_offsets(cx - body.get_width() // 2, body_top)
        body_bottom = body_top + body.get_height()

    verse = mission.get('verse') or {}
    if verse.get('text'):
        v_top = body_bottom + 130
        v_layer = make_text_layer(image, parent, 'mission_verse',
                                   wrap_text(verse['text'], int(cfg['verse_wrap_chars'])),
                                   script_font, int(cfg['verse_size_px']), color)
        v_layer.set_justification(Gimp.TextJustification.CENTER)
        v_layer.set_offsets(cx - v_layer.get_width() // 2, v_top)
        v_bottom = v_top + v_layer.get_height()
        if verse.get('reference'):
            ref = make_text_layer(image, parent, 'mission_ref',
                                   verse['reference'],
                                   body_font, int(cfg['ref_size_px']), color)
            ref.set_offsets(cx - ref.get_width() // 2, v_bottom + 50)


def draw_tips_block(image, layout, content, panel_rects, panel_groups):
    cfg = layout['interno']['front_cover']
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    tips = content['tips']
    title = make_text_layer(image, parent, 'tips_title', tips['title'],
                            title_font, int(cfg['title_size_px']), color)
    center_layer_at(title, cx, py + int(ph * 0.10))

    items = tips.get('items') or []
    if not items:
        return

    inner = int(layout['borders']['inner_margin_px'])
    icon_size = int(cfg['icon_size_px'])
    text_padding = 80
    text_w = pw - 2 * (inner + text_padding)
    chars_per_line = max(18, int(text_w / 19))

    block_top = py + int(ph * 0.20)
    block_bottom = py + ph - inner - 40
    icon_text_gap = 20

    units = []
    for i, item in enumerate(items):
        icon_layer = load_svg_icon(image, parent, item.get('icon', ''), icon_size)
        sentences = split_sentences(item.get('text', ''))
        wrapped = '\n'.join(wrap_text(line, chars_per_line)
                            for line in sentences.split('\n'))
        text_layer = make_text_layer(image, parent, 'tips_text_{}'.format(i),
                                      wrapped, body_font,
                                      int(cfg['body_size_px']), color)
        text_layer.set_justification(Gimp.TextJustification.CENTER)
        unit_h = icon_size + icon_text_gap + text_layer.get_height()
        units.append({'icon': icon_layer, 'text': text_layer, 'h': unit_h})

    total_h = sum(u['h'] for u in units)
    n = len(units)
    available = block_bottom - block_top
    gap_between = (available - total_h) / (n - 1) if n > 1 else 0

    y = block_top
    for u in units:
        if u['icon'] is not None:
            u['icon'].set_offsets(cx - icon_size // 2, int(y))
        tw = u['text'].get_width()
        u['text'].set_offsets(cx - tw // 2,
                              int(y + icon_size + icon_text_gap))
        y += u['h'] + gap_between


# ============================================================ palette helper
def draw_palette_with_labels(image, layout, panel_rects, panel_groups, *,
                              colors, names, panel_name, y_factor,
                              palette_cfg, label_size_px, label_y_offset_px=50,
                              layer_prefix='pal'):
    """Render N circles + a name below each.

    panel_name      : key into panel_rects/panel_groups for the host panel
    y_factor        : 0..1 — vertical center of the circles within the panel
    palette_cfg     : {circle_radius_px, circle_spacing_px}
    label_size_px   : font size of the color names
    """
    shim_layout = {
        'panels': {'madrinha': {'palette': palette_cfg}},
        'borders': layout['borders'],
    }
    shim_invite = {'madrinha': {'palette': colors}}
    shim_rects = {'madrinha': panel_rects[panel_name]}
    shim_groups = {'madrinha': panel_groups[panel_name]}
    palette_module.draw_palette(image, shim_layout, shim_invite,
                                shim_rects, shim_groups,
                                panel_name='madrinha', y_factor=y_factor,
                                layer_name='{}_palette'.format(layer_prefix))

    color = make_color(layout['text_color'])
    body_font = resolve_font(layout, 'serif')
    radius = int(palette_cfg['circle_radius_px'])
    centers = palette_module.compute_circle_centers(
        shim_layout, shim_rects, 'madrinha', len(colors),
    )
    px, py, pw, ph = panel_rects[panel_name]
    cy_palette = py + int(ph * y_factor)
    label_y = cy_palette + radius + int(label_y_offset_px)

    parent = panel_groups[panel_name]
    for i, name in enumerate(names):
        lbl = make_text_layer(image, parent,
                              '{}_color_label_{}'.format(layer_prefix, i),
                              name, body_font, int(label_size_px), color)
        lbl.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(lbl, centers[i], label_y)


# ============================================================ misc helpers
def split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return '\n'.join(p for p in parts if p)


def load_svg_icon(image, parent_group, icon_name, target_px):
    svg = _ICONS_DIR / '{}.svg'.format(icon_name)
    if not svg.exists():
        print('[bridal_party] icon not found: {}'.format(svg))
        return None
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image,
            Gio.File.new_for_path(str(svg)),
        )
    except Exception as e:
        print('[bridal_party] failed loading SVG {}: {}'.format(icon_name, e))
        return None
    image.insert_layer(layer, parent_group, 0)
    layer.set_name('icon_{}'.format(icon_name))
    cur_w = layer.get_width()
    if cur_w and cur_w != target_px:
        scale = target_px / float(cur_w)
        new_h = int(layer.get_height() * scale)
        layer.scale(target_px, new_h, False)
    return layer

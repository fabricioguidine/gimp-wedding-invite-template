"""Shared tri-fold leaflet engine (wedding-sponsors + wedding-juniors).

Each leaflet is a tri-fold with two sides:

    externo (visible when folded):
        back_cover     |  middle (calendar+info)  |  front_cover (title)

    interno (unfolded inside):
        back_cover (mission)  |  middle (role-specific)  |  front_cover (tips)

The externo, the back-cover mission and the front-cover tips are identical
across every variant; only the middle interno panel varies (single-role center
for one person, split center for a couple). Those shared bits live here; the
per-module variant list lives in each module's build.py.
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
import paper as paper_module


_REPO_ROOT = Path(__file__).resolve().parent.parent
_ICONS_DIR = _REPO_ROOT / 'assets' / 'ornaments' / 'icons'

# Sunday-first weekday initials per locale (content.date.locale). Used to fill
# the calendar header automatically instead of hardcoding it in layout.yaml.
_WEEKDAY_INITIALS = {
    'pt': ['D', 'S', 'T', 'Q', 'Q', 'S', 'S'],
    'en': ['S', 'M', 'T', 'W', 'T', 'F', 'S'],
    'es': ['D', 'L', 'M', 'X', 'J', 'V', 'S'],
    'fr': ['D', 'L', 'M', 'M', 'J', 'V', 'S'],
    'it': ['D', 'L', 'M', 'M', 'G', 'V', 'S'],
    'de': ['S', 'M', 'D', 'M', 'D', 'F', 'S'],
}


def _weekday_initials(locale, fallback):
    """Day initials for a locale code ('pt', 'pt-BR', 'en_US', ...) or fallback."""
    if not locale:
        return fallback
    key = str(locale).lower().replace('_', '-').split('-')[0]
    return _WEEKDAY_INITIALS.get(key, fallback)


def _input_png(inputs_dir, name):
    """Return inputs_dir/name if it exists (a user override PNG), else None."""
    if not inputs_dir:
        return None
    p = Path(inputs_dir) / name
    return p if p.exists() else None


def _clamp_pct(value, default=1.0):
    try:
        return max(0.1, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


# ============================================================ canvas/setup
def _apply_paper(layout, content):
    """Return a layout copy whose canvas matches content.paper's printable area
    (a4 or letter), so the leaflet prints with equal margins on that sheet."""
    name = paper_module.normalize((content or {}).get('paper'))
    dpi = int(layout['canvas'].get('dpi', 300))
    cw, ch = paper_module.printable_px(name, dpi=dpi)
    return dict(layout, canvas=dict(layout['canvas'], width_px=cw, height_px=ch))


def build_canvas(layout, bg_path, content=None, inputs_dir=None):
    image = create_canvas(layout, None)
    # content-level background colour override (TUI-editable via content.yaml)
    if content and content.get('background_color'):
        _fill_bg_color(image, content['background_color'])
    # full-bleed background image override from inputs/background.png
    bg_override = _input_png(inputs_dir, 'background.png')
    if bg_override:
        _place_background(image, layout, str(bg_override), full=True)
    elif bg_path:
        _place_background(image, layout, bg_path)
    return image


def _fill_bg_color(image, hex_color):
    bg = next((l for l in image.get_layers() if l.get_name() == 'bg'), None)
    if bg is None:
        return
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(make_color(hex_color))
        bg.fill(Gimp.FillType.FOREGROUND)
    finally:
        Gimp.context_pop()


def _place_background(image, layout, bg_path, full=False):
    cfg = layout.get('background_image') or {}
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image,
            Gio.File.new_for_path(str(bg_path)),
        )
    except Exception as e:
        print('[trifold] could not load bg {}: {}'.format(bg_path, e))
        return
    image.insert_layer(layer, None, 0)
    layer.set_name('bg_image')
    cw, ch = image.get_width(), image.get_height()
    lw, lh = layer.get_width(), layer.get_height()
    if lw == 0 or lh == 0:
        return
    # an inputs/background.png override fills full-bleed at full opacity;
    # a --bg image is a soft watermark (layout's opacity / scale_mode).
    mode = 'cover' if full else cfg.get('scale_mode', 'cover')
    scale = (min if mode == 'fit' else max)(cw / float(lw), ch / float(lh))
    new_w, new_h = max(1, int(lw * scale)), max(1, int(lh * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets((cw - new_w) // 2, (ch - new_h) // 2)
    opacity = 100.0 if full else float(cfg.get('opacity_pct', 20))
    layer.set_opacity(max(0.0, min(100.0, opacity)))


def create_panel_groups(image, panel_rects):
    groups = {}
    for name in panel_rects:
        g = Gimp.GroupLayer.new(image)
        g.set_name('panel_{}'.format(name))
        image.insert_layer(g, None, 0)
        groups[name] = g
    return groups


def prepare_image(layout, bg_path, content=None, inputs_dir=None):
    """One-shot: canvas + bg + panels + borders + panel groups.

    ``content`` may carry a ``background_color`` override; ``inputs_dir`` may hold
    a ``background.png`` to use full-bleed. Returns (image, panel_rects, panel_groups).
    """
    image = build_canvas(layout, bg_path, content, inputs_dir)
    panel_rects = compute_panel_rects(layout)
    draw_borders(image, layout, panel_rects)
    panel_groups = create_panel_groups(image, panel_rects)
    return image, panel_rects, panel_groups


def save_xcf(image, path):
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image,
                   Gio.File.new_for_path(str(path)), None)
    image.delete()


# ============================================================ externo
def draw_externo(image, layout, content, panel_rects, panel_groups, inputs_dir=None,
                 variant=None):
    """The folded-cover face. Same for all three manuals."""
    cfg = layout['externo']
    color = make_color(layout['text_color'])

    _draw_cover(image, layout, cfg['front_cover'], content, panel_rects,
                panel_groups, color, inputs_dir, variant)
    _draw_calendar_with_info(image, layout, cfg['middle'], content,
                             panel_rects, panel_groups, color)
    _draw_back_cover_logo(image, layout, cfg['back_cover'], content,
                          panel_rects, panel_groups, inputs_dir)


def _draw_cover(image, layout, cfg, content, panel_rects, panel_groups, color,
                inputs_dir, variant):
    """Front cover: optional illustration + title + couple, distributed evenly."""
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    inner = int(layout['borders']['inner_margin_px'])

    blocks = []
    art = _load_cover_art(image, layout, content, panel_rects, panel_groups,
                          inputs_dir, variant)
    if art is not None:
        blocks.append(art)

    # keep the author's explicit line breaks (so e.g. "Page Boy" stays on one
    # line); content.yaml splits the title across lines with a YAML block scalar
    title = make_text_layer(image, parent, 'cover_title',
                            content['cover']['title'].strip(),
                            resolve_font(layout, 'script_bold'),
                            int(cfg['title_size_px']), color)
    title.set_justification(Gimp.TextJustification.CENTER)
    blocks.append(title)

    subtitle = make_text_layer(
        image, parent, 'cover_subtitle',
        '{} & {}'.format(content['couple']['bride'], content['couple']['groom']),
        resolve_font(layout, 'serif'), int(cfg['subtitle_size_px']), color)
    subtitle.set_justification(Gimp.TextJustification.CENTER)
    blocks.append(subtitle)

    tops = _distribute_tops(py, ph, inner, [b.get_height() for b in blocks])
    _place_centered(blocks, tops, cx)


def _draw_calendar_with_info(image, layout, cfg, content, panel_rects, panel_groups, color):
    panel = 'middle'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    inner = int(layout['borders']['inner_margin_px'])

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    # weekday header: auto from content.date.locale; falls back to layout labels.
    cal_cfg = cfg['calendar']
    locale = content['date'].get('locale')
    if locale:
        cal_cfg = dict(cal_cfg)
        cal_cfg['weekday_labels'] = _weekday_initials(locale, cal_cfg['weekday_labels'])
    year, month = int(content['date']['year']), int(content['date']['month'])

    # blocks top→bottom: weekday, date, calendar grid, ceremony lines — evenly spaced
    blocks = []  # ('layer', layer) | ('cal', height)
    wd = make_text_layer(image, parent, 'cal_weekday', content['date']['weekday_name'],
                         title_font, int(cfg['weekday_size_px']), color)
    wd.set_justification(Gimp.TextJustification.CENTER)
    blocks.append(('layer', wd))

    date_text = '{} | {} | {}'.format(content['date']['day'],
                                       content['date']['month_name'],
                                       content['date']['year'])
    date = make_text_layer(image, parent, 'cal_date', date_text,
                           body_font, int(cfg['date_size_px']), color)
    date.set_justification(Gimp.TextJustification.CENTER)
    blocks.append(('layer', date))

    blocks.append(('cal', calendar_module.grid_height(year, month, cal_cfg['cell_size_px'])))

    ceremony = content['ceremony']
    if ceremony.get('arrival_time'):
        arr = make_text_layer(image, parent, 'cal_arrival',
                              '{}: {}'.format(ceremony['arrival_label'], ceremony['arrival_time']),
                              body_font, int(cfg['arrival_size_px']), color)
        arr.set_justification(Gimp.TextJustification.CENTER)
        blocks.append(('layer', arr))
    if ceremony.get('venue'):
        venue = make_text_layer(image, parent, 'cal_venue',
                                wrap_text(ceremony['venue'], 24),
                                body_font, int(cfg['venue_size_px']), color)
        venue.set_justification(Gimp.TextJustification.CENTER)
        blocks.append(('layer', venue))
    if ceremony.get('address'):
        addr = make_text_layer(image, parent, 'cal_addr',
                               wrap_text(ceremony['address'], 26),
                               body_font, int(cfg['address_size_px']), color)
        addr.set_justification(Gimp.TextJustification.CENTER)
        blocks.append(('layer', addr))

    heights = [b[1].get_height() if b[0] == 'layer' else b[1] for b in blocks]
    tops = _distribute_tops(py, ph, inner, heights)
    for b, t in zip(blocks, tops):
        if b[0] == 'layer':
            b[1].set_offsets(cx - b[1].get_width() // 2, int(t))
        else:
            shim_invite = {'save_the_date': {'year': year, 'month': month,
                                             'highlighted_day': int(content['date']['day'])}}
            calendar_module.draw_calendar(
                image, _shim_calendar_layout(layout, cal_cfg), shim_invite,
                {'save_the_date': panel_rects[panel]},
                {'save_the_date': panel_groups[panel]}, grid_top=int(t))


def _shim_calendar_layout(layout, calendar_cfg):
    return {
        'panels': {'save_the_date': {'calendar': calendar_cfg}},
        'borders': layout['borders'],
        'fonts': layout['fonts'],
    }


def _draw_back_cover_logo(image, layout, cfg, content, panel_rects, panel_groups,
                          inputs_dir=None):
    panel = 'back_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    # an inputs/logo.png override wins; otherwise draw a generic monogram from
    # the couple's initials, so no personal artwork is committed.
    override = _input_png(inputs_dir, 'logo.png')
    if override:
        _place_logo_image(image, override, cfg, content, px, py, pw, ph, parent)
    else:
        _draw_monogram(image, layout, content, px, py, pw, ph, parent)


def _place_logo_image(image, path, cfg, content, px, py, pw, ph, parent):
    try:
        layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image,
                                     Gio.File.new_for_path(str(path)))
    except Exception as e:
        print('[trifold] failed to load logo: {}'.format(e))
        return
    image.insert_layer(layer, parent, 0)
    layer.set_name('back_cover_logo')
    pad = int(cfg.get('logo_padding_px', 50))
    pct = _clamp_pct((content.get('images') or {}).get('logo_pct', 1.0))
    target_w, target_h = (pw - 2 * pad) * pct, (ph - 2 * pad) * pct
    cur_w, cur_h = layer.get_width(), layer.get_height()
    if cur_w == 0 or cur_h == 0:
        return
    scale = min(target_w / float(cur_w), target_h / float(cur_h))
    layer.scale(max(1, int(cur_w * scale)), max(1, int(cur_h * scale)), False)
    layer.set_offsets(px + (pw - layer.get_width()) // 2,
                      py + (ph - layer.get_height()) // 2)


def _draw_monogram(image, layout, content, px, py, pw, ph, parent):
    """Generic back-cover monogram: a ring around the couple's initials, with
    their names and the date — all derived from content (nothing personal)."""
    color = make_color(layout['text_color'])
    cx, cy = px + pw // 2, py + ph // 2
    radius = int(min(pw, ph) * 0.30)

    ring = Gimp.Layer.new(image, 'monogram_ring', image.get_width(),
                          image.get_height(), Gimp.ImageType.RGBA_IMAGE,
                          100.0, Gimp.LayerMode.NORMAL)
    image.insert_layer(ring, parent, 0)
    ring.add_alpha()
    ring.fill(Gimp.FillType.TRANSPARENT)
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(color)
        Gimp.context_set_antialias(True)
        Gimp.context_set_stroke_method(Gimp.StrokeMethod.LINE)
        Gimp.context_set_line_width(3.0)
        image.select_ellipse(Gimp.ChannelOps.REPLACE,
                             cx - radius, cy - radius, 2 * radius, 2 * radius)
        ring.edit_stroke_selection()
        Gimp.Selection.none(image)
    finally:
        Gimp.context_pop()

    couple = content.get('couple') or {}
    bride = (str(couple.get('bride', '')).strip() or '?')
    groom = (str(couple.get('groom', '')).strip() or '?')
    script = resolve_font(layout, 'script_bold')
    serif = resolve_font(layout, 'serif')

    ini = make_text_layer(image, parent, 'monogram_initials',
                          '{} {}'.format(bride[:1].upper(), groom[:1].upper()),
                          script, int(radius * 0.85), color)
    ini.set_justification(Gimp.TextJustification.CENTER)
    center_layer_at(ini, cx, cy - int(radius * 0.10))

    names = make_text_layer(image, parent, 'monogram_names',
                            '{} & {}'.format(bride, groom).upper(),
                            serif, max(14, int(radius * 0.14)), color)
    names.set_justification(Gimp.TextJustification.CENTER)
    center_layer_at(names, cx, cy + int(radius * 0.45))

    date = content.get('date') or {}
    if date.get('day') and date.get('month'):
        dstr = '{:02d}.{:02d}.{}'.format(int(date['day']), int(date['month']),
                                         str(date.get('year', ''))[-2:])
        dl = make_text_layer(image, parent, 'monogram_date', dstr, serif,
                             max(12, int(radius * 0.13)), color)
        dl.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(dl, cx, cy + int(radius * 0.68))


# ============================================================ vertical layout
def _distribute_tops(py, ph, inner, heights):
    """Top-y for each block so the gaps BETWEEN blocks and to the top/bottom
    inner margins are all equal (space-evenly). Keeps every panel visually
    balanced regardless of how much text each block holds."""
    avail = ph - 2 * inner
    n = len(heights)
    gap = (avail - sum(heights)) / (n + 1) if n else 0
    tops, y = [], py + inner + gap
    for h in heights:
        tops.append(y)
        y += h + gap
    return tops


def _place_centered(layers, tops, cx):
    for layer, t in zip(layers, tops):
        layer.set_offsets(cx - layer.get_width() // 2, int(t))


def _palette_block_height(palette_cfg, names, label_size_px, label_y_offset_px=50):
    """Height of a palette unit: swatch diameter + gap + (1 or 2)-line labels."""
    radius = int(palette_cfg['circle_radius_px'])
    lines = 2 if any(' ' in n for n in names) else 1
    return 2 * radius + int(label_y_offset_px) + int(lines * label_size_px * 1.3)


# ============================================================ interno blocks
def draw_mission_block(image, layout, content, panel_rects, panel_groups):
    cfg = layout['interno']['back_cover']
    panel = 'back_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    inner = int(layout['borders']['inner_margin_px'])
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    script_font = resolve_font(layout, 'script')
    body_font = resolve_font(layout, 'serif')

    mission = content['mission']
    layers = []

    title = make_text_layer(image, parent, 'mission_title', mission['title'],
                            title_font, int(cfg['title_size_px']), color)
    title.set_justification(Gimp.TextJustification.CENTER)
    layers.append(title)

    body_text = (mission.get('body') or '').strip()
    if body_text:
        body = make_text_layer(image, parent, 'mission_body',
                               wrap_text(body_text, int(cfg['body_wrap_chars'])),
                               body_font, int(cfg['body_size_px']), color)
        body.set_justification(Gimp.TextJustification.CENTER)
        layers.append(body)

    # optional highlighted call-to-action ("Aceita ser nosso Pajem?")
    highlight = (mission.get('highlight') or '').strip()
    if highlight:
        hl = make_text_layer(image, parent, 'mission_highlight',
                             wrap_text(highlight, int(cfg.get('highlight_wrap_chars', 16))),
                             title_font, int(cfg.get('highlight_size_px', 60)), color)
        hl.set_justification(Gimp.TextJustification.CENTER)
        layers.append(hl)

    verse = mission.get('verse') or {}
    if verse.get('text'):
        v_layer = make_text_layer(image, parent, 'mission_verse',
                                   wrap_text(verse['text'], int(cfg['verse_wrap_chars'])),
                                   script_font, int(cfg['verse_size_px']), color)
        v_layer.set_justification(Gimp.TextJustification.CENTER)
        layers.append(v_layer)
        if verse.get('reference'):
            ref = make_text_layer(image, parent, 'mission_ref', verse['reference'],
                                   body_font, int(cfg['ref_size_px']), color)
            ref.set_justification(Gimp.TextJustification.CENTER)
            layers.append(ref)

    tops = _distribute_tops(py, ph, inner, [l.get_height() for l in layers])
    _place_centered(layers, tops, cx)


def draw_tips_block(image, layout, content, panel_rects, panel_groups):
    cfg = layout['interno']['front_cover']
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    inner = int(layout['borders']['inner_margin_px'])
    tips = content['tips']
    title = make_text_layer(image, parent, 'tips_title', tips['title'],
                            title_font, int(cfg['title_size_px']), color)
    title.set_justification(Gimp.TextJustification.CENTER)

    items = tips.get('items') or []
    if not items:
        tops = _distribute_tops(py, ph, inner, [title.get_height()])
        _place_centered([title], tops, cx)
        return

    icon_size = int(cfg['icon_size_px'])
    text_padding = 80
    text_w = pw - 2 * (inner + text_padding)
    # avg glyph advance scales with the body font (~0.45 * size for Cormorant);
    # keep the wrap width in sync so a larger tips body doesn't overrun the panel.
    avg_glyph_px = max(1.0, int(cfg['body_size_px']) * 0.45)
    chars_per_line = max(14, int(text_w / avg_glyph_px))
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

    # title + each icon/text unit share equal gaps down the whole panel
    heights = [title.get_height()] + [u['h'] for u in units]
    tops = _distribute_tops(py, ph, inner, heights)
    title.set_offsets(cx - title.get_width() // 2, int(tops[0]))
    for u, t in zip(units, tops[1:]):
        if u['icon'] is not None:
            u['icon'].set_offsets(cx - icon_size // 2, int(t))
        tw = u['text'].get_width()
        u['text'].set_offsets(cx - tw // 2, int(t + icon_size + icon_text_gap))


# ============================================================ palette helper
def draw_palette_with_labels(image, layout, panel_rects, panel_groups, *,
                              colors, names, panel_name, y_factor=None,
                              circle_cy=None,
                              palette_cfg, label_size_px, label_y_offset_px=50,
                              layer_prefix='pal'):
    """Render N circles + a name below each.

    panel_name      : key into panel_rects/panel_groups for the host panel
    y_factor        : 0..1 — vertical center of the circles within the panel
    circle_cy       : absolute swatch-center y (overrides y_factor when given)
    palette_cfg     : {circle_radius_px, circle_spacing_px}
    label_size_px   : font size of the color names
    """
    _px, _py, _pw, _ph = panel_rects[panel_name]
    if circle_cy is not None:
        y_factor = (circle_cy - _py) / float(_ph)
    shim_layout = {
        'panels': {'swatches': {'palette': palette_cfg}},
        'borders': layout['borders'],
    }
    shim_invite = {'swatches': {'palette': colors}}
    shim_rects = {'swatches': panel_rects[panel_name]}
    shim_groups = {'swatches': panel_groups[panel_name]}
    palette_module.draw_palette(image, shim_layout, shim_invite,
                                shim_rects, shim_groups,
                                panel_name='swatches', y_factor=y_factor,
                                layer_name='{}_palette'.format(layer_prefix))

    color = make_color(layout['text_color'])
    body_font = resolve_font(layout, 'serif')
    radius = int(palette_cfg['circle_radius_px'])
    centers = palette_module.compute_circle_centers(
        shim_layout, shim_rects, 'swatches', len(colors),
    )
    px, py, pw, ph = panel_rects[panel_name]
    cy_palette = py + int(ph * y_factor)
    # top of the label block (anchor by top so 1- and 2-line labels line up and
    # 2-line labels don't ride up into the swatch)
    label_top = cy_palette + radius + int(label_y_offset_px)

    parent = panel_groups[panel_name]
    for i, name in enumerate(names):
        # stack multi-word names (e.g. "Marsala claro") so wide labels stay
        # inside the panel border instead of overrunning the margin
        wrapped = '\n'.join(name.split())
        lbl = make_text_layer(image, parent,
                              '{}_color_label_{}'.format(layer_prefix, i),
                              wrapped, body_font, int(label_size_px), color)
        lbl.set_justification(Gimp.TextJustification.CENTER)
        lbl.set_offsets(centers[i] - lbl.get_width() // 2, label_top)


# ============================================================ misc helpers
def split_sentences(text):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return '\n'.join(p for p in parts if p)


def load_svg_icon(image, parent_group, icon_name, target_px):
    svg = _ICONS_DIR / '{}.svg'.format(icon_name)
    if not svg.exists():
        print('[trifold] icon not found: {}'.format(svg))
        return None
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image,
            Gio.File.new_for_path(str(svg)),
        )
    except Exception as e:
        print('[trifold] failed loading SVG {}: {}'.format(icon_name, e))
        return None
    image.insert_layer(layer, parent_group, 0)
    layer.set_name('icon_{}'.format(icon_name))
    cur_w = layer.get_width()
    if cur_w and cur_w != target_px:
        scale = target_px / float(cur_w)
        new_h = int(layer.get_height() * scale)
        layer.scale(target_px, new_h, False)
    return layer


# ============================================================ variant runner
def run_variants(layout, content, bg_path, output_dir, module_name, variant_order):
    """Generic driver for the tri-fold modules.

    For each name in ``variant_order`` it merges the shared top-level content
    with ``content['variants'][name]`` and renders the externo + interno sides.
    The interno middle uses the split layout when the variant carries ``roles``
    (couple) and the single-role layout otherwise. An optional cover
    illustration (``cover.image``) is placed when present. Variants absent from
    ``content['variants']`` are skipped, so the TUI can build a chosen subset.

    The canvas is sized to the printable area of ``content.paper`` (a4/letter),
    so margins, text and distribution adapt to the selected paper.

    Returns the list of saved XCF paths (one per variant per side).
    """
    layout = _apply_paper(layout, content)
    # modules/<name>/inputs/ may hold user override PNGs (logo/background/cover).
    inputs_dir = Path(output_dir).resolve().parent.parent / 'inputs'
    shared = {k: v for k, v in content.items() if k != 'variants'}
    out = []
    for variant in variant_order:
        if variant not in content.get('variants', {}):
            continue
        vc = dict(shared)
        vc.update(content['variants'][variant])
        split = 'roles' in vc
        for side in ('externo', 'interno'):
            image, panel_rects, panel_groups = prepare_image(layout, bg_path, vc, inputs_dir)
            if side == 'externo':
                draw_externo(image, layout, vc, panel_rects, panel_groups,
                             inputs_dir, variant)
            else:
                draw_mission_block(image, layout, vc, panel_rects, panel_groups)
                if split:
                    draw_split_center(image, layout, vc, panel_rects, panel_groups)
                else:
                    draw_role_center(image, layout, vc, variant,
                                     panel_rects, panel_groups)
                draw_tips_block(image, layout, vc, panel_rects, panel_groups)
            xcf = str(Path(output_dir) /
                      '{}_{}_{}.xcf'.format(module_name, variant, side))
            save_xcf(image, xcf)
            out.append(xcf)
    return out


def _load_cover_art(image, layout, content, panel_rects, panel_groups,
                    inputs_dir=None, variant=None):
    """Load + scale the optional cover illustration; return the layer
    (unpositioned, so _draw_cover can place it in the even distribution) or None.

    Source priority: inputs/<variant>.png (user override) > content.cover.image.
    """
    override = _input_png(inputs_dir, '{}.png'.format(variant)) if variant else None
    if override:
        path = override
    else:
        rel = (content.get('cover') or {}).get('image')
        if not rel:
            return None
        path = _REPO_ROOT / rel
        if not path.exists():
            print('[trifold] cover art slot empty — drop {} or inputs/{}.png'
                  .format(path, variant))
            return None
    panel = 'front_cover'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    try:
        layer = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image,
                                     Gio.File.new_for_path(str(path)))
    except Exception as e:
        print('[trifold] failed cover art {}: {}'.format(path, e))
        return None
    image.insert_layer(layer, parent, 0)
    layer.set_name('cover_art')
    inner = int(layout['borders']['inner_margin_px'])
    cw, chh = layer.get_width(), layer.get_height()
    if not cw or not chh:
        return None
    pct = _clamp_pct((content.get('images') or {}).get('cover_pct', 1.0))
    avail_w, avail_h = (pw - 2 * inner) * pct, ph * 0.34 * pct
    scale = min(avail_w / float(cw), avail_h / float(chh))
    layer.scale(max(1, int(cw * scale)), max(1, int(chh * scale)), False)
    return layer


def draw_role_center(image, layout, content, variant, panel_rects, panel_groups):
    """Single-role interno center: title + body + palette subtitle + swatches,
    distributed evenly down the panel."""
    cfg = layout['interno']['middle']['single']
    px, py, pw, ph = panel_rects['middle']
    parent = panel_groups['middle']
    cx = px + pw // 2
    inner = int(layout['borders']['inner_margin_px'])
    color = make_color(layout['text_color'])
    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    role = content['role']

    layers = []
    title = make_text_layer(image, parent, 'role_title', role['title'],
                            title_font, int(cfg['role_title_size_px']), color)
    title.set_justification(Gimp.TextJustification.CENTER)
    layers.append(title)

    body_text = role.get('body') or ''
    if body_text:
        sentences = split_sentences(body_text)
        wrapped = '\n'.join(wrap_text(line, int(cfg['body_wrap_chars']))
                            for line in sentences.split('\n'))
        body = make_text_layer(image, parent, 'role_body', wrapped,
                               body_font, int(cfg['body_size_px']), color)
        body.set_justification(Gimp.TextJustification.CENTER)
        layers.append(body)

    subtitle = make_text_layer(image, parent, 'palette_subtitle',
                               role['palette_subtitle'], body_font,
                               int(cfg['palette_subtitle_size_px']), color)
    subtitle.set_justification(Gimp.TextJustification.CENTER)
    layers.append(subtitle)

    pal_h = _palette_block_height(cfg['palette'], role['color_names'],
                                  int(cfg['color_label_size_px']))
    tops = _distribute_tops(py, ph, inner,
                            [l.get_height() for l in layers] + [pal_h])
    _place_centered(layers, tops[:-1], cx)

    radius = int(cfg['palette']['circle_radius_px'])
    draw_palette_with_labels(
        image, layout, panel_rects, panel_groups,
        colors=role['colors'], names=role['color_names'],
        panel_name='middle', circle_cy=int(tops[-1]) + radius,
        palette_cfg=cfg['palette'],
        label_size_px=cfg['color_label_size_px'], layer_prefix=variant)


def draw_split_center(image, layout, content, panel_rects, panel_groups):
    """Split interno center (couple): overall title + two sections (each a
    title + body + palette), all distributed evenly down the panel."""
    cfg = layout['interno']['middle']['split']
    pal_cfg = cfg['palette']
    px, py, pw, ph = panel_rects['middle']
    parent = panel_groups['middle']
    cx = px + pw // 2
    inner = int(layout['borders']['inner_margin_px'])
    color = make_color(layout['text_color'])
    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    roles = content['roles']

    # build the ordered block list; palette entries carry a computed height
    blocks = []  # ('text', layer) | ('palette', role, prefix, height)
    overall = make_text_layer(image, parent, 'couple_title', roles['overall_title'],
                              title_font, int(cfg['overall_title_size_px']), color)
    overall.set_justification(Gimp.TextJustification.CENTER)
    blocks.append(('text', overall))

    for key, prefix in (('groomsman', 'cpl_groomsman'),
                        ('bridesmaid', 'cpl_bridesmaid')):
        role = roles[key]
        title = make_text_layer(image, parent, '{}_title'.format(prefix),
                                role['title'], title_font,
                                int(cfg['section_title_size_px']), color)
        title.set_justification(Gimp.TextJustification.CENTER)
        blocks.append(('text', title))
        if role.get('body'):
            body = make_text_layer(image, parent, '{}_body'.format(prefix),
                                   wrap_text(role['body'], int(cfg['body_wrap_chars'])),
                                   body_font, int(cfg['body_size_px']), color)
            body.set_justification(Gimp.TextJustification.CENTER)
            blocks.append(('text', body))
        pal_h = _palette_block_height(pal_cfg, role['color_names'],
                                      int(cfg['color_label_size_px']), 45)
        blocks.append(('palette', role, prefix, pal_h))

    heights = [b[1].get_height() if b[0] == 'text' else b[3] for b in blocks]
    tops = _distribute_tops(py, ph, inner, heights)
    radius = int(pal_cfg['circle_radius_px'])
    for b, t in zip(blocks, tops):
        if b[0] == 'text':
            b[1].set_offsets(cx - b[1].get_width() // 2, int(t))
        else:
            _, role, prefix, _ = b
            draw_palette_with_labels(
                image, layout, panel_rects, panel_groups,
                colors=role['colors'], names=role['color_names'],
                panel_name='middle', circle_cy=int(t) + radius, palette_cfg=pal_cfg,
                label_size_px=cfg['color_label_size_px'], label_y_offset_px=45,
                layer_prefix=prefix)

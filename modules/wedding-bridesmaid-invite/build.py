"""wedding-bridesmaid-invite — tri-fold leaflet, two sides (externo + interno).

Generates 2 XCFs per run. Shares cover/calendar/mission/tips/palette helpers
with the groomsman + couple modules via src/bridal_party_blocks.py; only the
bridesmaid-specific role center stays here.
"""

from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp

import bridal_party_blocks as bp
from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text


def run(layout, content, bg_path, output_dir, module_name):
    out = []
    for side, draw_fn in (('externo', _draw_externo),
                          ('interno', _draw_interno)):
        image, panel_rects, panel_groups = bp.prepare_image(layout, bg_path)
        draw_fn(image, layout, content, panel_rects, panel_groups)
        xcf = str(Path(output_dir) / '{}_{}.xcf'.format(module_name, side))
        bp.save_xcf(image, xcf)
        out.append(xcf)
    return out


def _draw_externo(image, layout, content, panel_rects, panel_groups):
    bp.draw_externo(image, layout, content, panel_rects, panel_groups)


def _draw_interno(image, layout, content, panel_rects, panel_groups):
    bp.draw_mission_block(image, layout, content, panel_rects, panel_groups)
    _draw_role_center(image, layout, content, panel_rects, panel_groups)
    bp.draw_tips_block(image, layout, content, panel_rects, panel_groups)


def _draw_role_center(image, layout, content, panel_rects, panel_groups):
    """Single-role center: title + body + palette + color labels."""
    cfg = layout['interno']['middle']
    panel = 'middle'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    role = content['role']
    title = make_text_layer(image, parent, 'role_title', role['title'],
                            title_font, int(cfg['role_title_size_px']), color)
    center_layer_at(title, cx, py + int(ph * 0.13))

    body_text = role.get('body') or ''
    if body_text:
        sentences = bp.split_sentences(body_text)
        wrapped = '\n'.join(wrap_text(line, int(cfg['body_wrap_chars']))
                            for line in sentences.split('\n'))
        body = make_text_layer(image, parent, 'role_body', wrapped,
                               body_font, int(cfg['body_size_px']), color)
        body.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(body, cx, py + int(ph * 0.40))

    subtitle = make_text_layer(image, parent, 'palette_subtitle',
                                role['palette_subtitle'], body_font,
                                int(cfg['palette_subtitle_size_px']), color)
    center_layer_at(subtitle, cx, py + int(ph * 0.66))

    bp.draw_palette_with_labels(
        image, layout, panel_rects, panel_groups,
        colors=role['colors'],
        names=role['color_names'],
        panel_name=panel,
        y_factor=0.78,
        palette_cfg=cfg['palette'],
        label_size_px=cfg['color_label_size_px'],
        layer_prefix='bridesmaid',
    )



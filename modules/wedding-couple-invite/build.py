"""wedding-couple-invite — for godparents who attend as a couple.

Externo + interno follow the same shape as the bridesmaid/groomsman manuals.
The interno *middle* panel is the only meaningful difference: it stacks a
groomsman section over a bridesmaid section, each with its own palette and
body text, under a single "Couple" header.
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
    _draw_split_center(image, layout, content, panel_rects, panel_groups)
    bp.draw_tips_block(image, layout, content, panel_rects, panel_groups)


def _draw_split_center(image, layout, content, panel_rects, panel_groups):
    """Stacked groomsman + bridesmaid sections, each with title/body/palette."""
    cfg = layout['interno']['middle']
    panel = 'middle'
    px, py, pw, ph = panel_rects[panel]
    parent = panel_groups[panel]
    cx = px + pw // 2
    color = make_color(layout['text_color'])

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')

    roles = content['roles']

    overall = make_text_layer(image, parent, 'couple_title',
                              roles['overall_title'], title_font,
                              int(cfg['overall_title_size_px']), color)
    inner_margin = int(layout['borders']['inner_margin_px'])
    overall.set_offsets(cx - overall.get_width() // 2,
                        py + inner_margin + int(cfg['overall_title_y_top_offset_px']))

    _draw_section(image, parent, layout, content, panel_rects, panel_groups,
                  role=roles['groomsman'],
                  layer_prefix='cpl_groomsman',
                  title_y_factor=float(cfg['groomsman_title_y_factor']),
                  body_y_factor=float(cfg['groomsman_body_y_factor']),
                  palette_y_factor=float(cfg['groomsman_palette_y_factor']),
                  cfg=cfg, color=color, cx=cx, py=py, ph=ph,
                  title_font=title_font, body_font=body_font)
    _draw_section(image, parent, layout, content, panel_rects, panel_groups,
                  role=roles['bridesmaid'],
                  layer_prefix='cpl_bridesmaid',
                  title_y_factor=float(cfg['bridesmaid_title_y_factor']),
                  body_y_factor=float(cfg['bridesmaid_body_y_factor']),
                  palette_y_factor=float(cfg['bridesmaid_palette_y_factor']),
                  cfg=cfg, color=color, cx=cx, py=py, ph=ph,
                  title_font=title_font, body_font=body_font)


def _draw_section(image, parent, layout, content, panel_rects, panel_groups, *,
                   role, layer_prefix, title_y_factor, body_y_factor,
                   palette_y_factor, cfg, color, cx, py, ph,
                   title_font, body_font):
    title = make_text_layer(image, parent, '{}_title'.format(layer_prefix),
                            role['title'], title_font,
                            int(cfg['section_title_size_px']), color)
    center_layer_at(title, cx, py + int(ph * title_y_factor))

    if role.get('body'):
        body = make_text_layer(image, parent, '{}_body'.format(layer_prefix),
                                wrap_text(role['body'], int(cfg['body_wrap_chars'])),
                                body_font, int(cfg['body_size_px']), color)
        body.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(body, cx, py + int(ph * body_y_factor))

    bp.draw_palette_with_labels(
        image, layout, panel_rects, panel_groups,
        colors=role['colors'],
        names=role['color_names'],
        panel_name='middle',
        y_factor=palette_y_factor,
        palette_cfg=cfg['palette'],
        label_size_px=cfg['color_label_size_px'],
        label_y_offset_px=45,
        layer_prefix=layer_prefix,
    )

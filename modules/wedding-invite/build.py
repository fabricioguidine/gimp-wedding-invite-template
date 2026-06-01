"""wedding-invite — GIMP 3 builder for the single-page portrait invite.

Reverse-engineered from the reference invite PDF:

    + verse (italic)              ~6% from top
    + verse reference             ~8.5%
    + blessing (UPPER bold)       ~17%
    + thin divider                ~20.5%
    + parents (2 columns)         ~25%
    + COUPLE NAMES (huge italic)  ~40%
    + invitation line (bold)      ~49%
    + day (script bold)           ~56%
    + date "10 | October | 2026"  ~61%
    + ceremony time + venue + addr ~71%
    + reception venue + addr      ~82%
    + RSVP small print            ~95%

The optional background image (church/venue/watercolor) sits below all text
at configurable opacity. Sizes/positions live in layout.yaml.
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio

from pathlib import Path

from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text


def run(layout, content, bg_path, output_dir, module_name):
    """Entrypoint called by src/module_runner.py. Returns list of saved XCF paths."""
    image = _create_canvas(layout)
    _place_background_layers(image, layout)
    if bg_path:
        _place_background(image, layout, bg_path)
    _draw_all_text(image, layout, content)

    xcf_path = str(Path(output_dir) / '{}.xcf'.format(module_name))
    Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE,
        image,
        Gio.File.new_for_path(xcf_path),
        None,
    )
    image.delete()
    return [xcf_path]


def _create_canvas(layout):
    canvas = layout['canvas']
    w = int(canvas['width_px'])
    h = int(canvas['height_px'])
    dpi = float(canvas['dpi'])

    image = Gimp.Image.new(w, h, Gimp.ImageBaseType.RGB)
    image.set_resolution(dpi, dpi)

    bg_layer = Gimp.Layer.new(
        image, 'bg', w, h,
        Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(bg_layer, None, 0)
    Gimp.context_set_foreground(make_color(canvas['background_color']))
    bg_layer.fill(Gimp.FillType.FOREGROUND)
    return image


def _place_background(image, layout, bg_path):
    cfg = layout.get('background_image') or {}
    try:
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE,
            image,
            Gio.File.new_for_path(str(bg_path)),
        )
    except Exception as e:
        print('[wedding-invite] could not load bg {}: {}'.format(bg_path, e))
        return

    # Insert ABOVE the creme fill but BELOW any text (text added later -> on top).
    image.insert_layer(layer, None, 0)
    layer.set_name('bg_image')

    cw = image.get_width()
    ch = image.get_height()
    lw, lh = layer.get_width(), layer.get_height()
    if lw == 0 or lh == 0:
        return

    mode = cfg.get('scale_mode', 'cover')
    if mode == 'fit':
        scale = min(cw / float(lw), ch / float(lh))
    else:  # cover
        scale = max(cw / float(lw), ch / float(lh))
    new_w = max(1, int(lw * scale))
    new_h = max(1, int(lh * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets((cw - new_w) // 2, (ch - new_h) // 2)

    opacity = float(cfg.get('opacity_pct', 35))
    layer.set_opacity(max(0.0, min(100.0, opacity)))


def _place_background_layers(image, layout):
    """Insert the configured design background layers below all text.

    Each entry in ``layout['background_layers']`` is a dict with ``file`` (path
    relative to the repo root), ``scale_mode`` ('cover' | 'fit'), ``opacity_pct``
    and an optional ``band`` ({center_pct, height_pct, feather_px}) that reveals
    only a feathered horizontal strip. List order is bottom-to-top.
    """
    specs = layout.get('background_layers') or []
    repo_root = Path(__file__).resolve().parent.parent.parent
    for spec in specs:
        rel = spec.get('file')
        if not rel:
            continue
        path = repo_root / rel
        if not path.exists():
            print('[wedding-invite] bg layer not found: {}'.format(path))
            continue
        try:
            layer = Gimp.file_load_layer(
                Gimp.RunMode.NONINTERACTIVE, image,
                Gio.File.new_for_path(str(path)),
            )
        except Exception as e:
            print('[wedding-invite] failed bg layer {}: {}'.format(path, e))
            continue
        image.insert_layer(layer, None, 0)
        layer.set_name('bg_{}'.format(Path(rel).stem))
        _scale_layer_to_canvas(image, layer, spec.get('scale_mode', 'cover'))
        band = spec.get('band')
        if band:
            _apply_band_mask(image, layer, band)
        layer.set_opacity(max(0.0, min(100.0, float(spec.get('opacity_pct', 100)))))


def _scale_layer_to_canvas(image, layer, mode):
    cw, ch = image.get_width(), image.get_height()
    lw, lh = layer.get_width(), layer.get_height()
    if lw == 0 or lh == 0:
        return
    if mode == 'fit':
        scale = min(cw / float(lw), ch / float(lh))
    else:  # cover
        scale = max(cw / float(lw), ch / float(lh))
    new_w, new_h = max(1, int(lw * scale)), max(1, int(lh * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets((cw - new_w) // 2, (ch - new_h) // 2)


def _apply_band_mask(image, layer, band):
    """Reveal only a feathered horizontal band of the layer via a layer mask."""
    w, h = image.get_width(), image.get_height()
    center = float(band.get('center_pct', 0.5))
    height_pct = float(band.get('height_pct', 0.4))
    feather = int(band.get('feather_px', 0))
    top = int((center - height_pct / 2.0) * h)
    band_h = int(height_pct * h)
    mask = layer.create_mask(Gimp.AddMaskType.BLACK)
    layer.add_mask(mask)
    image.select_rectangle(Gimp.ChannelOps.REPLACE, 0, top, w, band_h)
    if feather > 0:
        Gimp.Selection.feather(image, float(feather))
    mask.edit_fill(Gimp.FillType.WHITE)
    Gimp.Selection.none(image)


def _draw_all_text(image, layout, content):
    w = image.get_width()
    h = image.get_height()
    cx = w // 2
    color = make_color(layout['text_color'])
    blocks = layout['blocks']

    _draw_verse(image, layout, content, blocks['verse'], blocks['verse_reference'],
                cx, h, color)
    _draw_centered_line(image, layout, content['blessing'],
                        blocks['blessing'], cx, h, color, layer_name='blessing')
    _draw_divider(image, layout, blocks['divider'], cx, h, color)
    _draw_parents(image, layout, content['parents'], blocks['parents'],
                  w, h, color)
    _draw_couple(image, layout, content['couple'], blocks['couple'], cx, h, color)
    _draw_centered_line(image, layout, content['invitation'],
                        blocks['invitation'], cx, h, color, layer_name='invitation')
    _draw_centered_line(image, layout, content['day'],
                        blocks['day'], cx, h, color, layer_name='day')
    _draw_date(image, layout, content['date'], blocks['date'], cx, h, color)
    _draw_multi_line(image, layout, blocks['ceremony'], cx, h, color,
                     lines=[
                         (content['ceremony']['time'],    'time'),
                         (content['ceremony']['venue'],   'venue'),
                         (content['ceremony']['address'], 'address'),
                     ],
                     layer_prefix='ceremony')
    _draw_multi_line(image, layout, blocks['reception'], cx, h, color,
                     lines=[
                         (content['reception']['venue'],   'venue'),
                         (content['reception']['address'], 'address'),
                     ],
                     layer_prefix='reception')
    _draw_rsvp(image, layout, content['rsvp'], blocks['rsvp'], cx, h, color)


# ------------------------------------------------------------------ block fns
def _draw_verse(image, layout, content, cfg_text, cfg_ref, cx, h, color):
    text = wrap_text(content['verse']['text'], int(cfg_text['wrap_chars']))
    font = resolve_font(layout, cfg_text['font'])
    layer = make_text_layer(image, None, 'verse', text, font,
                            int(cfg_text['size_px']), color)
    layer.set_justification(Gimp.TextJustification.CENTER)
    center_layer_at(layer, cx, int(h * float(cfg_text['y_pct'])))

    font_ref = resolve_font(layout, cfg_ref['font'])
    layer_ref = make_text_layer(image, None, 'verse_ref',
                                content['verse']['reference'],
                                font_ref, int(cfg_ref['size_px']), color)
    center_layer_at(layer_ref, cx, int(h * float(cfg_ref['y_pct'])))


def _draw_centered_line(image, layout, text, cfg, cx, h, color, layer_name):
    font = resolve_font(layout, cfg['font'])
    layer = make_text_layer(image, None, layer_name, text, font,
                            int(cfg['size_px']), color)
    center_layer_at(layer, cx, int(h * float(cfg['y_pct'])))


def _draw_divider(image, layout, cfg, cx, h, color):
    width = int(cfg['width_px'])
    thickness = int(cfg['thickness_px'])
    y = int(h * float(cfg['y_pct']))
    layer = Gimp.Layer.new(image, 'divider', image.get_width(), image.get_height(),
                           Gimp.ImageType.RGBA_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    image.insert_layer(layer, None, 0)
    layer.add_alpha()
    layer.fill(Gimp.FillType.TRANSPARENT)
    image.select_rectangle(Gimp.ChannelOps.REPLACE,
                           cx - width // 2, y - thickness // 2,
                           width, thickness)
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(color)
        layer.edit_fill(Gimp.FillType.FOREGROUND)
    finally:
        Gimp.context_pop()
    Gimp.Selection.none(image)


def _draw_parents(image, layout, content, cfg, w, h, color):
    """Two-column block: bride's parents on the left, groom's on the right."""
    font = resolve_font(layout, cfg['name_font'])
    size = int(cfg['name_size_px'])
    spacing = int(cfg['line_spacing_px'])
    column_gap = int(cfg['column_gap_px'])
    center_y = int(h * float(cfg['y_pct']))

    left_lines = list(content.get('bride') or [])
    right_lines = list(content.get('groom') or [])

    left_layers = [
        make_text_layer(image, None, 'parents_bride_{}'.format(i),
                        line, font, size, color)
        for i, line in enumerate(left_lines)
    ]
    right_layers = [
        make_text_layer(image, None, 'parents_groom_{}'.format(i),
                        line, font, size, color)
        for i, line in enumerate(right_lines)
    ]

    left_w = max((l.get_width() for l in left_layers), default=0)
    right_w = max((l.get_width() for l in right_layers), default=0)
    total_w = left_w + column_gap + right_w
    left_cx = (w - total_w) // 2 + left_w // 2
    right_cx = left_cx + left_w // 2 + column_gap + right_w // 2

    def _stack(layers, col_cx):
        n = len(layers)
        if not n:
            return
        line_h = layers[0].get_height()
        block_h = n * line_h + (n - 1) * spacing
        top_y = center_y - block_h // 2
        for i, lay in enumerate(layers):
            lay.set_offsets(col_cx - lay.get_width() // 2,
                            top_y + i * (line_h + spacing))

    _stack(left_layers, left_cx)
    _stack(right_layers, right_cx)


def _draw_couple(image, layout, content, cfg, cx, h, color):
    text = '{} & {}'.format(content['bride'], content['groom'])
    font = resolve_font(layout, cfg['font'])
    layer = make_text_layer(image, None, 'couple', text, font,
                            int(cfg['size_px']), color)
    center_layer_at(layer, cx, int(h * float(cfg['y_pct'])))


def _draw_date(image, layout, content, cfg, cx, h, color):
    text = '{} | {} | {}'.format(content['day'], content['month_name'], content['year'])
    font = resolve_font(layout, cfg['font'])
    layer = make_text_layer(image, None, 'date', text, font,
                            int(cfg['size_px']), color)
    center_layer_at(layer, cx, int(h * float(cfg['y_pct'])))


def _draw_multi_line(image, layout, cfg, cx, h, color, lines, layer_prefix):
    """Stack of N lines, each with its own font/size from cfg.

    lines: [(text, kind)] where kind matches '{kind}_font' / '{kind}_size_px'.
    Block is vertically centered on cfg.y_pct.
    """
    spacing = int(cfg.get('line_spacing_px', 12))
    center_y = int(h * float(cfg['y_pct']))

    layers = []
    for text, kind in lines:
        if not text:
            continue
        font = resolve_font(layout, cfg['{}_font'.format(kind)])
        size = int(cfg['{}_size_px'.format(kind)])
        layer = make_text_layer(image, None, '{}_{}'.format(layer_prefix, kind),
                                text, font, size, color)
        layers.append(layer)

    if not layers:
        return
    total_h = sum(l.get_height() for l in layers) + (len(layers) - 1) * spacing
    top_y = center_y - total_h // 2
    y = top_y
    for layer in layers:
        layer.set_offsets(cx - layer.get_width() // 2, y)
        y += layer.get_height() + spacing


def _draw_rsvp(image, layout, content, cfg, cx, h, color):
    spacing = int(cfg.get('line_spacing_px', 8))
    center_y = int(h * float(cfg['y_pct']))

    intro_font = resolve_font(layout, cfg['intro_font'])
    detail_font = resolve_font(layout, cfg['detail_font'])

    intro = make_text_layer(image, None, 'rsvp_intro', content['intro'],
                            intro_font, int(cfg['intro_size_px']), color)
    detail = make_text_layer(image, None, 'rsvp_detail', content['detail'],
                             detail_font, int(cfg['detail_size_px']), color)

    total_h = intro.get_height() + spacing + detail.get_height()
    top_y = center_y - total_h // 2
    intro.set_offsets(cx - intro.get_width() // 2, top_y)
    detail.set_offsets(cx - detail.get_width() // 2,
                       top_y + intro.get_height() + spacing)

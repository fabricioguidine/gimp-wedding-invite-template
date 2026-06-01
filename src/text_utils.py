"""Helpers for creating text layers in GIMP 3.

Centralizes:
  - Font resolution with fallback (configured family -> fallback -> "Serif")
  - TextLayer creation + centered positioning within rectangles
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp


# Cache so the same font is not looked up 100 times
_font_cache = {}


def _all_font_names():
    """Cache of the full list of available font names."""
    if '_all' not in _font_cache:
        fonts = Gimp.fonts_get_list('') or []
        _font_cache['_all'] = [f.get_name() for f in fonts]
    return _font_cache['_all']


def _try_font(name):
    """Try to find a font by exact name, then with a ' Regular' suffix, then by
    a case-insensitive substring match on the family.
    """
    if name in _font_cache:
        return _font_cache[name]

    # 1) Exact name
    f = Gimp.Font.get_by_name(name)
    if f is not None:
        _font_cache[name] = f
        return f

    # 2) Append ' Regular' (the default style GIMP 3 expects)
    f = Gimp.Font.get_by_name(name + ' Regular')
    if f is not None:
        _font_cache[name] = f
        return f

    # 3) Substring search (e.g. "Georgia" matches "Georgia Regular")
    name_lower = name.lower()
    for full_name in _all_font_names():
        if name_lower in full_name.lower():
            f = Gimp.Font.get_by_name(full_name)
            if f is not None:
                _font_cache[name] = f
                return f

    return None


def resolve_font(layout, kind):
    """Return a Gimp.Font based on layout.fonts[kind].

    Tries the main family, then the fallback, then 'Serif'. Raises RuntimeError
    if nothing is found.
    """
    cfg = layout['fonts'][kind]
    candidates = [cfg.get('family'), cfg.get('fallback'), 'Serif']
    tried = []
    for name in candidates:
        if not name:
            continue
        tried.append(name)
        font = _try_font(name)
        if font is not None:
            return font
    raise RuntimeError(
        "No font resolved for kind '{}'. Tried: {}".format(kind, tried)
    )


def make_text_layer(image, parent_group, name, text, font, size_px, color):
    """Create a text layer and insert it inside parent_group.

    Returns the TextLayer (with no position set — call set_offsets or
    center_layer_at afterwards).
    """
    Gimp.context_push()
    try:
        Gimp.context_set_foreground(color)
        text_layer = Gimp.TextLayer.new(
            image,
            text,
            font,
            float(size_px),
            Gimp.Unit.pixel(),
        )
        # Position 0 = top of the group's stack
        image.insert_layer(text_layer, parent_group, 0)
        text_layer.set_name(name)
        return text_layer
    finally:
        Gimp.context_pop()


def center_layer_at(layer, cx, cy):
    """Center the layer at (cx, cy)."""
    w = layer.get_width()
    h = layer.get_height()
    layer.set_offsets(int(cx - w / 2), int(cy - h / 2))


def wrap_text(text, max_chars):
    """Word-wrap, preserving explicit '\n' line breaks from the YAML.

    max_chars: approximate target characters per line (never splits a word).
    """
    out_lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            out_lines.append('')
            continue
        words = paragraph.split()
        cur = words[0]
        for w in words[1:]:
            if len(cur) + 1 + len(w) <= max_chars:
                cur += ' ' + w
            else:
                out_lines.append(cur)
                cur = w
        out_lines.append(cur)
    return '\n'.join(out_lines)

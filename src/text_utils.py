"""Utilitários para criação de layers de texto no GIMP 3.

Centraliza:
  - Resolução de fontes com fallback (família configurada → fallback → "Sans")
  - Criação de TextLayer + posicionamento centralizado em retângulos
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp


# Cache pra não buscar a mesma fonte 100 vezes
_font_cache = {}


def _all_font_names():
    """Cache da lista completa de fontes disponíveis (nomes)."""
    global _all_fonts
    if '_all' not in _font_cache:
        fonts = Gimp.fonts_get_list('') or []
        _font_cache['_all'] = [f.get_name() for f in fonts]
    return _font_cache['_all']


def _try_font(name):
    """Tenta achar fonte por nome exato, com sufixo ' Regular',
    e por busca case-insensitive contendo a família.
    """
    if name in _font_cache:
        return _font_cache[name]

    # 1) Nome exato
    f = Gimp.Font.get_by_name(name)
    if f is not None:
        _font_cache[name] = f
        return f

    # 2) Adiciona ' Regular' (estilo padrão exigido pelo GIMP 3)
    f = Gimp.Font.get_by_name(name + ' Regular')
    if f is not None:
        _font_cache[name] = f
        return f

    # 3) Busca substring (ex: "Georgia" bate em "Georgia Regular")
    name_lower = name.lower()
    for full_name in _all_font_names():
        if name_lower in full_name.lower():
            f = Gimp.Font.get_by_name(full_name)
            if f is not None:
                _font_cache[name] = f
                return f

    return None


def resolve_font(layout, kind):
    """Retorna um Gimp.Font baseado em layout.fonts[kind].

    Tenta a família principal, depois fallback, depois 'Serif Regular'.
    Levanta RuntimeError se nada for encontrado.
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
        "Nenhuma fonte resolvida para tipo '{}'. Tentei: {}".format(kind, tried)
    )


def make_text_layer(image, parent_group, name, text, font, size_px, color):
    """Cria uma layer de texto e a insere dentro de parent_group.

    Retorna a TextLayer pronta (sem posição definida — chame
    set_offsets ou center_layer_at depois).
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
        # Posição 0 = topo da pilha do grupo
        image.insert_layer(text_layer, parent_group, 0)
        text_layer.set_name(name)
        return text_layer
    finally:
        Gimp.context_pop()


def center_layer_at(layer, cx, cy):
    """Centraliza a layer em (cx, cy)."""
    w = layer.get_width()
    h = layer.get_height()
    layer.set_offsets(int(cx - w / 2), int(cy - h / 2))


def wrap_text(text, max_chars):
    """Quebra de linha por palavra, preservando \\n explícitos do YAML.

    max_chars: alvo aproximado de caracteres por linha (não quebra palavra).
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

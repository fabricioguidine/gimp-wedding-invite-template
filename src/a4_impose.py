"""Geometria de imposição A4 (pura, sem GIMP — testável em qualquer lugar).

O tri-fold é desenhado em 30x15 cm (851x426 pt). Pra imprimir numa folha A4
real, precisa caber em A4 paisagem (29.7x21 cm) — como 30 > 29.7, a arte é
reduzida pra caber dentro das margens e centralizada. Aqui só calculamos a
escala/offsets/posição das dobras; o desenho fica em a4_render (GIMP).
"""

MM_PER_IN = 25.4


def mm_to_px(mm, dpi=300):
    return int(round(mm / MM_PER_IN * dpi))


def a4_landscape_px(dpi=300):
    """A4 paisagem (297x210 mm) em pixels no DPI dado."""
    return mm_to_px(297, dpi), mm_to_px(210, dpi)


def compute(src_w, src_h, margin_mm=5.0, dpi=300, page=None):
    """Escala-pra-caber + centraliza a arte na folha.

    Retorna dict com page_w/page_h, scale, new_w/new_h, off_x/off_y e fold_x
    (os dois x absolutos das dobras, nos terços da arte já escalada).
    """
    page_w, page_h = page if page is not None else a4_landscape_px(dpi)
    m = mm_to_px(margin_mm, dpi)
    avail_w = page_w - 2 * m
    avail_h = page_h - 2 * m
    scale = min(avail_w / float(src_w), avail_h / float(src_h))
    new_w = int(round(src_w * scale))
    new_h = int(round(src_h * scale))
    off_x = (page_w - new_w) // 2
    off_y = (page_h - new_h) // 2
    fold_x = [off_x + int(round(new_w * i / 3.0)) for i in (1, 2)]
    return {
        'page_w': page_w, 'page_h': page_h, 'margin_px': m, 'scale': scale,
        'new_w': new_w, 'new_h': new_h, 'off_x': off_x, 'off_y': off_y,
        'fold_x': fold_x,
    }

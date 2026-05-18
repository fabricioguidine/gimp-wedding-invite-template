"""Geometria dos três painéis do tri-fold.

A largura total é dividida igualmente em N painéis (default 3).
A ordem dos painéis no canvas aberto vem do layout.yaml em
fold.panel_order — para sanfona/Z-fold a capa fica no painel
da direita (índice 2 quando ordem é [madrinha, save_the_date, cover]).
"""


def compute_panel_rects(layout):
    """Retorna dict {nome_do_painel: (x, y, w, h)} em pixels.

    Distribui as larguras igualmente, ajustando arredondamentos para
    garantir que a soma das larguras seja exatamente canvas.width_px.
    """
    canvas_w = int(layout['canvas']['width_px'])
    canvas_h = int(layout['canvas']['height_px'])
    order = layout['fold']['panel_order']
    n = len(order)

    rects = {}
    panel_w = canvas_w / n
    for i, name in enumerate(order):
        x = int(round(i * panel_w))
        next_x = canvas_w if i == n - 1 else int(round((i + 1) * panel_w))
        rects[name] = (x, 0, next_x - x, canvas_h)
    return rects

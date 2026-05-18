"""Criação do documento base no GIMP 3.

Responsável por: canvas com dimensões/DPI corretos, layer de fundo creme,
guides verticais marcando as dobras do tri-fold.

API: GIMP 3.x via GObject Introspection (gi.repository.Gimp).
Não confundir com Python-Fu / gimpfu do GIMP 2.10 — assinatura das
funções e nomes de classes mudaram bastante.
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl


def hex_to_rgb01(hex_color):
    """Converte '#RRGGBB' em tupla (r, g, b) com componentes em [0, 1]."""
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def make_color(hex_color):
    """Constrói um Gegl.Color a partir de string '#RRGGBB'.

    No GIMP 3 a API de cor passa pelo Gegl.Color (não mais gimpcolor).
    """
    color = Gegl.Color.new('white')
    r, g, b = hex_to_rgb01(hex_color)
    color.set_rgba(r, g, b, 1.0)
    return color


def create_canvas(layout, invite=None):
    """Cria a imagem base com fundo creme e guides verticais nas dobras.

    Parâmetros:
        layout: dict carregado de layout.yaml (já convertido em JSON).
        invite: dict carregado de invite.yaml. Não usado nesta fase,
                mas mantido na assinatura pra próximas fases.

    Retorna: instância de Gimp.Image pronta pra ser salva.
    """
    canvas_cfg = layout['canvas']
    width = int(canvas_cfg['width_px'])
    height = int(canvas_cfg['height_px'])
    dpi = float(canvas_cfg['dpi'])
    bg_hex = canvas_cfg['background_color']

    # Cria imagem RGB sem alpha
    image = Gimp.Image.new(width, height, Gimp.ImageBaseType.RGB)
    image.set_resolution(dpi, dpi)

    # Pinta o fundo num layer dedicado (mais flexível que usar Gimp.Image fill)
    bg_layer = Gimp.Layer.new(
        image,
        'bg',
        width,
        height,
        Gimp.ImageType.RGB_IMAGE,
        100.0,                     # opacidade
        Gimp.LayerMode.NORMAL,
    )
    # parent=None, position=0 → topo da pilha (única layer por enquanto)
    image.insert_layer(bg_layer, None, 0)

    # Preenche o layer com a cor creme via context_set_foreground + fill
    Gimp.context_set_foreground(make_color(bg_hex))
    bg_layer.fill(Gimp.FillType.FOREGROUND)

    # Guides verticais nas dobras (sanfona / Z-fold)
    for pct in layout['fold']['guides_vertical_pct']:
        x = int(round(width * float(pct) / 100.0))
        image.add_vguide(x)

    return image

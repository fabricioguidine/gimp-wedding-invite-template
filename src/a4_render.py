"""Renderiza a arte (XCF/PNG) imposta numa folha A4 paisagem via GIMP 3.

Escala o tri-fold pra caber em A4, centraliza e desenha marcas de dobra finas
nas margens (nos dois terços). Mantém 300 DPI → imprime no tamanho calculado.
A geometria vem de a4_impose (puro); aqui é só o desenho no GIMP.
"""

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio

from a4_impose import compute, mm_to_px


def _color(r, g, b):
    c = Gegl.Color.new('white')
    c.set_rgba(r, g, b, 1.0)
    return c


def _draw_fold_marks(page, bg, geo, dpi):
    tick = mm_to_px(4, dpi)
    gap = mm_to_px(1.5, dpi)
    thickness = 2
    top_y = geo['off_y'] - gap - tick
    bot_y = geo['off_y'] + geo['new_h'] + gap
    Gimp.context_set_foreground(_color(0.6, 0.6, 0.6))
    for fx in geo['fold_x']:
        for y in (top_y, bot_y):
            page.select_rectangle(Gimp.ChannelOps.REPLACE,
                                  fx - thickness // 2, y, thickness, tick)
            bg.fill(Gimp.FillType.FOREGROUND)
    Gimp.Selection.none(page)


def render_to_a4(src_path, dst_path, margin_mm=5.0, fold_marks=True, dpi=300):
    src = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE,
                         Gio.File.new_for_path(src_path))
    src.flatten()
    draw = src.get_layers()[0]
    geo = compute(src.get_width(), src.get_height(), margin_mm, dpi)

    page = Gimp.Image.new(geo['page_w'], geo['page_h'], Gimp.ImageBaseType.RGB)
    page.set_resolution(dpi, dpi)
    bg = Gimp.Layer.new(page, 'bg', geo['page_w'], geo['page_h'],
                        Gimp.ImageType.RGB_IMAGE, 100.0, Gimp.LayerMode.NORMAL)
    page.insert_layer(bg, None, 0)
    Gimp.context_set_foreground(_color(1.0, 1.0, 1.0))
    bg.fill(Gimp.FillType.FOREGROUND)

    art = Gimp.Layer.new_from_drawable(draw, page)
    page.insert_layer(art, None, 0)
    art.scale(geo['new_w'], geo['new_h'], False)
    art.set_offsets(geo['off_x'], geo['off_y'])

    if fold_marks:
        _draw_fold_marks(page, bg, geo, dpi)

    page.flatten()
    Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, page,
                   Gio.File.new_for_path(dst_path), None)
    src.delete()
    page.delete()

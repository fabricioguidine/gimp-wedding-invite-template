"""Manuais separados para padrinhos e madrinhas.

Cada manual é tri-fold (mesma estrutura que o convite): 2 XCFs por manual
(externo + interno), 4 arquivos no total. Conteúdo ainda não decidido —
por enquanto cada manual mostra só o título de identificação na capa
externa e a paleta apropriada como acento visual.

Geração final (a partir de build.py):
  - manual_padrinhos_externo.xcf
  - manual_padrinhos_interno.xcf
  - manual_madrinhas_externo.xcf
  - manual_madrinhas_interno.xcf
"""

from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gio

from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text
import palette as palette_module


import calendar_panel as _calendar_module

import re as _re

_ICONS_DIR = Path(__file__).resolve().parent.parent / 'assets' / 'ornaments' / 'icons'
_LOGO_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'ornaments' / 'logo.png'


def _split_sentences(text):
    """Quebra texto em frases (após . ! ?) preservando a pontuação."""
    parts = _re.split(r'(?<=[.!?])\s+', text.strip())
    return '\n'.join(p for p in parts if p)


def _active_manual_text(invite, manual_key):
    """Retorna a string da sugestão atualmente selecionada no YAML, ou None."""
    cfg = (invite.get('manuals') or {}).get(manual_key) or {}
    idx = cfg.get('active_text')
    suggestions = cfg.get('text_suggestions') or []
    if idx is None or not suggestions:
        return None
    if 0 <= int(idx) < len(suggestions):
        return suggestions[int(idx)]
    return None


def _draw_cover_title(image, layout, invite, panel_rects, panel_groups, title_text,
                      size_px=140):
    """Título do manual no painel cover-pos. Tamanho menor que monograma
    para acomodar 'Manual do Padrinho e da Madrinha' (mais longo).
    """
    panel_name = 'cover'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['cover']
    # Títulos em bold itálico (mais peso visual que script regular)
    font = resolve_font(layout, 'script_bold')
    color = make_color(cfg.get('text_color') or layout['borders']['color'])

    # Cada palavra em uma linha separada
    multiline_title = '\n'.join(title_text.split())

    layer = make_text_layer(
        image, parent, 'manual_title',
        multiline_title, font, size_px, color,
    )
    layer.set_justification(Gimp.TextJustification.CENTER)
    # Ancora pelo TOPO (com respiro da borda) — assim 6 linhas (casal)
    # ou 3 (padrinho/madrinha) ficam dentro do painel sem encostar.
    inner_margin = int(layout['borders']['inner_margin_px'])
    title_top_y = py + inner_margin + 80   # 80px respiro do border superior
    layer.set_offsets(px + (pw - layer.get_width()) // 2, title_top_y)


_MONTHS_PT = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]
_WEEKDAYS_PT = [
    'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira',
    'Sexta-feira', 'Sábado', 'Domingo',
]


def _draw_calendar_with_info(image, layout, invite, panel_rects, panel_groups):
    """Calendário no painel central + data por extenso (acima) +
    horário/venue/endereço (abaixo).
    """
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    # 1) Calendário (renderizado pelo módulo dedicado)
    _calendar_module.draw_calendar(image, layout, invite, panel_rects, panel_groups)

    # 2) Texto ao redor
    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])
    cx = px + pw // 2

    std = invite.get('save_the_date') or {}
    day = int(std.get('highlighted_day', 10))
    month = int(std.get('month', 10))
    year = int(std.get('year', 2026))

    import datetime
    weekday_name = _WEEKDAYS_PT[datetime.date(year, month, day).weekday()]
    month_name = _MONTHS_PT[month - 1]

    # Acima do calendário
    wd_layer = make_text_layer(
        image, parent, 'cal_weekday', weekday_name,
        title_font, 70, color,
    )
    center_layer_at(wd_layer, cx, py + int(ph * 0.12))

    date_layer = make_text_layer(
        image, parent, 'cal_date',
        '{} | {} | {}'.format(day, month_name, year),
        body_font, 42, color,
    )
    center_layer_at(date_layer, cx, py + int(ph * 0.21))

    # Abaixo do calendário (mostra só chegada dos padrinhos, sem horário da cerimônia)
    ceremony = invite.get('ceremony') or {}
    bottom_y = 0.74

    if ceremony.get('bridal_party_arrival'):
        arrival_layer = make_text_layer(
            image, parent, 'cal_arrival',
            'Chegada dos padrinhos: {}'.format(ceremony['bridal_party_arrival']),
            body_font, 36, color,
        )
        center_layer_at(arrival_layer, cx, py + int(ph * bottom_y))
        bottom_y += 0.06

    if ceremony.get('venue'):
        venue_layer = make_text_layer(
            image, parent, 'cal_venue',
            wrap_text(ceremony['venue'], 24),
            body_font, 36, color,
        )
        venue_layer.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(venue_layer, cx, py + int(ph * bottom_y))
        bottom_y += 0.06

    if ceremony.get('address'):
        addr_layer = make_text_layer(
            image, parent, 'cal_addr',
            wrap_text(ceremony['address'], 26),
            body_font, 32, color,
        )
        addr_layer.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(addr_layer, cx, py + int(ph * bottom_y))


def _draw_back_cover_logo(image, panel_rects, panel_groups, panel_name='madrinha'):
    """Coloca a logo dos noivos centralizada num painel (geralmente
    madrinha-pos = back cover quando dobrado)."""
    if panel_name not in panel_rects:
        return
    if not _LOGO_PATH.exists():
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    try:
        gio_file = Gio.File.new_for_path(str(_LOGO_PATH))
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image, gio_file,
        )
    except Exception as e:
        print('[manuals] falha logo:', e)
        return

    image.insert_layer(layer, parent, 0)
    layer.set_name('back_cover_logo')

    pad = 50
    target_w = pw - 2 * pad
    target_h = ph - 2 * pad
    cur_w, cur_h = layer.get_width(), layer.get_height()
    if cur_w == 0 or cur_h == 0:
        return
    scale = min(target_w / float(cur_w), target_h / float(cur_h))
    new_w = max(1, int(cur_w * scale))
    new_h = max(1, int(cur_h * scale))
    layer.scale(new_w, new_h, False)
    layer.set_offsets(px + (pw - new_w) // 2, py + (ph - new_h) // 2)


def _draw_couple_subtitle(image, layout, invite, panel_rects, panel_groups):
    """Subtítulo "Luany & João Marcos" pequeno abaixo do título."""
    panel_name = 'cover'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    bride = invite['couple']['bride']
    groom = invite['couple']['groom']
    text = '{} & {}'.format(bride, groom)

    font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])

    layer = make_text_layer(
        image, parent, 'manual_couple',
        text, font, 100, color,
    )
    center_layer_at(layer, px + pw // 2, py + int(ph * 0.78))


# ============================================================ PADRINHOS
_PALETTE_MADRINHA = [   # 3 tons de marsala (do palette image original)
    '#8B0008', '#5C0808', '#2D0606',
]
_PALETTE_PADRINHO = [   # cinza do terno + branco da camisa + marsala da gravata
    '#878E99', '#FFFFFF', '#5C0808',
]
_PALETTE_CASAL = _PALETTE_MADRINHA + _PALETTE_PADRINHO

_PALETTE_NAMES_MADRINHA = ['Marsala claro', 'Marsala', 'Marsala escuro']
_PALETTE_NAMES_PADRINHO = ['Cinza', 'Branco', 'Marsala']
_PALETTE_NAMES_CASAL = _PALETTE_NAMES_MADRINHA + _PALETTE_NAMES_PADRINHO


def draw_padrinho_externo(image, layout, invite, panel_rects, panel_groups):
    _draw_cover_title(image, layout, invite, panel_rects, panel_groups,
                      'Manual do Padrinho')
    _draw_couple_subtitle(image, layout, invite, panel_rects, panel_groups)
    _draw_calendar_with_info(image, layout, invite, panel_rects, panel_groups)
    _draw_back_cover_logo(image, panel_rects, panel_groups, panel_name='madrinha')


def draw_padrinho_interno(image, layout, invite, panel_rects, panel_groups):
    """Esq: Sua Missão. Centro: título + paleta. Dir: Dicas."""
    _draw_sua_missao_panel(image, layout, invite, panel_rects, panel_groups,
                           panel_name='madrinha')
    _draw_role_center(image, layout, panel_rects, panel_groups,
                      role_title='Padrinho',
                      body_text=_active_manual_text(invite, 'padrinhos'),
                      colors=_PALETTE_PADRINHO,
                      color_names=_PALETTE_NAMES_PADRINHO,
                      palette_label='Padrinho',
                      layer_prefix='pad',
                      body_first=True)
    draw_dicas_block(image, layout, invite, panel_rects, panel_groups,
                     panel_name='cover')


def _draw_role_center(image, layout, panel_rects, panel_groups,
                      role_title, body_text, colors, color_names,
                      palette_label, layer_prefix, body_first=False):
    """Painel central padrão dos manuais interno.

    body_first=False (default): título → paleta → labels → body.
    body_first=True:             título → body → paleta → labels.
    """
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])
    cx = px + pw // 2

    # Título no topo
    title = make_text_layer(
        image, parent, layer_prefix + '_title',
        role_title, title_font, 140, color,
    )
    center_layer_at(title, cx, py + int(ph * 0.13))

    if body_first:
        # title 13% → body 40% → subtitle 68% → palette 78% (labels ~85%)
        body_y_factor = 0.40
        subtitle_y_factor = 0.66
        palette_y_factor = 0.78
    else:
        # subtitle 40% → palette 50% → labels 58% → body 78%
        subtitle_y_factor = 0.40
        palette_y_factor = 0.50
        body_y_factor = 0.78

    # Body (se houver) — quebra por frase em cada ponto final
    if body_text:
        sentence_split = _split_sentences(body_text)
        wrapped_body = '\n'.join(
            wrap_text(line, 24) for line in sentence_split.split('\n')
        )
        body = make_text_layer(
            image, parent, layer_prefix + '_body',
            wrapped_body, body_font, 42, color,
        )
        body.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(body, cx, py + int(ph * body_y_factor))

    # Subtítulo "Paleta de cores - {label}"
    subtitle = make_text_layer(
        image, parent, layer_prefix + '_pal_subtitle',
        'Paleta de cores — {}'.format(palette_label),
        body_font, 50, color,
    )
    center_layer_at(subtitle, cx, py + int(ph * subtitle_y_factor))

    # Paleta
    _draw_subset_palette(
        image, layout, panel_rects, panel_groups,
        colors=colors, panel_name=panel_name, y_factor=palette_y_factor,
        layer_name=layer_prefix + '_palette',
    )

    # Nomes das cores abaixo de cada bolinha (usa o mesmo cálculo da paleta)
    pal_cfg = layout['panels']['madrinha']['palette']
    radius = int(pal_cfg['circle_radius_px'])
    n = len(colors)
    circle_centers = palette_module.compute_circle_centers(
        layout, panel_rects, panel_name, n,
    )
    cy_palette = py + int(ph * palette_y_factor)
    label_y = cy_palette + radius + 50  # 50px abaixo do círculo

    for i, name in enumerate(color_names):
        circle_cx = circle_centers[i]
        label = make_text_layer(
            image, parent,
            '{}_color_label_{}'.format(layer_prefix, i),
            name, body_font, 40, color,
        )
        label.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(label, circle_cx, label_y)


# ============================================================ MADRINHAS
def draw_madrinha_externo(image, layout, invite, panel_rects, panel_groups):
    _draw_cover_title(image, layout, invite, panel_rects, panel_groups,
                      'Manual das Madrinhas')
    _draw_couple_subtitle(image, layout, invite, panel_rects, panel_groups)
    _draw_calendar_with_info(image, layout, invite, panel_rects, panel_groups)
    _draw_back_cover_logo(image, panel_rects, panel_groups, panel_name='madrinha')


def draw_madrinha_interno(image, layout, invite, panel_rects, panel_groups):
    """Esq: Sua Missão. Centro: título + corpo + paleta. Dir: Dicas."""
    _draw_sua_missao_panel(image, layout, invite, panel_rects, panel_groups,
                           panel_name='madrinha')
    _draw_role_center(image, layout, panel_rects, panel_groups,
                      role_title='Madrinha',
                      body_text=_active_manual_text(invite, 'madrinhas'),
                      colors=_PALETTE_MADRINHA,
                      color_names=_PALETTE_NAMES_MADRINHA,
                      palette_label='Madrinha',
                      layer_prefix='mad',
                      body_first=True)
    draw_dicas_block(image, layout, invite, panel_rects, panel_groups,
                     panel_name='cover')


# ============================================================ CASAL
# Manual para padrinhos que são casais — concatena os dois conteúdos.
def draw_casal_externo(image, layout, invite, panel_rects, panel_groups):
    _draw_cover_title(image, layout, invite, panel_rects, panel_groups,
                      'Manual dos Padrinhos')
    _draw_couple_subtitle(image, layout, invite, panel_rects, panel_groups)
    _draw_calendar_with_info(image, layout, invite, panel_rects, panel_groups)
    _draw_back_cover_logo(image, panel_rects, panel_groups, panel_name='madrinha')


def _draw_palette_with_label(image, layout, panel_rects, panel_groups,
                              colors, label, panel_name, y_factor, layer_name):
    """Paleta + label de texto centralizado acima."""
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    # Label acima da paleta
    label_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])
    label_layer = make_text_layer(
        image, parent, layer_name + '_label',
        label, label_font, 22, color,
    )
    # Label fica ~80px acima da paleta
    cy = py + int(ph * y_factor)
    center_layer_at(label_layer, px + pw // 2, cy - 60)

    # Paleta
    _draw_subset_palette(
        image, layout, panel_rects, panel_groups,
        colors=colors, panel_name=panel_name, y_factor=y_factor,
        layer_name=layer_name,
    )


def draw_casal_interno(image, layout, invite, panel_rects, panel_groups):
    """Esq: Sua Missão. Centro: Padrinho|Madrinha separadas com suas paletas. Dir: Dicas."""
    _draw_sua_missao_panel(image, layout, invite, panel_rects, panel_groups,
                           panel_name='madrinha')
    _draw_casal_split_center(image, layout, invite, panel_rects, panel_groups)
    draw_dicas_block(image, layout, invite, panel_rects, panel_groups,
                     panel_name='cover')


def _draw_casal_split_center(image, layout, invite, panel_rects, panel_groups):
    """Painel central do casal_interno: título 'Casal' + 2 seções
    (Padrinho com paleta+texto, Madrinha com paleta+texto).
    """
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    title_font_bold = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])
    cx = px + pw // 2

    pad_text = _active_manual_text(invite, 'padrinhos') or ''
    mad_text = _active_manual_text(invite, 'madrinhas') or ''

    # Título "Casal" no topo, ancorado pelo topo do painel
    title = make_text_layer(
        image, parent, 'cas_title', 'Casal',
        title_font_bold, 90, color,
    )
    inner_margin_px = int(layout['borders']['inner_margin_px'])
    title.set_offsets(
        cx - title.get_width() // 2,
        py + inner_margin_px + 30,
    )

    # ── Seção Padrinho: título → texto → paleta ──
    pad_section = make_text_layer(
        image, parent, 'cas_section_padrinho',
        'Padrinho', title_font_bold, 60, color,
    )
    center_layer_at(pad_section, cx, py + int(ph * 0.19))

    if pad_text:
        pad_body = make_text_layer(
            image, parent, 'cas_pad_body',
            wrap_text(pad_text, 58), body_font, 34, color,
        )
        pad_body.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(pad_body, cx, py + int(ph * 0.31))

    _draw_subset_palette(
        image, layout, panel_rects, panel_groups,
        colors=_PALETTE_PADRINHO, panel_name=panel_name, y_factor=0.43,
        layer_name='cas_pad_palette',
    )
    _draw_palette_color_labels(
        image, parent, layout, panel_rects, panel_name,
        colors=_PALETTE_PADRINHO, names=_PALETTE_NAMES_PADRINHO,
        y_factor=0.43, layer_prefix='cas_pad',
        body_font=body_font, color=color,
    )

    # ── Seção Madrinha: título → texto → paleta ──
    mad_section = make_text_layer(
        image, parent, 'cas_section_madrinha',
        'Madrinha', title_font_bold, 60, color,
    )
    center_layer_at(mad_section, cx, py + int(ph * 0.56))

    if mad_text:
        mad_body = make_text_layer(
            image, parent, 'cas_mad_body',
            wrap_text(mad_text, 58), body_font, 34, color,
        )
        mad_body.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(mad_body, cx, py + int(ph * 0.69))

    _draw_subset_palette(
        image, layout, panel_rects, panel_groups,
        colors=_PALETTE_MADRINHA, panel_name=panel_name, y_factor=0.83,
        layer_name='cas_mad_palette',
    )
    _draw_palette_color_labels(
        image, parent, layout, panel_rects, panel_name,
        colors=_PALETTE_MADRINHA, names=_PALETTE_NAMES_MADRINHA,
        y_factor=0.83, layer_prefix='cas_mad',
        body_font=body_font, color=color,
    )


def _draw_palette_color_labels(image, parent, layout, panel_rects, panel_name,
                                colors, names, y_factor, layer_prefix,
                                body_font, color):
    """Renderiza nomes de cor centralizados embaixo de cada bolinha."""
    px, py, pw, ph = panel_rects[panel_name]
    pal_cfg = layout['panels']['madrinha']['palette']
    radius = int(pal_cfg['circle_radius_px'])
    n = len(colors)
    circle_centers = palette_module.compute_circle_centers(
        layout, panel_rects, panel_name, n,
    )
    cy_palette = py + int(ph * y_factor)
    label_y = cy_palette + radius + 45

    for i, name in enumerate(names):
        circle_cx = circle_centers[i]
        label = make_text_layer(
            image, parent,
            '{}_color_label_{}'.format(layer_prefix, i),
            name, body_font, 32, color,
        )
        label.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(label, circle_cx, label_y)


# -------------------------------------------------------------------- util
def _draw_subset_palette(image, layout, panel_rects, panel_groups,
                         colors, panel_name, y_factor, layer_name):
    """Versão lean de palette.draw_palette aceitando lista direta de cores."""
    fake_invite = {'madrinha': {'palette': colors}}
    palette_module.draw_palette(
        image, layout, fake_invite, panel_rects, panel_groups,
        panel_name=panel_name, y_factor=y_factor, layer_name=layer_name,
    )


def _load_svg_icon(image, parent_group, icon_name, target_px):
    """Carrega um SVG de assets/ornaments/icons/<icon_name>.svg como layer.

    Retorna a layer carregada (ainda sem posição), ou None se o arquivo
    não existir ou der erro no carregamento.
    """
    svg_path = _ICONS_DIR / '{}.svg'.format(icon_name)
    if not svg_path.exists():
        print('[manuals] icon não encontrado:', svg_path)
        return None
    try:
        gio_file = Gio.File.new_for_path(str(svg_path))
        # GIMP 3 file_load_layer abre o arquivo como uma única layer.
        # SVGs são rasterizados no carregamento.
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image, gio_file,
        )
    except Exception as e:
        print('[manuals] falha carregando SVG {}: {}'.format(icon_name, e))
        return None

    image.insert_layer(layer, parent_group, 0)
    layer.set_name('icon_{}'.format(icon_name))

    # Escala mantendo aspect ratio (assume SVG quadrado)
    cur_w = layer.get_width()
    if cur_w and cur_w != target_px:
        scale = target_px / float(cur_w)
        new_h = int(layer.get_height() * scale)
        layer.scale(target_px, new_h, False)
    return layer


def _draw_sua_missao_panel(image, layout, invite, panel_rects, panel_groups,
                           panel_name):
    """Renderiza o bloco completo 'Sua Missão' — título + corpo + ♥ + verso.

    Layout vertical (% da altura do painel):
       8%   título "Sua Missão" (script grande)
      24%   corpo (serif, ~30 chars/linha)
      66%   coração centralizado
      75%   verso (script)
      90%   referência (serif pequena)
    """
    cfg = (invite.get('manuals') or {}).get('sua_missao') or {}
    if not cfg.get('title') or panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    title_font_bold = resolve_font(layout, 'script_bold')
    title_font = resolve_font(layout, 'script')  # pro verso (regular itálico)
    body_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2

    # Título
    title = make_text_layer(
        image, parent, 'sm_title', cfg['title'],
        title_font_bold, 100, color,
    )
    center_layer_at(title, cx, py + int(ph * 0.10))

    inner_margin = int(layout['borders']['inner_margin_px'])

    # Layout top-down com gaps fixos garantidos (sem centralizar no meio)
    body_top = py + int(ph * 0.20)
    body_bottom = body_top

    body_text = cfg.get('body', '').strip()
    if body_text:
        body = make_text_layer(
            image, parent, 'sm_body',
            wrap_text(body_text, 24),
            body_font, 38, color,
        )
        body.set_justification(Gimp.TextJustification.CENTER)
        body.set_offsets(cx - body.get_width() // 2, body_top)
        body_bottom = body_top + body.get_height()

    # Verso com 130px de gap depois do body
    verse_cfg = cfg.get('verse') or {}
    verse_bottom = body_bottom + 130
    if verse_cfg.get('text'):
        verse_top = body_bottom + 130
        verse_layer = make_text_layer(
            image, parent, 'sm_verse',
            wrap_text(verse_cfg['text'], 26),
            title_font, 40, color,
        )
        verse_layer.set_justification(Gimp.TextJustification.CENTER)
        verse_layer.set_offsets(cx - verse_layer.get_width() // 2, verse_top)
        verse_bottom = verse_top + verse_layer.get_height()

    # Ref com 50px de gap depois do verso
    if verse_cfg.get('reference'):
        ref_top = verse_bottom + 50
        ref_layer = make_text_layer(
            image, parent, 'sm_ref',
            verse_cfg['reference'], body_font, 28, color,
        )
        ref_layer.set_offsets(cx - ref_layer.get_width() // 2, ref_top)


def _draw_extra_verse(image, layout, invite, panel_rects, panel_groups,
                      panel_name):
    """Renderiza invite.manuals.bible_verse_extra centralizado num painel."""
    verse = (invite.get('manuals') or {}).get('bible_verse_extra') or {}
    if not verse.get('text') or panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    text_font = resolve_font(layout, 'script')
    ref_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2
    cy = py + ph // 2

    text_layer = make_text_layer(
        image, parent, 'extra_verse_text',
        wrap_text(verse['text'], 28),
        text_font, 36, color,
    )
    th = text_layer.get_height()
    text_layer.set_offsets(cx - text_layer.get_width() // 2, cy - th)

    if verse.get('reference'):
        ref_layer = make_text_layer(
            image, parent, 'extra_verse_ref',
            verse['reference'], ref_font, 24, color,
        )
        center_layer_at(ref_layer, cx, cy + 30)


def draw_dicas_block(image, layout, invite, panel_rects, panel_groups,
                     panel_name='save_the_date'):
    """Renderiza o bloco 'Dicas para o grande dia' no painel indicado.

    Layout: título no topo, depois 3 linhas de [ícone | texto].
    """
    dicas = (invite.get('manuals') or {}).get('dicas')
    if not dicas:
        return
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    title_font = resolve_font(layout, 'script_bold')
    body_font = resolve_font(layout, 'serif')
    color = make_color(layout['borders']['color'])

    # Título no topo
    title_text = dicas.get('title', 'Dicas para o grande dia:')
    title = make_text_layer(
        image, parent, 'dicas_title', title_text,
        title_font, 100, color,
    )
    center_layer_at(title, px + pw // 2, py + int(ph * 0.10))

    items = dicas.get('items') or []
    if not items:
        return

    # Layout: ícone centralizado horizontalmente, texto centralizado abaixo.
    inner_margin = int(layout['borders']['inner_margin_px'])
    icon_size = 130
    # 80px de respiro entre texto e borda do painel (~7mm impressos)
    text_padding = 80
    text_w = pw - 2 * (inner_margin + text_padding)
    chars_per_line = max(18, int(text_w / 19))

    cx = px + pw // 2
    block_top = py + int(ph * 0.20)
    # Respeita inner_margin: fim do bloco fica DENTRO da borda do painel.
    block_bottom = py + ph - inner_margin - 40
    icon_text_gap = 20

    # Pass 1: cria cada unidade (ícone + texto) e mede sua altura.
    units = []
    for i, item in enumerate(items):
        icon_layer = _load_svg_icon(image, parent, item.get('icon', ''), icon_size)

        sentence_split = _split_sentences(item.get('text', ''))
        wrapped = '\n'.join(
            wrap_text(line, chars_per_line) for line in sentence_split.split('\n')
        )
        text_layer = make_text_layer(
            image, parent, 'dicas_text_{}'.format(i),
            wrapped, body_font, 42, color,
        )
        text_layer.set_justification(Gimp.TextJustification.CENTER)

        unit_h = icon_size + icon_text_gap + text_layer.get_height()
        units.append({'icon': icon_layer, 'text': text_layer, 'h': unit_h})

    # Pass 2: gap igual entre unidades (texto conta como parte da unidade)
    total_h = sum(u['h'] for u in units)
    n = len(units)
    available = block_bottom - block_top
    gap_between = (available - total_h) / (n - 1) if n > 1 else 0

    y = block_top
    for u in units:
        if u['icon'] is not None:
            u['icon'].set_offsets(cx - icon_size // 2, int(y))
        tw = u['text'].get_width()
        u['text'].set_offsets(cx - tw // 2, int(y + icon_size + icon_text_gap))
        y += u['h'] + gap_between

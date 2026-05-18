"""Distribuição de conteúdo entre os dois lados do tri-fold.

convite_externo.xcf — face visível quando o convite está dobrado:
  panel madrinha-pos (esq): verso bíblico (= back cover quando dobrado)
  panel save_the_date-pos (meio): vazio (escondido na dobra)
  panel cover-pos (dir): monograma do casal (= front cover quando dobrado)

convite_interno.xcf — face vista quando o convite está aberto:
  panel madrinha-pos (esq): pais (com a bênção...)
  panel save_the_date-pos (meio): convidam... + Save the Date + cerimônia
  panel cover-pos (dir): recepção + RSVP
"""

from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp, Gio

from document import make_color
from text_utils import resolve_font, make_text_layer, center_layer_at, wrap_text
import palette as palette_module
import manuals as manuals_module


_LOGO_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'ornaments' / 'logo.png'


# ============================================================ EXTERNO
def draw_externo(image, layout, invite, panel_rects, panel_groups):
    """Layout do convite_externo (face visível quando dobrado):
       Esq (madrinha-pos):       Dicas para o grande dia (ícones + textos)
       Meio (save_the_date-pos): Frase bíblica (centralizada)
       Dir (cover-pos):          Logo dos noivos
    """
    # Dicas no painel esquerdo
    manuals_module.draw_dicas_block(
        image, layout, invite, panel_rects, panel_groups,
        panel_name='madrinha',
    )
    # Frase bíblica do invite.verse no painel central
    _draw_verse_panel_at(image, layout, invite, panel_rects, panel_groups,
                         panel_name='save_the_date')
    # Logo no painel direito (= front cover quando o convite está dobrado)
    _draw_cover_logo(image, panel_rects, panel_groups, panel_name='cover')


def _draw_cover_monogram(image, layout, invite, panel_rects, panel_groups):
    """Painel cover-pos: 'Luany & João Marcos' grande, centralizado."""
    panel_name = 'cover'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['cover']
    font = resolve_font(layout, cfg.get('monogram_font', 'script'))
    base_size = int(cfg['monogram_size_px'])
    color = make_color(cfg.get('text_color') or layout['borders']['color'])

    bride = invite['couple']['bride']
    groom = invite['couple']['groom']

    cx = px + pw // 2

    line_specs = [
        ('cover_bride', bride, base_size),
        ('cover_amp',   '&',   int(base_size * 0.55)),
        ('cover_groom', groom, base_size),
    ]
    layers = []
    total_h = 0
    for name, text, size in line_specs:
        layer = make_text_layer(image, parent, name, text, font, size, color)
        layers.append((layer, size))
        total_h += layer.get_height()

    gap = int(base_size * 0.05)
    block_h = total_h + gap * (len(layers) - 1)
    cy_top = py + (ph - block_h) // 2

    y_cursor = cy_top
    for layer, _size in layers:
        h = layer.get_height()
        center_layer_at(layer, cx, y_cursor + h // 2)
        y_cursor += h + gap


def _draw_verse_panel_at(image, layout, invite, panel_rects, panel_groups,
                         panel_name='madrinha'):
    """Verso bíblico (invite.verse) centralizado num painel arbitrário."""
    if panel_name not in panel_rects:
        return
    verse = invite.get('verse') or {}
    if not verse.get('text'):
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['verse']
    text_font = resolve_font(layout, cfg.get('text_font', 'script'))
    text_size = int(cfg['text_size_px'])
    ref_font = resolve_font(layout, cfg.get('ref_font', 'bold'))
    ref_size = int(cfg['ref_size_px'])
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2
    cy = py + ph // 2

    text_layer = make_text_layer(
        image, parent, 'verse_text',
        wrap_text(verse['text'], 28),
        text_font, text_size, color,
    )
    center_layer_at(text_layer, cx, cy - text_layer.get_height() // 2)

    if verse.get('reference'):
        ref_layer = make_text_layer(
            image, parent, 'verse_ref',
            verse['reference'], ref_font, ref_size, color,
        )
        center_layer_at(ref_layer, cx, cy + text_layer.get_height() // 2 + 20)


def _draw_cover_logo(image, panel_rects, panel_groups, panel_name='cover'):
    """Carrega assets/ornaments/logo.png e centraliza no painel."""
    if panel_name not in panel_rects:
        return
    if not _LOGO_PATH.exists():
        print('[sides] AVISO: logo não encontrada em', _LOGO_PATH)
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    try:
        gio_file = Gio.File.new_for_path(str(_LOGO_PATH))
        layer = Gimp.file_load_layer(
            Gimp.RunMode.NONINTERACTIVE, image, gio_file,
        )
    except Exception as e:
        print('[sides] falha ao carregar logo:', e)
        return

    image.insert_layer(layer, parent, 0)
    layer.set_name('cover_logo')

    # Escala mantendo aspect ratio, com margem interna
    pad = 80
    target_w = pw - 2 * pad
    target_h = ph - 2 * pad
    cur_w = layer.get_width()
    cur_h = layer.get_height()
    if cur_w == 0 or cur_h == 0:
        return
    scale = min(target_w / float(cur_w), target_h / float(cur_h))
    new_w = max(1, int(cur_w * scale))
    new_h = max(1, int(cur_h * scale))
    layer.scale(new_w, new_h, False)

    # Centraliza
    layer.set_offsets(px + (pw - new_w) // 2, py + (ph - new_h) // 2)


# ============================================================ INTERNO
def draw_interno(image, layout, invite, panel_rects, panel_groups):
    _draw_parents_panel(image, layout, invite, panel_rects, panel_groups)
    _draw_ceremony_panel(image, layout, invite, panel_rects, panel_groups)
    _draw_reception_rsvp_panel(image, layout, invite, panel_rects, panel_groups)


def _draw_parents_panel(image, layout, invite, panel_rects, panel_groups):
    """Painel madrinha-pos no interno: bênção + pais em 2 colunas."""
    panel_name = 'madrinha'
    if panel_name not in panel_rects:
        return
    parents = invite.get('parents') or {}
    if not parents:
        return
    parent_group = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['parents']
    blessing_font = resolve_font(layout, cfg.get('blessing_font', 'bold'))
    blessing_size = int(cfg['blessing_size_px'])
    name_font = resolve_font(layout, cfg.get('name_font', 'bold'))
    name_size = int(cfg['name_size_px'])
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2

    # Bênção no topo
    blessing = parents.get('blessing_text', '')
    if blessing:
        wrapped = wrap_text(blessing, 30)
        bl_layer = make_text_layer(
            image, parent_group, 'parents_blessing',
            wrapped, blessing_font, blessing_size, color,
        )
        center_layer_at(bl_layer, cx, py + int(ph * 0.30))

    # Duas colunas com 2 nomes cada
    bride_names = parents.get('bride') or []
    groom_names = parents.get('groom') or []
    col_gap = int(cfg.get('column_gap_px', 30))
    col_w = (pw - col_gap) // 2 - 60  # margem extra das laterais

    left_text = '\n'.join(bride_names)
    right_text = '\n'.join(groom_names)
    cy_columns = py + int(ph * 0.55)

    if left_text:
        left = make_text_layer(
            image, parent_group, 'parents_bride',
            left_text, name_font, name_size, color,
        )
        center_layer_at(left, px + 30 + col_w // 2, cy_columns)

    if right_text:
        right = make_text_layer(
            image, parent_group, 'parents_groom',
            right_text, name_font, name_size, color,
        )
        center_layer_at(right, px + pw - 30 - col_w // 2, cy_columns)


def _draw_ceremony_panel(image, layout, invite, panel_rects, panel_groups):
    """Painel save_the_date-pos: 'Convidam...' + calendário + cerimônia.

    O calendário em si vem do calendar_panel.draw_calendar (chamado antes).
    Aqui adicionamos os textos ao redor.
    """
    panel_name = 'save_the_date'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['save_the_date']
    title_text = cfg.get('title_text', 'Save the Date')
    title_font = resolve_font(layout, cfg.get('title_font', 'script'))
    title_size = int(cfg['title_size_px'])
    inv_font = resolve_font(layout, cfg.get('invitation_font', 'bold'))
    inv_size = int(cfg['invitation_size_px'])
    body_font = resolve_font(layout, cfg.get('body_font', 'serif'))
    body_size = int(cfg['body_size_px'])
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2

    # Título no topo
    title = make_text_layer(
        image, parent, 'std_title', title_text, title_font, title_size, color,
    )
    center_layer_at(title, cx, py + int(ph * 0.10))

    # Subtítulo "CONVIDAM..."
    inv_text = (invite.get('ceremony') or {}).get('invitation_text', '').strip()
    if inv_text:
        inv_wrapped = wrap_text(inv_text, 28)
        inv_layer = make_text_layer(
            image, parent, 'std_invitation',
            inv_wrapped, inv_font, inv_size, color,
        )
        center_layer_at(inv_layer, cx, py + int(ph * 0.20))

    # Bloco de info abaixo do calendário
    ceremony = invite.get('ceremony', {})
    info_lines = []
    if ceremony.get('time'):
        info_lines.append('Às {} horas'.format(ceremony['time']))
    if ceremony.get('venue'):
        info_lines.append(ceremony['venue'])
    if ceremony.get('address'):
        info_lines.append(ceremony['address'])
    if ceremony.get('bridal_party_arrival'):
        info_lines.append('Padrinhos: {}'.format(ceremony['bridal_party_arrival']))

    if info_lines:
        info_layer = make_text_layer(
            image, parent, 'std_info',
            '\n'.join(info_lines), body_font, body_size, color,
        )
        # Centraliza linhas individualmente (cada uma centrada na layer)
        info_layer.set_justification(Gimp.TextJustification.CENTER)
        center_layer_at(info_layer, cx, py + int(ph * 0.92))


def _draw_reception_rsvp_panel(image, layout, invite, panel_rects, panel_groups):
    """Painel cover-pos no interno: recepção + RSVP."""
    panel_name = 'cover'
    if panel_name not in panel_rects:
        return
    parent = panel_groups[panel_name]
    px, py, pw, ph = panel_rects[panel_name]

    cfg = layout['panels']['reception_rsvp']
    title_font = resolve_font(layout, cfg.get('title_font', 'bold'))
    title_size = int(cfg['title_size_px'])
    body_font = resolve_font(layout, cfg.get('body_font', 'serif'))
    body_size = int(cfg['body_size_px'])
    rsvp_size = int(cfg['rsvp_size_px'])
    color = make_color(layout['borders']['color'])

    cx = px + pw // 2

    # Recepção no topo
    reception = invite.get('reception') or {}
    if reception.get('venue'):
        title = make_text_layer(
            image, parent, 'recep_title',
            'RECEPÇÃO', title_font, title_size, color,
        )
        center_layer_at(title, cx, py + int(ph * 0.20))

        venue = make_text_layer(
            image, parent, 'recep_venue',
            reception['venue'], body_font, body_size, color,
        )
        center_layer_at(venue, cx, py + int(ph * 0.30))

        if reception.get('address'):
            addr = make_text_layer(
                image, parent, 'recep_addr',
                reception['address'], body_font, body_size, color,
            )
            center_layer_at(addr, cx, py + int(ph * 0.36))

    # RSVP no rodapé
    rsvp = invite.get('rsvp') or {}
    if rsvp.get('intro') or rsvp.get('url') or rsvp.get('phone'):
        intro_y = py + int(ph * 0.78)

        if rsvp.get('intro'):
            wrapped = wrap_text(rsvp['intro'], 36)
            intro = make_text_layer(
                image, parent, 'rsvp_intro',
                wrapped, title_font, rsvp_size, color,
            )
            center_layer_at(intro, cx, intro_y)
            intro_y += intro.get_height() + 10

        if rsvp.get('url'):
            url_layer = make_text_layer(
                image, parent, 'rsvp_url',
                rsvp['url'], body_font, rsvp_size, color,
            )
            center_layer_at(url_layer, cx, intro_y)
            intro_y += url_layer.get_height() + 6

        if rsvp.get('phone'):
            phone = make_text_layer(
                image, parent, 'rsvp_phone',
                rsvp['phone'], body_font, rsvp_size, color,
            )
            center_layer_at(phone, cx, intro_y)

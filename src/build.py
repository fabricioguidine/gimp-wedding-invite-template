"""Entrypoint do build do convite.

Carrega o config combinado (JSON gerado pelo run.ps1 a partir dos YAMLs),
orquestra a criação do documento e salva como .xcf no diretório de saída.

Executado dentro do GIMP 3 via:
    gimp-console-3.2.exe --batch-interpreter=python-fu-eval -b "import build; build.main()"

Variáveis de ambiente esperadas (definidas pelo run.ps1):
    WEDDING_INVITE_CONFIG  → caminho absoluto do JSON de config
    WEDDING_INVITE_OUTPUT  → diretório onde salvar o .xcf
"""

import json
import os
import sys
from pathlib import Path

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, Gio

# Garante que o diretório deste arquivo está no sys.path pra importar `document`
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import document         # noqa: E402
import panels           # noqa: E402
import borders          # noqa: E402
import calendar_panel   # noqa: E402
import sides            # noqa: E402
import manuals          # noqa: E402


def _load_config():
    config_path = os.environ.get('WEDDING_INVITE_CONFIG')
    if not config_path:
        raise RuntimeError(
            "Variável de ambiente WEDDING_INVITE_CONFIG não definida. "
            "Use run.ps1 para invocar o build."
        )
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _output_dir():
    out = os.environ.get('WEDDING_INVITE_OUTPUT')
    if not out:
        raise RuntimeError("Variável WEDDING_INVITE_OUTPUT não definida.")
    p = Path(out)
    p.mkdir(parents=True, exist_ok=True)
    return p


# Lista declarativa dos documentos gerados. (filename, draw_callable)
# draw_callable assina: (image, layout, invite, panel_rects, panel_groups)
# Especiais como 'convite_interno' precisam do calendário antes do draw.
def _draw_convite_interno(image, layout, invite, panel_rects, panel_groups):
    calendar_panel.draw_calendar(image, layout, invite, panel_rects, panel_groups)
    sides.draw_interno(image, layout, invite, panel_rects, panel_groups)


# Apenas os 3 manuais — convite removido (Opção A do usuário).
# Conteúdo do convite (logo, verso, dicas, etc.) está distribuído nos manuais.
_DOCUMENTS = [
    ('padrinho_externo', manuals.draw_padrinho_externo),
    ('padrinho_interno', manuals.draw_padrinho_interno),
    ('madrinha_externo', manuals.draw_madrinha_externo),
    ('madrinha_interno', manuals.draw_madrinha_interno),
    ('casal_externo',    manuals.draw_casal_externo),
    ('casal_interno',    manuals.draw_casal_interno),
]


def _build_document(name, draw_fn, layout, invite, output_dir):
    """Cria canvas+bordas+grupos vazios, chama o drawer e salva."""
    image = document.create_canvas(layout, invite)
    panel_rects = panels.compute_panel_rects(layout)
    borders.draw_borders(image, layout, panel_rects)

    panel_groups = {}
    for panel_name in panel_rects:
        group = Gimp.GroupLayer.new(image)
        group.set_name('panel_{}'.format(panel_name))
        image.insert_layer(group, None, 0)
        panel_groups[panel_name] = group

    draw_fn(image, layout, invite, panel_rects, panel_groups)

    output_path = output_dir / '{}.xcf'.format(name)
    Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE,
        image,
        Gio.File.new_for_path(str(output_path)),
        None,
    )
    print('[wedding-invite-gimp] Salvo: {}'.format(output_path))
    image.delete()


def main():
    Gegl.init(None)
    config = _load_config()
    layout = config['layout']
    invite = config['invite']

    output_dir = _output_dir()
    for name, draw_fn in _DOCUMENTS:
        _build_document(name, draw_fn, layout, invite, output_dir)

    Gimp.displays_flush()


main()

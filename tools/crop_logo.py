"""Pós-processa o screenshot do Canva pra extrair só a região da logo.

Recorta a área do design (que está centralizada no editor) e remove o
fundo (transparência onde for branco-quase-puro).
"""

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'assets' / 'ornaments' / '_debug_fullpage.png'
DST = ROOT / 'assets' / 'ornaments' / 'logo.png'

# Caixa de recorte do design dentro do editor Canva (1920x1080).
# Ajustado pra pegar o logo com folga, pulando sidebar/header.
CROP = (580, 165, 1410, 960)


def main():
    if not SRC.exists():
        print('ERRO: screenshot não encontrado em', SRC)
        sys.exit(2)

    im = Image.open(SRC).convert('RGBA')
    print('Original:', im.size)
    cropped = im.crop(CROP)
    print('Cropped:', cropped.size)

    # Detecta cor de fundo a partir dos 4 cantos (Canva usa um cream
    # ~#F5EDE0, threshold de 240 não pega). Usa a cor mais frequente
    # dos cantos com tolerância pra eliminar.
    pixels = cropped.load()
    w, h = cropped.size
    corner_samples = [pixels[1, 1], pixels[w - 2, 1], pixels[1, h - 2], pixels[w - 2, h - 2]]
    bg_r = sum(p[0] for p in corner_samples) // 4
    bg_g = sum(p[1] for p in corner_samples) // 4
    bg_b = sum(p[2] for p in corner_samples) // 4
    print('Fundo detectado: R={}, G={}, B={}'.format(bg_r, bg_g, bg_b))

    # Tolerância: pixels dentro de ±25 dos canais do fundo viram transparentes
    tol = 25
    for y in range(h):
        for x in range(w):
            r, g, b, _a = pixels[x, y]
            if (abs(r - bg_r) <= tol
                    and abs(g - bg_g) <= tol
                    and abs(b - bg_b) <= tol):
                pixels[x, y] = (r, g, b, 0)
    cropped.save(DST)
    print('Salvo:', DST)


if __name__ == '__main__':
    main()

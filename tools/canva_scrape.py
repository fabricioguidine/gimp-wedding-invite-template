"""Scraper Playwright para baixar a logo do Canva.

Estratégia: navega no design URL com cookies de auth, espera renderizar
e captura via UI download (PNG transparente). Se a UI mudar, cai pra
screenshot da viewport como fallback.

Cookies sensíveis ficam fora do projeto: ~/claude-temp/canva-cookies.json
(não commitado).

Uso:
    python tools/canva_scrape.py
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CANVA_URL = (
    "https://www.canva.com/design/DAG74QciZ7A/"
    "KARgIyJvDpBHo1e4VKed0w/edit"
)
COOKIES_PATH = Path.home() / 'claude-temp' / 'canva-cookies.json'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / 'assets' / 'ornaments' / 'logo.png'


def _convert_cookies(raw):
    """Converte cookies do formato extension Chrome pro formato do Playwright.

    Diferenças:
      - sameSite: 'unspecified'/'lax'/'no_restriction' → 'Lax'/'Lax'/'None'
      - sameSite=None exige secure=True (Playwright valida)
      - expirationDate (float) → expires (int)
    """
    same_site_map = {
        'unspecified': 'Lax',
        'lax': 'Lax',
        'strict': 'Strict',
        'no_restriction': 'None',
        'none': 'None',
    }
    out = []
    for c in raw:
        same_site = same_site_map.get(str(c.get('sameSite', 'lax')).lower(), 'Lax')
        secure = bool(c.get('secure', False))
        # Playwright exige secure=True quando sameSite='None'
        if same_site == 'None':
            secure = True
        cookie = {
            'name': c['name'],
            'value': c['value'],
            'domain': c['domain'],
            'path': c.get('path', '/'),
            'secure': secure,
            'httpOnly': bool(c.get('httpOnly', False)),
            'sameSite': same_site,
        }
        if 'expirationDate' in c and c.get('session') is not True:
            cookie['expires'] = int(c['expirationDate'])
        out.append(cookie)
    return out


def main():
    if not COOKIES_PATH.exists():
        print('ERRO: cookies não encontrados em', COOKIES_PATH)
        sys.exit(2)

    raw_cookies = json.loads(COOKIES_PATH.read_text(encoding='utf-8'))
    cookies = _convert_cookies(raw_cookies)
    print('[1/5] Cookies carregados: {} entradas'.format(len(cookies)))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # headless=False ajuda a evitar detecção de bot do Canva
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='pt-BR',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/131.0.0.0 Safari/537.36'
            ),
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print('[2/5] Abrindo design no Canva...')
        try:
            page.goto(CANVA_URL, wait_until='domcontentloaded', timeout=60000)
        except PWTimeout:
            print('AVISO: timeout no goto — continuando mesmo assim')

        # Espera a página estabilizar — Canva carrega muita coisa async
        print('[3/5] Aguardando design renderizar (15s)...')
        page.wait_for_timeout(15000)

        # Screenshot inteira primeiro (debug + fallback)
        debug_path = OUTPUT_PATH.parent / '_debug_fullpage.png'
        page.screenshot(path=str(debug_path), full_page=False)
        print('  full-page screenshot:', debug_path)

        # Tenta achar o canvas principal do design
        print('[4/5] Procurando elemento do canvas...')
        candidate_selectors = [
            'canvas',                               # qualquer canvas
            '[data-testid="DesignViewport"]',       # canvas do editor
            '[class*="page-content"]',              # wrapper do design
            'iframe',                               # caso esteja em iframe
        ]
        canvas_locator = None
        for sel in candidate_selectors:
            els = page.locator(sel)
            count = els.count()
            if count > 0:
                # Primeiro elemento visível
                for i in range(count):
                    el = els.nth(i)
                    if el.is_visible():
                        bbox = el.bounding_box()
                        if bbox and bbox['width'] > 100 and bbox['height'] > 100:
                            canvas_locator = el
                            print('  match: {} (#{}/{}) bbox={}'.format(sel, i, count, bbox))
                            break
                if canvas_locator:
                    break

        if canvas_locator is None:
            print('AVISO: nenhum canvas encontrado — usando full page')
            page.screenshot(path=str(OUTPUT_PATH), full_page=False)
        else:
            print('[5/5] Capturando canvas...')
            canvas_locator.screenshot(path=str(OUTPUT_PATH))

        print('Logo salva em:', OUTPUT_PATH)
        browser.close()


if __name__ == '__main__':
    main()

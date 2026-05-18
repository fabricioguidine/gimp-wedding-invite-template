# wedding-invite-gimp

Gerador automatizado da estrutura base de um convite de casamento tri-fold (sanfona / Z-fold) usando **GIMP 3.2 + Python (GObject Introspection)**.

A ideia é separar **conteúdo** (configurável via YAML) de **estrutura** (código), de modo a gerar variações apenas editando os configs.

## Status

- Fase 0 — Bootstrap: ✅ estrutura de pastas, configs de exemplo, .gitignore, README
- Fase 1 — Documento base: ⏳ canvas + guides + fundo
- Fase 2 — Painéis e bordas: ⏳
- Fase 3 — Calendário: ⏳
- Fase 4 — Paleta de madrinhas: ⏳
- Fase 5 — Textos: ⏳
- Fase 6 — Polimento: ⏳

## Ambiente

- Windows 11, PowerShell
- GIMP 3.2.4 (em `C:\Users\fabri\AppData\Local\Programs\GIMP 3\bin\`)
- Python 3 + GObject Introspection (embarcado no GIMP 3)
- Editor: VS Code

> **Nota sobre a API:** GIMP 3 abandonou o `gimpfu` (Python-Fu antigo do 2.10) em favor de `gi.repository.Gimp`. Plug-ins agora são classes que herdam de `Gimp.PlugIn` e registram procedures. Não tente reaproveitar exemplos antigos do 2.10 sem adaptar.

## Estrutura

```
wedding-invite-gimp/
├── config/
│   ├── invite.yaml          # conteúdo (nomes, data, paleta…)
│   └── layout.yaml          # estrutura (canvas, fontes, dobras…)
├── assets/
│   └── ornaments/           # ornamentos SVG/PNG (opcional)
├── src/                     # preenchido a partir da Fase 1
├── output/                  # gitignored — .xcf gerados
├── run.ps1                  # launcher (criado na Fase 1)
├── .gitignore
└── README.md
```

## Fontes necessárias

Antes da Fase 5, baixar e instalar do Google Fonts:

- **[Great Vibes](https://fonts.google.com/specimen/Great+Vibes)** — para os nomes dos noivos e títulos (estilo script/caligráfico).
- **[Cormorant Garamond](https://fonts.google.com/specimen/Cormorant+Garamond)** — para corpo de texto e endereços (serifa clássica).

Instalação no Windows: baixar o `.zip`, extrair, selecionar todos os `.ttf`, clicar com botão direito → **Instalar para todos os usuários**.

Fallbacks definidos em `config/layout.yaml` (`Segoe Script`, `Georgia`) entram em ação se as principais não forem encontradas.

## Como rodar (a partir da Fase 1)

```powershell
.\run.ps1
```

O launcher invoca `gimp-console-3.2.exe` em modo batch e gera `output/convite.xcf`. Abra no GIMP pra inspecionar.

## Decisões de projeto

- **Tipo de dobra:** sanfona (Z-fold). Painéis no canvas aberto da esquerda pra direita: `madrinha | save_the_date | cover`. Quando o convite é dobrado, a capa fica visível por fora.
- **Dimensões:** 3543 × 1772 px @ 300 DPI (≈ 30 × 15 cm aberto).
- **Cor base:** creme `#F5EDE0`.
- **Paleta sugerida:** verde musgo, terracota, marrom, vinho, nude.

Tudo configurável em `config/`.

## Próximos passos

Fase 1: criar `src/document.py`, `src/build.py` e `run.ps1` para gerar o canvas vazio com fundo creme e guides verticais nas dobras. Aguardando feedback antes de prosseguir.

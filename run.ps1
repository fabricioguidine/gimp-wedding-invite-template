# run.ps1 — Launcher do build no Windows / PowerShell
#
# Fluxo:
#   1. Converte config/*.yaml em output/_config.json (usa Python 3.13 do
#      sistema, que tem pyyaml). Necessário porque a Python embarcada do
#      GIMP 3.2 não tem pip nem pyyaml e é externally-managed (PEP 668).
#   2. Define variáveis de ambiente WEDDING_INVITE_CONFIG e
#      WEDDING_INVITE_OUTPUT que o build.py vai ler.
#   3. Invoca gimp-console-3.2.exe em modo batch com python-fu-eval,
#      importando src/build.py.

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ConfigDir   = Join-Path $ProjectRoot 'config'
$SrcDir      = Join-Path $ProjectRoot 'src'
$OutputDir   = Join-Path $ProjectRoot 'output'
$ConfigJson  = Join-Path $OutputDir   '_config.json'

$Gimp = 'C:\Users\fabri\AppData\Local\Programs\GIMP 3\bin\gimp-console-3.2.exe'

if (-not (Test-Path $Gimp)) {
    throw "GIMP 3 não encontrado em: $Gimp"
}

# Garante a pasta de saída
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# --- Passo 1: YAML → JSON ---------------------------------------------
$YamlConverter = Join-Path $ProjectRoot 'tools\yaml_to_json.py'
python $YamlConverter $ConfigDir $ConfigJson
if ($LASTEXITCODE -ne 0) { throw "Falha convertendo YAML em JSON" }

# --- Passo 2: variáveis de ambiente -----------------------------------
$env:WEDDING_INVITE_CONFIG = $ConfigJson
$env:WEDDING_INVITE_OUTPUT = $OutputDir

# --- Passo 3: invoca GIMP em batch ------------------------------------
# Usa forward-slashes pra evitar interpretação de \ como escape no batch
$SrcForBatch = ($SrcDir -replace '\\','/')
$Batch = "import sys; sys.path.insert(0, r'$SrcForBatch'); import build"

Write-Host "Invocando GIMP em batch..."
# -i = no GUI, -d = no brushes/patterns/etc (faster). Fontes carregadas
# (sem -f) porque a partir da Fase 3 textos dependem delas.
& $Gimp -i -d --quit --batch-interpreter=python-fu-eval -b $Batch
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Warning "GIMP retornou código $ExitCode"
    exit $ExitCode
}

$Expected = @(
    'padrinho_externo.xcf', 'padrinho_interno.xcf',
    'madrinha_externo.xcf', 'madrinha_interno.xcf',
    'casal_externo.xcf',    'casal_interno.xcf'
)

# Limpa qualquer XCF não esperado (manual_*, convite*, etc.) + PNGs.
Get-ChildItem $OutputDir -File -ErrorAction SilentlyContinue | Where-Object {
    ($_.Extension -in '.xcf','.png') -and ($Expected -notcontains $_.Name)
} | Remove-Item -Force
$missing = @()
foreach ($name in $Expected) {
    $p = Join-Path $OutputDir $name
    if (-not (Test-Path $p)) { $missing += $name }
}
if ($missing.Count -gt 0) {
    throw "Build terminou sem erro mas faltaram arquivos: $($missing -join ', ')"
}
Write-Host "Pronto. 6 XCFs em: $OutputDir"

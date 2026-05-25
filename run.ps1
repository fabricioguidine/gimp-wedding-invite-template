# run.ps1 — Launcher for the wedding-stationery modules.
#
# Usage:
#   .\run.ps1                                     # interactive TUI: pick module + fill in fields
#   .\run.ps1 wedding-invite                      # build that module, all defaults from content.yaml
#   .\run.ps1 wedding-invite --bg "C:/path/x.jpg" # build with background image
#   .\run.ps1 -List                               # list known modules and skip the picker
#
# Anything after the module name is forwarded to tui.py as a CLI arg.

[CmdletBinding()]
param(
    [Parameter(Position=0)] [string]$Module,
    [switch]$List,
    [Parameter(ValueFromRemainingArguments=$true)] [string[]]$Rest
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$Tui = Join-Path $ProjectRoot 'tui.py'

# pyyaml is required; questionary is optional (nicer TUI). Check + hint, don't
# auto-install — managing dependencies is the user's job.
try {
    & python -c "import yaml" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "pyyaml missing" }
} catch {
    Write-Warning "pyyaml not installed. Run: pip install pyyaml questionary"
    exit 2
}

if ($List) {
    & python $Tui --module __list__ 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Fall back to listing dirs directly.
        Get-ChildItem (Join-Path $ProjectRoot 'modules') -Directory `
            | Select-Object -ExpandProperty Name
    }
    exit 0
}

$pyArgs = @()
if ($Module)   { $pyArgs += @('--module', $Module) }
if ($Rest)     { $pyArgs += $Rest }

python $Tui @pyArgs
exit $LASTEXITCODE

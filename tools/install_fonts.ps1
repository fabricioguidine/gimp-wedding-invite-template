# Instala Cormorant Garamond no perfil do usuário atual (sem admin).
# Roda só uma vez. Idempotente: pula se já estiver instalada.

$ErrorActionPreference = 'Stop'

$FontFamily = 'Cormorant Garamond'
$BaseUrl = 'https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond'
# Variable fonts (cobrem Regular/Medium/SemiBold/Bold num único arquivo).
$Variants = @(
    @{ UrlFile = 'CormorantGaramond%5Bwght%5D.ttf';        File = 'CormorantGaramond-VF.ttf';       Name = 'Cormorant Garamond Variable (TrueType)' },
    @{ UrlFile = 'CormorantGaramond-Italic%5Bwght%5D.ttf'; File = 'CormorantGaramond-Italic-VF.ttf'; Name = 'Cormorant Garamond Italic Variable (TrueType)' }
)

$DestDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$RegKey  = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'

New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
if (-not (Test-Path $RegKey)) { New-Item -Path $RegKey -Force | Out-Null }

foreach ($v in $Variants) {
    $destFile = Join-Path $DestDir $v.File
    if (Test-Path $destFile) {
        Write-Host "[skip] $($v.File) já existe"
    } else {
        $url = "$BaseUrl/$($v.UrlFile)"
        Write-Host "[get ] $url"
        Invoke-WebRequest -Uri $url -OutFile $destFile -UseBasicParsing
    }

    $existing = Get-ItemProperty -Path $RegKey -Name $v.Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "[skip] registro '$($v.Name)' já presente"
    } else {
        Set-ItemProperty -Path $RegKey -Name $v.Name -Value $destFile
        Write-Host "[reg ] $($v.Name)"
    }
}

# Notifica o sistema (Windows) sobre nova fonte. Apps já abertos (incluindo GIMP)
# precisam reiniciar pra ver a fonte nova.
Add-Type -ErrorAction SilentlyContinue @'
using System;
using System.Runtime.InteropServices;
public class FontHelper {
    [DllImport("gdi32.dll")]
    public static extern int AddFontResource(string lpFilename);
    [DllImport("user32.dll")]
    public static extern int SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}
'@

foreach ($v in $Variants) {
    $destFile = Join-Path $DestDir $v.File
    if (Test-Path $destFile) {
        [void][FontHelper]::AddFontResource($destFile)
    }
}
[void][FontHelper]::SendMessage([IntPtr]0xFFFF, 0x001D, [IntPtr]0, [IntPtr]0)  # WM_FONTCHANGE

Write-Host "Pronto. Cormorant Garamond instalado em $DestDir"

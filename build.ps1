param(
    [switch]$Clean,
    [string]$Icon
)

$ErrorActionPreference = 'Stop'

# Ensure venv
if (-not (Test-Path .\.venv)) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1


pip install -r requirements.txt

# Optionally convert PNG icon to ICO for Windows executables
function Convert-PngToIco($pngPath, $icoOut){
    $code = @'
from PIL import Image
import sys
png, ico = sys.argv[1], sys.argv[2]
img = Image.open(png).convert("RGBA")
# Build multi-size ICO for best scaling
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
img.save(ico, format='ICO', sizes=sizes)
'@
    $tmpScript = Join-Path $env:TEMP ('png2ico_' + [System.Guid]::NewGuid().ToString('N') + '.py')
    Set-Content -Path $tmpScript -Value $code -Encoding UTF8 -NoNewline
    & python $tmpScript $pngPath $icoOut
    Remove-Item $tmpScript -ErrorAction SilentlyContinue
}

# Determine icon file to use
$iconIco = $null
if ($Icon) {
    if ($Icon.ToLower().EndsWith('.ico')) {
        $iconIco = $Icon
    } elseif (Test-Path $Icon) {
        pip install pillow | Out-Null
        $tmpIco = Join-Path $PWD 'icon.auto.ico'
        Convert-PngToIco -pngPath $Icon -icoOut $tmpIco
        $iconIco = $tmpIco
    }
} elseif (Test-Path 'icon.ico') {
    $iconIco = 'icon.ico'
} elseif (Test-Path 'icon.png') {
    pip install pillow | Out-Null
    $tmpIco = Join-Path $PWD 'icon.auto.ico'
    Convert-PngToIco -pngPath 'icon.png' -icoOut $tmpIco
    $iconIco = $tmpIco
}

# PyInstaller build (smaller with UPX, fast and simple)
pip install pyinstaller
$spec = 'better_advanced_paste.spec'
if (-not (Test-Path $spec)) { throw "Missing $spec" }

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
}

# Attempt to use UPX if available in PATH (PyInstaller picks it up automatically)
$hasUpx = (Get-Command upx -ErrorAction SilentlyContinue) -ne $null
if ($hasUpx) { Write-Host 'UPX found: enabling executable compression' }
# Ensure spec references icon.ico; if we only have a generated icon, temporarily copy
if ($iconIco -and (Split-Path -Leaf $iconIco) -ne 'icon.ico') {
    Copy-Item $iconIco -Destination 'icon.ico' -Force
}
pyinstaller --noconfirm --clean $spec

# Place final exe at repo root for convenience
$exe = Join-Path 'dist' 'BetterAdvancedPaste.exe'
if (Test-Path $exe) {
    Copy-Item $exe -Destination . -Force
    Write-Host "Built -> $(Resolve-Path .\BetterAdvancedPaste.exe)"
} else {
    Write-Warning 'Build did not produce expected EXE.'
}
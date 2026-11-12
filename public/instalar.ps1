# Instalador del kit Acuifero para Windows (PowerShell 5.1 o superior).
#
# Uso rapido:
#   irm https://acuifero-agentes.vercel.app/instalar.ps1 | iex
#
# Con opciones:
#   & ([scriptblock]::Create((irm https://acuifero-agentes.vercel.app/instalar.ps1))) -Hermes
#
#   -Hermes            instala ademas en Hermes Agent
#   -Proyecto          instala solo en la carpeta actual (.claude)
#   -Quitar            desinstala lo que este script instalo
#   -Origen C:\kit     instala desde una carpeta local, sin internet
#   -Destino RUTA      instala en otra carpeta
#
# Que hace: copia los agentes a <destino>\agents y las skills a <destino>\skills.
# Si ya existe un archivo distinto con el mismo nombre, lo guarda antes en
# <destino>\acuifero-respaldo. No toca nada mas.

param(
    [string]$Destino = "",
    [string]$Origen = "",
    [switch]$Proyecto,
    [switch]$Hermes,
    [switch]$Quitar
)

$ErrorActionPreference = "Stop"
$Fuentes = @(
    "https://acuifero-agentes.vercel.app/descargas/acuifero-kit.zip",
    "https://raw.githubusercontent.com/Nikolaaa11/acuifero-agentes/main/public/descargas/acuifero-kit.zip"
)

if ($env:ACUIFERO_DESTINO -and -not $Destino) { $Destino = $env:ACUIFERO_DESTINO }
if ($env:ACUIFERO_ORIGEN -and -not $Origen) { $Origen = $env:ACUIFERO_ORIGEN }
if ($env:ACUIFERO_HERMES -eq "1") { $Hermes = $true }
if ($env:ACUIFERO_QUITAR -eq "1") { $Quitar = $true }
if (-not $Destino) {
    if ($Proyecto) { $Destino = Join-Path (Get-Location).Path ".claude" }
    else { $Destino = Join-Path $HOME ".claude" }
}
$Registro = Join-Path $Destino "acuifero-instalado.json"
$Sello = Get-Date -Format "yyyyMMdd-HHmmss"

function Escribir($texto, $color = "Gray") { Write-Host $texto -ForegroundColor $color }

function Iguales($a, $b) {
    if (-not (Test-Path $a) -or -not (Test-Path $b)) { return $false }
    return (Get-FileHash $a).Hash -eq (Get-FileHash $b).Hash
}

function CarpetasIguales($a, $b) {
    $fa = @(Get-ChildItem -Path $a -Recurse -File | ForEach-Object { $_.FullName.Substring($a.Length) } | Sort-Object)
    $fb = @(Get-ChildItem -Path $b -Recurse -File | ForEach-Object { $_.FullName.Substring($b.Length) } | Sort-Object)
    if ($fa.Count -ne $fb.Count) { return $false }
    for ($i = 0; $i -lt $fa.Count; $i++) {
        if ($fa[$i] -ne $fb[$i]) { return $false }
        if (-not (Iguales ($a + $fa[$i]) ($b + $fb[$i]))) { return $false }
    }
    return $true
}

function Respaldar($ruta, $base) {
    $dir = Join-Path (Join-Path $base "acuifero-respaldo") $Sello
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Move-Item -Path $ruta -Destination (Join-Path $dir (Split-Path $ruta -Leaf)) -Force
    return $dir
}

# ---------- Desinstalar ----------
if ($Quitar) {
    if (-not (Test-Path $Registro)) {
        Escribir "No hay registro de instalacion en $Destino. Nada que quitar." "Yellow"
        return
    }
    $datos = Get-Content $Registro -Raw -Encoding UTF8 | ConvertFrom-Json
    $n = 0
    foreach ($ruta in @($datos.archivos)) {
        if (Test-Path $ruta) { Remove-Item -Path $ruta -Recurse -Force -Confirm:$false; $n++ }
    }
    Remove-Item -Path $Registro -Force -Confirm:$false
    Escribir "Listo: se quitaron $n elementos del kit Acuifero." "Green"
    return
}

# ---------- Obtener el kit ----------
$Temporal = $null
if ($Origen) {
    if (-not (Test-Path (Join-Path $Origen "agents"))) { throw "La carpeta $Origen no contiene el kit (falta la carpeta agents)." }
    $Kit = (Resolve-Path $Origen).Path
} else {
    $Temporal = Join-Path ([System.IO.Path]::GetTempPath()) ("acuifero-" + $Sello)
    New-Item -ItemType Directory -Force -Path $Temporal | Out-Null
    $zip = Join-Path $Temporal "kit.zip"
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12 } catch {}
    $bajado = $false
    foreach ($url in $Fuentes) {
        try {
            Escribir "Descargando el kit..."
            Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
            $bajado = $true
            break
        } catch { Escribir "  No se pudo desde $url" "DarkGray" }
    }
    if (-not $bajado) { throw "No se pudo descargar el kit. Revisa la conexion a internet e intenta de nuevo." }
    $Kit = Join-Path $Temporal "kit"
    Expand-Archive -Path $zip -DestinationPath $Kit -Force
}

# ---------- Instalar ----------
$instalados = New-Object System.Collections.ArrayList
$respaldos = 0
$dirAgentes = Join-Path $Destino "agents"
$dirSkills = Join-Path $Destino "skills"
New-Item -ItemType Directory -Force -Path $dirAgentes, $dirSkills | Out-Null

$agentes = @(Get-ChildItem -Path (Join-Path $Kit "agents") -Filter "*.md" -File)
foreach ($a in $agentes) {
    $dest = Join-Path $dirAgentes $a.Name
    if ((Test-Path $dest) -and -not (Iguales $a.FullName $dest)) { Respaldar $dest $Destino | Out-Null; $respaldos++ }
    Copy-Item -Path $a.FullName -Destination $dest -Force
    [void]$instalados.Add($dest)
}

$skills = @(Get-ChildItem -Path (Join-Path $Kit "skills") -Directory)
foreach ($s in $skills) {
    $dest = Join-Path $dirSkills $s.Name
    if (Test-Path $dest) {
        if (CarpetasIguales $s.FullName $dest) { [void]$instalados.Add($dest); continue }
        Respaldar $dest $Destino | Out-Null; $respaldos++
    }
    Copy-Item -Path $s.FullName -Destination $dest -Recurse -Force
    [void]$instalados.Add($dest)
}

# ---------- Hermes Agent (opcional) ----------
$nHermes = 0
if ($Hermes) {
    $dirHermes = Join-Path (Join-Path $HOME ".hermes") "skills"
    if ($env:ACUIFERO_HERMES_DESTINO) { $dirHermes = $env:ACUIFERO_HERMES_DESTINO }
    New-Item -ItemType Directory -Force -Path $dirHermes | Out-Null
    foreach ($s in $skills) {
        $dest = Join-Path $dirHermes $s.Name
        if (Test-Path $dest) { Remove-Item -Path $dest -Recurse -Force -Confirm:$false }
        Copy-Item -Path $s.FullName -Destination $dest -Recurse -Force
        [void]$instalados.Add($dest); $nHermes++
    }
    # En Hermes los agentes se instalan como skills: mismas instrucciones, mismo nombre
    foreach ($a in $agentes) {
        $dest = Join-Path $dirHermes $a.BaseName
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item -Path $a.FullName -Destination (Join-Path $dest "SKILL.md") -Force
        [void]$instalados.Add($dest); $nHermes++
    }
}

# Conserva lo registrado en instalaciones anteriores (por ejemplo, la de Hermes)
if (Test-Path $Registro) {
    try {
        $previo = Get-Content $Registro -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($ruta in @($previo.archivos)) {
            if ($ruta -and (Test-Path $ruta) -and -not $instalados.Contains($ruta)) { [void]$instalados.Add($ruta) }
        }
    } catch {}
}

$version = "1.0.0"
$manifiesto = Join-Path $Kit ".claude-plugin\plugin.json"
if (Test-Path $manifiesto) { $version = (Get-Content $manifiesto -Raw -Encoding UTF8 | ConvertFrom-Json).version }
$registroDatos = [ordered]@{ kit = "acuifero"; version = $version; fecha = (Get-Date -Format "s"); destino = $Destino; archivos = @($instalados) }
$json = $registroDatos | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText($Registro, $json, (New-Object System.Text.UTF8Encoding($false)))

if ($Temporal) { Remove-Item -Path $Temporal -Recurse -Force -Confirm:$false -ErrorAction SilentlyContinue }

# ---------- Resumen ----------
Escribir ""
Escribir "Kit Acuifero $version instalado." "Green"
Escribir "  $($agentes.Count) agentes en $dirAgentes"
Escribir "  $($skills.Count) skills en $dirSkills"
if ($Hermes) { Escribir "  $nHermes skills en Hermes Agent ($dirHermes)" }
if ($respaldos -gt 0) { Escribir "  $respaldos elementos anteriores guardados en $(Join-Path $Destino 'acuifero-respaldo')" "Yellow" }

$py = Get-Command python -ErrorAction SilentlyContinue
$tienePython = $false
if ($py) { try { $v = & python --version 2>&1; if ("$v" -match "Python 3") { $tienePython = $true } } catch {} }
if ($tienePython) {
    $verificador = Join-Path $dirSkills "guia-acuifero\scripts\comprobar.py"
    if (Test-Path $verificador) {
        try {
            $linea = & python $verificador --breve 2>&1 | Select-Object -Last 1
            if ($LASTEXITCODE -eq 0) { Escribir "  $linea" "Green" } else { Escribir "  $linea" "Yellow" }
        } catch { Escribir "  No se pudo correr la comprobacion automatica." "Yellow" }
    }
}
if (-not $tienePython) {
    Escribir ""
    Escribir "Aviso: no encontre Python 3. Los agentes funcionan igual, pero los calculos lo necesitan." "Yellow"
    Escribir "Instalalo gratis desde https://www.python.org/downloads/ (marca 'Add python.exe to PATH')." "Yellow"
}

Escribir ""
Escribir "Siguiente paso: cierra y vuelve a abrir Claude, y escribe:" "Cyan"
Escribir "  Que agentes del kit Acuifero tengo disponibles?" "White"
Escribir ""

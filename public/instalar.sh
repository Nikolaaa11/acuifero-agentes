#!/usr/bin/env bash
# Instalador del kit Acuífero para Mac y Linux.
#
# Uso rápido:
#   curl -fsSL https://acuifero-agentes.vercel.app/instalar.sh | bash
#
# Con opciones:
#   curl -fsSL https://acuifero-agentes.vercel.app/instalar.sh | bash -s -- --hermes
#   bash instalar.sh --proyecto        instala solo en la carpeta actual (.claude)
#   bash instalar.sh --quitar          desinstala lo que este script instaló
#   bash instalar.sh --origen ./kit    instala desde una carpeta local, sin internet
#   bash instalar.sh --destino RUTA    instala en otra carpeta
#
# Qué hace: copia los agentes a <destino>/agents y las skills a <destino>/skills.
# Si ya existe un archivo distinto con el mismo nombre, lo guarda antes en
# <destino>/acuifero-respaldo. No toca nada más.

set -euo pipefail

FUENTES=(
  "https://acuifero-agentes.vercel.app/descargas/acuifero-kit.zip"
  "https://raw.githubusercontent.com/Nikolaaa11/acuifero-agentes/main/public/descargas/acuifero-kit.zip"
)
DESTINO="${ACUIFERO_DESTINO:-}"
ORIGEN="${ACUIFERO_ORIGEN:-}"
HERMES="${ACUIFERO_HERMES:-0}"
PROYECTO=0
QUITAR="${ACUIFERO_QUITAR:-0}"

while [ $# -gt 0 ]; do
  case "$1" in
    --destino) DESTINO="$2"; shift 2 ;;
    --origen) ORIGEN="$2"; shift 2 ;;
    --hermes) HERMES=1; shift ;;
    --proyecto) PROYECTO=1; shift ;;
    --quitar) QUITAR=1; shift ;;
    -h|--help) sed -n '2,16p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$DESTINO" ]; then
  if [ "$PROYECTO" = 1 ]; then DESTINO="$(pwd)/.claude"; else DESTINO="$HOME/.claude"; fi
fi
REGISTRO="$DESTINO/acuifero-instalado.txt"
SELLO="$(date +%Y%m%d-%H%M%S)"

verde() { printf '\033[32m%s\033[0m\n' "$1"; }
amarillo() { printf '\033[33m%s\033[0m\n' "$1"; }

# ---------- Desinstalar ----------
if [ "$QUITAR" = 1 ]; then
  if [ ! -f "$REGISTRO" ]; then
    amarillo "No hay registro de instalación en $DESTINO. Nada que quitar."
    exit 0
  fi
  n=0
  while IFS= read -r ruta; do
    [ -n "$ruta" ] || continue
    if [ -e "$ruta" ]; then rm -rf -- "$ruta"; n=$((n + 1)); fi
  done < "$REGISTRO"
  rm -f -- "$REGISTRO"
  verde "Listo: se quitaron $n elementos del kit Acuífero."
  exit 0
fi

# ---------- Obtener el kit ----------
TEMPORAL=""
limpiar() { if [ -n "$TEMPORAL" ]; then rm -rf -- "$TEMPORAL"; fi; }
trap limpiar EXIT

if [ -n "$ORIGEN" ]; then
  [ -d "$ORIGEN/agents" ] || { echo "La carpeta $ORIGEN no contiene el kit (falta la carpeta agents)." >&2; exit 1; }
  KIT="$(cd "$ORIGEN" && pwd)"
else
  TEMPORAL="$(mktemp -d)"
  bajado=0
  for url in "${FUENTES[@]}"; do
    echo "Descargando el kit..."
    if curl -fsSL "$url" -o "$TEMPORAL/kit.zip"; then bajado=1; break; fi
    echo "  No se pudo desde $url"
  done
  [ "$bajado" = 1 ] || { echo "No se pudo descargar el kit. Revisa la conexión a internet e intenta de nuevo." >&2; exit 1; }
  KIT="$TEMPORAL/kit"
  mkdir -p "$KIT"
  if command -v unzip >/dev/null 2>&1; then
    unzip -q "$TEMPORAL/kit.zip" -d "$KIT"
  elif command -v python3 >/dev/null 2>&1; then
    python3 -m zipfile -e "$TEMPORAL/kit.zip" "$KIT"
  else
    echo "Hace falta unzip o python3 para descomprimir el kit." >&2; exit 1
  fi
fi

# ---------- Instalar ----------
mkdir -p "$DESTINO/agents" "$DESTINO/skills"
LISTA="$(mktemp)"
respaldos=0

respaldar() {
  mkdir -p "$DESTINO/acuifero-respaldo/$SELLO"
  mv -- "$1" "$DESTINO/acuifero-respaldo/$SELLO/"
  respaldos=$((respaldos + 1))
}

n_agentes=0
for a in "$KIT"/agents/*.md; do
  [ -f "$a" ] || continue
  dest="$DESTINO/agents/$(basename "$a")"
  if [ -e "$dest" ] && ! cmp -s "$a" "$dest"; then respaldar "$dest"; fi
  cp -- "$a" "$dest"
  echo "$dest" >> "$LISTA"
  n_agentes=$((n_agentes + 1))
done

n_skills=0
for s in "$KIT"/skills/*/; do
  [ -d "$s" ] || continue
  nombre="$(basename "$s")"
  dest="$DESTINO/skills/$nombre"
  if [ -e "$dest" ]; then
    if diff -rq "$s" "$dest" >/dev/null 2>&1; then
      echo "$dest" >> "$LISTA"; n_skills=$((n_skills + 1)); continue
    fi
    respaldar "$dest"
  fi
  cp -R -- "${s%/}" "$dest"
  echo "$dest" >> "$LISTA"
  n_skills=$((n_skills + 1))
done

# ---------- Hermes Agent (opcional) ----------
n_hermes=0
if [ "$HERMES" = 1 ]; then
  DIR_HERMES="${ACUIFERO_HERMES_DESTINO:-$HOME/.hermes/skills}"
  mkdir -p "$DIR_HERMES"
  for s in "$KIT"/skills/*/; do
    [ -d "$s" ] || continue
    dest="$DIR_HERMES/$(basename "$s")"
    rm -rf -- "$dest"
    cp -R -- "${s%/}" "$dest"
    echo "$dest" >> "$LISTA"; n_hermes=$((n_hermes + 1))
  done
  # En Hermes los agentes se instalan como skills: mismas instrucciones, mismo nombre
  for a in "$KIT"/agents/*.md; do
    [ -f "$a" ] || continue
    dest="$DIR_HERMES/$(basename "$a" .md)"
    mkdir -p "$dest"
    cp -- "$a" "$dest/SKILL.md"
    echo "$dest" >> "$LISTA"; n_hermes=$((n_hermes + 1))
  done
fi

# Conserva lo registrado en instalaciones anteriores (por ejemplo, la de Hermes)
if [ -f "$REGISTRO" ]; then cat "$REGISTRO" >> "$LISTA"; fi
sort -u "$LISTA" > "$REGISTRO"
rm -f -- "$LISTA"

# ---------- Resumen ----------
echo
verde "Kit Acuífero instalado."
echo "  $n_agentes agentes en $DESTINO/agents"
echo "  $n_skills skills en $DESTINO/skills"
if [ "$HERMES" = 1 ]; then echo "  $n_hermes skills en Hermes Agent ($DIR_HERMES)"; fi
if [ "$respaldos" -gt 0 ]; then amarillo "  $respaldos elementos anteriores guardados en $DESTINO/acuifero-respaldo"; fi

# Busca un Python 3.8 o posterior que de verdad funcione (en algunos equipos "python3" es solo un acceso a la tienda)
PY=""
for candidato in python3 python; do
  if command -v "$candidato" >/dev/null 2>&1 && "$candidato" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    PY="$candidato"; break
  fi
done
if [ -n "$PY" ] && [ -f "$DESTINO/skills/guia-acuifero/scripts/comprobar.py" ]; then
  if linea="$("$PY" "$DESTINO/skills/guia-acuifero/scripts/comprobar.py" --breve 2>&1 | tail -n 1)"; then verde "  $linea"; else amarillo "  $linea"; fi
fi

if [ -z "$PY" ]; then
  echo
  amarillo "Aviso: no encontré Python 3. Los agentes funcionan igual, pero los cálculos lo necesitan."
  amarillo "Instálalo gratis desde https://www.python.org/downloads/"
fi

echo
echo "Siguiente paso: cierra y vuelve a abrir Claude, y escribe:"
echo "  ¿Qué agentes del kit Acuífero tengo disponibles?"
echo

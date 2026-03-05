#!/usr/bin/env bash
set -euo pipefail

# =========================
# Paths
# =========================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TOPIC_DEFAULT="Single_URL_Run"
INSECURE=0
URL=""
TOPIC="$TOPIC_DEFAULT"

usage() {
  cat <<EOF
Uso:
  ./scripts/oneclick.sh --url "https://..." [--topic "Mi tema"] [--insecure]

Opciones:
  --url        URL a procesar (recomendado para evitar bloqueos por input)
  --topic      Nombre para el ZIP (por defecto: ${TOPIC_DEFAULT})
  --insecure   (NO recomendado) Desactiva verificación SSL (REQUESTS_INSECURE=1)
EOF
}

# =========================
# Parse args
# =========================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      URL="${2:-}"
      shift 2
      ;;
    --topic)
      TOPIC="${2:-}"
      shift 2
      ;;
    --insecure)
      INSECURE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "❌ Opción desconocida: $1"
      usage
      exit 1
      ;;
  esac
done

# =========================
# Read URL (only if tty)
# =========================
if [[ -z "${URL}" ]]; then
  if [[ -t 0 ]]; then
    echo "========================================"
    echo " AI Tech Research - One Click (URL -> Notion Import ZIP)"
    echo "========================================"
    read -r -p "Pega el link (URL) a procesar: " URL
  else
    echo "❌ No hay TTY para pedir input. Usa: --url \"https://...\""
    exit 1
  fi
fi

if [[ -z "${URL}" ]]; then
  echo "❌ No ingresaste URL."
  exit 1
fi

cd "$PROJECT_DIR"

# =========================
# Run folder (no mezcla)
# =========================
TS="$(date +%Y%m%d_%H%M%S)"
RUN_DIR="${PROJECT_DIR}/out/runs/${TS}"
mkdir -p "$RUN_DIR"

echo "📁 Run dir: $RUN_DIR"
echo "🔗 URL: $URL"
echo "🏷️ Topic: $TOPIC"

# =========================
# venv
# =========================
if [[ ! -d ".venv" ]]; then
  echo "🔧 Creando entorno virtual .venv ..."
  python3 -m venv .venv
fi

echo "✅ Activando .venv ..."
# shellcheck disable=SC1091
source .venv/bin/activate

# =========================
# deps (mínimas, sin colgar)
# =========================
echo "📦 Actualizando pip (rápido)..."
python -m pip install --disable-pip-version-check -q --upgrade pip setuptools wheel

# Fix lxml clean (tu error)
python -m pip install --disable-pip-version-check -q -U lxml_html_clean

if [[ -f "requirements.txt" ]]; then
  echo "📦 Instalando requirements.txt..."
  python -m pip install --disable-pip-version-check -q -r requirements.txt
fi

# =========================
# env for fetch/ssl
# =========================
export REQUESTS_TRUST_ENV=0
export OUT_DIR="$RUN_DIR"
export TOPIC
export URL

if [[ $INSECURE -eq 1 ]]; then
  export REQUESTS_INSECURE=1
  echo "⚠️ Modo --insecure activado (REQUESTS_INSECURE=1)."
else
  unset REQUESTS_INSECURE || true
fi

# =========================
# Run URL analysis
# =========================
echo "🚀 Ejecutando análisis..."
set +e
python -m research.cli url "$URL" --out "$RUN_DIR"
STATUS=$?
set -e

# Retry with certifi bundle if SSL failed
if [[ $STATUS -ne 0 ]]; then
  echo "⚠️ Falló el primer intento. Reintentando con certifi..."
  python -m pip install --disable-pip-version-check -q -U certifi
  export REQUESTS_CA_BUNDLE
  REQUESTS_CA_BUNDLE="$(python -c "import certifi; print(certifi.where())")"

  set +e
  python -m research.cli url "$URL" --out "$RUN_DIR"
  STATUS=$?
  set -e
fi

if [[ $STATUS -ne 0 ]]; then
  echo "❌ No se pudo procesar la URL."
  echo "   - Si es SSL roto del sitio, prueba: --insecure"
  echo "   - Output parcial en: $RUN_DIR"
  exit 1
fi

echo "✅ Análisis terminado."

# =========================
# Find jsonl
# =========================
RESULTS_JSONL=""
if [[ -f "$RUN_DIR/results.jsonl" ]]; then
  RESULTS_JSONL="$RUN_DIR/results.jsonl"
elif [[ -f "$RUN_DIR/oneclick_results.jsonl" ]]; then
  RESULTS_JSONL="$RUN_DIR/oneclick_results.jsonl"
fi

if [[ -z "$RESULTS_JSONL" ]]; then
  echo "⚠️ No encontré results.jsonl dentro de: $RUN_DIR"
  echo "📄 Archivos en run dir:"
  ls -la "$RUN_DIR"
  exit 1
fi

export RESULTS_JSONL

# =========================
# Build Notion ZIP (import directo)
# =========================
echo "📦 Generando ZIP para Notion (import directo)..."
python - <<'PY'
from pathlib import Path
import os
from research.pack import build_notion_import_zip

run_dir = Path(os.environ["OUT_DIR"]).resolve()
topic = os.environ.get("TOPIC", "Single_URL_Run")
results = Path(os.environ["RESULTS_JSONL"]).resolve()

zip_path = build_notion_import_zip(run_dir, topic=topic, results_jsonl=results)
print("✅ ZIP listo:", zip_path.resolve())
print("📁 Notebook folder:", run_dir.resolve())
PY

echo "========================================"
echo "✅ Listo."
echo "📁 Carpeta de ejecución: $RUN_DIR"
echo "➡️ Importa el ZIP en Notion: Settings → Import → ZIP"
echo "========================================"
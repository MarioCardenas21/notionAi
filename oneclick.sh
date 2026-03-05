#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${PROJECT_DIR}/out"

echo "========================================"
echo " AI Tech Research - One Click (URL -> Notion ZIP)"
echo "========================================"
read -rp "Pega el link (URL) a procesar: " URL

if [[ -z "${URL}" ]]; then
  echo "❌ No ingresaste URL."
  exit 1
fi

cd "$PROJECT_DIR"

# 1) Crear venv si no existe
if [[ ! -d ".venv" ]]; then
  echo "🔧 Creando entorno virtual .venv ..."
  python3 -m venv .venv
fi

# 2) Activar venv
echo "✅ Activando .venv ..."
# shellcheck disable=SC1091
source .venv/bin/activate

# 4) Asegurar out/
mkdir -p "$OUT_DIR"

echo "🚀 Ejecutando análisis del link..."
set +e
python3 -m research.cli url "$URL" --out "$OUT_DIR/"
STATUS=$?
set -e

# 5) Si falla por SSL (caso inecol.mx), reintenta con REQUESTS_CA_BUNDLE
if [[ $STATUS -ne 0 ]]; then
  echo "⚠️ Falló el primer intento."
  echo "👉 Reintentando con REQUESTS_CA_BUNDLE (certifi)..."
  export REQUESTS_CA_BUNDLE
  REQUESTS_CA_BUNDLE="$(python3 -c "import certifi; print(certifi.where())")"

  set +e
  python3 -m research.cli url "$URL" --out "$OUT_DIR/"
  STATUS=$?
  set -e
fi

if [[ $STATUS -ne 0 ]]; then
  echo "❌ No se pudo procesar la URL. (posible problema SSL del sitio)"
  echo "Sugerencia: prueba otra fuente o ajusta fetch.py para permitir verify=False por bandera."
  exit 1
fi

echo "✅ Análisis terminado."

# 6) (Opcional pero recomendado) Forzar creación de ZIP Notion si tu CLI no lo hace automáticamente
#    Asume que tu sistema genera oneclick_results.jsonl o results.jsonl
RESULTS_JSONL=""
if [[ -f "$OUT_DIR/oneclick_results.jsonl" ]]; then
  RESULTS_JSONL="$OUT_DIR/oneclick_results.jsonl"
elif [[ -f "$OUT_DIR/results.jsonl" ]]; then
  RESULTS_JSONL="$OUT_DIR/results.jsonl"
fi

if [[ -n "$RESULTS_JSONL" ]]; then
  echo "📦 Generando pack ZIP para Notion desde: $RESULTS_JSONL"
  python3 - <<'PY'
from pathlib import Path
import os
from research.pack import build_notion_upload_pack

out_dir = Path(os.environ.get("OUT_DIR", "out")).resolve()
topic = os.environ.get("TOPIC", "Single_URL_Run")
results = Path(os.environ.get("RESULTS_JSONL")).resolve()

zip_path = build_notion_upload_pack(out_dir, topic=topic, results_jsonl=results)
print("ZIP listo:", zip_path)
PY
else
  echo "⚠️ No encontré results jsonl para empaquetar (oneclick_results.jsonl o results.jsonl)."
  echo "Revisa qué nombre genera tu pipeline en out/."
fi

echo "========================================"
echo "✅ Listo. Revisa la carpeta: $OUT_DIR"
echo "   El ZIP para Notion debe estar ahí."
echo "========================================"
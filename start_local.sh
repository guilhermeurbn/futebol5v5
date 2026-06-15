#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".venv"
PORT_VALUE="${PORT:-5050}"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null

ensure_module() {
  local module_name="$1"
  local package_spec="$2"

  if ! python -c "import ${module_name}" >/dev/null 2>&1; then
    echo "Instalando ${package_spec}..."
    python -m pip install "${package_spec}"
  fi
}

# Dependências essenciais para rodar local sem Postgres obrigatório.
ensure_module flask "Flask>=3.1.3,<4"
ensure_module jinja2 "Jinja2>=3.1.5"
ensure_module flask_wtf "Flask-WTF>=1.1.1"
ensure_module flask_talisman "flask-talisman>=1.0.0"
ensure_module flask_limiter "Flask-Limiter>=3.5.0"
ensure_module requests "requests>=2.32.0"
ensure_module reportlab "reportlab==4.5.1"
ensure_module qrcode "qrcode[pil]"

echo "Subindo localhost em http://localhost:${PORT_VALUE}"
PORT="$PORT_VALUE" python run.py

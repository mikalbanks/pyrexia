#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
  python3.12 -m venv .venv
fi
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  .venv/bin/python -m ensurepip --upgrade
fi
.venv/bin/python -m pip install --disable-pip-version-check -e .
exec .venv/bin/python -m uvicorn pyrexia.app:app --host "${HOST:-0.0.0.0}" --port "${PORT:-3000}"

#!/usr/bin/env bash
# Termux install for artisan-companion — the zero-toolchain way to run the app
# on an Android phone.
#
# Usage (inside Termux, from anywhere inside a checkout of this repo):
#   bash mobile/termux/setup.sh
#
# Then start the app and open Chrome at http://127.0.0.1:8000
#
# To get the repo onto the phone, either:
#   - git clone <repo-url>            (Termux: pkg install git)
#   - sync the folder with Syncthing / Dropbox / USB copy, then open Termux
#     in that folder.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
  echo "ERROR: pyproject.toml not found at $REPO_ROOT" >&2
  echo "Run this script from inside a checkout of artisan-companion." >&2
  exit 1
fi

echo "==> Repo root: $REPO_ROOT"

# Make sure Python is available (Termux package).
if ! command -v python >/dev/null 2>&1; then
  echo "==> Installing python via pkg..."
  pkg install -y python python-pip || true
fi

VENV="$REPO_ROOT/.venv-mobile"
if [ ! -d "$VENV" ]; then
  echo "==> Creating virtualenv at $VENV"
  python -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "==> Upgrading pip"
pip install --upgrade pip

echo "==> Installing artisan-companion[app] (editable)"
pip install -e "$REPO_ROOT[app]"

# Default logs folder (override with ARTISAN_LOGS_DIR).
LOGS_DIR="${ARTISAN_LOGS_DIR:-$REPO_ROOT/logs}"
SENSORY_DIR="${ARTISAN_SENSORY_DIR:-$LOGS_DIR/../sensory}"
mkdir -p "$LOGS_DIR" "$SENSORY_DIR"

cat <<EOF

Done.

Start the app on your phone:

  source "$VENV/bin/activate"
  artisan-companion --logs-dir "$LOGS_DIR" --sensory-dir "$SENSORY_DIR"

Then open Chrome and go to:

  http://127.0.0.1:8000

Put your .alog files in:
  $LOGS_DIR

Tip: in Chrome, use the menu -> "Add to Home screen" to pin the app.
EOF

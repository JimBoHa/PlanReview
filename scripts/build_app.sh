#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

rm -rf build dist release/app
mkdir -p release/app

pyinstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name PlanReview \
  --osx-bundle-identifier com.PlanReviewer.installer \
  --add-data "src/planreview/templates:planreview/templates" \
  --add-data "src/planreview/static:planreview/static" \
  --add-data "src/planreview/data:planreview/data" \
  src/planreview/desktop.py

APP_PATH="$ROOT_DIR/dist/PlanReview.app"
SIGNED_APP_PATH="$ROOT_DIR/release/app/PlanReview.app"
rm -rf "$SIGNED_APP_PATH"
cp -R "$APP_PATH" "$SIGNED_APP_PATH"

IDENTITY="${PLANREVIEW_CODESIGN_IDENTITY:-}"
if [[ -n "$IDENTITY" ]]; then
  codesign --force --deep --options runtime --sign "$IDENTITY" "$SIGNED_APP_PATH"
fi

echo "Built app at $SIGNED_APP_PATH"

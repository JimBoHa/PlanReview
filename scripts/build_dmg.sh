#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

APP_PATH="${1:-$ROOT_DIR/release/app/PlanReview.app}"
DMG_PATH="${2:-$ROOT_DIR/release/PlanReview.dmg}"
VOL_NAME="PlanReview"
IDENTITY="${PLANREVIEW_CODESIGN_IDENTITY:-}"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found at $APP_PATH" >&2
  exit 1
fi

mkdir -p "$ROOT_DIR/release"
rm -f "$DMG_PATH"

TMP_DIR="$ROOT_DIR/release/dmg-root"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
cp -R "$APP_PATH" "$TMP_DIR/"
ln -s /Applications "$TMP_DIR/Applications"

hdiutil create \
  -volname "$VOL_NAME" \
  -srcfolder "$TMP_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

if [[ -n "$IDENTITY" ]]; then
  codesign --force --sign "$IDENTITY" "$DMG_PATH"
fi

echo "Built DMG at $DMG_PATH"

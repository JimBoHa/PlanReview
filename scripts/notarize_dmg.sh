#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

DMG_PATH="${1:-$ROOT_DIR/release/PlanReview.dmg}"
if [[ ! -f "$DMG_PATH" ]]; then
  echo "DMG not found at $DMG_PATH" >&2
  exit 1
fi

KEY_FILE="${PLANREVIEW_NOTARY_KEY_FILE:-$HOME/Desktop/AuthKey_85UV77M2Z3.p8}"
KEY_ID="${PLANREVIEW_NOTARY_KEY_ID:-85UV77M2Z3}"
ISSUER_ID="${PLANREVIEW_NOTARY_ISSUER_ID:-9a497746-bc2b-4019-bde4-ace11385d79b}"
TEAM_ID="${PLANREVIEW_TEAM_ID:-Q3NM3D8P4S}"
IDENTITY="${PLANREVIEW_CODESIGN_IDENTITY:-}"
APP_PATH="${PLANREVIEW_APP_PATH:-$ROOT_DIR/release/app/PlanReview.app}"

if [[ -n "$IDENTITY" && -d "$APP_PATH" ]]; then
  codesign --force --deep --options runtime --sign "$IDENTITY" "$APP_PATH"
fi

xcrun notarytool submit \
  "$DMG_PATH" \
  --key "$KEY_FILE" \
  --key-id "$KEY_ID" \
  --issuer "$ISSUER_ID" \
  --wait

xcrun stapler staple "$APP_PATH"
xcrun stapler staple "$DMG_PATH"
echo "Notarization completed for $DMG_PATH"
echo "Team ID: $TEAM_ID"

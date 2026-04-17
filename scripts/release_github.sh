#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TAG="${1:-v0.1.2}"
DMG_PATH="${2:-$ROOT_DIR/release/PlanReview.dmg}"

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "Set GH_TOKEN before running this script." >&2
  exit 1
fi

if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" --title "$TAG" --notes "PlanReview desktop release"
fi

gh release upload "$TAG" "$DMG_PATH" --clobber
echo "Uploaded $DMG_PATH to release $TAG"

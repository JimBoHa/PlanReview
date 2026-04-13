#!/bin/zsh
set -euo pipefail

P12_PATH="${1:-$HOME/Desktop/developerID.p12}"
PASSWORD="${2:-}"

security import "$P12_PATH" -k "$HOME/Library/Keychains/login.keychain-db" -P "$PASSWORD" -T /usr/bin/codesign
security find-identity -v -p codesigning

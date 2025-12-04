#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIVERSAL_SCRIPT="/Users/home/GitHub/universal_dmg.sh"
CONFIG_FILE="$SCRIPT_DIR/dmg-config.json"

if [[ ! -x "$UNIVERSAL_SCRIPT" ]]; then
  echo "Universal DMG script not found at $UNIVERSAL_SCRIPT" >&2
  exit 1
fi

exec "$UNIVERSAL_SCRIPT" "$CONFIG_FILE"

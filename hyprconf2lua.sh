#!/bin/bash
# hyprconf2lua - works from the repo clone without pip install
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
if [ -d "$SCRIPT_DIR/src/hyprconf2lua" ]; then
    PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH" exec python3 -m hyprconf2lua "$@"
else
    exec python3 -m hyprconf2lua "$@"
fi

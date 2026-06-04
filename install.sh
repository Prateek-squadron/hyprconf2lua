#!/bin/bash
# install.sh — Symlink hyprconf2lua into your PATH
# Run: ./install.sh [target_dir]
# Default target: ~/.local/bin

TARGET="${1:-$HOME/.local/bin}"
mkdir -p "$TARGET"

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
LINK="$TARGET/hyprconf2lua"

if [ -f "$LINK" ] || [ -L "$LINK" ]; then
    echo "Warning: $LINK already exists, overwriting."
fi
ln -sf "$SCRIPT_DIR/hyprconf2lua.sh" "$LINK"
chmod +x "$SCRIPT_DIR/hyprconf2lua.sh"

echo "Installed hyprconf2lua -> $LINK"
echo ""
echo "Make sure $TARGET is in your PATH."
echo "Then run: hyprconf2lua ~/.config/hypr/hyprland.conf > hyprland.lua"

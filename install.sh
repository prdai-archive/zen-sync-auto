#!/bin/bash
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
LIB_DIR="${HOME}/.local/lib/zensync"
REPO="prdai-archive/zen-sync-auto"
mkdir -p "$BIN_DIR" "$LIB_DIR"

curl -fsSL "https://raw.githubusercontent.com/$REPO/main/zensync" -o "$BIN_DIR/zensync"
curl -fsSL "https://raw.githubusercontent.com/$REPO/main/merge.py" -o "$LIB_DIR/merge.py"
chmod +x "$BIN_DIR/zensync"

echo "Installed zensync to $BIN_DIR/zensync"

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    echo "Add this to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

command -v gh >/dev/null 2>&1 || echo "Note: gh (GitHub CLI) is required — brew install gh / your distro's package"

echo "Run 'zensync init' on each machine (uses your gh auth session), then just run 'zensync' whenever you switch machines."

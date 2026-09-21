#!/usr/bin/env bash
# Put the app in the applications menu so it can be launched by name.
#
#   ./install-desktop.sh          install for the current user
#   ./install-desktop.sh --remove undo
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"

if [ "${1:-}" = "--remove" ]; then
    rm -f "$BIN/io24-mixer" "$APPS/org.io24.Mixer.desktop" \
          "$ICONS/org.io24.Mixer.svg"
    update-desktop-database "$APPS" 2>/dev/null || true
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    echo "removed"
    exit 0
fi

mkdir -p "$BIN" "$APPS" "$ICONS"
# Substitute with python, not sed: this project's own directory name contains
# a pipe character, which is the obvious sed delimiter — and every other
# delimiter is a character some path can legitimately contain too.
APP_DIR="$APP_DIR" python3 - "$APP_DIR/io24-mixer" "$BIN/io24-mixer" <<'PYEOF'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
open(dst, "w").write(open(src).read().replace("__APP_DIR__", os.environ["APP_DIR"]))
PYEOF
chmod +x "$BIN/io24-mixer"
install -m 644 "$APP_DIR/icons/org.io24.Mixer.svg" "$ICONS/"
install -m 644 "$APP_DIR/org.io24.Mixer.desktop"   "$APPS/"

# Without these the entry can take minutes to appear, or show a blank icon.
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "installed:"
echo "  launcher  $BIN/io24-mixer"
echo "  entry     $APPS/org.io24.Mixer.desktop"
echo "  icon      $ICONS/org.io24.Mixer.svg"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "  NOTE: $BIN is not on PATH";; esac

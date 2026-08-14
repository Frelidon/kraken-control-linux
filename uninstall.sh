#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/open-hardware-control"
rm -f "$HOME/.local/bin/open-hardware-control"
rm -f "$HOME/.local/bin/open-hardware-control-diagnostics"
rm -f "$HOME/.local/bin/kraken-control"
rm -f "$HOME/.local/share/applications/open-hardware-control.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/open-hardware-control.svg"
rm -f "$HOME/.config/autostart/open-hardware-control.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
echo "Open Hardware Control wurde für diesen Benutzer entfernt."
echo "Programmdateien einer älteren Kraken-Control-Installation wurden nicht gelöscht."
echo "Die udev-Regel wurde nicht entfernt."

#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/kraken-control"
rm -f "$HOME/.local/bin/kraken-control"
rm -f "$HOME/.local/bin/kraken-control-diagnostics"
rm -f "$HOME/.local/share/applications/kraken-control.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/kraken-control.svg"
rm -f "$HOME/.config/autostart/kraken-control.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
echo "Kraken Control wurde für diesen Benutzer entfernt."
echo "Die udev-Regel wurde nicht entfernt."

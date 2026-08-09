#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/.local/share/kraken-control"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
install -m 0755 "$SOURCE_DIR/kraken_control.py" "$APP_DIR/kraken_control.py"
install -m 0644 "$SOURCE_DIR/kraken-control.svg" "$APP_DIR/kraken-control.svg"
install -m 0644 "$SOURCE_DIR/kraken-control.svg" "$ICON_DIR/kraken-control.svg"
install -m 0755 "$SOURCE_DIR/collect-diagnostics.sh" "$APP_DIR/collect-diagnostics.sh"
install -m 0755 "$SOURCE_DIR/install-udev-rule.sh" "$APP_DIR/install-udev-rule.sh"
install -m 0755 "$SOURCE_DIR/install-dependencies.sh" "$APP_DIR/install-dependencies.sh"
install -m 0644 "$SOURCE_DIR/71-nzxt-kraken-2023.rules" "$APP_DIR/71-nzxt-kraken-2023.rules"
install -m 0644 "$SOURCE_DIR/LICENSE" "$APP_DIR/LICENSE"
install -m 0644 "$SOURCE_DIR/SUPPORTED_DEVICES.md" "$APP_DIR/SUPPORTED_DEVICES.md"
install -m 0644 "$SOURCE_DIR/SECURITY.md" "$APP_DIR/SECURITY.md"
install -m 0644 "$SOURCE_DIR/README.md" "$APP_DIR/README.md"
install -m 0644 "$SOURCE_DIR/CHANGELOG.md" "$APP_DIR/CHANGELOG.md"
install -m 0644 "$SOURCE_DIR/README.en.md" "$APP_DIR/README.en.md"
install -m 0644 "$SOURCE_DIR/SOFTWARE_AND_LINKS.md" "$APP_DIR/SOFTWARE_AND_LINKS.md"
install -m 0644 "$SOURCE_DIR/SOFTWARE_AND_LINKS.en.md" "$APP_DIR/SOFTWARE_AND_LINKS.en.md"
install -m 0644 "$SOURCE_DIR/SUPPORTED_DEVICES.en.md" "$APP_DIR/SUPPORTED_DEVICES.en.md"
install -m 0644 "$SOURCE_DIR/PROJECT_SCOPE.md" "$APP_DIR/PROJECT_SCOPE.md"
install -m 0644 "$SOURCE_DIR/PROJECT_SCOPE.en.md" "$APP_DIR/PROJECT_SCOPE.en.md"
install -m 0644 "$SOURCE_DIR/CPU_PROFILES.md" "$APP_DIR/CPU_PROFILES.md"
install -m 0644 "$SOURCE_DIR/CPU_PROFILES.en.md" "$APP_DIR/CPU_PROFILES.en.md"
install -m 0644 "$SOURCE_DIR/COMPONENT_VERSIONS.md" "$APP_DIR/COMPONENT_VERSIONS.md"
install -m 0644 "$SOURCE_DIR/ANIMATED_BACKGROUNDS.md" "$APP_DIR/ANIMATED_BACKGROUNDS.md"
install -m 0644 "$SOURCE_DIR/PROFILES.md" "$APP_DIR/PROFILES.md"
install -m 0644 "$SOURCE_DIR/FEATURES_BY_VERSION.md" "$APP_DIR/FEATURES_BY_VERSION.md"
install -m 0644 "$SOURCE_DIR/SOURCE_CODE.md" "$APP_DIR/SOURCE_CODE.md"

cat > "$BIN_DIR/kraken-control" <<LAUNCHER
#!/usr/bin/env bash
"$APP_DIR/install-dependencies.sh" --check-and-install || exit \$?
exec python3 "$APP_DIR/kraken_control.py" "\$@"
LAUNCHER
chmod 0755 "$BIN_DIR/kraken-control"

cat > "$BIN_DIR/kraken-control-diagnostics" <<LAUNCHER
#!/usr/bin/env bash
exec "$APP_DIR/collect-diagnostics.sh" "\$@"
LAUNCHER
chmod 0755 "$BIN_DIR/kraken-control-diagnostics"

sed -e "s|@EXEC@|$BIN_DIR/kraken-control|g" \
    -e "s|@ICON@|$APP_DIR/kraken-control.svg|g" \
    "$SOURCE_DIR/kraken-control.desktop.in" > "$DESKTOP_DIR/kraken-control.desktop"
chmod 0644 "$DESKTOP_DIR/kraken-control.desktop"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

# KDE/Plasma liest Desktop-Dateien und Symbole teilweise aus einem Cache.
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
command -v kbuildsycoca5 >/dev/null 2>&1 && kbuildsycoca5 --noincremental >/dev/null 2>&1 || true

echo
echo "Kraken Control by Frelidon 2.9.6 wurde installiert."
echo "Start im Terminal: $BIN_DIR/kraken-control"
echo "Diagnosebericht: $BIN_DIR/kraken-control-diagnostics"
echo "Oder im Anwendungsmenü nach 'Kraken Control by Frelidon' suchen."
echo
echo "Fehlende Abhängigkeiten werden beim Start geprüft und können nach Bestätigung installiert werden."
echo "Manuell auf Nobara/Fedora: sudo dnf install liquidctl python3-pyside6 python3-pillow polkit"
echo
echo "Bei Schreibfehlern: $APP_DIR/install-udev-rule.sh"

#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Open Hardware Control - Fedora KDE desktop look helper
# Usage:
#   desktop-look-fedora-kde.sh --windows11
#   desktop-look-fedora-kde.sh --macos
#   desktop-look-fedora-kde.sh --restore

set -Eeuo pipefail
IFS=$'\n\t'

LOOK=""
ACTION="install"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/open-hardware-control/desktop-look"
BACKUP_ROOT="$STATE_DIR/backups"
LATEST_FILE="$STATE_DIR/latest-backup"
WORKDIR="${XDG_CACHE_HOME:-$HOME/.cache}/open-hardware-control-desktop-look"

for arg in "$@"; do
    case "$arg" in
        --windows11|--win11) LOOK="windows11" ;;
        --macos|--mac) LOOK="macos" ;;
        --restore) ACTION="restore" ;;
        -h|--help)
            cat <<'EOF'
Open Hardware Control - Fedora KDE Desktop-Look

Optionen:
  --windows11   Windows-11-artigen KDE-Look installieren
  --macos       macOS-artigen KDE-Look installieren
  --restore     letztes Backup wiederherstellen
EOF
            exit 0
            ;;
        *) echo "Unbekannte Option: $arg" >&2; exit 1 ;;
    esac
done

if [[ "$ACTION" == "install" && -z "$LOOK" ]]; then
    echo "Bitte --windows11 oder --macos angeben." >&2
    exit 1
fi

info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok() { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
die() { printf '\033[1;31mFehler:\033[0m %s\n' "$*" >&2; exit 1; }

[[ -r /etc/os-release ]] || die "/etc/os-release fehlt."
. /etc/os-release
[[ "${ID:-}" == "fedora" ]] || die "Dieses Skript ist für Fedora KDE gedacht."
[[ "${XDG_CURRENT_DESKTOP:-}" == *KDE* || "${KDE_FULL_SESSION:-}" == "true" ]] || warn "KDE Plasma wurde nicht eindeutig erkannt."

mkdir -p "$STATE_DIR" "$BACKUP_ROOT"

backup_config() {
    local stamp backup
    stamp="$(date +%Y%m%d-%H%M%S)"
    backup="$BACKUP_ROOT/$stamp"
    mkdir -p "$backup/config"

    info "Sichere KDE/Plasma-Konfiguration …"
    local files=(
        kdeglobals kwinrc plasmarc plasmashellrc
        plasma-org.kde.plasma.desktop-appletsrc
        kglobalshortcutsrc kcminputrc dolphinrc
    )
    for f in "${files[@]}"; do
        [[ -e "$HOME/.config/$f" ]] && cp -a "$HOME/.config/$f" "$backup/config/"
    done
    printf '%s\n' "$backup" > "$LATEST_FILE"
    ok "Backup: $backup"
}

restore_config() {
    [[ -f "$LATEST_FILE" ]] || die "Kein Backup gefunden."
    local backup
    backup="$(cat "$LATEST_FILE")"
    [[ -d "$backup/config" ]] || die "Backup-Ordner fehlt: $backup"

    info "Stelle Backup wieder her: $backup"
    command -v kquitapp6 >/dev/null 2>&1 && kquitapp6 plasmashell >/dev/null 2>&1 || true
    shopt -s nullglob
    for f in "$backup/config/"*; do cp -a "$f" "$HOME/.config/"; done
    shopt -u nullglob
    command -v plasmashell >/dev/null 2>&1 && nohup plasmashell --replace >/dev/null 2>&1 &
    ok "Wiederhergestellt. Danach einmal abmelden/anmelden."
}

run_plasma_js() {
    local js_file="$1"
    local js
    js="$(cat "$js_file")"
    if command -v qdbus6 >/dev/null 2>&1; then
        qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "$js" >/dev/null
    elif command -v gdbus >/dev/null 2>&1; then
        gdbus call --session --dest org.kde.plasmashell --object-path /PlasmaShell \
            --method org.kde.PlasmaShell.evaluateScript "$js" >/dev/null
    else
        return 1
    fi
}

apply_common_kde_settings() {
    local icons="$1" color_scheme="$2" plasma_theme="$3" aurorae="$4" kvantum="$5"

    kwriteconfig6 --file kdeglobals --group Icons --key Theme "$icons"
    kwriteconfig6 --file kdeglobals --group General --key ColorScheme "$color_scheme"
    kwriteconfig6 --file plasmarc --group Theme --key name "$plasma_theme"
    kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle "kvantum"
    mkdir -p "$HOME/.config/Kvantum"
    kwriteconfig6 --file "$HOME/.config/Kvantum/kvantum.kvconfig" --group General --key theme "$kvantum"

    kwriteconfig6 --file kdeglobals --group KDE --key SingleClick false
    kwriteconfig6 --file kdeglobals --group KDE --key ShowDeleteCommand true
    kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library org.kde.kwin.aurorae
    kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme "$aurorae"
    kwriteconfig6 --file kwinrc --group Plugins --key blurEnabled true
    kwriteconfig6 --file kwinrc --group Plugins --key contrastEnabled true
    kwriteconfig6 --file dolphinrc --group General --key ShowFullPath false
    kwriteconfig6 --file dolphinrc --group General --key ShowStatusBar true
}

install_deps() {
    info "Installiere Pakete …"
    sudo dnf install -y git kvantum kvantum-data qt6ct google-noto-sans-fonts google-noto-sans-mono-fonts curl unzip
}

install_windows11() {
    info "Installiere Windows-11-artigen Fluent-Look …"
    rm -rf "$WORKDIR"; mkdir -p "$WORKDIR"; cd "$WORKDIR"
    git clone --depth=1 https://github.com/vinceliuice/Fluent-kde.git
    (cd Fluent-kde && ./install.sh --round -c dark)
    git clone --depth=1 https://github.com/vinceliuice/Fluent-icon-theme.git
    (cd Fluent-icon-theme && ./install.sh standard)

    command -v plasma-apply-lookandfeel >/dev/null 2>&1 && \
        plasma-apply-lookandfeel -a com.github.vinceliuice.Fluent-round-dark || true

    apply_common_kde_settings "Fluent" "FluentDark" "Fluent-round-dark" \
        "__aurorae__svg__Fluent-round-dark" "Fluent-round"

    local js
    js="$(mktemp)"
    cat > "$js" <<'EOF'
var ps = panels();
var p = null;
for (var i = 0; i < ps.length; ++i) {
    if (ps[i].formFactor === "horizontal") { p = ps[i]; break; }
}
if (p !== null) {
    p.location = "bottom";
    p.height = 48;
    p.lengthMode = "fill";
    p.alignment = "center";
    p.hiding = "none";
    var oldWidgets = p.widgets();
    for (var j = oldWidgets.length - 1; j >= 0; --j) oldWidgets[j].remove();
    var left = p.addWidget("org.kde.plasma.panelspacer");
    if (left) { left.currentConfigGroup = ["General"]; left.writeConfig("expanding", true); }
    var kickoff = p.addWidget("org.kde.plasma.kickoff");
    if (kickoff) kickoff.globalShortcut = "Alt+F1";
    p.addWidget("org.kde.plasma.icontasks");
    var right = p.addWidget("org.kde.plasma.panelspacer");
    if (right) { right.currentConfigGroup = ["General"]; right.writeConfig("expanding", true); }
    p.addWidget("org.kde.plasma.systemtray");
    p.addWidget("org.kde.plasma.digitalclock");
    p.addWidget("org.kde.plasma.showdesktop");
    p.reloadConfig();
}
EOF
    run_plasma_js "$js" || warn "Panel konnte nicht live geändert werden."
    rm -f "$js"
}

install_macos() {
    info "Installiere macOS-artigen WhiteSur-Look …"
    rm -rf "$WORKDIR"; mkdir -p "$WORKDIR"; cd "$WORKDIR"
    git clone --depth=1 https://github.com/vinceliuice/WhiteSur-kde.git
    (cd WhiteSur-kde && ./install.sh)
    git clone --depth=1 https://github.com/vinceliuice/WhiteSur-icon-theme.git
    (cd WhiteSur-icon-theme && ./install.sh)
    git clone --depth=1 https://github.com/vinceliuice/WhiteSur-cursors.git
    (cd WhiteSur-cursors && ./install.sh)

    command -v plasma-apply-lookandfeel >/dev/null 2>&1 && \
        plasma-apply-lookandfeel -a com.github.vinceliuice.WhiteSur-dark || true

    apply_common_kde_settings "WhiteSur-dark" "WhiteSurDark" "WhiteSur-dark" \
        "__aurorae__svg__WhiteSur-dark" "WhiteSur-dark"

    kwriteconfig6 --file kcminputrc --group Mouse --key cursorTheme "WhiteSur-cursors"

    local js
    js="$(mktemp)"
    cat > "$js" <<'EOF'
var ps = panels();
for (var i = ps.length - 1; i >= 0; --i) {
    try { ps[i].remove(); } catch (e) {}
}

var top = new Panel;
top.location = "top";
top.height = 28;
top.lengthMode = "fill";
top.hiding = "none";
top.addWidget("org.kde.plasma.kickoff");
top.addWidget("org.kde.plasma.appmenu");
var spacer = top.addWidget("org.kde.plasma.panelspacer");
if (spacer) { spacer.currentConfigGroup = ["General"]; spacer.writeConfig("expanding", true); }
top.addWidget("org.kde.plasma.systemtray");
top.addWidget("org.kde.plasma.digitalclock");

var dock = new Panel;
dock.location = "bottom";
dock.height = 64;
dock.lengthMode = "fit";
dock.alignment = "center";
dock.hiding = "autohide";
dock.addWidget("org.kde.plasma.icontasks");
dock.reloadConfig();
top.reloadConfig();
EOF
    run_plasma_js "$js" || warn "Panel konnte nicht live geändert werden."
    rm -f "$js"
}

if [[ "$ACTION" == "restore" ]]; then
    restore_config
    exit 0
fi

backup_config
install_deps

case "$LOOK" in
    windows11) install_windows11 ;;
    macos) install_macos ;;
esac

command -v qdbus6 >/dev/null 2>&1 && qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
command -v kbuildsycoca6 >/dev/null 2>&1 && kbuildsycoca6 >/dev/null 2>&1 || true

cat <<EOF

Fertig 😄
Aktiver Look: $LOOK

Bitte einmal von KDE abmelden und wieder anmelden.

Rückgängig:
  $0 --restore

Backup:
  $(cat "$LATEST_FILE")
EOF

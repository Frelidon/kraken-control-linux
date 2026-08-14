#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

MODE="${1:---check-and-install}"
PKEXEC_BIN="$(command -v pkexec || true)"

declare -a missing_keys=()
declare -a missing_labels=()
declare -a missing_packages=()

if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
fi

DISTRO_ID="${ID:-unknown}"
PACKAGE_FAMILY="unknown"
PACKAGE_MANAGER=""

if command -v dnf >/dev/null 2>&1; then
    PACKAGE_FAMILY="dnf"
    PACKAGE_MANAGER="$(command -v dnf)"
elif command -v apt-get >/dev/null 2>&1; then
    PACKAGE_FAMILY="apt"
    PACKAGE_MANAGER="$(command -v apt-get)"
elif command -v pacman >/dev/null 2>&1; then
    PACKAGE_FAMILY="pacman"
    PACKAGE_MANAGER="$(command -v pacman)"
elif command -v zypper >/dev/null 2>&1; then
    PACKAGE_FAMILY="zypper"
    PACKAGE_MANAGER="$(command -v zypper)"
fi

package_for() {
    local key="$1"
    case "$PACKAGE_FAMILY:$key" in
        dnf:liquidctl) echo "liquidctl" ;;
        dnf:pyside6) echo "python3-pyside6" ;;
        dnf:qtsvg) echo "qt6-qtsvg" ;;
        dnf:pillow) echo "python3-pillow" ;;
        dnf:polkit) echo "polkit" ;;
        apt:liquidctl) echo "liquidctl" ;;
        apt:pyside6) echo "python3-pyside6.qtwidgets" ;;
        apt:qtsvg) echo "python3-pyside6.qtsvg" ;;
        apt:pillow) echo "python3-pil" ;;
        apt:polkit) echo "policykit-1" ;;
        pacman:liquidctl) echo "liquidctl" ;;
        pacman:pyside6) echo "pyside6" ;;
        pacman:qtsvg) echo "qt6-svg" ;;
        pacman:pillow) echo "python-pillow" ;;
        pacman:polkit) echo "polkit" ;;
        zypper:liquidctl) echo "liquidctl" ;;
        zypper:pyside6) echo "python3-pyside6" ;;
        zypper:qtsvg) echo "libQt6Svg6" ;;
        zypper:pillow) echo "python3-Pillow" ;;
        zypper:polkit) echo "polkit" ;;
        *) return 1 ;;
    esac
}

add_missing() {
    local key="$1"
    local label="$2"
    local package
    package="$(package_for "$key" 2>/dev/null || true)"
    missing_keys+=("$key")
    missing_labels+=("$label")
    [[ -n "$package" ]] && missing_packages+=("$package")
}

if [[ "$MODE" != "--check-gui-and-install" ]]; then
    command -v liquidctl >/dev/null 2>&1 || add_missing "liquidctl" "liquidctl"
fi
python3 -c 'import PySide6' >/dev/null 2>&1 || add_missing "pyside6" "PySide6 / Qt for Python"
python3 -c 'from PySide6.QtGui import QImageReader; assert any(bytes(x).lower() == b"svg" for x in QImageReader.supportedImageFormats())' >/dev/null 2>&1 || add_missing "qtsvg" "Qt-SVG-Unterstützung"
if [[ "$MODE" != "--check-gui-and-install" ]]; then
    python3 -c 'from PIL import Image' >/dev/null 2>&1 || add_missing "pillow" "Pillow"
fi

if (( ${#missing_keys[@]} == 0 )); then
    echo "Alle benötigten Abhängigkeiten sind installiert."
    exit 0
fi

if [[ -z "$PKEXEC_BIN" ]] && ! command -v sudo >/dev/null 2>&1; then
    missing_packages+=("$(package_for polkit 2>/dev/null || true)")
fi

mapfile -t missing_packages < <(printf '%s\n' "${missing_packages[@]}" | sed '/^$/d' | awk '!seen[$0]++')
label_list="$(printf '%s\n' "${missing_labels[@]}" | sed 's/^/• /')"
package_list="${missing_packages[*]}"

case "$PACKAGE_FAMILY" in
    dnf) manual_command="sudo dnf install ${package_list}" ;;
    apt) manual_command="sudo apt update && sudo apt install ${package_list}" ;;
    pacman) manual_command="sudo pacman -S --needed ${package_list}" ;;
    zypper) manual_command="sudo zypper install ${package_list}" ;;
    *) manual_command="Siehe INSTALL.md für die manuelle Installation." ;;
esac

show_error() {
    local message="$1"
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Open Hardware Control by Frelidon" --error "$message" || true
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Open Hardware Control by Frelidon" --text="$message" || true
    else
        printf '%b\n' "$message" >&2
    fi
}

ask_confirmation() {
    local purpose="für das NZXT-Modul"
    [[ "$MODE" == "--check-gui-and-install" ]] && purpose="für die grafische Oberfläche"
    local message="Open Hardware Control benötigt ${purpose} folgende Pakete:\n\n${label_list}\n\nDistribution: ${DISTRO_ID} (${PACKAGE_FAMILY})\nEs werden nur die bereits eingerichteten Paketquellen verwendet. Es werden keine fremden Paketquellen hinzugefügt.\n\nFortfahren?"
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Abhängigkeiten installieren" --yesno "$message"
        return $?
    fi
    if command -v zenity >/dev/null 2>&1; then
        zenity --question --title="Abhängigkeiten installieren" --text="$message"
        return $?
    fi
    if [[ -t 0 ]]; then
        printf 'Fehlende Abhängigkeiten:\n%s\n\nInstallieren? [j/N] ' "$label_list"
        read -r answer
        [[ "$answer" =~ ^[JjYy]$ ]]
        return $?
    fi
    show_error "Fehlende Abhängigkeiten:\n\n${label_list}\n\nStarte im Terminal:\n${manual_command}"
    return 1
}

if [[ "$MODE" == "--check" ]]; then
    printf '%s\n' "${missing_packages[@]}"
    exit 10
fi

if [[ "$PACKAGE_FAMILY" == "unknown" || -z "$PACKAGE_MANAGER" || ${#missing_packages[@]} -eq 0 ]]; then
    show_error "Die Distribution wurde nicht eindeutig erkannt.\n\nFehlende Komponenten:\n${label_list}\n\nSiehe INSTALL.md für die manuelle Installation."
    exit 2
fi

if [[ "$MODE" == "--check-and-install" || "$MODE" == "--check-gui-and-install" ]]; then
    if ! ask_confirmation; then
        echo "Installation abgebrochen."
        exit 20
    fi
elif [[ "$MODE" != "--install" ]]; then
    echo "Unbekannter Modus: $MODE" >&2
    exit 64
fi

declare -a install_command=()
case "$PACKAGE_FAMILY" in
    dnf) install_command=("$PACKAGE_MANAGER" install -y "${missing_packages[@]}") ;;
    apt) install_command=("$PACKAGE_MANAGER" install -y "${missing_packages[@]}") ;;
    pacman) install_command=("$PACKAGE_MANAGER" -S --needed --noconfirm "${missing_packages[@]}") ;;
    zypper) install_command=("$PACKAGE_MANAGER" --non-interactive install "${missing_packages[@]}") ;;
esac

if [[ $EUID -eq 0 ]]; then
    "${install_command[@]}"
elif [[ -n "$PKEXEC_BIN" ]]; then
    "$PKEXEC_BIN" "${install_command[@]}"
elif command -v sudo >/dev/null 2>&1 && [[ -t 0 ]]; then
    sudo "${install_command[@]}"
else
    show_error "Für die Administratorabfrage wurde weder pkexec noch ein interaktives sudo gefunden.\n\nInstalliere manuell:\n${manual_command}"
    exit 3
fi

remaining=()
if [[ "$MODE" != "--check-gui-and-install" ]]; then
    command -v liquidctl >/dev/null 2>&1 || remaining+=("liquidctl")
fi
python3 -c 'import PySide6' >/dev/null 2>&1 || remaining+=("PySide6")
python3 -c 'from PySide6.QtGui import QImageReader; assert any(bytes(x).lower() == b"svg" for x in QImageReader.supportedImageFormats())' >/dev/null 2>&1 || remaining+=("Qt SVG")
if [[ "$MODE" != "--check-gui-and-install" ]]; then
    python3 -c 'from PIL import Image' >/dev/null 2>&1 || remaining+=("Pillow")
fi

if (( ${#remaining[@]} > 0 )); then
    echo "Nach der Installation weiterhin nicht erkannt: ${remaining[*]}" >&2
    echo "Prüfe die distributionsspezifischen Hinweise in INSTALL.md." >&2
    exit 4
fi

echo "Alle benötigten Abhängigkeiten wurden installiert."

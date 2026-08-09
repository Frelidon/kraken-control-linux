#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

MODE="${1:---check-and-install}"
DNF_BIN="$(command -v dnf || true)"
PKEXEC_BIN="$(command -v pkexec || true)"

missing_packages=()
missing_labels=()

add_missing() {
    local package="$1"
    local label="$2"
    missing_packages+=("$package")
    missing_labels+=("$label")
}

command -v liquidctl >/dev/null 2>&1 || add_missing "liquidctl" "liquidctl"
python3 -c 'import PySide6' >/dev/null 2>&1 || add_missing "python3-pyside6" "PySide6 / Qt for Python"
python3 -c 'from PIL import Image' >/dev/null 2>&1 || add_missing "python3-pillow" "Pillow"

if (( ${#missing_packages[@]} == 0 )); then
    echo "Alle benötigten Abhängigkeiten sind installiert."
    exit 0
fi

package_list="${missing_packages[*]}"
label_list="$(printf '%s\n' "${missing_labels[@]}" | sed 's/^/• /')"
manual_command="sudo dnf install ${package_list}"

show_error() {
    local message="$1"
    if command -v kdialog >/dev/null 2>&1; then
        kdialog --title "Kraken Control by Frelidon" --error "$message" || true
    elif command -v zenity >/dev/null 2>&1; then
        zenity --error --title="Kraken Control by Frelidon" --text="$message" || true
    else
        printf '%s\n' "$message" >&2
    fi
}

ask_confirmation() {
    local message="Kraken Control benötigt folgende Pakete:\n\n${label_list}\n\nSie werden ausschließlich aus den bereits eingerichteten DNF-Paketquellen installiert. Es werden keine fremden Paketquellen hinzugefügt.\n\nFortfahren?"
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

if [[ -z "$DNF_BIN" ]]; then
    show_error "Die automatische Installation unterstützt derzeit Nobara/Fedora mit DNF.\n\nFehlende Pakete:\n${label_list}"
    exit 2
fi

if [[ "$MODE" == "--check-and-install" ]]; then
    if ! ask_confirmation; then
        echo "Installation abgebrochen."
        exit 20
    fi
elif [[ "$MODE" != "--install" ]]; then
    echo "Unbekannter Modus: $MODE" >&2
    exit 64
fi

if [[ $EUID -eq 0 ]]; then
    "$DNF_BIN" install -y "${missing_packages[@]}"
elif [[ -n "$PKEXEC_BIN" ]]; then
    "$PKEXEC_BIN" "$DNF_BIN" install -y "${missing_packages[@]}"
elif command -v sudo >/dev/null 2>&1 && [[ -t 0 ]]; then
    sudo "$DNF_BIN" install "${missing_packages[@]}"
else
    show_error "Für die Administratorabfrage wurde pkexec nicht gefunden.\n\nInstalliere manuell:\n${manual_command}"
    exit 3
fi

remaining=()
command -v liquidctl >/dev/null 2>&1 || remaining+=("liquidctl")
python3 -c 'import PySide6' >/dev/null 2>&1 || remaining+=("python3-pyside6")
python3 -c 'from PIL import Image' >/dev/null 2>&1 || remaining+=("python3-pillow")

if (( ${#remaining[@]} > 0 )); then
    echo "Nach der Installation weiterhin nicht erkannt: ${remaining[*]}" >&2
    exit 4
fi

echo "Alle benötigten Abhängigkeiten wurden installiert."

#!/usr/bin/env bash
set -euo pipefail
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
RULE_SOURCE="$SOURCE_DIR/71-nzxt-kraken-2023.rules"
RULE_TARGET="/etc/udev/rules.d/71-nzxt-kraken-2023.rules"

run_root() {
    if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
        "$@"
    else
        sudo "$@"
    fi
}

run_root install -m 0644 "$RULE_SOURCE" "$RULE_TARGET"
run_root udevadm control --reload-rules
run_root udevadm trigger --action=add --subsystem-match=usb || true
run_root udevadm trigger --action=add --subsystem-match=hidraw || true
run_root udevadm trigger --action=change --subsystem-match=hidraw || true
run_root udevadm settle

echo "udev-Regel installiert und USB/HID-Regeln neu ausgelöst."
echo "Teste nun: liquidctl --match 'NZXT Kraken 2023' status"
echo "Falls Schreibzugriffe noch fehlschlagen: Kraken kurz neu verbinden oder das System neu starten."

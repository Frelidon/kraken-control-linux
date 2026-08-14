#!/usr/bin/env bash
set -u

OUT="${1:-$PWD/open-hardware-control-diagnostics-$(date +%Y%m%d-%H%M%S).txt}"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

{
  echo "Open Hardware Control by Frelidon diagnostics"
  echo "Version: 3.0.9"
  echo "Generated: $(date --iso-8601=seconds 2>/dev/null || date)"
  echo "Mode: diagnostics are read-only (application controls require explicit session approval)"
  echo
  echo "== System =="
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "Operating system: ${PRETTY_NAME:-unknown}"
  fi
  echo "Kernel: $(uname -s) $(uname -r)"
  echo "Architecture: $(uname -m)"
  echo "Desktop: ${XDG_CURRENT_DESKTOP:-unknown}"
  echo "Session type: ${XDG_SESSION_TYPE:-unknown}"
  echo
  echo "== Software =="
  python3 --version 2>&1
  liquidctl --version 2>&1 || true
  echo
  echo "== liquidctl devices (read-only) =="
  liquidctl list --verbose 2>&1 || true
  echo
  echo "== liquidctl status (read-only) =="
  liquidctl status 2>&1 || true
  echo
  echo "== NZXT USB devices =="
  lsusb 2>&1 | grep -i -E '1e71|NZXT' || true
  echo
  echo "== Relevant hidraw permissions =="
  for dev in /dev/hidraw*; do
    [ -e "$dev" ] || continue
    props="$(udevadm info -q property -n "$dev" 2>/dev/null || true)"
    if grep -qi -E 'ID_VENDOR_ID=1e71|NZXT' <<<"$props"; then
      stat -c '%A %U %G %n' "$dev" 2>/dev/null || true
      printf '%s\n' "$props" | grep -E '^(ID_VENDOR|ID_MODEL|ID_VENDOR_ID|ID_MODEL_ID)=' || true
    fi
  done
  echo
  echo "== udev rule =="
  cat /etc/udev/rules.d/71-nzxt-kraken-2023.rules 2>&1 || true
  echo
  echo "== OpenLinkHub local status (read-only, serial suffix only) =="
  python3 "$SOURCE_DIR/openlinkhub_integration.py" --status 2>&1 || true
} > "$TMP" 2>&1

# Defense in depth: remove common personal and device identifiers even when a
# future liquidctl/udev version adds them to otherwise harmless output.
sed -E \
  -e 's/(Serial number:).*/\1 [REDACTED]/I' \
  -e 's/(ID_SERIAL(_SHORT)?=).*/\1[REDACTED]/I' \
  -e 's/(serial=)[^ ]+/\1[REDACTED]/Ig' \
  -e 's#(/home/)[^/[:space:]]+#\1[USER]#g' \
  -e 's#(/run/user/)[0-9]+#\1[UID]#g' \
  -e 's/(Machine ID|Boot ID|machine-id|boot-id)([=: ]+)[0-9a-f-]+/\1\2[REDACTED]/Ig' \
  -e 's/(Hostname|Static hostname)([=: ]+).*/\1\2[REDACTED]/Ig' \
  -e 's/(USER|USERNAME|LOGNAME)=.*/\1=[REDACTED]/g' \
  "$TMP" > "$OUT"
chmod 0600 "$OUT"
echo "Anonymisierter, rein lesender Diagnosebericht erstellt: $OUT"
echo "Bitte den Bericht vor dem Teilen trotzdem kurz kontrollieren."

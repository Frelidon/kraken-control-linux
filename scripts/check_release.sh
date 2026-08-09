#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TMP_PYCACHE="$(mktemp -d)"
trap 'rm -rf "$TMP_PYCACHE"' EXIT

PYTHONPYCACHEPREFIX="$TMP_PYCACHE" python3 -m py_compile kraken_control.py
bash -n install.sh install-dependencies.sh install-udev-rule.sh collect-diagnostics.sh uninstall.sh scripts/*.sh
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_security_static.py
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_runtime_logic_stub.py

VERSION="$(tr -d '\r\n' < VERSION)"
if [[ "$VERSION" != "2.9.6" ]]; then
  echo "Unexpected VERSION: $VERSION" >&2
  exit 1
fi
if ! grep -q 'APP_VERSION = "2.9.6"' kraken_control.py; then
  echo "APP_VERSION does not match VERSION." >&2
  exit 1
fi

# Public-repository hygiene checks.
if grep -RInE \
  --exclude-dir=.git --exclude-dir=dist --exclude-dir=__pycache__ \
  --exclude='*.gz' --exclude='*.zip' --exclude='*.png' --exclude='*.jpg' --exclude='*.jpeg' \
  '(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})' .; then
  echo "Potential secret detected." >&2
  exit 1
fi

if grep -RInE \
  --exclude-dir=.git --exclude-dir=dist --exclude-dir=__pycache__ \
  --exclude='*.gz' --exclude='*.zip' \
  '/home/[A-Za-z0-9._-]+' . | grep -vE '\[USER\]|exampleuser|collect-diagnostics\.sh|kraken_control\.py'; then
  echo "Potential personal home path detected." >&2
  exit 1
fi

if find . -type d -name __pycache__ -print -quit | grep -q .; then
  echo "Remove __pycache__ before release." >&2
  exit 1
fi

for required in LICENSE README.md README.en.md CHANGELOG.md SECURITY.md PRIVACY.md CONTRIBUTING.md VERSION; do
  [[ -f "$required" ]] || { echo "Missing required file: $required" >&2; exit 1; }
done

if [[ "$(tail -n 1 README.md)" != "Offizielle Kraken-Spezifikationen: <https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs>" ]]; then
  echo "README.md must keep the supported-device section at the end." >&2
  exit 1
fi

echo "All repository release checks passed."

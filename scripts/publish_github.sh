#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_NAME="${1:-kraken-control-linux}"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
cd "$ROOT"

for cmd in git gh python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing command: $cmd" >&2
    echo "On Nobara/Fedora: sudo dnf install git gh python3" >&2
    exit 1
  fi
done

if ! gh auth status >/dev/null 2>&1; then
  echo "Sign in first with: gh auth login --web" >&2
  exit 1
fi

if ! git config user.name >/dev/null 2>&1 || ! git config user.email >/dev/null 2>&1; then
  echo "Git identity is not configured." >&2
  echo 'Example: git config --global user.name "Frelidon"' >&2
  echo 'Then set a GitHub email or GitHub noreply address with git config --global user.email "..."' >&2
  exit 1
fi

OWNER="$(gh api user --jq .login)"
URL="https://github.com/$OWNER/$REPO_NAME"

if gh repo view "$OWNER/$REPO_NAME" >/dev/null 2>&1; then
  echo "Repository already exists: $URL" >&2
  echo "This script intentionally refuses to overwrite an existing repository." >&2
  exit 1
fi

printf 'Create PUBLIC repository %s from this folder? [y/N] ' "$URL"
read -r answer
case "$answer" in
  y|Y|yes|YES|j|J|ja|JA) ;;
  *) echo "Cancelled."; exit 0 ;;
esac

python3 scripts/configure_repository.py "$URL"
./scripts/check_release.sh

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .
if git diff --cached --quiet; then
  echo "Nothing to commit." >&2
  exit 1
fi
git commit -m "Initial public release v$VERSION"

gh repo create "$REPO_NAME" \
  --public \
  --source=. \
  --remote=origin \
  --push \
  --description "Independent open-source Linux control app for supported NZXT Kraken 2023 hardware"

gh repo edit "$OWNER/$REPO_NAME" --enable-issues=true --enable-wiki=false >/dev/null || true

for topic in linux nzxt kraken liquidctl cooling pyside6 qt nobara fedora open-source; do
  gh repo edit "$OWNER/$REPO_NAME" --add-topic "$topic" >/dev/null || true
done

for spec in \
  "bug|d73a4a|Reproducible bug" \
  "enhancement|a2eeef|Feature or improvement" \
  "hardware|5319e7|Hardware compatibility" \
  "needs-testing|fbca04|Needs real hardware testing" \
  "documentation|0075ca|Documentation" \
  "dependencies|0366d6|Dependency update"; do
  IFS='|' read -r label color description <<<"$spec"
  gh label create "$label" --color "$color" --description "$description" --force >/dev/null || true
done

echo
echo "Repository published: $URL"
echo "Wait for the CI workflow to finish successfully before creating v$VERSION."
echo "Then run: ./scripts/create_release.sh"

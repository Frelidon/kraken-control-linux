#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
TAG="${1:-v$VERSION}"
cd "$ROOT"

if ! command -v gh >/dev/null 2>&1 || ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is missing or not authenticated. Run: gh auth login --web" >&2
  exit 1
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  echo "No GitHub origin remote found. Publish the repository first." >&2
  exit 1
fi
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree is not clean. Commit or discard changes first." >&2
  exit 1
fi
if [[ "$TAG" != "v$VERSION" ]]; then
  echo "Tag $TAG does not match VERSION $VERSION." >&2
  exit 1
fi
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Tag already exists locally: $TAG" >&2
  exit 1
fi

./scripts/check_release.sh
./scripts/build_release.sh "$VERSION"

printf 'Create and push tag %s? This will trigger the public GitHub Release workflow. [y/N] ' "$TAG"
read -r answer
case "$answer" in
  y|Y|yes|YES|j|J|ja|JA) ;;
  *) echo "Cancelled."; exit 0 ;;
esac

git tag -a "$TAG" -m "Kraken Control $TAG"
git push origin "$TAG"

echo "Tag pushed: $TAG"
echo "GitHub Actions will validate the source, build the assets and create the release."
echo "Open the workflow/release page with: gh release view '$TAG' --web"

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
requested = sys.argv[1] if len(sys.argv) > 1 else VERSION
if requested != VERSION:
    raise SystemExit(f"Requested version {requested!r} does not match VERSION {VERSION!r}")
if not all(part.isdigit() for part in VERSION.split(".")) or len(VERSION.split(".")) != 3:
    raise SystemExit("VERSION must be x.y.z")

DIST = ROOT / "dist"
if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

EXCLUDED_DIRS = {".git", ".github", "dist", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv"}
EXCLUDED_FILES = {"MANIFEST.sha256"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def should_copy(rel: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if rel.name in EXCLUDED_FILES:
        return False
    if rel.suffix in EXCLUDED_SUFFIXES:
        return False
    return True


def copy_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if not should_copy(rel):
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


with tempfile.TemporaryDirectory(prefix="kraken-control-release-") as temp_dir:
    temp = Path(temp_dir)
    pkg_name = f"kraken_control_v{VERSION.replace('.', '_')}"
    pkg = temp / pkg_name
    pkg.mkdir()
    copy_tree(ROOT, pkg)

    # A compact source snapshot is built before adding itself to the package.
    internal_snapshot = temp / f"kraken_control_source_{VERSION.replace('.', '_')}.tar.gz"
    with tarfile.open(internal_snapshot, "w:gz") as tf:
        tf.add(pkg, arcname=pkg_name)

    external_snapshot = DIST / f"Kraken-Control-Source-v{VERSION}.tar.gz"
    shutil.copy2(internal_snapshot, external_snapshot)
    shutil.copy2(internal_snapshot, pkg / internal_snapshot.name)

    manifest_lines = []
    for path in sorted(p for p in pkg.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256"):
        rel = path.relative_to(pkg).as_posix()
        manifest_lines.append(f"{sha256(path)}  ./{rel}")
    (pkg / "MANIFEST.sha256").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    release_zip = DIST / f"Kraken-Control-by-Frelidon-{VERSION}-linux.zip"
    with zipfile.ZipFile(release_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in pkg.rglob("*") if p.is_file()):
            arcname = (Path(pkg_name) / path.relative_to(pkg)).as_posix()
            info = zipfile.ZipInfo.from_file(path, arcname=arcname)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as fh:
                zf.writestr(info, fh.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

checks = []
for path in sorted(DIST.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS":
        checks.append(f"{sha256(path)}  {path.name}")
(DIST / "SHA256SUMS").write_text("\n".join(checks) + "\n", encoding="utf-8")
print("Built release assets:")
for path in sorted(DIST.iterdir()):
    print(f"  {path.name}")

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
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
if len(VERSION.split(".")) != 3 or not all(part.isdigit() for part in VERSION.split(".")):
    raise SystemExit("VERSION must be x.y.z")

DIST = ROOT / "dist"
if DIST.exists():
    shutil.rmtree(DIST)
DIST.mkdir()

EXCLUDED_DIRS = {
    ".git", "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".venv", "venv",
}
EXCLUDED_FILES = {"MANIFEST.sha256", "SHA256SUMS"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}

RUNTIME_FILES = {
    "71-nzxt-kraken-2023.rules",
    "collect-diagnostics.sh",
    "install-dependencies.sh",
    "install-udev-rule.sh",
    "install.sh",
    "kraken-control.desktop.in",
    "kraken-control.svg",
    "kraken_cam_streamer.py",
    "kraken_control.py",
    "kraken_lcd_designs.py",
    "kraken_sensors.py",
    "LICENSE",
    "openlinkhub_integration.py",
    "openlinkhub_mouse_visuals.py",
    "uninstall.sh",
    "VERSION",
}


def should_copy(rel: Path, *, developer: bool) -> bool:
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return False
    if rel.name in EXCLUDED_FILES or rel.suffix in EXCLUDED_SUFFIXES:
        return False
    if developer:
        return True
    if len(rel.parts) == 1 and (rel.name in RUNTIME_FILES or rel.suffix == ".md"):
        return True
    return rel.parts[0] in {"assets", "test-gifs", "docs"}


def copy_tree(src: Path, dst: Path, *, developer: bool) -> None:
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if not should_copy(rel, developer=developer):
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "MANIFEST.sha256"):
        lines.append(f"{sha256(path)}  ./{path.relative_to(root).as_posix()}")
    (root / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_zip(source: Path, output: Path, archive_root: str) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            name = (Path(archive_root) / path.relative_to(source)).as_posix()
            info = zipfile.ZipInfo.from_file(path, arcname=name)
            info.compress_type = zipfile.ZIP_DEFLATED
            with path.open("rb") as stream:
                archive.writestr(info, stream.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def install_runtime_tree(package_root: Path) -> None:
    app_dir = package_root / "usr/share/open-hardware-control"
    app_dir.mkdir(parents=True)
    for name in sorted(RUNTIME_FILES - {"install.sh", "uninstall.sh", "kraken-control.desktop.in"}):
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, app_dir / name)
    for name in ("assets",):
        shutil.copytree(ROOT / name, app_dir / name)
    for source in sorted(ROOT.glob("*.md")):
        shutil.copy2(source, app_dir / source.name)

    bin_dir = package_root / "usr/bin"
    bin_dir.mkdir(parents=True)
    launcher = bin_dir / "open-hardware-control"
    launcher.write_text(
        "#!/usr/bin/env bash\nexec python3 /usr/share/open-hardware-control/kraken_control.py \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    compatibility = bin_dir / "kraken-control"
    compatibility.write_text("#!/usr/bin/env bash\nexec /usr/bin/open-hardware-control \"$@\"\n", encoding="utf-8")
    compatibility.chmod(0o755)
    diagnostics = bin_dir / "open-hardware-control-diagnostics"
    diagnostics.write_text(
        "#!/usr/bin/env bash\nexec /usr/share/open-hardware-control/collect-diagnostics.sh \"$@\"\n",
        encoding="utf-8",
    )
    diagnostics.chmod(0o755)

    desktop_dir = package_root / "usr/share/applications"
    desktop_dir.mkdir(parents=True)
    desktop = (ROOT / "kraken-control.desktop.in").read_text(encoding="utf-8")
    desktop = desktop.replace("@EXEC@", "/usr/bin/open-hardware-control")
    desktop = desktop.replace("@ICON@", "open-hardware-control")
    (desktop_dir / "open-hardware-control.desktop").write_text(desktop, encoding="utf-8")

    icon_dir = package_root / "usr/share/icons/hicolor/scalable/apps"
    icon_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "kraken-control.svg", icon_dir / "open-hardware-control.svg")

    rules_dir = package_root / "usr/lib/udev/rules.d"
    rules_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "71-nzxt-kraken-2023.rules", rules_dir)


def build_deb(temp: Path) -> Path:
    if not shutil.which("dpkg-deb"):
        raise SystemExit("dpkg-deb is required to build the Debian package")
    root = temp / "deb-root"
    install_runtime_tree(root)
    control_dir = root / "DEBIAN"
    control_dir.mkdir()
    (control_dir / "control").write_text(
        "\n".join(
            [
                "Package: open-hardware-control",
                f"Version: {VERSION}",
                "Section: utils",
                "Priority: optional",
                "Architecture: all",
                "Maintainer: Frelidon <noreply@github.com>",
                "Depends: python3, liquidctl, python3-pil, python3-pyside6.qtwidgets, python3-pyside6.qtsvg, policykit-1",
                "Homepage: https://github.com/Frelidon/kraken-control-linux",
                "Description: NZXT Kraken and Corsair/OpenLinkHub control for Linux",
                " Open-source Linux GUI for Kraken LCD, pump, fan and RGB control",
                " with an allow-listed local OpenLinkHub integration for Corsair devices.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    output = DIST / f"open-hardware-control_{VERSION}_all.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", str(root), str(output)], check=True)
    return output


def build_rpm(temp: Path) -> Path:
    if not shutil.which("rpmbuild"):
        raise SystemExit("rpmbuild is required to build the Fedora RPM")
    top = temp / "rpmbuild"
    for name in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
        (top / name).mkdir(parents=True)

    payload = temp / f"open-hardware-control-{VERSION}"
    payload.mkdir()
    install_runtime_tree(payload)
    source = top / "SOURCES" / f"open-hardware-control-{VERSION}.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        archive.add(payload, arcname=payload.name)

    spec = top / "SPECS" / "open-hardware-control.spec"
    spec.write_text(
        f"""Name:           open-hardware-control
Version:        {VERSION}
Release:        1%{{?dist}}
Summary:        NZXT Kraken and Corsair/OpenLinkHub control for Linux
License:        GPL-3.0-or-later
URL:            https://github.com/Frelidon/kraken-control-linux
Source0:        %{{name}}-%{{version}}.tar.gz
BuildArch:      noarch
Requires:       python3
Requires:       liquidctl
Requires:       python3-pyside6
Requires:       python3-pillow
Requires:       qt6-qtsvg
Requires:       polkit

%description
Open-source Linux GUI for NZXT Kraken LCD, pump, fan and RGB control with
an allow-listed local OpenLinkHub integration for Corsair devices.

%prep
%setup -q

%build

%install
mkdir -p %{{buildroot}}
cp -a usr %{{buildroot}}/

%files
/usr/bin/open-hardware-control
/usr/bin/open-hardware-control-diagnostics
/usr/bin/kraken-control
/usr/share/open-hardware-control
/usr/share/applications/open-hardware-control.desktop
/usr/share/icons/hicolor/scalable/apps/open-hardware-control.svg
/usr/lib/udev/rules.d/71-nzxt-kraken-2023.rules

%changelog
* Fri Aug 14 2026 Frelidon <noreply@github.com> - {VERSION}-1
- Open Hardware Control {VERSION}
""",
        encoding="utf-8",
    )
    subprocess.run(["rpmbuild", "-bb", "--define", f"_topdir {top}", str(spec)], check=True)
    built = next((top / "RPMS").rglob("*.rpm"))
    output = DIST / f"open-hardware-control-{VERSION}-1.noarch.rpm"
    shutil.copy2(built, output)
    return output


with tempfile.TemporaryDirectory(prefix="open-hardware-control-release-") as temp_name:
    temp = Path(temp_name)

    runtime_name = f"open-hardware-control-{VERSION}"
    runtime = temp / runtime_name
    runtime.mkdir()
    copy_tree(ROOT, runtime, developer=False)
    write_manifest(runtime)
    write_zip(runtime, DIST / f"open_hardware_control_v{VERSION.replace('.', '_')}.zip", runtime_name)

    developer_name = f"Entwicklerpaket {VERSION}"
    developer = temp / developer_name
    developer.mkdir()
    copy_tree(ROOT, developer, developer=True)
    write_manifest(developer)
    write_zip(developer, DIST / f"{developer_name}.zip", developer_name)

    source_name = f"open-hardware-control-{VERSION}-source"
    source_root = temp / source_name
    source_root.mkdir()
    copy_tree(ROOT, source_root, developer=True)
    write_manifest(source_root)
    with tarfile.open(DIST / f"{source_name}.tar.gz", "w:gz") as archive:
        archive.add(source_root, arcname=source_name)

    build_deb(temp)
    if os.environ.get("OHC_SKIP_RPM") == "1":
        print("Skipping RPM build because OHC_SKIP_RPM=1")
    else:
        build_rpm(temp)

checks = []
for path in sorted(DIST.iterdir()):
    if path.is_file() and path.name != "SHA256SUMS":
        checks.append(f"{sha256(path)}  {path.name}")
(DIST / "SHA256SUMS").write_text("\n".join(checks) + "\n", encoding="utf-8")

print("Built release assets:")
for path in sorted(DIST.iterdir()):
    print(f"  {path.name}")

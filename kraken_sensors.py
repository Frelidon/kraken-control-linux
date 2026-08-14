#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only Linux temperature sensors shared by the GUI and LCD streamer."""

from __future__ import annotations

from pathlib import Path


def read_amd_cpu_temperature(
    hwmon_root: Path = Path("/sys/class/hwmon"),
) -> tuple[float | None, str]:
    """Read k10temp, preferring Tctl and then Tdie."""
    for hwmon in sorted(hwmon_root.glob("hwmon*")):
        try:
            if (hwmon / "name").read_text(encoding="ascii").strip() != "k10temp":
                continue
            candidates: list[tuple[int, Path, str]] = []
            for input_file in hwmon.glob("temp*_input"):
                label_file = input_file.with_name(input_file.name.replace("_input", "_label"))
                label = (
                    label_file.read_text(encoding="utf-8").strip()
                    if label_file.exists()
                    else input_file.stem
                )
                priority = 0 if label == "Tctl" else 1 if label == "Tdie" else 2
                candidates.append((priority, input_file, label))
            for _priority, input_file, label in sorted(candidates):
                value = float(input_file.read_text(encoding="ascii").strip()) / 1000.0
                if 0.0 < value < 125.0:
                    return value, label
        except (OSError, ValueError):
            continue
    return None, "k10temp nicht gefunden"


def read_amd_gpu_temperature(
    drm_root: Path = Path("/sys/class/drm"),
) -> tuple[float | None, str]:
    """Read amdgpu temperature, preferring the card with the most VRAM.

    AM5 systems can expose both an integrated GPU and a dedicated Radeon.
    Selecting by ``mem_info_vram_total`` keeps the LCD focused on the dGPU
    without depending on unstable card numbers.
    """
    cards: list[tuple[int, int, float, str]] = []
    for card in sorted(drm_root.glob("card[0-9]*")):
        device = card / "device"
        try:
            vendor_file = device / "vendor"
            if (
                vendor_file.exists()
                and vendor_file.read_text(encoding="ascii").strip().lower() != "0x1002"
            ):
                continue
            vram_file = device / "mem_info_vram_total"
            vram = int(vram_file.read_text(encoding="ascii").strip()) if vram_file.exists() else 0
            for hwmon in sorted((device / "hwmon").glob("hwmon*")):
                name_file = hwmon / "name"
                if name_file.exists() and name_file.read_text(encoding="ascii").strip() != "amdgpu":
                    continue
                for input_file in sorted(hwmon.glob("temp*_input")):
                    label_file = input_file.with_name(input_file.name.replace("_input", "_label"))
                    label = (
                        label_file.read_text(encoding="utf-8").strip()
                        if label_file.exists()
                        else input_file.stem
                    )
                    priority = {"edge": 0, "junction": 1, "gpu": 2}.get(label.lower(), 3)
                    value = float(input_file.read_text(encoding="ascii").strip()) / 1000.0
                    if 0.0 < value < 130.0:
                        cards.append((vram, -priority, value, f"amdgpu {card.name} · {label}"))
        except (OSError, ValueError):
            continue
    if not cards:
        return None, "amdgpu nicht gefunden"
    _vram, _priority, value, label = max(cards, key=lambda item: (item[0], item[1]))
    return value, label

#!/usr/bin/env python3
"""Dependency-free checks for shared read-only AMD hwmon sensors."""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kraken_sensors import read_amd_cpu_temperature, read_amd_gpu_temperature  # noqa: E402


with tempfile.TemporaryDirectory(prefix="kraken-sensors-") as td:
    root = Path(td)
    hwmon_root = root / "hwmon"
    k10 = hwmon_root / "hwmon0"
    k10.mkdir(parents=True)
    (k10 / "name").write_text("k10temp\n", encoding="ascii")
    (k10 / "temp1_input").write_text("63125\n", encoding="ascii")
    (k10 / "temp1_label").write_text("Tctl\n", encoding="ascii")
    (k10 / "temp2_input").write_text("59250\n", encoding="ascii")
    (k10 / "temp2_label").write_text("Tdie\n", encoding="ascii")
    cpu, cpu_label = read_amd_cpu_temperature(hwmon_root)
    assert cpu == 63.125 and cpu_label == "Tctl"

    drm_root = root / "drm"
    for card_number, vram, temperature in ((0, 512 * 1024**2, 48_000), (1, 16 * 1024**3, 62_000)):
        device = drm_root / f"card{card_number}" / "device"
        hwmon = device / "hwmon" / "hwmon0"
        hwmon.mkdir(parents=True)
        (device / "vendor").write_text("0x1002\n", encoding="ascii")
        (device / "mem_info_vram_total").write_text(f"{vram}\n", encoding="ascii")
        (hwmon / "name").write_text("amdgpu\n", encoding="ascii")
        (hwmon / "temp1_input").write_text(f"{temperature}\n", encoding="ascii")
        (hwmon / "temp1_label").write_text("edge\n", encoding="ascii")
    gpu, gpu_label = read_amd_gpu_temperature(drm_root)
    assert gpu == 62.0 and "card1" in gpu_label

print("Shared k10temp and dedicated-amdgpu sensor selection passed.")

#!/usr/bin/env python3
"""Pure renderer, color, localization and AMD-GPU sensor checks."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kraken_lcd_designs import COLOR_PRESETS, DEFAULT_ACCENT, DESIGNS, LABELS, normalize_hex_color, render_hardware_animation, render_hardware_design, render_hardware_frame  # noqa: E402


assert normalize_hex_color("#00C8FF") == "#00c8ff"
assert normalize_hex_color("39ff88") == "#39ff88"
assert normalize_hex_color("#12345") is None
assert normalize_hex_color("#purple") is None
assert DEFAULT_ACCENT == "#00c8ff"
assert COLOR_PRESETS[0] == ("Eisblau", DEFAULT_ACCENT)
assert DEFAULT_ACCENT != "#a855f7"
assert set(LABELS) == {"de", "en", "es", "fr"}

output_dir = Path(tempfile.mkdtemp(prefix="kraken-lcd-design-test-"))
digests: set[bytes] = set()
for language in LABELS:
    for design_id, _label in DESIGNS:
        output = render_hardware_design(
            design_id,
            DEFAULT_ACCENT,
            31.8,
            62.4,
            55.9,
            output_dir / f"{language}-{design_id}.png",
            language=language,
        )
        with Image.open(output) as image:
            assert image.size == (240, 240)
            assert image.mode == "RGB"
            digests.add(image.tobytes())

for fps in (20, 25):
    for design_id, _label in DESIGNS:
        animation = render_hardware_animation(
            design_id,
            DEFAULT_ACCENT,
            31.8,
            62.4,
            55.9,
            output_dir / f"animated-{design_id}-{fps}fps.gif",
            language="de",
            font_scale_percent=135,
            fps=fps,
        )
        with Image.open(animation) as image:
            assert image.size == (240, 240)
            assert image.n_frames == fps
            assert image.info.get("loop") == 0
            assert image.info.get("duration") == round(1000 / fps)
            image.seek(0)
            first_frame = image.convert("RGB").tobytes()
            image.seek(fps // 2)
            assert image.convert("RGB").tobytes() != first_frame

assert len(digests) >= len(DESIGNS)

snapshot = render_hardware_frame("system_trio", DEFAULT_ACCENT, 31.8, 62.4, 55.9)
live = render_hardware_frame(
    "system_trio",
    DEFAULT_ACCENT,
    31.8,
    62.4,
    55.9,
    live_sensor_status=True,
)
assert snapshot.tobytes() == live.tobytes()

fahrenheit = render_hardware_frame(
    "system_trio",
    DEFAULT_ACCENT,
    31.8,
    62.4,
    55.9,
    temperature_unit="f",
    label_color_hex="#39ff88",
    value_color_hex="#ff9a32",
    label_scale_percent=90,
    value_scale_percent=155,
)
assert fahrenheit.tobytes() != snapshot.tobytes()

print("Five clean static/animated LCD designs, split text controls, Fahrenheit and four renderer languages passed.")

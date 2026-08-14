#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rounded 240 x 240 hardware dashboards for Kraken Control.

The renderer is intentionally independent from Qt and liquidctl.  This keeps
preview generation deterministic and allows every layout to be tested without
connected hardware.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


LCD_SIZE = 240
DEFAULT_ACCENT = "#00c8ff"
DEFAULT_LABEL_COLOR = "#8ba2b5"
DEFAULT_VALUE_COLOR = "#f2f8fc"

COLOR_PRESETS: tuple[tuple[str, str], ...] = (
    ("Eisblau", DEFAULT_ACCENT),
    ("Neongrün", "#39ff88"),
    ("Orange", "#ff9a32"),
    ("Rot", "#ff4058"),
    ("Gold", "#ffd54a"),
    ("Weiß", "#f4f7ff"),
    ("Lila", "#a855f7"),
)

DESIGNS: tuple[tuple[str, str], ...] = (
    ("water_halo", "Wasser · Halo"),
    ("cpu_orbit", "CPU · Orbit"),
    ("gpu_arc", "GPU · Arc"),
    ("cpu_gpu_dual", "CPU + GPU · Dual"),
    ("system_trio", "Wasser + CPU + GPU · Trio"),
)

LABELS: dict[str, dict[str, str]] = {
    "de": {"water": "WASSER", "cpu": "CPU", "gpu": "GPU", "system": "SYSTEM", "live": "LIVE", "last": "LETZTER WERT"},
    "en": {"water": "LIQUID", "cpu": "CPU", "gpu": "GPU", "system": "SYSTEM", "live": "LIVE", "last": "LAST VALUE"},
    "es": {"water": "LÍQUIDO", "cpu": "CPU", "gpu": "GPU", "system": "SISTEMA", "live": "EN VIVO", "last": "ÚLTIMO VALOR"},
    "fr": {"water": "LIQUIDE", "cpu": "CPU", "gpu": "GPU", "system": "SYSTÈME", "live": "DIRECT", "last": "DERNIÈRE VALEUR"},
}


def normalize_hex_color(value: str) -> str | None:
    """Return a canonical #rrggbb color or None for invalid input."""
    text = value.strip().lower()
    if text and not text.startswith("#"):
        text = "#" + text
    if len(text) != 7:
        return None
    try:
        int(text[1:], 16)
    except ValueError:
        return None
    return text


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/usr/share/fonts/google-noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def _rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _mix(color: tuple[int, int, int], other: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(a + (b - a) * amount) for a, b in zip(color, other))


def _temperature(value: float | None, unit: str = "c") -> str:
    normalized = "f" if str(unit).casefold() == "f" else "c"
    suffix = "°F" if normalized == "f" else "°C"
    if value is None:
        return f"--{suffix}"
    displayed = value * 9.0 / 5.0 + 32.0 if normalized == "f" else value
    return f"{displayed:.0f}{suffix}"


class _Canvas:
    """A 2x supersampled drawing canvas with logical 240 px coordinates."""

    scale = 2

    def __init__(
        self,
        accent: str,
        label_color: str = DEFAULT_LABEL_COLOR,
        value_color: str = DEFAULT_VALUE_COLOR,
        label_scale_percent: int = 125,
        value_scale_percent: int = 125,
        temperature_unit: str = "c",
        phase: float = 0.0,
    ):
        self.accent = _rgb(accent)
        self.label_color = _rgb(label_color)
        self.value_color = _rgb(value_color)
        self.label_scale = max(0.60, min(2.00, label_scale_percent / 100.0))
        self.value_scale = max(0.60, min(2.00, value_scale_percent / 100.0))
        self.temperature_unit = "f" if str(temperature_unit).casefold() == "f" else "c"
        self.phase = phase % 1.0
        self.background = (7, 13, 21)
        self.panel = (14, 25, 37)
        self.muted = (118, 139, 157)
        self.white = (242, 248, 252)
        self.image = Image.new("RGB", (LCD_SIZE * self.scale, LCD_SIZE * self.scale), self.background)
        self.draw = ImageDraw.Draw(self.image)
        self.draw.ellipse(self.box(4, 4, 236, 236), fill=(8, 15, 24), outline=_mix(self.accent, self.background, 0.55), width=2 * self.scale)

    def box(self, x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
        s = self.scale
        return round(x1 * s), round(y1 * s), round(x2 * s), round(y2 * s)

    def text(
        self,
        text: str,
        y: float,
        size: int,
        color: tuple[int, int, int],
        *,
        bold: bool = False,
        center_x: float = 120,
        max_width: float = 210,
        scale_kind: str = "none",
    ) -> None:
        scale = self.label_scale if scale_kind == "label" else self.value_scale if scale_kind == "value" else 1.0
        logical_size = max(7, round(size * scale))
        font = _font(logical_size * self.scale, bold=bold)
        bounds = self.draw.textbbox((0, 0), text, font=font)
        width = bounds[2] - bounds[0]
        while width > max_width * self.scale and logical_size > 7:
            logical_size -= 1
            font = _font(logical_size * self.scale, bold=bold)
            bounds = self.draw.textbbox((0, 0), text, font=font)
            width = bounds[2] - bounds[0]
        self.draw.text((center_x * self.scale - width / 2, y * self.scale), text, font=font, fill=color)

    def label(self, text: str, y: float, *, center_x: float = 120) -> None:
        self.text(text, y, 12, self.label_color, bold=True, center_x=center_x, max_width=82, scale_kind="label")

    def value(self, value: float | None, y: float, *, size: int = 47, center_x: float = 120) -> None:
        self.text(
            _temperature(value, self.temperature_unit),
            y,
            size,
            self.value_color,
            bold=True,
            center_x=center_x,
            max_width=96 if center_x != 120 else 180,
            scale_kind="value",
        )

    def rounded_panel(self, x1: float, y1: float, x2: float, y2: float, radius: float = 18) -> None:
        self.draw.rounded_rectangle(self.box(x1, y1, x2, y2), radius=radius * self.scale, fill=self.panel, outline=_mix(self.accent, self.background, 0.68), width=self.scale)

    def finish(self) -> Image.Image:
        return self.image.resize((LCD_SIZE, LCD_SIZE), Image.Resampling.LANCZOS)


def _draw_focus(
    canvas: _Canvas,
    label: str,
    value: float | None,
    *,
    style: str,
    status: str | None = None,
    status_live: bool = False,
) -> None:
    rotation = canvas.phase * 360.0
    if style == "halo":
        canvas.draw.arc(canvas.box(25, 25, 215, 215), 205 + rotation, 505 + rotation, fill=_mix(canvas.accent, canvas.white, 0.12), width=9 * canvas.scale)
        canvas.draw.arc(canvas.box(38, 38, 202, 202), 212 - rotation * 0.65, 498 - rotation * 0.65, fill=_mix(canvas.accent, canvas.background, 0.48), width=3 * canvas.scale)
    elif style == "orbit":
        canvas.draw.arc(canvas.box(23, 23, 217, 217), 155 + rotation, 385 + rotation, fill=canvas.accent, width=7 * canvas.scale)
        for offset, radius, dot_size in ((0.0, 94.0, 10.0), (0.44, 82.0, 8.0)):
            angle = 2 * math.pi * (canvas.phase + offset)
            x = 120 + math.cos(angle) * radius
            y = 120 + math.sin(angle) * radius
            canvas.draw.ellipse(canvas.box(x - dot_size / 2, y - dot_size / 2, x + dot_size / 2, y + dot_size / 2), fill=canvas.white if offset == 0 else _mix(canvas.accent, canvas.white, 0.3))
    else:
        canvas.draw.arc(canvas.box(24, 24, 216, 216), 200 + rotation, 520 + rotation, fill=canvas.accent, width=8 * canvas.scale)
        canvas.draw.arc(canvas.box(35, 35, 205, 205), 25 - rotation * 0.8, 155 - rotation * 0.8, fill=_mix(canvas.accent, canvas.background, 0.52), width=4 * canvas.scale)
    canvas.label(label, 66)
    canvas.value(value, 91, size=54)


def _draw_dual(
    canvas: _Canvas,
    cpu: float | None,
    gpu: float | None,
    labels: dict[str, str],
    *,
    show_sensor_status: bool = False,
) -> None:
    pulse = (math.sin(canvas.phase * math.tau) + 1.0) / 2.0
    canvas.text(labels["system"], 28, 12, canvas.label_color, bold=True, scale_kind="label")
    canvas.rounded_panel(22, 65, 116, 179, 22)
    canvas.rounded_panel(124, 65, 218, 179, 22)
    for index, center_x in enumerate((69, 171)):
        color = canvas.accent if index == 0 else _mix(canvas.accent, canvas.white, 0.35)
        start = -90 + canvas.phase * 360 * (1 if index == 0 else -1)
        canvas.draw.arc(canvas.box(center_x - 35, 92, center_x + 35, 162), start, start + 245, fill=color, width=4 * canvas.scale)
        dot_angle = math.radians(start + 245)
        dot_x = center_x + math.cos(dot_angle) * 35
        dot_y = 127 + math.sin(dot_angle) * 35
        canvas.draw.ellipse(canvas.box(dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3), fill=canvas.white)
    canvas.label(labels["cpu"], 71, center_x=69)
    canvas.label(labels["gpu"], 71, center_x=171)
    canvas.value(cpu, 109, size=31, center_x=69)
    canvas.value(gpu, 109, size=31, center_x=171)
    bar_width = 44 + 20 * pulse
    canvas.draw.rounded_rectangle(canvas.box(120 - bar_width, 190, 120 + bar_width, 196), radius=3 * canvas.scale, fill=_mix(canvas.accent, canvas.white, 0.18))


def _draw_trio(
    canvas: _Canvas,
    liquid: float | None,
    cpu: float | None,
    gpu: float | None,
    labels: dict[str, str],
    *,
    show_sensor_status: bool = False,
) -> None:
    canvas.text(labels["system"], 22, 12, canvas.label_color, bold=True, scale_kind="label")
    values = ((labels["water"], liquid, 62), (labels["cpu"], cpu, 120), (labels["gpu"], gpu, 178))
    for index, (label, value, center_x) in enumerate(values):
        color = canvas.accent if index != 2 else _mix(canvas.accent, canvas.white, 0.32)
        canvas.draw.ellipse(canvas.box(center_x - 25, 66, center_x + 25, 116), fill=canvas.panel, outline=_mix(color, canvas.background, 0.6), width=2 * canvas.scale)
        rotation = canvas.phase * 360 * (1 if index != 1 else -1) + index * 110
        canvas.draw.arc(canvas.box(center_x - 27, 64, center_x + 27, 118), rotation, rotation + 210, fill=color, width=4 * canvas.scale)
        canvas.text(
            _temperature(value, canvas.temperature_unit), 79, 18, canvas.value_color,
            bold=True, center_x=center_x, max_width=52, scale_kind="value",
        )
        canvas.text(
            label, 126, 9, canvas.label_color, bold=True,
            center_x=center_x, max_width=55, scale_kind="label",
        )
    canvas.rounded_panel(39, 159, 201, 184, 12)
    canvas.draw.rounded_rectangle(canvas.box(49, 168, 191, 175), radius=4 * canvas.scale, fill=_mix(canvas.accent, canvas.background, 0.45))
    travel = 92 * (0.5 - 0.5 * math.cos(canvas.phase * math.tau))
    canvas.draw.rounded_rectangle(canvas.box(49 + travel, 168, 89 + travel, 175), radius=4 * canvas.scale, fill=canvas.accent)


def render_hardware_frame(
    design_id: str,
    accent_hex: str,
    liquid: float | None,
    cpu: float | None,
    gpu: float | None,
    *,
    language: str = "de",
    font_scale_percent: int = 125,
    label_color_hex: str = DEFAULT_LABEL_COLOR,
    value_color_hex: str = DEFAULT_VALUE_COLOR,
    label_scale_percent: int | None = None,
    value_scale_percent: int | None = None,
    temperature_unit: str = "c",
    phase: float = 0.0,
    live_sensor_status: bool = False,
) -> Image.Image:
    """Render one static or animated hardware frame."""
    accent = normalize_hex_color(accent_hex)
    if accent is None:
        raise ValueError("accent_hex must be a color in #RRGGBB format")
    valid_designs = {identifier for identifier, _label in DESIGNS}
    if design_id not in valid_designs:
        raise ValueError(f"unknown hardware design: {design_id}")
    label_color = normalize_hex_color(label_color_hex)
    value_color = normalize_hex_color(value_color_hex)
    if label_color is None or value_color is None:
        raise ValueError("label/value colors must use #RRGGBB")
    labels = LABELS.get(language, LABELS["de"])
    canvas = _Canvas(
        accent,
        label_color,
        value_color,
        font_scale_percent if label_scale_percent is None else label_scale_percent,
        font_scale_percent if value_scale_percent is None else value_scale_percent,
        temperature_unit,
        phase,
    )
    if design_id == "water_halo":
        _draw_focus(canvas, labels["water"], liquid, style="halo", status=labels["last"] if live_sensor_status else None)
    elif design_id == "cpu_orbit":
        _draw_focus(canvas, labels["cpu"], cpu, style="orbit", status=labels["live"] if live_sensor_status else None, status_live=live_sensor_status)
    elif design_id == "gpu_arc":
        _draw_focus(canvas, labels["gpu"], gpu, style="arc", status=labels["live"] if live_sensor_status else None, status_live=live_sensor_status)
    elif design_id == "cpu_gpu_dual":
        _draw_dual(canvas, cpu, gpu, labels, show_sensor_status=live_sensor_status)
    else:
        _draw_trio(canvas, liquid, cpu, gpu, labels, show_sensor_status=live_sensor_status)
    return canvas.finish()


def render_hardware_design(
    design_id: str,
    accent_hex: str,
    liquid: float | None,
    cpu: float | None,
    gpu: float | None,
    output_path: str | Path,
    *,
    language: str = "de",
    font_scale_percent: int = 125,
    label_color_hex: str = DEFAULT_LABEL_COLOR,
    value_color_hex: str = DEFAULT_VALUE_COLOR,
    label_scale_percent: int | None = None,
    value_scale_percent: int | None = None,
    temperature_unit: str = "c",
) -> Path:
    """Render a localized hardware dashboard and return its PNG path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    render_hardware_frame(
        design_id,
        accent_hex,
        liquid,
        cpu,
        gpu,
        language=language,
        font_scale_percent=font_scale_percent,
        label_color_hex=label_color_hex,
        value_color_hex=value_color_hex,
        label_scale_percent=label_scale_percent,
        value_scale_percent=value_scale_percent,
        temperature_unit=temperature_unit,
    ).save(destination, format="PNG", optimize=True)
    return destination


def render_hardware_animation(
    design_id: str,
    accent_hex: str,
    liquid: float | None,
    cpu: float | None,
    gpu: float | None,
    output_path: str | Path,
    *,
    language: str = "de",
    font_scale_percent: int = 125,
    label_color_hex: str = DEFAULT_LABEL_COLOR,
    value_color_hex: str = DEFAULT_VALUE_COLOR,
    label_scale_percent: int | None = None,
    value_scale_percent: int | None = None,
    temperature_unit: str = "c",
    fps: int = 25,
    seconds: float = 1.0,
) -> Path:
    """Generate a seamless animated GIF for the existing CAM-raw streamer."""
    fps = max(10, min(25, int(fps)))
    frame_count = max(12, round(fps * max(0.6, min(2.0, seconds))))
    frames = [
        render_hardware_frame(
            design_id,
            accent_hex,
            liquid,
            cpu,
            gpu,
            language=language,
            font_scale_percent=font_scale_percent,
            label_color_hex=label_color_hex,
            value_color_hex=value_color_hex,
            label_scale_percent=label_scale_percent,
            value_scale_percent=value_scale_percent,
            temperature_unit=temperature_unit,
            phase=index / frame_count,
        )
        for index in range(frame_count)
    ]
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        destination,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / fps),
        loop=0,
        disposal=2,
        optimize=False,
    )
    return destination

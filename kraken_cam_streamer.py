#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Frelidon contributors
"""CAM-nearer firmware-2.x LCD streamer for NZXT Kraken 2023 Standard.

This helper intentionally replaces the 2.9.14 25.6/30/32-Hz experiment.
It normally keeps one liquidctl device connection open and owns the exact
firmware-2.x frame transaction itself:

  36 01 ... -> ACK -> 20-byte bulk header -> 115200-byte RGB565 frame -> 36 02 -> ACK

That sequence matches the liquidctl 1.16 firmware-2.x implementation and the
captured NZXT CAM traffic used during Kraken Control development.  Version
2.9.16 additionally clears stale HID reports and explicitly matches 37 01/37 02
responses, because unsolicited 75 02 status reports can otherwise be mistaken
for acknowledgements by liquidctl 1.16's private _write_then_read helper.
Version 2.9.19/2.9.20 keeps the captured 26.667-Hz CAM cadence but advances the
prepared LCD cache strictly one phase at a time.  A full USB time window can no
longer select a later wall-clock phase.  Isolated overruns are paid back only
when real transfer headroom exists and in steps no larger than 0.25 ms.  A
known-stable 25.6-Hz wall-clock fallback is retained.  There are no catch-up
bursts and frame transfers are never overlapped.

Version 2.9.23 can render generated hardware dashboards from a validated JSON
description.  CPU/GPU integer changes are read through Linux hwmon, rendered
in an isolated spawn process and swapped only as a complete RGB565 phase cache.
Liquid temperature remains the last value read before exclusive streaming, so
the proven no-parallel-Kraken-access rule is preserved.

Open Hardware Control 3.0.1 adds a PAUSE/RESUME ownership handoff for manual
cooling writes.  PAUSE completes the current frame and closes HID/Bulk before
the GUI is notified.  The prepared RGB565 cache stays alive; RESUME reconnects,
primes the last phase and continues without introducing a concurrent writer.

For motion smoothing, 2.9.15 no longer uses a plain Image.blend crossfade as
its primary interpolation.  It estimates a small global translation between
adjacent frames on a downscaled grayscale image and motion-compensates the
pair before blending.  This is deliberately conservative: if no convincing
motion vector is found it falls back to a normal blend.
"""

from __future__ import annotations

import argparse
import bisect
import concurrent.futures
import contextlib
import importlib.metadata
import json
import math
import multiprocessing
import select
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageSequence, ImageStat

from kraken_lcd_designs import (
    DEFAULT_LABEL_COLOR,
    DEFAULT_VALUE_COLOR,
    DESIGNS,
    normalize_hex_color,
    render_hardware_frame,
)
from kraken_sensors import read_amd_cpu_temperature, read_amd_gpu_temperature

KRAKEN_DESCRIPTION = "NZXT Kraken 2023"
KRAKEN_PRODUCT_ID = 0x300E
LCD_SIZE = (240, 240)
RGB565_FRAME_BYTES = LCD_SIZE[0] * LCD_SIZE[1] * 2
MAX_STREAM_FPS = 27
DEFAULT_ADAPTIVE_FPS_CAP = 25
CAM_TRANSPORT_FPS = 80.0 / 3.0  # 26.666... Hz, near the captured CAM cadence
SAFE_TRANSPORT_FPS = 25.6
TRANSPORT_MODES = {
    "cam": CAM_TRANSPORT_FPS,
    "safe": SAFE_TRANSPORT_FPS,
}
# CAM starts the next frame a median 0.113 ms after the previous 37 02 ACK
# (0.070 ms minimum in the supplied capture).  This tiny guard keeps the same
# confirmed ACK safety gap and still leaves a stop-command polling window.
CAM_ACK_GUARD_S = 0.0001
SAFE_DISPLAY_GUARD_S = 0.0002
MAX_PHASE_CORRECTION_STEP_S = 0.00025
MAX_PHASE_DEBT_S = 0.002
MAX_PRECACHE_BYTES = 128 * 1024 * 1024
MIN_SOURCE_FRAME_MS = 20
METRIC_WINDOW = 192
ADAPT_PERCENTILE = 0.90
MOTION_SEARCH_RADIUS = 7
MOTION_ANALYSIS_SIZE = (60, 60)
MOTION_MIN_IMPROVEMENT = 0.035
HID_RESPONSE_READ_ATTEMPTS = 12
HARDWARE_SENSOR_INTERVAL_S = 2.0
HARDWARE_LOOP_DURATION_S = 1.0


@dataclass(frozen=True)
class SourceFrame:
    image: Image.Image
    duration_s: float


@dataclass(frozen=True)
class MotionPair:
    dx: float
    dy: float
    confidence: float


@dataclass(frozen=True)
class PreparedFrame:
    data: bytes
    duration_s: float


@dataclass(frozen=True)
class HardwareSpec:
    design_id: str
    accent_hex: str
    liquid: float | None
    cpu: float | None
    gpu: float | None
    language: str
    font_scale_percent: int
    content_fps: int
    label_color_hex: str = DEFAULT_LABEL_COLOR
    value_color_hex: str = DEFAULT_VALUE_COLOR
    label_scale_percent: int = 125
    value_scale_percent: int = 125
    temperature_unit: str = "c"

    def with_temperatures(self, cpu: float | None, gpu: float | None) -> "HardwareSpec":
        return HardwareSpec(
            self.design_id,
            self.accent_hex,
            self.liquid,
            cpu,
            gpu,
            self.language,
            self.font_scale_percent,
            self.content_fps,
            self.label_color_hex,
            self.value_color_hex,
            self.label_scale_percent,
            self.value_scale_percent,
            self.temperature_unit,
        )


def emit(event: str, **payload: object) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False), flush=True)


def rgb565_bytes(image: Image.Image) -> bytes:
    """Convert RGB to the verified 240x240 RGB565 big-endian byte layout."""
    rgb = image.convert("RGB")
    result = bytearray(rgb.width * rgb.height * 2)
    offset = 0
    pixels = rgb.get_flattened_data() if hasattr(rgb, "get_flattened_data") else rgb.getdata()
    for r, g, b in pixels:
        dr = r >> 3
        dg = g >> 2
        db = b >> 3
        result[offset] = (dr << 3) + (dg >> 3)
        result[offset + 1] = ((dg & 0x7) << 5) + db
        offset += 2
    return bytes(result)


def _fit_square(frame: Image.Image) -> Image.Image:
    rgba = frame.convert("RGBA")
    width, height = rgba.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    rgba = rgba.crop((left, top, left + side, top + side))
    return rgba.resize(LCD_SIZE, Image.Resampling.LANCZOS).convert("RGB")


def _load_source_frames(path: Path, orientation_deg: int) -> list[SourceFrame]:
    frames: list[SourceFrame] = []
    with Image.open(path) as source:
        if not getattr(source, "is_animated", False):
            raise ValueError("Die ausgewählte GIF-Datei enthält keine Animation.")
        default_duration_ms = max(MIN_SOURCE_FRAME_MS, int(source.info.get("duration", 100) or 100))
        for frame in ImageSequence.Iterator(source):
            prepared = _fit_square(frame.copy())
            if orientation_deg:
                prepared = prepared.rotate(-orientation_deg, expand=False)
            duration_ms = max(
                MIN_SOURCE_FRAME_MS,
                int(frame.info.get("duration", default_duration_ms) or default_duration_ms),
            )
            frames.append(SourceFrame(prepared, duration_ms / 1000.0))
    if not frames:
        raise ValueError("Keine GIF-Frames gefunden.")
    return frames


def _starts(frames: list[SourceFrame]) -> tuple[list[float], float]:
    starts: list[float] = []
    cursor = 0.0
    for frame in frames:
        starts.append(cursor)
        cursor += frame.duration_s
    return starts, cursor


def _motion_score(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / max(1, len(stat.mean)))


def loop_transition_diagnostics(frames: list[SourceFrame]) -> dict[str, object]:
    """Estimate whether the last-to-first GIF transition is an outlier.

    This deliberately reports a probability-style warning rather than rejecting
    the file: hard cuts can be intentional, but a transition that is far larger
    than the animation's normal neighbouring changes often explains a regular
    hitch at exactly the same point in every loop.
    """
    if len(frames) < 3:
        return {
            "loop_warning": False,
            "loop_transition_score": 0.0,
            "typical_transition_score": 0.0,
            "loop_warning_ratio": 0.0,
        }
    internal = [_motion_score(frames[i].image, frames[i + 1].image) for i in range(len(frames) - 1)]
    typical = percentile(internal, 0.50)
    p90 = percentile(internal, 0.90)
    loop_score = _motion_score(frames[-1].image, frames[0].image)
    ratio = loop_score / max(1.0, typical)
    threshold = max(10.0, typical * 2.5, p90 * 1.6)
    warning = loop_score >= threshold and (loop_score - typical) >= 6.0
    return {
        "loop_warning": warning,
        "loop_transition_score": round(loop_score, 2),
        "typical_transition_score": round(typical, 2),
        "loop_warning_ratio": round(ratio, 2),
    }


def estimate_global_motion(a: Image.Image, b: Image.Image) -> MotionPair:
    """Estimate a conservative global x/y translation from a to b.

    The search is intentionally tiny and runs on 60x60 grayscale copies.  It is
    good at the scrolling bars used for validation and cheap enough to precompute
    for every neighbouring frame pair.  Low-confidence results become (0, 0).
    """
    small_a = a.convert("L").resize(MOTION_ANALYSIS_SIZE, Image.Resampling.BILINEAR)
    small_b = b.convert("L").resize(MOTION_ANALYSIS_SIZE, Image.Resampling.BILINEAR)
    baseline = _motion_score(small_a, small_b)
    best_score = baseline
    best_dx = best_dy = 0
    for dy in range(-MOTION_SEARCH_RADIUS, MOTION_SEARCH_RADIUS + 1):
        for dx in range(-MOTION_SEARCH_RADIUS, MOTION_SEARCH_RADIUS + 1):
            if dx == 0 and dy == 0:
                continue
            shifted = ImageChops.offset(small_a, dx, dy)
            score = _motion_score(shifted, small_b)
            better = score < (best_score - 1e-9)
            tied_but_smaller = abs(score - best_score) <= 1e-9 and (abs(dx) + abs(dy) < abs(best_dx) + abs(best_dy))
            if better or tied_but_smaller:
                best_score = score
                best_dx, best_dy = dx, dy
    if baseline <= 1e-9:
        return MotionPair(0.0, 0.0, 0.0)
    improvement = max(0.0, (baseline - best_score) / baseline)
    if improvement < MOTION_MIN_IMPROVEMENT:
        return MotionPair(0.0, 0.0, improvement)
    scale_x = LCD_SIZE[0] / MOTION_ANALYSIS_SIZE[0]
    scale_y = LCD_SIZE[1] / MOTION_ANALYSIS_SIZE[1]
    return MotionPair(best_dx * scale_x, best_dy * scale_y, improvement)


def _shift_wrap(image: Image.Image, dx: float, dy: float) -> Image.Image:
    # Integer pixel motion is enough at 240x240 and avoids a costly affine filter.
    return ImageChops.offset(image, int(round(dx)), int(round(dy)))


def motion_interpolate(a: Image.Image, b: Image.Image, motion: MotionPair, alpha: float) -> Image.Image:
    """Motion-compensated interpolation; plain blend is the safe fallback."""
    alpha = min(1.0, max(0.0, alpha))
    if alpha <= 0.001:
        return a
    if alpha >= 0.999:
        return b
    if motion.confidence < MOTION_MIN_IMPROVEMENT or (abs(motion.dx) < 0.5 and abs(motion.dy) < 0.5):
        return Image.blend(a, b, alpha)
    from_a = _shift_wrap(a, motion.dx * alpha, motion.dy * alpha)
    from_b = _shift_wrap(b, -motion.dx * (1.0 - alpha), -motion.dy * (1.0 - alpha))
    return Image.blend(from_a, from_b, alpha)


def sample_timeline(
    frames: list[SourceFrame],
    starts: list[float],
    total_duration_s: float,
    sample_time_s: float,
    interpolate: bool,
    motions: list[MotionPair] | None = None,
) -> Image.Image:
    t = sample_time_s % total_duration_s
    index = bisect.bisect_right(starts, t) - 1
    index = max(0, min(index, len(frames) - 1))
    current = frames[index]
    if not interpolate or len(frames) == 1:
        return current.image
    local_t = max(0.0, t - starts[index])
    alpha = min(1.0, local_t / max(0.001, current.duration_s))
    nxt = frames[(index + 1) % len(frames)]
    motion = motions[index] if motions and index < len(motions) else MotionPair(0.0, 0.0, 0.0)
    return motion_interpolate(current.image, nxt.image, motion, alpha)


def requested_transport_fps(mode: str) -> float:
    try:
        return float(TRANSPORT_MODES[mode])
    except KeyError as exc:
        raise ValueError(f"Unbekannter LCD-Transportmodus: {mode}") from exc


def _logical_content_frames(
    source_frames: list[SourceFrame],
    source_starts: list[float],
    total_duration_s: float,
    target_fps: int,
    interpolate: bool,
    source_motions: list[MotionPair],
) -> tuple[list[SourceFrame], float]:
    count = max(2, int(round(total_duration_s * target_fps)))
    interval = total_duration_s / count
    logical: list[SourceFrame] = []
    for i in range(count):
        image = sample_timeline(
            source_frames, source_starts, total_duration_s, i * interval, interpolate, source_motions
        )
        logical.append(SourceFrame(image, interval))
    return logical, count / total_duration_s


def prepare_gif(
    path: Path,
    orientation_deg: int,
    fixed_fps: int,
    interpolate: bool = True,
    transport_mode: str = "cam",
) -> tuple[list[PreparedFrame], dict[str, object]]:
    if fixed_fps < 0 or fixed_fps > MAX_STREAM_FPS:
        raise ValueError(f"Ungültige GIF-Bildrate: {fixed_fps}")

    source_frames = _load_source_frames(path, orientation_deg)
    source_starts, total_duration_s = _starts(source_frames)
    loop_diagnostics = loop_transition_diagnostics(source_frames)
    source_average_fps = len(source_frames) / total_duration_s
    target_fps = fixed_fps or max(1, min(DEFAULT_ADAPTIVE_FPS_CAP, int(round(source_average_fps))))
    transport_fps = requested_transport_fps(transport_mode)

    source_motions = [
        estimate_global_motion(source_frames[i].image, source_frames[(i + 1) % len(source_frames)].image)
        for i in range(len(source_frames))
    ] if interpolate and len(source_frames) > 1 else [MotionPair(0.0, 0.0, 0.0)] * len(source_frames)

    logical_frames, content_fps = _logical_content_frames(
        source_frames, source_starts, total_duration_s, target_fps, interpolate, source_motions
    )
    logical_starts, _ = _starts(logical_frames)
    logical_motions = [
        estimate_global_motion(logical_frames[i].image, logical_frames[(i + 1) % len(logical_frames)].image)
        for i in range(len(logical_frames))
    ] if interpolate and len(logical_frames) > 1 else [MotionPair(0.0, 0.0, 0.0)] * len(logical_frames)

    # At 26.67 Hz almost every LCD tick lands at a fractional point of a 25-FPS
    # source.  Precomputing one full loop therefore gives genuinely different
    # motion-compensated phases instead of repeated or pure cross-faded bars.
    phase_count = max(2, int(math.ceil(total_duration_s * transport_fps - 1e-12)))
    phase_interval = total_duration_s / phase_count
    prepared: list[PreparedFrame] = []
    bytes_total = 0
    motion_phase_count = 0
    unique_data: set[bytes] = set()
    for i in range(phase_count):
        sample_time = i * phase_interval
        logical_interval = logical_frames[0].duration_s
        phase = (sample_time / logical_interval) % 1.0
        if interpolate and 0.001 < phase < 0.999:
            motion_phase_count += 1
        image = sample_timeline(
            logical_frames, logical_starts, total_duration_s, sample_time, interpolate, logical_motions
        )
        data = rgb565_bytes(image)
        if len(data) != RGB565_FRAME_BYTES:
            raise RuntimeError(f"Unerwartete RGB565-Framegröße: {len(data)} Byte")
        prepared.append(PreparedFrame(data, phase_interval))
        unique_data.add(data)
        bytes_total += len(data)
        if bytes_total > MAX_PRECACHE_BYTES:
            raise ValueError("GIF-Frame-Cache überschreitet 128 MiB; GIF kürzen oder niedrigere Inhaltsrate verwenden.")

    confident = [m for m in logical_motions if m.confidence >= MOTION_MIN_IMPROVEMENT]
    metadata: dict[str, object] = {
        "source_frames": len(source_frames),
        "content_frames": len(logical_frames),
        "output_frames": len(prepared),
        "transport_cache_frames": len(prepared),
        "transport_cache_fps": round(len(prepared) / total_duration_s, 3),
        "source_duration_ms": int(round(total_duration_s * 1000.0)),
        "source_duration_s": total_duration_s,
        "target_fps": target_fps,
        "content_fps": round(content_fps, 3),
        "transport_fps": round(transport_fps, 3),
        "transport_mode": transport_mode,
        "interpolation": interpolate,
        "interpolation_kind": "motion-compensated-global" if interpolate else "off",
        "interpolated_transport_frames": motion_phase_count,
        "motion_pairs": len(confident),
        "motion_confidence_avg": round(sum(m.confidence for m in confident) / len(confident), 3) if confident else 0.0,
        "unique_transport_frames": len(unique_data),
        **loop_diagnostics,
    }
    return prepared, metadata


def load_hardware_spec(path: Path) -> HardwareSpec:
    """Load and validate a generated hardware-animation description."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Hardwareanimations-Datei enthält kein gültiges Objekt.")
    design_id = str(payload.get("design_id", ""))
    if design_id not in {identifier for identifier, _label in DESIGNS}:
        raise ValueError("Unbekanntes Hardwareanimations-Layout.")
    accent = normalize_hex_color(str(payload.get("accent_hex", "")))
    if accent is None:
        raise ValueError("Ungültige Akzentfarbe in der Hardwareanimations-Datei.")
    language = str(payload.get("language", "de"))
    if language not in {"de", "en", "es", "fr"}:
        language = "de"
    font_scale = max(70, min(150, int(payload.get("font_scale_percent", 125))))
    label_color = normalize_hex_color(str(payload.get("label_color_hex", DEFAULT_LABEL_COLOR)))
    value_color = normalize_hex_color(str(payload.get("value_color_hex", DEFAULT_VALUE_COLOR)))
    if label_color is None or value_color is None:
        raise ValueError("Ungültige Textfarbe in der Hardwareanimations-Datei.")
    label_scale = max(60, min(200, int(payload.get("label_scale_percent", font_scale))))
    value_scale = max(60, min(200, int(payload.get("value_scale_percent", font_scale))))
    temperature_unit = "f" if str(payload.get("temperature_unit", "c")).casefold() == "f" else "c"
    content_fps = int(payload.get("content_fps", 25))
    if content_fps not in (20, 25):
        raise ValueError("Hardwareanimation unterstützt nur 20 oder 25 FPS Inhalt.")

    def optional_temperature(name: str, upper: float) -> float | None:
        value = payload.get(name)
        if value is None:
            return None
        number = float(value)
        return number if 0.0 < number < upper else None

    return HardwareSpec(
        design_id=design_id,
        accent_hex=accent,
        liquid=optional_temperature("liquid", 80.0),
        cpu=optional_temperature("cpu", 125.0),
        gpu=optional_temperature("gpu", 130.0),
        language=language,
        font_scale_percent=font_scale,
        label_color_hex=label_color,
        value_color_hex=value_color,
        label_scale_percent=label_scale,
        value_scale_percent=value_scale,
        temperature_unit=temperature_unit,
        content_fps=content_fps,
    )


def prepare_hardware_animation(
    spec: HardwareSpec,
    orientation_deg: int,
    transport_mode: str,
) -> tuple[list[PreparedFrame], dict[str, object]]:
    """Prepare one second of ring/orbit phases with live-value markers."""
    transport_fps = requested_transport_fps(transport_mode)
    phase_count = max(2, int(math.ceil(HARDWARE_LOOP_DURATION_S * transport_fps - 1e-12)))
    phase_interval = HARDWARE_LOOP_DURATION_S / phase_count
    prepared: list[PreparedFrame] = []
    unique_data: set[bytes] = set()
    for index in range(phase_count):
        image = render_hardware_frame(
            spec.design_id,
            spec.accent_hex,
            spec.liquid,
            spec.cpu,
            spec.gpu,
            language=spec.language,
            font_scale_percent=spec.font_scale_percent,
            label_color_hex=spec.label_color_hex,
            value_color_hex=spec.value_color_hex,
            label_scale_percent=spec.label_scale_percent,
            value_scale_percent=spec.value_scale_percent,
            temperature_unit=spec.temperature_unit,
            phase=index / phase_count,
            live_sensor_status=True,
        )
        if orientation_deg:
            image = image.rotate(-orientation_deg, expand=False)
        data = rgb565_bytes(image)
        if len(data) != RGB565_FRAME_BYTES:
            raise RuntimeError(f"Unerwartete RGB565-Framegröße: {len(data)} Byte")
        prepared.append(PreparedFrame(data, phase_interval))
        unique_data.add(data)
    metadata: dict[str, object] = {
        "source_frames": spec.content_fps,
        "content_frames": spec.content_fps,
        "output_frames": len(prepared),
        "transport_cache_frames": len(prepared),
        "transport_cache_fps": round(len(prepared) / HARDWARE_LOOP_DURATION_S, 3),
        "source_duration_ms": 1000,
        "source_duration_s": HARDWARE_LOOP_DURATION_S,
        "target_fps": spec.content_fps,
        "content_fps": float(spec.content_fps),
        "transport_fps": round(transport_fps, 3),
        "transport_mode": transport_mode,
        "interpolation": False,
        "interpolation_kind": "procedural-hardware",
        "interpolated_transport_frames": 0,
        "motion_pairs": 0,
        "motion_confidence_avg": 0.0,
        "unique_transport_frames": len(unique_data),
        "loop_warning": False,
        "loop_transition_score": 0.0,
        "typical_transition_score": 0.0,
        "loop_warning_ratio": 0.0,
        "hardware_live": True,
        "liquid_snapshot": spec.liquid,
        "cpu": spec.cpu,
        "gpu": spec.gpu,
        "sensor_interval_s": HARDWARE_SENSOR_INTERVAL_S,
    }
    return prepared, metadata


def render_hardware_cache_worker(
    spec: HardwareSpec,
    orientation_deg: int,
    transport_mode: str,
    output_path: str,
) -> dict[str, object]:
    """Render a replacement cache outside the timing-critical USB process."""
    started = time.monotonic()
    frames, metadata = prepare_hardware_animation(spec, orientation_deg, transport_mode)
    destination = Path(output_path)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(b"".join(frame.data for frame in frames))
    temporary.replace(destination)
    return {
        **metadata,
        "cache_path": str(destination),
        "generation_ms": round((time.monotonic() - started) * 1000.0, 1),
    }


def frames_from_cache_file(path: Path, frame_count: int, duration_s: float) -> list[PreparedFrame]:
    blob = path.read_bytes()
    expected = frame_count * RGB565_FRAME_BYTES
    if len(blob) != expected:
        raise RuntimeError(f"Live-Frame-Cache hat {len(blob)} statt {expected} Byte.")
    interval = duration_s / max(1, frame_count)
    return [
        PreparedFrame(blob[offset:offset + RGB565_FRAME_BYTES], interval)
        for offset in range(0, len(blob), RGB565_FRAME_BYTES)
    ]


def hardware_dynamic_fields(design_id: str) -> tuple[bool, bool]:
    return design_id in {"cpu_orbit", "cpu_gpu_dual", "system_trio"}, design_id in {
        "gpu_arc",
        "cpu_gpu_dual",
        "system_trio",
    }


def displayed_temperature(value: float | None) -> int | None:
    return None if value is None else round(value)


def prepared_frame_index(frames: list[PreparedFrame], elapsed_s: float, loop_duration_s: float) -> int:
    if not frames:
        raise ValueError("Keine vorbereiteten Frames vorhanden.")
    phase = (elapsed_s % max(1e-9, loop_duration_s)) / max(1e-9, loop_duration_s)
    return min(len(frames) - 1, int(phase * len(frames) + 1e-12))


def logical_content_index(content_fps: float, count: int, elapsed_s: float, loop_duration_s: float) -> int:
    if count <= 0:
        return 0
    t = elapsed_s % max(1e-9, loop_duration_s)
    return min(count - 1, int(t * content_fps + 1e-9) % count)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = min(1.0, max(0.0, q)) * (len(ordered) - 1)
    lo = int(pos)
    hi = min(len(ordered) - 1, lo + 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def next_transfer_start(
    upload_started: float,
    upload_finished: float,
    interval_s: float,
) -> tuple[float, bool]:
    nominal = upload_started + interval_s
    guarded = upload_finished + SAFE_DISPLAY_GUARD_S
    if guarded > nominal:
        return guarded, True
    return nominal, False


def next_phase_locked_start(
    upload_started: float,
    upload_finished: float,
    interval_s: float,
    phase_debt_s: float,
) -> tuple[float, bool, float, float]:
    """Schedule the next CAM phase without bursts or frame selection by time.

    A transfer that genuinely exceeds the 26.667-Hz budget starts the next
    complete frame after the matching ACK and records only that single-window
    overrun.  Existing phase debt is reduced only from real spare time, capped
    at 0.25 ms per frame, so recovery can never create a fast catch-up burst.
    """
    nominal = upload_started + interval_s
    guarded = upload_finished + CAM_ACK_GUARD_S
    debt = min(MAX_PHASE_DEBT_S, max(0.0, phase_debt_s))
    if guarded > nominal:
        overrun = guarded - nominal
        return guarded, True, overrun, min(MAX_PHASE_DEBT_S, max(debt, overrun))
    spare = nominal - guarded
    correction = min(MAX_PHASE_CORRECTION_STEP_S, debt, spare)
    return nominal - correction, False, 0.0, max(0.0, debt - correction)


def upload_histogram_bucket(upload_s: float) -> str:
    ms = upload_s * 1000.0
    if ms < 20: return "lt20"
    if ms < 30: return "20_30"
    if ms < 35: return "30_35"
    if ms < 42: return "35_42"
    return "ge42"


def _product_id(dev: object) -> int | None:
    value = getattr(dev, "product_id", None)
    if value is not None:
        return int(value)
    device = getattr(dev, "device", None)
    value = getattr(device, "product_id", None)
    return int(value) if value is not None else None


def find_kraken():
    from liquidctl import find_liquidctl_devices
    matches = [
        dev for dev in find_liquidctl_devices()
        if getattr(dev, "description", "") == KRAKEN_DESCRIPTION and _product_id(dev) == KRAKEN_PRODUCT_ID
    ]
    if not matches:
        raise RuntimeError("NZXT Kraken 2023 (1e71:300e) wurde nicht gefunden.")
    if len(matches) > 1:
        raise RuntimeError("Mehrere passende NZXT Kraken 2023 gefunden; Stream aus Sicherheitsgründen abgebrochen.")
    return matches[0]


def read_control_command(timeout_s: float) -> str | None:
    """Read one GUI control command without delaying the frame schedule."""
    timeout_s = max(0.0, timeout_s)
    try:
        readable, _, _ = select.select([sys.stdin], [], [], timeout_s)
    except (OSError, ValueError):
        time.sleep(timeout_s)
        return None
    if not readable:
        return None
    line = sys.stdin.readline()
    if line == "":
        return "STOP"
    command = line.strip().upper()
    return command if command in {"STOP", "PAUSE", "RESUME"} else None


def stop_requested(timeout_s: float) -> bool:
    """Compatibility wrapper retained for timing/unit tests."""
    return read_control_command(timeout_s) == "STOP"


class CamRawTransport:
    """Own the exact FW2 transaction instead of calling the high-level screen path."""
    START = [0x36, 0x01, 0x00, 0x01, 0x06]
    END = [0x36, 0x02]
    HEADER_PREFIX = [0x12, 0xFA, 0x01, 0xE8, 0xAB, 0xCD, 0xEF, 0x98, 0x76, 0x54, 0x32, 0x10]

    def __init__(self, dev: object):
        self.dev = dev
        self.write = getattr(dev, "_write", None)
        self.read = getattr(dev, "_read", None)
        self.bulk_write = getattr(dev, "_bulk_write", None)
        hid_device = getattr(dev, "device", None)
        self.clear_enqueued_reports = getattr(hid_device, "clear_enqueued_reports", None)
        if not all(callable(method) for method in (self.write, self.read, self.bulk_write, self.clear_enqueued_reports)):
            raise RuntimeError("liquidctl stellt den benötigten direkten Firmware-2.x-USB-Pfad nicht bereit.")
        if getattr(dev, "bulk_device", None) is None:
            raise RuntimeError("liquidctl konnte den USB-Bulk-Endpunkt der Kraken nicht öffnen.")
        length = RGB565_FRAME_BYTES
        self.header = self.HEADER_PREFIX + [0x06, 0, 0, 0] + list(length.to_bytes(4, "little"))
        self.unrelated_hid_reports = 0

    def _command_with_matching_reply(self, data: list[int]) -> bytes:
        """Send one HID command and accept only its matching response prefix."""
        self.clear_enqueued_reports()
        self.write(data)
        expected = bytes(((data[0] + 1) & 0xFF, data[1]))
        for _ in range(HID_RESPONSE_READ_ATTEMPTS):
            message = self.read()
            if not message:
                break
            raw = bytes(message)
            if raw[:2] == expected:
                return raw
            self.unrelated_hid_reports += 1
        raise RuntimeError(
            f"Keine passende Kraken-Antwort {expected.hex(' ')} auf Befehl {bytes(data[:2]).hex(' ')} erhalten."
        )

    def send(self, data: bytes) -> None:
        if len(data) != RGB565_FRAME_BYTES:
            raise ValueError(f"CAM-Raw-Frame muss exakt {RGB565_FRAME_BYTES} Byte groß sein.")
        self._command_with_matching_reply(self.START)
        self.bulk_write(self.header)
        # One contiguous 115200-byte write; liquidctl's 2023 bulk buffer is much
        # larger, so splitting it would only add userspace jitter.
        self.bulk_write(data)
        self._command_with_matching_reply(self.END)


def transport_policy_name(mode: str) -> str:
    return "cam-raw-26.667hz-phase-locked" if mode == "cam" else "cam-raw-safe-25.6hz-phase-locked"


def run_stream(
    path: Path | None,
    orientation: int,
    fixed_fps: int,
    interpolate: bool,
    transport_mode: str,
    *,
    hardware_spec_path: Path | None = None,
) -> int:
    started_prepare = time.monotonic()
    hardware_spec = load_hardware_spec(hardware_spec_path) if hardware_spec_path is not None else None
    if hardware_spec is not None:
        frames, metadata = prepare_hardware_animation(hardware_spec, orientation, transport_mode)
        interpolate = False
    else:
        if path is None:
            raise ValueError("Keine GIF-Datei angegeben.")
        frames, metadata = prepare_gif(path, orientation, fixed_fps, interpolate, transport_mode)
    prepare_ms = int((time.monotonic() - started_prepare) * 1000)
    try:
        liquidctl_version = importlib.metadata.version("liquidctl")
    except importlib.metadata.PackageNotFoundError:
        liquidctl_version = "unbekannt"

    transport_fps = requested_transport_fps(transport_mode)
    phase_locked = True
    guard_s = CAM_ACK_GUARD_S if transport_mode == "cam" else SAFE_DISPLAY_GUARD_S
    emit(
        "ready",
        **metadata,
        prepare_ms=prepare_ms,
        liquidctl=liquidctl_version,
        guard_ms=round(guard_s * 1000, 2),
        device_paced=False,
        phase_locked=phase_locked,
        timing=transport_policy_name(transport_mode),
        raw_transport=True,
        ack_matching=True,
    )

    dev = find_kraken()
    transport_frames = 0
    recent_uploads: deque[float] = deque(maxlen=METRIC_WINDOW)
    max_upload_s = 0.0
    upload_ema_s: float | None = None
    deadline_misses = 0
    total_overrun_s = 0.0
    max_overrun_s = 0.0
    phase_debt_s = 0.0
    content_repeats = content_skips = 0
    lcd_frame_repeats = lcd_frame_skips = 0
    last_content_index = last_lcd_index = 0
    content_count = int(metadata["content_frames"])
    content_fps = float(metadata["content_fps"])
    loop_duration_s = float(metadata["source_duration_s"])
    histogram = {"lt20": 0, "20_30": 0, "30_35": 0, "35_42": 0, "ge42": 0}
    dynamic_cpu, dynamic_gpu = hardware_dynamic_fields(hardware_spec.design_id) if hardware_spec else (False, False)
    live_cache_enabled = bool(hardware_spec and (dynamic_cpu or dynamic_gpu))
    cache_context = tempfile.TemporaryDirectory(prefix="kraken-live-cache-") if live_cache_enabled else contextlib.nullcontext(None)
    worker_context = (
        concurrent.futures.ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
        )
        if live_cache_enabled
        else contextlib.nullcontext(None)
    )

    with cache_context as cache_directory, worker_context as render_executor, contextlib.ExitStack() as device_stack:
        def connect_raw_transport() -> CamRawTransport:
            device_stack.enter_context(dev.connect())
            connected_raw = CamRawTransport(dev)
            get_fw = getattr(dev, "_get_fw_version", None)
            if callable(get_fw):
                # Reduce the chance that liquidctl 1.16's blind helper consumes an
                # already queued unsolicited status report during the FW check.
                connected_raw.clear_enqueued_reports()
                get_fw()
                fw = getattr(dev, "_fw", None)
                if fw and int(fw[0]) != 2:
                    raise RuntimeError(
                        f"CAM-Streamer ist nur für Kraken-Firmware 2.x vorgesehen; erkannt: {fw[0]}.{fw[1]}.{fw[2]}."
                    )
            return connected_raw

        raw = connect_raw_transport()

        first = frames[0].data
        prime_started = time.monotonic()
        raw.send(first)
        raw.send(first)
        prime_ms = (time.monotonic() - prime_started) * 1000.0

        stream_started = time.monotonic()
        report_started = stream_started
        next_start = stream_started + 1.0 / transport_fps
        emit(
            "started",
            frames=len(frames),
            first_uploads=2,
            prime_ms=round(prime_ms, 1),
            transport_fps=round(transport_fps, 3),
            transport_mode=transport_mode,
            content_fps=content_fps,
            interpolation=interpolate,
            interpolation_kind=metadata["interpolation_kind"],
            motion_pairs=metadata["motion_pairs"],
            unique_transport_frames=metadata["unique_transport_frames"],
            guard_ms=round(guard_s * 1000, 2),
            device_paced=False,
            phase_locked=phase_locked,
            raw_transport=True,
            ack_matching=True,
            unrelated_hid_reports=raw.unrelated_hid_reports,
            timeline="sequential-cache-phases",
            hardware_live=bool(hardware_spec),
            hardware_design=hardware_spec.design_id if hardware_spec else None,
            liquid_snapshot=hardware_spec.liquid if hardware_spec else None,
            cpu_live=dynamic_cpu,
            gpu_live=dynamic_gpu,
            sensor_interval_s=HARDWARE_SENSOR_INTERVAL_S if live_cache_enabled else None,
        )

        render_future: concurrent.futures.Future[dict[str, object]] | None = None
        pending_spec: HardwareSpec | None = None
        active_spec = hardware_spec
        next_sensor_read = time.monotonic() + HARDWARE_SENSOR_INTERVAL_S
        cache_sequence = 0

        while True:
            now = time.monotonic()
            if render_future is not None and render_future.done():
                try:
                    rendered = render_future.result()
                    cache_path = Path(str(rendered["cache_path"]))
                    frames = frames_from_cache_file(
                        cache_path,
                        int(rendered["transport_cache_frames"]),
                        float(rendered["source_duration_s"]),
                    )
                    cache_path.unlink(missing_ok=True)
                    if pending_spec is not None:
                        active_spec = pending_spec
                    emit(
                        "sensor_update",
                        cpu=active_spec.cpu if active_spec else None,
                        gpu=active_spec.gpu if active_spec else None,
                        liquid_snapshot=active_spec.liquid if active_spec else None,
                        hardware_design=active_spec.design_id if active_spec else None,
                        cpu_live=dynamic_cpu,
                        gpu_live=dynamic_gpu,
                        generation_ms=rendered.get("generation_ms", "?"),
                        transport_cache_frames=len(frames),
                    )
                except Exception as exc:  # noqa: BLE001
                    emit("sensor_update_error", message=str(exc))
                render_future = None
                pending_spec = None

            if (
                live_cache_enabled
                and active_spec is not None
                and render_future is None
                and now >= next_sensor_read
            ):
                next_sensor_read = now + HARDWARE_SENSOR_INTERVAL_S
                cpu_value = active_spec.cpu
                gpu_value = active_spec.gpu
                if dynamic_cpu:
                    measured_cpu, _cpu_label = read_amd_cpu_temperature()
                    if measured_cpu is not None:
                        cpu_value = measured_cpu
                if dynamic_gpu:
                    measured_gpu, _gpu_label = read_amd_gpu_temperature()
                    if measured_gpu is not None:
                        gpu_value = measured_gpu
                changed = (
                    dynamic_cpu and displayed_temperature(cpu_value) != displayed_temperature(active_spec.cpu)
                ) or (
                    dynamic_gpu and displayed_temperature(gpu_value) != displayed_temperature(active_spec.gpu)
                )
                if changed and render_executor is not None and cache_directory is not None:
                    pending_spec = active_spec.with_temperatures(cpu_value, gpu_value)
                    cache_sequence += 1
                    output_path = str(Path(cache_directory) / f"hardware-cache-{cache_sequence:05d}.rgb565")
                    render_future = render_executor.submit(
                        render_hardware_cache_worker,
                        pending_spec,
                        orientation,
                        transport_mode,
                        output_path,
                    )

            wait_s = max(0.0, next_start - time.monotonic())
            control_command = read_control_command(wait_s)
            if control_command == "STOP":
                emit(
                    "stopped",
                    frames_sent=transport_frames,
                    skipped=0,
                    deadline_misses=deadline_misses,
                    content_repeats=content_repeats,
                    content_skips=content_skips,
                    lcd_frame_repeats=lcd_frame_repeats,
                    lcd_frame_skips=lcd_frame_skips,
                    transport_fps=round(transport_fps, 3),
                    histogram=histogram,
                    unrelated_hid_reports=raw.unrelated_hid_reports,
                )
                return 0
            if control_command == "PAUSE":
                paused_at = time.monotonic()
                paused_lcd_index = (transport_frames + 1) % len(frames)
                # Closing the ExitStack releases both HID and bulk interfaces
                # while keeping every prepared RGB565 frame in this process.
                device_stack.close()
                emit(
                    "paused",
                    reason="cooling-write",
                    lcd_index=paused_lcd_index,
                    frames_sent=transport_frames,
                )
                while True:
                    paused_command = read_control_command(0.5)
                    if paused_command == "STOP":
                        emit(
                            "stopped",
                            frames_sent=transport_frames,
                            skipped=0,
                            deadline_misses=deadline_misses,
                            content_repeats=content_repeats,
                            content_skips=content_skips,
                            lcd_frame_repeats=lcd_frame_repeats,
                            lcd_frame_skips=lcd_frame_skips,
                            transport_fps=round(transport_fps, 3),
                            histogram=histogram,
                            unrelated_hid_reports=raw.unrelated_hid_reports,
                        )
                        return 0
                    if paused_command != "RESUME":
                        continue
                    raw = connect_raw_transport()
                    # Prime the same visible phase twice after reacquiring the
                    # device. The next regular transfer then continues the
                    # prepared sequence instead of rebuilding/restarting it.
                    raw.send(frames[paused_lcd_index].data)
                    raw.send(frames[paused_lcd_index].data)
                    # Treat the primed phase as the resumed logical phase so
                    # the first normal upload advances instead of displaying
                    # the same cached image a third time.
                    transport_frames += 1
                    last_lcd_index = paused_lcd_index
                    paused_phase_time = (paused_lcd_index / len(frames)) * loop_duration_s
                    last_content_index = logical_content_index(
                        content_fps,
                        content_count,
                        paused_phase_time,
                        loop_duration_s,
                    )
                    paused_for = time.monotonic() - paused_at
                    stream_started += paused_for
                    report_started += paused_for
                    next_sensor_read += paused_for
                    next_start = time.monotonic() + 1.0 / transport_fps
                    emit(
                        "resumed",
                        reason="cooling-write",
                        lcd_index=paused_lcd_index,
                        pause_ms=round(paused_for * 1000, 1),
                        prime_uploads=2,
                        frames_sent=transport_frames,
                        ack_matching=True,
                    )
                    break
                continue

            upload_started = time.monotonic()
            # Advance the prepared cache in strict order.  The first phase was
            # already used for priming, so live playback starts at phase 1.
            lcd_index = (transport_frames + 1) % len(frames)
            phase_time = (lcd_index / len(frames)) * loop_duration_s
            content_index = logical_content_index(content_fps, content_count, phase_time, loop_duration_s)
            if transport_frames:
                if content_index == last_content_index:
                    content_repeats += 1
                else:
                    delta = (content_index - last_content_index) % content_count
                    if delta > 1: content_skips += delta - 1
                if lcd_index == last_lcd_index:
                    lcd_frame_repeats += 1
                else:
                    delta = (lcd_index - last_lcd_index) % len(frames)
                    if delta > 1: lcd_frame_skips += delta - 1
            last_content_index, last_lcd_index = content_index, lcd_index

            raw.send(frames[lcd_index].data)
            upload_finished = time.monotonic()
            upload_s = upload_finished - upload_started
            recent_uploads.append(upload_s)
            histogram[upload_histogram_bucket(upload_s)] += 1
            max_upload_s = max(max_upload_s, upload_s)
            upload_ema_s = upload_s if upload_ema_s is None else upload_ema_s * 0.85 + upload_s * 0.15
            transport_frames += 1

            interval_s = 1.0 / transport_fps
            if transport_mode == "cam":
                next_start, missed, overrun, phase_debt_s = next_phase_locked_start(
                    upload_started, upload_finished, interval_s, phase_debt_s
                )
            else:
                next_start, missed = next_transfer_start(upload_started, upload_finished, interval_s)
                overrun = max(
                    0.0,
                    (upload_finished + SAFE_DISPLAY_GUARD_S) - (upload_started + interval_s),
                ) if missed else 0.0
            if missed:
                deadline_misses += 1
                total_overrun_s += overrun
                max_overrun_s = max(max_overrun_s, overrun)

            now = time.monotonic()
            if now - report_started >= 5.0:
                recent = list(recent_uploads)
                emit(
                    "stats",
                    effective_fps=round(transport_frames / max(0.001, now - stream_started), 1),
                    content_fps=content_fps,
                    transport_fps=round(transport_fps, 3),
                    last_upload_ms=round(upload_s * 1000, 1),
                    upload_ema_ms=round((upload_ema_s or 0) * 1000, 1),
                    p90_upload_ms=round(percentile(recent, ADAPT_PERCENTILE) * 1000, 1),
                    max_upload_ms=round(max_upload_s * 1000, 1),
                    deadline_misses=deadline_misses,
                    total_overrun_ms=round(total_overrun_s * 1000, 1),
                    max_overrun_ms=round(max_overrun_s * 1000, 2),
                    content_repeats=content_repeats,
                    content_skips=content_skips,
                    lcd_frame_repeats=lcd_frame_repeats,
                    lcd_frame_skips=lcd_frame_skips,
                    histogram=dict(histogram),
                    skipped=0,
                    frames_sent=transport_frames,
                    pacing=transport_policy_name(transport_mode),
                    device_paced=False,
                    phase_locked=phase_locked,
                    phase_debt_ms=round(phase_debt_s * 1000, 2),
                    interpolation=interpolate,
                    interpolation_kind=metadata["interpolation_kind"],
                    motion_pairs=metadata["motion_pairs"],
                    raw_transport=True,
                    ack_matching=True,
                    unrelated_hid_reports=raw.unrelated_hid_reports,
                )
                report_started = now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CAM-nearer Kraken 2023 firmware-2.x LCD streamer")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--hardware-spec", type=Path)
    parser.add_argument("--orientation", type=int, choices=(0, 90, 180, 270), default=0)
    parser.add_argument("--fps", type=int, choices=(0, 5, 8, 10, 12, 15, 20, 24, 25, 26, 27), default=0)
    parser.add_argument("--transport", choices=("cam", "safe"), default="cam")
    parser.add_argument("--interpolate", action="store_true", help="Use motion-compensated intermediate frames")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.hardware_spec if args.hardware_spec is not None else args.file
    if source_path is None or not source_path.exists():
        emit("error", message="GIF- oder Hardwareanimations-Datei wurde nicht gefunden.")
        return 2
    if args.file is not None and args.file.suffix.lower() != ".gif":
        emit("error", message="Der GIF-Streamer akzeptiert nur .gif-Dateien.")
        return 2
    try:
        return run_stream(
            args.file,
            args.orientation,
            args.fps,
            args.interpolate,
            args.transport,
            hardware_spec_path=args.hardware_spec,
        )
    except KeyboardInterrupt:
        emit("stopped", reason="keyboard")
        return 0
    except Exception as exc:  # noqa: BLE001
        emit("error", message=str(exc), kind=exc.__class__.__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

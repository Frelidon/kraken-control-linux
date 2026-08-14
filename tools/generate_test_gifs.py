#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate deterministic 240x240 GIF motion tests with exact average FPS timing."""
from __future__ import annotations

import colorsys
import math
from pathlib import Path
from PIL import Image, ImageDraw

SIZE = 240
TARGET_FPS = (24, 25, 26, 27)
MOVING_BAR_STEP = 4
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test-gifs"


def one_second_durations(fps: int) -> list[int]:
    """GIF delays are 10 ms units; distribute floor/ceil delays to total 1000 ms."""
    floor_ms = max(20, (1000 // fps // 10) * 10)
    ceil_ms = floor_ms + 10
    extra = 1000 - (fps * floor_ms)
    n_ceil = extra // 10
    if n_ceil < 0 or n_ceil > fps or (fps - n_ceil) * floor_ms + n_ceil * ceil_ms != 1000:
        raise ValueError(f"FPS {fps} cannot be represented with 10 ms GIF timing")
    # Evenly distribute the longer delays instead of clustering them.
    durations = []
    accumulator = 0
    for _ in range(fps):
        accumulator += n_ceil
        if accumulator >= fps:
            durations.append(ceil_ms)
            accumulator -= fps
        else:
            durations.append(floor_ms)
    assert len(durations) == fps and sum(durations) == 1000
    return durations


def save_gif(path: Path, frames: list[Image.Image], durations: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        optimize=False,
    )


def color_cycle(fps: int) -> tuple[list[Image.Image], list[int]]:
    durations = one_second_durations(fps)
    frames: list[Image.Image] = []
    for i in range(fps):
        hue = i / fps
        r, g, b = (round(v * 255) for v in colorsys.hsv_to_rgb(hue, 1.0, 1.0))
        image = Image.new("RGB", (SIZE, SIZE), (r, g, b))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, SIZE - 26, SIZE, SIZE), fill=(0, 0, 0))
        draw.text((8, SIZE - 21), f"COLOR {fps} FPS  {i + 1:02d}/{fps}", fill=(255, 255, 255))
        frames.append(image)
    return frames, durations


def moving_bars(fps: int) -> tuple[list[Image.Image], list[int]]:
    durations = one_second_durations(fps) * 2
    count = fps * 2
    period = count * MOVING_BAR_STEP
    spacing = period // 4
    frames: list[Image.Image] = []
    colors = [(255, 70, 70), (70, 255, 100), (70, 150, 255), (255, 220, 60)]
    for i in range(count):
        image = Image.new("RGB", (SIZE, SIZE), (10, 12, 18))
        draw = ImageDraw.Draw(image)
        # Thin reference grid makes micro-stutter easy to see.
        for x in range(0, SIZE, 20):
            draw.line((x, 0, x, SIZE), fill=(32, 36, 46), width=1)
        for y in range(0, SIZE, 20):
            draw.line((0, y, SIZE, y), fill=(32, 36, 46), width=1)
        # The 25-FPS reference has 50 frames.  A four-pixel step over the
        # 200-pixel coloured-bar period makes all 50 transitions, including
        # last -> first, exactly equal.  Duplicate wrapped bars keep the full
        # 240-pixel LCD covered without introducing a loop jump.
        base = (i * MOVING_BAR_STEP) % period
        for j, color in enumerate(colors):
            center = (base + j * spacing) % period - 14
            for x in (center - period, center, center + period):
                draw.rectangle((x - 6, 0, x + 6, SIZE - 28), fill=color)
        draw.rectangle((0, SIZE - 28, SIZE, SIZE), fill=(0, 0, 0))
        draw.text((8, SIZE - 22), f"MOVING BARS {fps} FPS", fill=(255, 255, 255))
        frames.append(image)
    return frames, durations


def diagonal_sweep_27() -> tuple[list[Image.Image], list[int]]:
    fps = 27
    durations = one_second_durations(fps)
    frames: list[Image.Image] = []
    for i in range(fps):
        image = Image.new("RGB", (SIZE, SIZE), (8, 10, 16))
        draw = ImageDraw.Draw(image)
        offset = int((i / fps) * (SIZE * 2)) - SIZE
        for delta, width, value in ((0, 9, 255), (-12, 4, 120), (12, 4, 120)):
            draw.line((offset + delta, 0, offset + SIZE + delta, SIZE), fill=(value, 220, 255), width=width)
        draw.text((8, 8), "DIAGONAL 27 FPS", fill=(255, 255, 255))
        frames.append(image)
    return frames, durations


def checker_scroll_27() -> tuple[list[Image.Image], list[int]]:
    fps = 27
    durations = one_second_durations(fps)
    frames: list[Image.Image] = []
    tile = 24
    for i in range(fps):
        image = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        offset = round((i / fps) * tile * 2)
        for gy in range(-2, SIZE // tile + 3):
            for gx in range(-2, SIZE // tile + 3):
                x0 = gx * tile + offset
                y0 = gy * tile + offset
                color = (235, 235, 235) if (gx + gy) % 2 == 0 else (35, 35, 45)
                draw.rectangle((x0, y0, x0 + tile - 1, y0 + tile - 1), fill=color)
        draw.rectangle((0, SIZE - 28, SIZE, SIZE), fill=(0, 0, 0))
        draw.text((8, SIZE - 22), "CHECKER SCROLL 27 FPS", fill=(255, 255, 255))
        frames.append(image)
    return frames, durations


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fps in TARGET_FPS:
        frames, durations = color_cycle(fps)
        save_gif(OUT / f"01_color-cycle_{fps}fps.gif", frames, durations)
        frames, durations = moving_bars(fps)
        save_gif(OUT / f"02_moving-bars_{fps}fps.gif", frames, durations)
    frames, durations = diagonal_sweep_27()
    save_gif(OUT / "03_diagonal-sweep_27fps.gif", frames, durations)
    frames, durations = checker_scroll_27()
    save_gif(OUT / "04_checker-scroll_27fps.gif", frames, durations)


if __name__ == "__main__":
    main()

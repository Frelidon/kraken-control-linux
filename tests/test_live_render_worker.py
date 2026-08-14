#!/usr/bin/env python3
"""Check the isolated live-cache process used during USB streaming."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kraken_cam_streamer import (  # noqa: E402
    HardwareSpec,
    RGB565_FRAME_BYTES,
    frames_from_cache_file,
    render_hardware_cache_worker,
)


def main() -> None:
    spec = HardwareSpec("system_trio", "#00c8ff", 32.4, 61.2, 55.8, "de", 125, 25)
    with tempfile.TemporaryDirectory(prefix="kraken-live-worker-") as td:
        output = Path(td) / "cache.rgb565"
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            result = executor.submit(
                render_hardware_cache_worker,
                spec,
                0,
                "cam",
                str(output),
            ).result(timeout=20)
        count = int(result["transport_cache_frames"])
        assert count == 27
        assert output.stat().st_size == count * RGB565_FRAME_BYTES
        frames = frames_from_cache_file(output, count, 1.0)
        assert len(frames) == count
        assert len({frame.data for frame in frames}) == count

    print("Spawned live hardware cache renderer and atomic cache handoff passed.")


if __name__ == "__main__":
    main()

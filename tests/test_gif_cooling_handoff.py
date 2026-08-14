#!/usr/bin/env python3
"""Regression test for cached GIF pause/write/resume ownership handoff."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import kraken_cam_streamer as streamer  # noqa: E402


class FakeConnection:
    def __init__(self, device: "FakeDevice"):
        self.device = device

    def __enter__(self):
        self.device.connects += 1
        return self.device

    def __exit__(self, _exc_type, _exc, _tb):
        self.device.disconnects += 1


class FakeDevice:
    connects = 0
    disconnects = 0

    def connect(self):
        return FakeConnection(self)


class FakeRaw:
    instances: list["FakeRaw"] = []

    def __init__(self, _device):
        self.sent: list[bytes] = []
        self.unrelated_hid_reports = 0
        self.__class__.instances.append(self)

    def send(self, data: bytes):
        self.sent.append(data)


class GifCoolingHandoffTests(unittest.TestCase):
    def test_stream_releases_device_and_resumes_from_cached_frames(self):
        device = FakeDevice()
        FakeRaw.instances.clear()
        frame_a = streamer.PreparedFrame(b"a" * streamer.RGB565_FRAME_BYTES, 0.04)
        frame_b = streamer.PreparedFrame(b"b" * streamer.RGB565_FRAME_BYTES, 0.04)
        metadata = {
            "source_frames": 1,
            "content_frames": 2,
            "output_frames": 2,
            "transport_cache_frames": 2,
            "transport_cache_fps": 2.0,
            "source_duration_ms": 1000,
            "source_duration_s": 1.0,
            "target_fps": 2,
            "content_fps": 2.0,
            "transport_fps": streamer.CAM_TRANSPORT_FPS,
            "transport_mode": "cam",
            "interpolation": False,
            "interpolation_kind": "none",
            "interpolated_transport_frames": 0,
            "motion_pairs": 0,
            "unique_transport_frames": 2,
            "loop_warning": False,
            "loop_transition_score": 0.0,
            "typical_transition_score": 0.0,
            "loop_warning_ratio": 0.0,
        }
        events: list[dict[str, object]] = []

        def capture(event: str, **payload):
            events.append({"event": event, **payload})

        with (
            patch.object(streamer, "prepare_gif", return_value=([frame_a, frame_b], metadata)),
            patch.object(streamer, "find_kraken", return_value=device),
            patch.object(streamer, "CamRawTransport", FakeRaw),
            patch.object(streamer, "read_control_command", side_effect=["PAUSE", "RESUME", None, "STOP"]),
            patch.object(streamer, "emit", side_effect=capture),
        ):
            result = streamer.run_stream(Path("test.gif"), 0, 25, False, "cam")

        self.assertEqual(result, 0)
        self.assertEqual(device.connects, 2)
        self.assertEqual(device.disconnects, 2)
        self.assertEqual([event["event"] for event in events], ["ready", "started", "paused", "resumed", "stopped"])
        self.assertEqual(len(FakeRaw.instances), 2)
        self.assertEqual(len(FakeRaw.instances[0].sent), 2)
        self.assertEqual(FakeRaw.instances[0].sent, [frame_a.data, frame_a.data])
        self.assertEqual(FakeRaw.instances[1].sent, [frame_b.data, frame_b.data, frame_a.data])
        self.assertEqual(events[2]["reason"], "cooling-write")
        self.assertEqual(events[3]["prime_uploads"], 2)
        self.assertEqual(events[3]["lcd_index"], 1)
        self.assertEqual(events[3]["frames_sent"], 1)
        self.assertEqual(events[4]["frames_sent"], 2)

    def test_control_commands_are_strict(self):
        for raw, expected in (("PAUSE\n", "PAUSE"), ("resume\n", "RESUME"), ("STOP\n", "STOP"), ("other\n", None)):
            with patch.object(streamer.select, "select", return_value=([sys.stdin], [], [])), patch.object(streamer.sys, "stdin") as stdin:
                stdin.readline.return_value = raw
                self.assertEqual(streamer.read_control_command(0), expected)


if __name__ == "__main__":
    unittest.main()

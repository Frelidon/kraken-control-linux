#!/usr/bin/env python3
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import tempfile
import warnings

from PIL import Image, ImageChops, ImageDraw, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = spec_from_file_location("kraken_cam_streamer", ROOT / "kraken_cam_streamer.py")
mod = module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

assert mod.MAX_STREAM_FPS == 27
assert mod.DEFAULT_ADAPTIVE_FPS_CAP == 25
assert abs(mod.CAM_TRANSPORT_FPS - (80/3)) < 1e-12
assert mod.SAFE_TRANSPORT_FPS == 25.6
assert mod.requested_transport_fps("cam") == mod.CAM_TRANSPORT_FPS
assert mod.requested_transport_fps("safe") == 25.6
assert mod.transport_policy_name("cam") == "cam-raw-26.667hz-phase-locked"
assert mod.transport_policy_name("safe") == "cam-raw-safe-25.6hz-phase-locked"
assert mod.RGB565_FRAME_BYTES == 115200

with warnings.catch_warnings():
    warnings.simplefilter("error", DeprecationWarning)
    assert mod.rgb565_bytes(Image.new("RGB", (1, 1), (255, 0, 0))) == bytes([0xF8, 0x00])
    assert mod.rgb565_bytes(Image.new("RGB", (1, 1), (0, 255, 0))) == bytes([0x07, 0xE0])
    assert mod.rgb565_bytes(Image.new("RGB", (1, 1), (0, 0, 255))) == bytes([0x00, 0x1F])

# Motion estimator: a high-contrast bar translated to the right must produce a
# confident non-zero horizontal vector, and motion interpolation must differ
# from a plain 50/50 crossfade.
a = Image.new("RGB", (240, 240), "black")
d = ImageDraw.Draw(a)
d.rectangle((60, 0, 80, 239), fill="white")
b = ImageChops.offset(a, 16, 0)
motion = mod.estimate_global_motion(a, b)
assert motion.confidence >= mod.MOTION_MIN_IMPROVEMENT, motion
assert abs(motion.dx) >= 8 and abs(motion.dy) <= 4, motion
mid_motion = mod.motion_interpolate(a, b, motion, 0.5)
mid_blend = Image.blend(a, b, 0.5)
assert mid_motion.tobytes() != mid_blend.tobytes()

with tempfile.TemporaryDirectory() as td:
    path = Path(td) / "test.gif"
    frames = [Image.new("RGB", (40, 30), c) for c in ((255,0,0),(0,255,0),(0,0,255),(255,255,255))]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=[250]*4, loop=0)

    cam, meta = mod.prepare_gif(path, 0, 25, interpolate=True, transport_mode="cam")
    assert meta["source_frames"] == 4
    assert meta["source_duration_ms"] == 1000
    assert meta["content_frames"] == 25
    assert meta["content_fps"] == 25
    assert abs(meta["transport_fps"] - 26.667) < 0.001
    assert meta["transport_cache_frames"] == 27
    assert meta["loop_warning"] is False
    assert meta["interpolation_kind"] == "motion-compensated-global"
    assert all(len(frame.data) == 240*240*2 for frame in cam)

    safe, safe_meta = mod.prepare_gif(path, 0, 25, interpolate=True, transport_mode="safe")
    assert safe_meta["transport_cache_frames"] == 26
    assert safe_meta["transport_fps"] == 25.6

    off, off_meta = mod.prepare_gif(path, 0, 25, interpolate=False, transport_mode="cam")
    assert off_meta["interpolation_kind"] == "off"
    assert off_meta["motion_pairs"] == 0

    assert mod.prepared_frame_index(cam, 0.000, 1.0) == 0
    assert mod.prepared_frame_index(cam, 0.999, 1.0) == len(cam)-1
    assert mod.prepared_frame_index(cam, 1.001, 1.0) == 0

    hardware_path = Path(td) / "hardware.json"
    hardware_path.write_text(json.dumps({
        "schema": 1,
        "design_id": "system_trio",
        "accent_hex": "#39ff88",
        "liquid": 32.4,
        "cpu": 61.2,
        "gpu": 55.8,
        "language": "de",
        "font_scale_percent": 135,
        "content_fps": 25,
    }), encoding="utf-8")
    hardware_spec = mod.load_hardware_spec(hardware_path)
    hardware_frames, hardware_meta = mod.prepare_hardware_animation(hardware_spec, 0, "cam")
    assert len(hardware_frames) == 27
    assert hardware_meta["hardware_live"] is True
    assert hardware_meta["liquid_snapshot"] == 32.4
    assert hardware_meta["sensor_interval_s"] == 2.0
    assert len({frame.data for frame in hardware_frames}) == 27
    assert mod.hardware_dynamic_fields("water_halo") == (False, False)
    assert mod.hardware_dynamic_fields("cpu_gpu_dual") == (True, True)
    assert mod.displayed_temperature(61.49) == 61
    assert mod.displayed_temperature(61.51) == 62

    # A gradual animation with a large final-to-first reset must be reported as
    # a probable visible loop transition, without rejecting the GIF.
    jump_path = Path(td) / "visible-loop.gif"
    jump_frames = [Image.new("RGB", (40, 40), (value, value, value)) for value in range(0, 121, 10)]
    jump_frames[0].save(jump_path, save_all=True, append_images=jump_frames[1:], duration=[40] * len(jump_frames), loop=0)
    _, jump_meta = mod.prepare_gif(jump_path, 0, 25, interpolate=False, transport_mode="cam")
    assert jump_meta["loop_warning"] is True, jump_meta
    assert jump_meta["loop_transition_score"] > jump_meta["typical_transition_score"] * 5

# Direct CAM-style FW2 transaction must clear stale reports and match the exact
# 37 01 / 37 02 replies around the bulk header and contiguous RGB565 payload.
class FakeHid:
    def __init__(self, owner): self.owner=owner
    def clear_enqueued_reports(self): self.owner.calls.append(("clear",))

class FakeDev:
    bulk_device = object()
    def __init__(self):
        self.calls=[]
        self.replies=[]
        self.device=FakeHid(self)
    def _write(self, data):
        self.calls.append(("ctl", list(data)))
        # An unsolicited status packet before the real response must be ignored.
        self.replies.append(bytes([0x75,0x02])+bytes(62))
        self.replies.append(bytes([data[0]+1,data[1]])+bytes(62))
    def _read(self): return self.replies.pop(0)
    def _bulk_write(self, data): self.calls.append(("bulk", bytes(data)))

fake = FakeDev()
raw = mod.CamRawTransport(fake)
payload = bytes(mod.RGB565_FRAME_BYTES)
raw.send(payload)
assert fake.calls[0] == ("clear",)
assert fake.calls[1] == ("ctl", mod.CamRawTransport.START)
assert fake.calls[2][0] == "bulk" and len(fake.calls[2][1]) == 20
assert fake.calls[3] == ("bulk", payload)
assert fake.calls[4] == ("clear",)
assert fake.calls[5] == ("ctl", mod.CamRawTransport.END)
assert raw.unrelated_hid_reports == 2

class BadAckDev(FakeDev):
    def _write(self, data):
        self.calls.append(("ctl", list(data)))
        self.replies.append(bytes([0x75,0x02])+bytes(62))
    def _read(self):
        return self.replies.pop(0) if self.replies else b""

try:
    mod.CamRawTransport(BadAckDev()).send(payload)
    raise AssertionError("missing matching ACK did not abort")
except RuntimeError as exc:
    assert "Keine passende Kraken-Antwort 37 01" in str(exc)

next_start, guarded = mod.next_transfer_start(10.000, 10.016, 1/mod.CAM_TRANSPORT_FPS)
assert guarded is False
next_start, guarded = mod.next_transfer_start(10.000, 10.040, 1/mod.CAM_TRANSPORT_FPS)
assert guarded is True and next_start > 10.040
# 2.9.19/2.9.20 phase lock: one 0.7-ms full window is repaid only from
# genuine slack and never faster than 0.25 ms per following interval.
interval = 1 / mod.CAM_TRANSPORT_FPS
next_start, missed, overrun, debt = mod.next_phase_locked_start(
    10.0, 10.0 + interval + 0.0006, interval, 0.0
)
assert missed is True
assert abs(overrun - 0.0007) < 1e-12
assert abs(debt - 0.0007) < 1e-12
slow_start = next_start
next_start, missed, overrun, debt = mod.next_phase_locked_start(slow_start, slow_start + 0.016, interval, debt)
assert missed is False and overrun == 0.0
assert abs((next_start - slow_start) - (interval - 0.00025)) < 1e-12
assert abs(debt - 0.00045) < 1e-12

# Ten-minute logical simulation: injected full windows never overlap, never
# cause a catch-up burst and their small debt returns to zero.
start = 0.0
debt = 0.0
minimum_gap = interval
misses = 0
maximum_debt = 0.0
for i in range(16000):
    upload = interval + 0.0006 if i and i % 761 == 0 else 0.016
    following, missed, _, debt = mod.next_phase_locked_start(start, start + upload, interval, debt)
    minimum_gap = min(minimum_gap, following - start)
    misses += int(missed)
    maximum_debt = max(maximum_debt, debt)
    start = following
assert misses == 21
assert minimum_gap >= interval - mod.MAX_PHASE_CORRECTION_STEP_S - 1e-12
assert maximum_debt <= 0.0007 + 1e-12
assert debt == 0.0

assert mod.upload_histogram_bucket(0.019) == "lt20"
assert mod.upload_histogram_bucket(0.025) == "20_30"
assert mod.upload_histogram_bucket(0.033) == "30_35"
assert mod.upload_histogram_bucket(0.039) == "35_42"
assert mod.upload_histogram_bucket(0.043) == "ge42"

for fps in (24,25,26,27):
    for stem in ("01_color-cycle","02_moving-bars"):
        gif=ROOT/"test-gifs"/f"{stem}_{fps}fps.gif"
        assert gif.exists(), gif
        with Image.open(gif) as source:
            source_frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(source)]
            durations=[int(frame.info.get("duration",0)) for frame in ImageSequence.Iterator(source)]
        assert abs(len(durations)/(sum(durations)/1000.0)-fps)<1e-9
        if stem == "02_moving-bars":
            samples = [mod.SourceFrame(frame, duration / 1000.0) for frame, duration in zip(source_frames, durations)]
            diagnostics = mod.loop_transition_diagnostics(samples)
            assert diagnostics["loop_warning"] is False, (gif, diagnostics)

assert not (ROOT/"test-gifs"/"02_moving-bars_30fps.gif").exists()
assert not (ROOT/"test-gifs"/"02_moving-bars_32fps.gif").exists()
print("GIF 2.9.23 phase-locked CAM transport, live hardware cache and timing checks passed.")

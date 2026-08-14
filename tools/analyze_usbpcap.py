#!/usr/bin/env python3
"""Summarize Kraken 2023 LCD transactions from USBPcap .pcap files."""

from __future__ import annotations

import argparse
import bisect
import json
import statistics
import struct
from pathlib import Path

PCAP_GLOBAL = struct.Struct("<IHHIIII")
PCAP_RECORD = struct.Struct("<IIII")
USBPCAP_HEADER = struct.Struct("<HQIHBHHBBI")
PCAP_MAGIC_USEC_LE = 0xA1B2C3D4
USBPCAP_LINKTYPE = 249


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1)))]


def largest_continuous_segment(values: list[float], gap_s: float = 0.5) -> list[float]:
    segments: list[list[float]] = [[]]
    for value in values:
        if segments[-1] and value - segments[-1][-1] > gap_s:
            segments.append([])
        segments[-1].append(value)
    return max(segments, key=len, default=[])


def read_payload_events(path: Path):
    with path.open("rb") as stream:
        global_header = stream.read(PCAP_GLOBAL.size)
        if len(global_header) != PCAP_GLOBAL.size:
            raise ValueError("PCAP-Globalheader fehlt oder ist unvollständig")
        magic, _major, _minor, _zone, _sigfigs, _snaplen, linktype = PCAP_GLOBAL.unpack(global_header)
        if magic != PCAP_MAGIC_USEC_LE or linktype != USBPCAP_LINKTYPE:
            raise ValueError("Nur Little-Endian-USBPcap mit Mikrosekunden-Zeitstempeln wird unterstützt")
        while True:
            record_header = stream.read(PCAP_RECORD.size)
            if not record_header:
                break
            if len(record_header) != PCAP_RECORD.size:
                raise ValueError("Abgeschnittener PCAP-Datensatzheader")
            sec, usec, included, _original = PCAP_RECORD.unpack(record_header)
            packet = stream.read(included)
            if len(packet) != included or len(packet) < USBPCAP_HEADER.size:
                continue
            header_len, _irp, _status, _function, info, bus, device, endpoint, transfer, _length = USBPCAP_HEADER.unpack(
                packet[: USBPCAP_HEADER.size]
            )
            if header_len > len(packet):
                continue
            payload = packet[header_len:]
            if payload:
                yield sec + usec / 1_000_000.0, bus, device, endpoint, transfer, info, payload


def analyze(path: Path) -> dict[str, object]:
    starts: list[float] = []
    start_acks: list[float] = []
    payloads: list[float] = []
    ends: list[float] = []
    end_acks: list[float] = []
    commands: dict[str, int] = {}
    for time_s, _bus, _device, endpoint, _transfer, info, payload in read_payload_events(path):
        prefix = payload[:2]
        if endpoint == 1 and info == 0:
            key = prefix.hex()
            commands[key] = commands.get(key, 0) + 1
            if prefix == b"\x36\x01":
                starts.append(time_s)
            elif prefix == b"\x36\x02":
                ends.append(time_s)
        elif endpoint == 129 and info == 1:
            if prefix == b"\x37\x01":
                start_acks.append(time_s)
            elif prefix == b"\x37\x02":
                end_acks.append(time_s)
        elif endpoint == 2 and info == 0 and len(payload) == 115200:
            payloads.append(time_s)

    segment = largest_continuous_segment(starts)
    intervals = [b - a for a, b in zip(segment, segment[1:])]
    full = [b - a for a, b in zip(starts, end_acks) if 0 <= b - a < 1.0]
    handoff_gaps: list[float] = []
    for start in segment[1:]:
        previous_ack = bisect.bisect_left(end_acks, start) - 1
        if previous_ack >= 0:
            gap = start - end_acks[previous_ack]
            if 0 <= gap < 0.1:
                handoff_gaps.append(gap)

    def timing(values: list[float]) -> dict[str, float]:
        return {
            "mean_ms": round(statistics.mean(values) * 1000, 3) if values else 0.0,
            "median_ms": round(statistics.median(values) * 1000, 3) if values else 0.0,
            "p90_ms": round(percentile(values, 0.90) * 1000, 3) if values else 0.0,
            "min_ms": round(min(values) * 1000, 3) if values else 0.0,
            "max_ms": round(max(values) * 1000, 3) if values else 0.0,
        }

    duration = segment[-1] - segment[0] if len(segment) > 1 else 0.0
    return {
        "file": path.name,
        "start_commands": len(starts),
        "start_acks": len(start_acks),
        "rgb565_payloads": len(payloads),
        "end_commands": len(ends),
        "end_acks": len(end_acks),
        "continuous_frames": len(segment),
        "continuous_duration_s": round(duration, 3),
        "continuous_rate_hz": round((len(segment) - 1) / duration, 3) if duration else 0.0,
        "start_intervals": timing(intervals),
        "full_transactions": timing(full),
        "end_ack_to_next_start": timing(handoff_gaps),
        "end_ack_to_next_start_samples": len(handoff_gaps),
        "out_command_prefixes": dict(sorted(commands.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pcap", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([analyze(path) for path in args.pcap], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

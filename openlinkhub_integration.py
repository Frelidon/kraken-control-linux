#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe local OpenLinkHub discovery, service and control integration.

The GUI invokes this dependency-free helper out of process.  It deliberately
limits API access to the loopback interface.  Version 3.0.9 exposes a bounded
allow-list of documented OpenLinkHub write endpoints; arbitrary paths and
arbitrary JSON are never accepted from the GUI.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_API_URL = "http://127.0.0.1:27003"
SERVICE_NAME = "OpenLinkHub.service"
USER_ACTIONS = {"start", "stop", "restart", "enable", "disable"}
MAX_API_RESPONSE_BYTES = 4 * 1024 * 1024
CONTROL_ID_RE = re.compile(r"^[0-9a-f]{64}$")

# Actions are intentionally named independently from HTTP paths.  The caller
# cannot select a URL or method and every payload is rebuilt after validation.
WRITE_ENDPOINTS = {
    "speed-profile": ("POST", "/api/speed"),
    "speed-manual": ("POST", "/api/speed/manual"),
    "rgb-profile": ("POST", "/api/color"),
    "label": ("POST", "/api/label"),
    "brightness": ("POST", "/api/brightness/gradual"),
    "lcd-rotation": ("POST", "/api/lcd/rotation"),
    "mouse-dpi": ("POST", "/api/mouse/dpi"),
    "mouse-polling": ("POST", "/api/mouse/pollingRate"),
    "mouse-sleep": ("POST", "/api/mouse/sleep"),
    "mouse-angle-snapping": ("POST", "/api/mouse/angleSnapping"),
    "mouse-button-optimization": ("POST", "/api/mouse/buttonOptimization"),
    "mouse-key-assignment": ("POST", "/api/mouse/updateKeyAssignment"),
    "macro-create-recording": ("MULTI", "/api/macro/new"),
    "keyboard-user-profile": ("POST", "/api/userProfile/change"),
    "keyboard-profile": ("POST", "/api/keyboard/profile/change"),
    "keyboard-layout": ("POST", "/api/keyboard/layout"),
    "keyboard-dial": ("POST", "/api/keyboard/dial"),
    "keyboard-sleep": ("POST", "/api/keyboard/sleep"),
    "keyboard-polling": ("POST", "/api/keyboard/pollingRate"),
    "psu-speed": ("POST", "/api/psu/speed"),
    "headset-sleep": ("POST", "/api/headset/sleep"),
    "headset-mute-indicator": ("POST", "/api/headset/muteIndicator"),
    "headset-anc": ("POST", "/api/headset/anc"),
    "headset-sidetone": ("POST", "/api/headset/sidetone"),
    "headset-sidetone-value": ("POST", "/api/headset/sidetoneValue"),
}


def validate_local_api_url(value: str) -> str:
    """Return a normalized loopback OpenLinkHub URL or raise ValueError."""
    raw = value.strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("Nur eine lokale HTTP-Adresse ohne Zugangsdaten ist erlaubt.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Die API-Adresse darf keinen Pfad, Query oder Fragment enthalten.")
    if parsed.hostname is None or parsed.port is None:
        raise ValueError("Die API-Adresse benötigt Host und Port.")
    hostname = parsed.hostname.lower()
    loopback = hostname == "localhost"
    if not loopback:
        try:
            loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            loopback = False
    if not loopback:
        raise ValueError("OpenLinkHub wird aus Sicherheitsgründen nur über Loopback angesprochen.")
    return f"http://{parsed.netloc}"


def _run(args: list[str], timeout: float = 4.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(args, 127, "", str(exc))


def _service_state(*, user: bool) -> dict[str, Any]:
    args = ["systemctl"]
    if user:
        args.append("--user")
    args.extend([
        "show", SERVICE_NAME, "--no-pager",
        "--property=LoadState,ActiveState,SubState,UnitFileState",
    ])
    result = _run(args)
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    load = values.get("LoadState", "unknown")
    return {
        "available": load not in {"not-found", "unknown", ""},
        "load": load,
        "active": values.get("ActiveState", "unknown"),
        "sub": values.get("SubState", "unknown"),
        "enabled": values.get("UnitFileState", "unknown"),
        "error": "" if result.returncode == 0 else (result.stderr.strip() or "systemctl nicht erreichbar"),
    }


def installed_version() -> str:
    for package in ("OpenLinkHub", "openlinkhub"):
        result = _run(["rpm", "-q", "--qf", "%{VERSION}-%{RELEASE}", package])
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    binary = "/opt/OpenLinkHub/OpenLinkHub"
    if os.path.isfile(binary) or shutil.which("OpenLinkHub"):
        return "installiert (Version unbekannt)"
    return "nicht erkannt"


def _api_request(
    base_url: str,
    endpoint: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: float = 2.5,
) -> Any:
    if not endpoint.startswith("/api/") or "?" in endpoint or "#" in endpoint:
        raise ValueError("Ungültiger OpenLinkHub-API-Pfad")
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        f"{validate_local_api_url(base_url)}{endpoint}",
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Open-Hardware-Control/3.0.9",
        },
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback validated above
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        raw = response.read(MAX_API_RESPONSE_BYTES + 1)
        if len(raw) > MAX_API_RESPONSE_BYTES:
            raise RuntimeError("OpenLinkHub-Antwort überschreitet 4 MiB")
        result = json.loads(raw.decode("utf-8"))
    if isinstance(result, dict):
        code = result.get("code")
        if isinstance(code, int) and code >= 400:
            message = result.get("message") or result.get("error") or f"API-Fehler {code}"
            raise RuntimeError(str(message))
    return result


def _api_get(base_url: str, endpoint: str, timeout: float = 2.5) -> Any:
    return _api_request(base_url, endpoint, timeout=timeout)


def _control_id(device_id: str) -> str:
    return hashlib.sha256(device_id.encode("utf-8")).hexdigest()


def _safe_control_id(value: Any) -> str:
    control_id = str(value or "").strip().lower()
    if not CONTROL_ID_RE.fullmatch(control_id):
        raise ValueError("Ungültige OpenLinkHub-Steuerkennung")
    return control_id


def _safe_int(payload: dict[str, Any], key: str, minimum: int, maximum: int) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{key} muss zwischen {minimum} und {maximum} liegen")
    return value


def _safe_choice(payload: dict[str, Any], key: str, choices: set[int]) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value not in choices:
        raise ValueError(f"Ungültiger Wert für {key}")
    return value


def _safe_text(payload: dict[str, Any], key: str, *, maximum: int = 64) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} muss Text sein")
    value = value.strip()
    if not value or len(value) > maximum or any(ord(char) < 32 for char in value):
        raise ValueError(f"Ungültiger Text für {key}")
    return value


def validate_write_payload(action: str, payload: Any) -> dict[str, Any]:
    """Build the exact documented OpenLinkHub JSON payload for one action."""
    if action not in WRITE_ENDPOINTS or not isinstance(payload, dict):
        raise ValueError("Nicht erlaubter OpenLinkHub-Schreibbefehl")
    control_id = _safe_control_id(payload.get("control_id"))
    if action == "speed-profile":
        return {
            "_controlId": control_id,
            "channelId": _safe_int(payload, "channel_id", 0, 255),
            "profile": _safe_text(payload, "profile"),
        }
    if action == "speed-manual":
        return {
            "_controlId": control_id,
            "channelId": _safe_int(payload, "channel_id", 0, 255),
            "value": _safe_int(payload, "value", 0, 100),
        }
    if action == "rgb-profile":
        return {
            "_controlId": control_id,
            "channelId": _safe_int(payload, "channel_id", -1, 255),
            "profile": _safe_text(payload, "profile"),
        }
    if action == "label":
        return {
            "_controlId": control_id,
            "channelId": _safe_int(payload, "channel_id", 0, 255),
            "deviceType": _safe_int(payload, "device_type", 0, 255),
            "label": _safe_text(payload, "label", maximum=48),
        }
    if action == "brightness":
        return {"_controlId": control_id, "brightness": _safe_int(payload, "brightness", 0, 100)}
    if action == "lcd-rotation":
        return {
            "_controlId": control_id,
            "channelId": _safe_int(payload, "channel_id", 0, 255),
            "rotation": _safe_choice(payload, "rotation", {0, 1, 2, 3}),
        }
    if action == "mouse-dpi":
        stages = payload.get("stages")
        if not isinstance(stages, dict) or set(stages) != {"0", "1", "2", "3", "4"}:
            raise ValueError("Es werden genau fünf DPI-Stufen benötigt")
        clean_stages = {
            key: _safe_int({"dpi": value}, "dpi", 100, 30000)
            for key, value in stages.items()
        }
        return {"_controlId": control_id, "stages": clean_stages}
    if action == "mouse-polling":
        return {"_controlId": control_id, "pollingRate": _safe_choice(payload, "polling_rate", {1, 2, 3, 4})}
    if action == "mouse-sleep":
        return {"_controlId": control_id, "sleepMode": _safe_choice(payload, "sleep_mode", {1, 5, 10, 15, 30, 60})}
    if action == "mouse-angle-snapping":
        return {"_controlId": control_id, "angleSnapping": _safe_choice(payload, "enabled", {0, 1})}
    if action == "mouse-button-optimization":
        return {"_controlId": control_id, "buttonOptimization": _safe_choice(payload, "enabled", {0, 1})}
    if action == "mouse-key-assignment":
        press_and_hold = bool(_safe_choice(payload, "press_and_hold", {0, 1}))
        on_release = bool(_safe_choice(payload, "on_release", {0, 1}))
        if press_and_hold and on_release:
            raise ValueError("Gedrückt halten und Beim Loslassen schließen einander aus")
        return {
            "_controlId": control_id,
            "keyIndex": _safe_int(payload, "key_index", 0, 255),
            "enabled": bool(_safe_choice(payload, "default", {0, 1})),
            "pressAndHold": press_and_hold,
            "onRelease": on_release,
            "keyAssignmentType": _safe_choice(payload, "assignment_type", {0, 1, 2, 3, 8, 9, 10}),
            "keyAssignmentValue": _safe_int(payload, "assignment_value", 0, 65535),
        }
    if action == "macro-create-recording":
        steps = payload.get("steps")
        if not isinstance(steps, list) or not 1 <= len(steps) <= 64:
            raise ValueError("Eine Makroaufnahme benötigt 1 bis 64 Tastenschritte")
        clean_steps: list[dict[str, int]] = []
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("Ungültiger Makroschritt")
            clean_steps.append({
                "key": _safe_int(step, "key", 1, 65535),
                "delay": _safe_int(step, "delay", 0, 5000),
            })
        name = _safe_text(payload, "name", maximum=48)
        if len(name) < 3:
            raise ValueError("Der Makroname benötigt mindestens drei Zeichen")
        return {
            "_controlId": control_id,
            "name": name,
            "steps": clean_steps,
        }
    if action == "keyboard-user-profile":
        return {"_controlId": control_id, "userProfileName": _safe_text(payload, "profile", maximum=48)}
    if action == "keyboard-profile":
        return {"_controlId": control_id, "keyboardProfileName": _safe_text(payload, "profile", maximum=48)}
    if action == "keyboard-layout":
        layout = _safe_text(payload, "layout", maximum=16)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", layout):
            raise ValueError("Ungültige Tastaturbelegung")
        return {"_controlId": control_id, "keyboardLayout": layout}
    if action == "keyboard-dial":
        return {"_controlId": control_id, "keyboardControlDial": _safe_int(payload, "dial", 0, 20)}
    if action == "keyboard-sleep":
        return {"_controlId": control_id, "sleepMode": _safe_int(payload, "sleep_mode", 0, 60)}
    if action == "keyboard-polling":
        return {"_controlId": control_id, "pollingRate": _safe_int(payload, "polling_rate", 1, 8)}
    if action == "psu-speed":
        return {"_controlId": control_id, "fanMode": _safe_int(payload, "fan_mode", 0, 10)}
    if action == "headset-sleep":
        return {"_controlId": control_id, "sleepMode": _safe_int(payload, "sleep_mode", 0, 60)}
    if action == "headset-mute-indicator":
        return {"_controlId": control_id, "muteIndicator": _safe_choice(payload, "enabled", {0, 1})}
    if action == "headset-anc":
        return {"_controlId": control_id, "noiseCancellation": _safe_choice(payload, "mode", {0, 1, 2})}
    if action == "headset-sidetone":
        return {"_controlId": control_id, "sideTone": _safe_choice(payload, "enabled", {0, 1})}
    if action == "headset-sidetone-value":
        return {"_controlId": control_id, "sideToneValue": _safe_int(payload, "value", 0, 100)}
    raise ValueError("Nicht erlaubter OpenLinkHub-Schreibbefehl")


def _resolve_device_id(api_url: str, control_id: str) -> str:
    payload = _api_get(api_url, "/api/devices/")
    container = _device_container(payload)
    raw_devices = list(container.values()) if isinstance(container, dict) else container
    if not isinstance(raw_devices, list):
        raise RuntimeError("OpenLinkHub-Geräteliste ist ungültig")
    matches: list[str] = []
    for item in raw_devices:
        if not isinstance(item, dict):
            continue
        detail = item.get("GetDevice", item.get("getDevice", {}))
        if not isinstance(detail, dict):
            detail = {}
        serial = _text(item, "Serial", "SerialNumber", default="") or _text(
            detail, "Serial", "SerialNumber", default=""
        )
        if serial and _control_id(serial) == control_id:
            matches.append(serial)
    if len(matches) != 1:
        raise RuntimeError("OpenLinkHub-Gerät wurde nicht eindeutig gefunden; bitte aktualisieren")
    return matches[0]


def run_write_action(action: str, payload: Any, api_url: str = DEFAULT_API_URL) -> dict[str, Any]:
    clean_payload = validate_write_payload(action, payload)
    control_id = str(clean_payload.pop("_controlId"))
    device_id = _resolve_device_id(api_url, control_id)
    if action == "macro-create-recording":
        return _create_recorded_macro(api_url, clean_payload, device_id)
    clean_payload["deviceId"] = device_id
    method, endpoint = WRITE_ENDPOINTS[action]
    _api_request(api_url, endpoint, method=method, payload=clean_payload, timeout=5.0)
    return {"ok": True, "action": action}


def _macro_items(payload: Any) -> list[tuple[int, dict[str, Any]]]:
    container = _device_container(payload)
    if isinstance(container, dict):
        result: list[tuple[int, dict[str, Any]]] = []
        for raw_id, value in container.items():
            if not isinstance(value, dict):
                continue
            try:
                macro_id = int(raw_id)
            except (TypeError, ValueError):
                found = _number(value, "id", "Id", "macroId", "MacroId")
                if found is None:
                    continue
                macro_id = int(found)
            result.append((macro_id, value))
        return result
    if isinstance(container, list):
        result = []
        for value in container:
            if not isinstance(value, dict):
                continue
            found = _number(value, "id", "Id", "macroId", "MacroId")
            if found is not None:
                result.append((int(found), value))
        return result
    return []


def _create_recorded_macro(api_url: str, payload: dict[str, Any], _device_id: str) -> dict[str, Any]:
    """Create one bounded keyboard macro through the documented OLH API."""
    name = str(payload["name"])
    before_ids = {macro_id for macro_id, _value in _macro_items(_api_get(api_url, "/api/macro/"))}
    _api_request(api_url, "/api/macro/new", method="PUT", payload={"macroName": name}, timeout=5.0)
    after = _macro_items(_api_get(api_url, "/api/macro/"))
    candidates = [
        macro_id for macro_id, value in after
        if macro_id not in before_ids and _text(value, "name", "Name", default="") == name
    ]
    if len(candidates) != 1:
        raise RuntimeError("Das neu angelegte OpenLinkHub-Makro konnte nicht eindeutig gefunden werden")
    macro_id = candidates[0]
    try:
        for step in payload["steps"]:
            delay = int(step["delay"])
            if delay:
                _api_request(
                    api_url, "/api/macro/newValue", method="POST",
                    payload={"macroId": macro_id, "macroType": 5, "macroValue": 0, "macroDelay": delay},
                    timeout=5.0,
                )
            _api_request(
                api_url, "/api/macro/newValue", method="POST",
                payload={"macroId": macro_id, "macroType": 3, "macroValue": int(step["key"]), "macroDelay": 0},
                timeout=5.0,
            )
    except Exception:
        try:
            _api_request(
                api_url, "/api/macro/profile", method="DELETE",
                payload={"macroId": macro_id}, timeout=5.0,
            )
        except Exception:
            pass
        raise
    return {"ok": True, "action": "macro-create-recording", "macro_id": macro_id}


def _safe_error_text(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    # Some OpenLinkHub handlers may echo a device identifier in an error.
    # Keep copyable GUI/log output useful without exposing long serial-like IDs.
    return re.sub(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{16,128}(?![A-Za-z0-9_-])", "[GERÄT]", text)[:500]


def _device_container(payload: Any) -> Any:
    """Unwrap the response shapes used by OpenLinkHub releases."""
    current = payload
    for _depth in range(4):
        if not isinstance(current, dict):
            return current
        lowered = {str(key).lower(): key for key in current}
        for candidate in ("devices", "data"):
            if candidate in lowered:
                current = current[lowered[candidate]]
                break
        else:
            return current
    return current


def _text(mapping: dict[str, Any], *names: str, default: str = "—") -> str:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return str(value)
    return default


def _number(mapping: dict[str, Any], *names: str) -> float | int | None:
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for name in names:
        value = lowered.get(name.lower())
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value
    return None


def _nested_channels(device: dict[str, Any]) -> list[dict[str, Any]]:
    candidate: Any = device.get("GetDevice", device.get("getDevice", {}))
    if isinstance(candidate, dict):
        candidate = candidate.get("devices", candidate.get("Devices", []))
    if isinstance(candidate, dict):
        candidate = list(candidate.values())
    if not isinstance(candidate, list):
        return []
    channels: list[dict[str, Any]] = []
    for item in candidate:
        if not isinstance(item, dict):
            continue
        channels.append({
            "channel_id": int(_number(item, "ChannelId", "channelId") or 0),
            "device_type": int(_number(item, "Type", "DeviceType") or 0),
            "name": _text(item, "Name", "Description", "Device", default="Kanal"),
            "label": _text(item, "Label", default=""),
            "rpm": _number(item, "Rpm", "RPM"),
            "temperature": _number(item, "Temperature", "Temp"),
            "profile": _text(item, "Profile", default=""),
            "rgb": _text(item, "RGB", "Rgb", default=""),
            "has_speed": bool(item.get("HasSpeed", item.get("hasSpeed", False))),
            "has_temps": bool(item.get("HasTemps", item.get("hasTemps", False))),
            "is_cpu_block": bool(item.get("IsCpuBlock", item.get("isCpuBlock", False))),
            "aio": bool(item.get("AIO", item.get("aio", False))),
            "lcd_serial_present": bool(_text(item, "LCDSerial", default="")),
        })
    return channels


_ASSIGNMENT_CONTAINER_NAMES = {
    "keyassignment", "keyassignments", "buttonassignment", "buttonassignments",
    "mouseassignment", "mouseassignments", "assignments",
}


def _bounded_public_text(value: Any, maximum: int) -> str:
    """Convert a simple API value to short, control-character-free UI text."""
    if isinstance(value, dict):
        value = _text(
            value,
            "Name", "ActionName", "Function", "Command", "KeyName", "Label", "Value",
            default="",
        )
    if isinstance(value, (list, tuple, set, dict)) or value is None:
        return ""
    text = str(value).strip()
    if not text or any(ord(char) < 32 for char in text):
        return ""
    # Never pass long opaque identifiers from the helper into the GUI.
    if len(text) >= 16 and re.fullmatch(r"[A-Za-z0-9_-]+", text):
        return ""
    return text[:maximum]


def _assignment_records(value: Any) -> list[dict[str, Any]]:
    record_fields = {
        "index", "keyindex", "buttonindex", "buttonid", "keyid", "name", "label",
        "action", "actionname", "actiontype", "function", "assignment", "command", "value",
    }
    records: list[dict[str, Any]] = []

    def collect(node: Any, depth: int = 0) -> None:
        if depth > 4 or len(records) >= 32:
            return
        if isinstance(node, dict):
            lowered = {str(key).casefold() for key in node}
            if lowered.intersection(record_fields):
                records.append(node)
                return
            for nested in list(node.values())[:64]:
                collect(nested, depth + 1)
        elif isinstance(node, list):
            for nested in node[:64]:
                collect(nested, depth + 1)

    collect(value)
    return records


def _mouse_assignments(device: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a redacted, bounded view of mouse assignments reported by OLH."""
    candidates: list[dict[str, Any]] = []

    def visit(node: Any, depth: int = 0) -> None:
        if depth > 6 or len(candidates) >= 32:
            return
        if isinstance(node, dict):
            for key, value in node.items():
                normalized = re.sub(r"[^a-z]", "", str(key).casefold())
                if normalized in _ASSIGNMENT_CONTAINER_NAMES:
                    candidates.extend(_assignment_records(value)[: 32 - len(candidates)])
                elif isinstance(value, (dict, list)):
                    visit(value, depth + 1)
        elif isinstance(node, list):
            for value in node[:64]:
                visit(value, depth + 1)

    visit(device)
    results: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for record in candidates[:32]:
        index_value = _number(record, "ButtonIndex", "KeyIndex", "Index", "ButtonId", "KeyId")
        # Numeric indexes differ between device families.  Never turn our
        # enumeration order into a writable hardware index.
        index = int(index_value) if isinstance(index_value, (int, float)) else -1
        button_id = _bounded_public_text(
            _text(record, "Button", "ButtonName", "Key", "KeyName", "ButtonId", "KeyId", default=""),
            48,
        )
        label = _bounded_public_text(
            _text(record, "Label", "Description", "Name", "KeyName", "ButtonName", default=""),
            64,
        )
        action_type_value = _number(record, "ActionType", "AssignmentType", "KeyAssignmentType")
        action_command_value = _number(record, "ActionCommand", "AssignmentValue", "KeyAssignmentValue")
        action_type = int(action_type_value) if action_type_value is not None else 0
        action_command = int(action_command_value) if action_command_value is not None else 0
        default_action = bool(record.get("Default", record.get("default", False)))
        press_and_hold = bool(record.get("ActionHold", record.get("PressAndHold", record.get("pressAndHold", False))))
        on_release = bool(record.get("OnRelease", record.get("onRelease", False)))
        is_macro = bool(record.get("IsMacro", record.get("isMacro", action_type == 10)))
        lowered = {str(key).casefold(): value for key, value in record.items()}
        function = ""
        for name in ("actionname", "function", "action", "actiontype", "assignment", "command", "value", "default"):
            if name in lowered:
                function = _bounded_public_text(lowered[name], 96)
                if function:
                    break
        if function.isdigit():
            function = ""
        if default_action:
            function = "Originalfunktion"
        elif not function and action_type:
            type_name = {1: "Medientaste", 2: "DPI-Funktion", 3: "Tastatur", 8: "Sniper-DPI", 9: "Maustaste", 10: "Makro"}.get(action_type, "Funktion")
            function = f"{type_name} · Wert {action_command}"
        if not function and not label and not button_id:
            continue
        item = {
            "index": max(-1, min(255, index)),
            "button_id": button_id,
            "label": label,
            "function": function or "Von OpenLinkHub gemeldet",
            "assignment_type": action_type,
            "assignment_value": max(0, min(65535, action_command)),
            "default": default_action,
            "press_and_hold": press_and_hold,
            "on_release": on_release,
            "is_macro": is_macro,
        }
        fingerprint = (item["index"], item["button_id"], item["label"], item["function"])
        if fingerprint not in seen:
            seen.add(fingerprint)
            results.append(item)
    return results


def _input_catalog(payload: Any) -> list[dict[str, Any]]:
    """Return a bounded, non-sensitive OpenLinkHub input-action catalog."""
    container = _device_container(payload)
    if isinstance(container, dict):
        raw_items = list(container.items())
    elif isinstance(container, list):
        raw_items = list(enumerate(container))
    else:
        return []
    results: list[dict[str, Any]] = []
    for raw_id, value in raw_items[:2048]:
        if not isinstance(value, dict):
            continue
        try:
            action_id = int(raw_id)
        except (TypeError, ValueError):
            found = _number(value, "id", "Id", "Index")
            if found is None:
                continue
            action_id = int(found)
        if not 0 <= action_id <= 65535:
            continue
        name = _bounded_public_text(_text(value, "Name", "name", "Label", default=""), 96)
        if not name:
            continue
        command_code = _number(value, "CommandCode", "commandCode")
        results.append({
            "id": action_id,
            "name": name,
            "command_code": int(command_code) if command_code is not None else 0,
        })
    return results


def _macro_catalog(payload: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for macro_id, value in _macro_items(payload)[:256]:
        name = _bounded_public_text(_text(value, "name", "Name", default=""), 96)
        if name and 0 <= macro_id <= 65535:
            results.append({"id": macro_id, "name": name})
    return sorted(results, key=lambda item: str(item["name"]).casefold())


def infer_device_kind(product: str) -> str:
    normalized = product.casefold()
    if any(token in normalized for token in (" psu", "power supply", "hx750", "hx850", "hx1000", "hx1200", "hx1500", "rm750", "rm850", "rm1000", "axi")):
        return "psu"
    if any(token in normalized for token in ("virtuoso", "headset", "void ", "hs55", "hs65", "hs70", "hs80")):
        return "headset"
    if any(token in normalized for token in (
        "mouse", "scimitar", "sabre", "m65", "m75", "dark core", "nightsabre", "katar", "harpoon",
    )):
        return "mouse"
    if any(token in normalized for token in ("keyboard", "strafe", "k55", "k57", "k60", "k65", "k68", "k70", "k95", "k100", "vanguard")):
        return "keyboard"
    if any(token in normalized for token in ("commander", "link system hub", "cooler", "h100", "h115", "h150", "h170", "aio")):
        return "cooling"
    return "generic"


def summarize_devices(payload: Any) -> list[dict[str, Any]]:
    container = _device_container(payload)
    if isinstance(container, dict):
        raw_devices = list(container.values())
    elif isinstance(container, list):
        raw_devices = container
    else:
        raw_devices = []
    devices: list[dict[str, Any]] = []
    for item in raw_devices:
        if not isinstance(item, dict):
            continue
        detail = item.get("GetDevice", item.get("getDevice", {}))
        if not isinstance(detail, dict):
            detail = {}
        serial = _text(item, "Serial", "SerialNumber", default="")
        if not serial:
            serial = _text(detail, "Serial", "SerialNumber", default="")
        firmware = _text(item, "Firmware", "FirmwareVersion")
        if firmware == "—":
            firmware = _text(detail, "Firmware", "FirmwareVersion")
        product = _text(item, "Product", "ProductName", "Name", default="Corsair-Gerät")
        if product == "Corsair-Gerät":
            product = _text(detail, "Product", "ProductName", "Name", default=product)
        channels = _nested_channels(item)
        kind = infer_device_kind(product)
        devices.append({
            # The GUI receives only a one-way control token.  The helper maps
            # it back to the current local device list for each write, so the
            # full serial never reaches the surface or application log.
            "control_id": _control_id(serial) if serial else "",
            "product": product,
            "product_type": int(_number(item, "ProductType") or 0),
            "kind": kind,
            "serial_suffix": serial[-4:] if serial else "",
            "firmware": firmware,
            "channels": channels,
            "has_speed": any(bool(channel.get("has_speed")) for channel in channels),
            "has_lcd": any(bool(channel.get("lcd_serial_present")) for channel in channels) or "lcd" in product.casefold(),
            "mouse_assignments": _mouse_assignments(item) if kind == "mouse" else [],
        })
    return devices


def _profile_names(payload: Any) -> list[str]:
    container = _device_container(payload)
    if not isinstance(container, dict):
        return []
    result = []
    for name, profile in container.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if isinstance(profile, dict) and bool(profile.get("Hidden", profile.get("hidden", False))):
            continue
        result.append(name.strip())
    return sorted(set(result), key=str.casefold)


def _rgb_profile_names(payload: Any) -> dict[str, list[str]]:
    container = _device_container(payload)
    if not isinstance(container, dict):
        return {}
    result: dict[str, list[str]] = {}
    for device_id, data in container.items():
        if not isinstance(device_id, str) or not isinstance(data, dict):
            continue
        profiles = data.get("profiles", data.get("Profiles", {}))
        if not isinstance(profiles, dict):
            continue
        names = [str(name).strip() for name in profiles if str(name).strip()]
        result[_control_id(device_id)] = sorted(set(names), key=str.casefold)
    return result


@dataclass
class OpenLinkHubStatus:
    installed_version: str
    user_service: dict[str, Any]
    system_service: dict[str, Any]
    service_context: str
    api_url: str
    api_reachable: bool
    api_error: str
    devices: list[dict[str, Any]]
    temperature_profiles: list[str]
    rgb_profiles: dict[str, list[str]]
    input_catalogs: dict[str, list[dict[str, Any]]]
    macros: list[dict[str, Any]]
    capability_errors: list[str]


def collect_status(api_url: str = DEFAULT_API_URL) -> OpenLinkHubStatus:
    normalized = validate_local_api_url(api_url)
    user = _service_state(user=True)
    system = _service_state(user=False)
    user_active = user["active"] == "active"
    system_active = system["active"] == "active"
    if user_active and system_active:
        context = "conflict"
    elif user_active:
        context = "user"
    elif system_active:
        context = "system"
    elif user["available"]:
        context = "user-stopped"
    elif system["available"]:
        context = "system-stopped"
    else:
        context = "absent"

    devices: list[dict[str, Any]] = []
    temperature_profiles: list[str] = []
    rgb_profiles: dict[str, list[str]] = {}
    input_catalogs: dict[str, list[dict[str, Any]]] = {"media": [], "keyboard": [], "mouse": []}
    macros: list[dict[str, Any]] = []
    capability_errors: list[str] = []
    reachable = False
    error = ""
    try:
        devices = summarize_devices(_api_get(normalized, "/api/devices/"))
        reachable = True
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        error = str(exc)
    if reachable:
        try:
            temperature_profiles = _profile_names(_api_get(normalized, "/api/temperatures/"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            capability_errors.append(f"Temperaturprofile: {exc}")
        try:
            rgb_profiles = _rgb_profile_names(_api_get(normalized, "/api/color/"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            capability_errors.append(f"RGB-Profile: {exc}")
        for catalog_name in ("media", "keyboard", "mouse"):
            try:
                input_catalogs[catalog_name] = _input_catalog(
                    _api_get(normalized, f"/api/input/{catalog_name}")
                )
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
                capability_errors.append(f"Eingabekatalog {catalog_name}: {exc}")
        try:
            macros = _macro_catalog(_api_get(normalized, "/api/macro/"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            capability_errors.append(f"Makros: {exc}")
    return OpenLinkHubStatus(
        installed_version=installed_version(),
        user_service=user,
        system_service=system,
        service_context=context,
        api_url=normalized,
        api_reachable=reachable,
        api_error=error,
        devices=devices,
        temperature_profiles=temperature_profiles,
        rgb_profiles=rgb_profiles,
        input_catalogs=input_catalogs,
        macros=macros,
        capability_errors=capability_errors,
    )


def run_user_service_action(action: str) -> dict[str, Any]:
    if action not in USER_ACTIONS:
        raise ValueError("Nicht erlaubte Dienstaktion")
    args = ["systemctl", "--user", action]
    if action in {"enable", "disable"}:
        args.append("--now")
    args.append(SERVICE_NAME)
    result = _run(args, timeout=15)
    return {
        "ok": result.returncode == 0,
        "action": action,
        "returncode": result.returncode,
        "message": (result.stdout.strip() or result.stderr.strip()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lokale OpenLinkHub-Integration")
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true")
    group.add_argument("--user-service-action", choices=sorted(USER_ACTIONS))
    group.add_argument("--write-action", choices=sorted(WRITE_ENDPOINTS))
    parser.add_argument("--payload-json", default="{}")
    args = parser.parse_args(argv)
    try:
        if args.status:
            result: Any = asdict(collect_status(args.api_url))
        elif args.user_service_action:
            result = run_user_service_action(args.user_service_action)
        else:
            payload = json.loads(args.payload_json)
            result = run_write_action(str(args.write_action), payload, args.api_url)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok", True) else 1
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": _safe_error_text(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())

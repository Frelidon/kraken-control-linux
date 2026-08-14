#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Copyright-safe OpenLinkHub mouse schematics and button mapping helpers.

The geometry is deliberately generic and was drawn for Open Hardware Control.
It does not copy product photography, vendor renders or OpenLinkHub artwork.
"""

from __future__ import annotations

import re
from typing import Any


COMMON_BUTTONS = (
    {"id": "left", "number": "1", "label": "Linke Maustaste", "function": "Primärklick", "rect": (214, 42, 80, 105), "aliases": ("left", "leftclick", "primary", "button1", "mouse1")},
    {"id": "right", "number": "2", "label": "Rechte Maustaste", "function": "Sekundärklick", "rect": (306, 42, 80, 105), "aliases": ("right", "rightclick", "secondary", "button2", "mouse2")},
    {"id": "wheel", "number": "3", "label": "Mausrad drücken", "function": "Mittelklick", "rect": (286, 70, 28, 64), "aliases": ("wheel", "middle", "middleclick", "button3", "mouse3")},
    {"id": "dpi", "number": "D", "label": "DPI-Taste", "function": "DPI-Stufe wechseln", "rect": (282, 148, 36, 30), "aliases": ("dpi", "dpicycle", "dpitoggle")},
)

SIDE_BUTTONS = (
    {"id": "back", "number": "4", "label": "Seitentaste hinten", "function": "Zurück", "rect": (140, 142, 40, 47), "aliases": ("back", "backward", "button4", "mouse4", "sideback")},
    {"id": "forward", "number": "5", "label": "Seitentaste vorn", "function": "Vorwärts", "rect": (143, 90, 40, 48), "aliases": ("forward", "button5", "mouse5", "sideforward")},
)


def _button(identifier: str, number: str, label: str, function: str, rect: tuple[int, int, int, int], *aliases: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "number": number,
        "label": label,
        "function": function,
        "rect": rect,
        "aliases": aliases,
    }


LAYOUTS: dict[str, dict[str, Any]] = {
    "compact": {
        "title": "Kompakte Gaming-Maus",
        "asset": "mouse-compact.svg",
        "buttons": COMMON_BUTTONS + SIDE_BUTTONS,
    },
    "ergonomic": {
        "title": "Ergonomische Gaming-Maus",
        "asset": "mouse-ergonomic.svg",
        "buttons": COMMON_BUTTONS + SIDE_BUTTONS + (
            _button("sniper", "S", "Präzisionstaste", "Sniper-DPI", (139, 202, 44, 55), "sniper", "precision", "button6", "mouse6"),
        ),
    },
    "symmetric": {
        "title": "Symmetrische Gaming-Maus",
        "asset": "mouse-symmetric.svg",
        "buttons": COMMON_BUTTONS + SIDE_BUTTONS + (
            _button("right-forward", "6", "Rechte Seitentaste vorn", "Nicht belegt", (419, 90, 38, 48), "rightforward", "button6", "mouse6"),
            _button("right-back", "7", "Rechte Seitentaste hinten", "Nicht belegt", (422, 141, 38, 48), "rightback", "button7", "mouse7"),
        ),
    },
    "multi": {
        "title": "Mehrknopf-Gaming-Maus",
        "asset": "mouse-multi.svg",
        "buttons": COMMON_BUTTONS + SIDE_BUTTONS + tuple(
            _button(
                f"side-{index}", str(index + 5), f"Zusatz-Seitentaste {index}", "Nicht belegt",
                (131, 197 + ((index - 1) % 3) * 42, 44, 38),
                f"side{index}", f"button{index + 5}", f"mouse{index + 5}",
            )
            for index in range(1, 4)
        ),
    },
    "mmo": {
        "title": "MMO-Gaming-Maus",
        "asset": "mouse-mmo.svg",
        "buttons": COMMON_BUTTONS + tuple(
            _button(
                f"side-{index}", str(index + 3), f"Seitentaste {index}", f"MMO-Taste {index}",
                (98 + ((index - 1) % 3) * 25, 85 + ((index - 1) // 3) * 42, 23, 35),
                f"side{index}", f"button{index + 3}", f"mouse{index + 3}", f"g{index}",
            )
            for index in range(1, 13)
        ),
    },
}


def normalize_token(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def classify_mouse_layout(product: str) -> str:
    """Choose a generic shape from a Corsair model name."""
    name = normalize_token(product)
    if "scimitar" in name:
        return "mmo"
    if any(token in name for token in ("darkstar", "nightsabre")):
        return "multi"
    if any(token in name for token in ("m55", "m75")):
        return "symmetric"
    if any(token in name for token in ("m65", "darkcore", "ironclaw", "glaive", "sabre")):
        return "ergonomic"
    return "compact"


def mouse_schema(product: str) -> dict[str, Any]:
    return LAYOUTS[classify_mouse_layout(product)]


def _assignment_tokens(assignment: dict[str, object]) -> set[str]:
    tokens: set[str] = set()
    for key in ("button_id", "button", "label"):
        token = normalize_token(assignment.get(key))
        if token:
            tokens.add(token)
    index = assignment.get("index")
    if isinstance(index, int):
        tokens.update({f"button{index}", f"mouse{index}", f"side{index}"})
        if index >= 0:
            tokens.update({f"button{index + 1}", f"mouse{index + 1}"})
    return tokens


def visual_button_rows(product: str, assignments: object) -> list[dict[str, object]]:
    """Merge bounded OpenLinkHub assignments with the selected schematic."""
    schema = mouse_schema(product)
    clean_assignments = [item for item in assignments if isinstance(item, dict)] if isinstance(assignments, list) else []
    remaining = list(clean_assignments[:32])
    rows: list[dict[str, object]] = []
    for raw_button in schema["buttons"]:
        button = dict(raw_button)
        aliases = {normalize_token(button["id"]), normalize_token(button["label"])}
        aliases.update(normalize_token(value) for value in button.get("aliases", ()))
        matched = None
        # Explicit OpenLinkHub button names are more reliable than numeric
        # indexes, whose base differs between device families/releases.
        for assignment in remaining:
            named_tokens = {
                normalize_token(assignment.get("button_id")),
                normalize_token(assignment.get("button")),
                normalize_token(assignment.get("label")),
            }
            named_tokens.discard("")
            if aliases.intersection(named_tokens):
                matched = assignment
                break
        if matched is None:
            for assignment in remaining:
                named_tokens = {
                    normalize_token(assignment.get("button_id")),
                    normalize_token(assignment.get("button")),
                    normalize_token(assignment.get("label")),
                }
                named_tokens.discard("")
                if named_tokens:
                    continue
                if aliases.intersection(_assignment_tokens(assignment)):
                    matched = assignment
                    break
        if matched is not None:
            remaining.remove(matched)
            function = str(matched.get("function") or matched.get("action") or button["function"])
            if function.strip():
                button["function"] = function.strip()[:96]
            reported_label = str(matched.get("label") or "").strip()
            if reported_label:
                button["reported_label"] = reported_label[:64]
            button["reported"] = True
            button["key_index"] = int(matched.get("index", -1))
            button["assignment_type"] = int(matched.get("assignment_type", 0))
            button["assignment_value"] = int(matched.get("assignment_value", 0))
            button["default"] = bool(matched.get("default", False))
            button["press_and_hold"] = bool(matched.get("press_and_hold", False))
            button["on_release"] = bool(matched.get("on_release", False))
            button["is_macro"] = bool(matched.get("is_macro", False))
        else:
            button["reported"] = False
        rows.append(button)
    for index, assignment in enumerate(remaining):
        label = str(assignment.get("label") or assignment.get("button_id") or f"Gemeldete Taste {index + 1}")
        function = str(assignment.get("function") or assignment.get("action") or "Von OpenLinkHub gemeldet")
        rows.append({
            "id": f"reported-{index}",
            "number": "?",
            "label": label[:64],
            "function": function[:96],
            "rect": (-100, -100, 0, 0),
            "reported": True,
            "reported_only": True,
            "key_index": int(assignment.get("index", -1)),
            "assignment_type": int(assignment.get("assignment_type", 0)),
            "assignment_value": int(assignment.get("assignment_value", 0)),
            "default": bool(assignment.get("default", False)),
            "press_and_hold": bool(assignment.get("press_and_hold", False)),
            "on_release": bool(assignment.get("on_release", False)),
            "is_macro": bool(assignment.get("is_macro", False)),
        })
    return rows

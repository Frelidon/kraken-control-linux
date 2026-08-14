#!/usr/bin/env python3
"""Tests for copyright-safe OpenLinkHub mouse schematic mapping."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import openlinkhub_mouse_visuals as visuals  # noqa: E402


class MouseVisualTests(unittest.TestCase):
    def test_model_families_choose_distinct_generic_shapes(self):
        self.assertEqual(visuals.classify_mouse_layout("SCIMITAR RGB ELITE"), "mmo")
        self.assertEqual(visuals.classify_mouse_layout("M75 Wireless"), "symmetric")
        self.assertEqual(visuals.classify_mouse_layout("M65 RGB Ultra"), "ergonomic")
        self.assertEqual(visuals.classify_mouse_layout("Darkstar Wireless"), "multi")
        self.assertEqual(visuals.classify_mouse_layout("Harpoon RGB"), "compact")

    def test_reported_assignment_is_merged_with_physical_button(self):
        rows = visuals.visual_button_rows("M75 Wireless", [
            {"index": 0, "button_id": "Left Click", "label": "Linksklick", "function": "Primärklick"},
            {"index": 3, "button_id": "Back", "label": "Hinten", "function": "Tastatur R"},
        ])
        by_id = {row["id"]: row for row in rows}
        self.assertTrue(by_id["left"]["reported"])
        self.assertEqual(by_id["left"]["function"], "Primärklick")
        self.assertTrue(by_id["back"]["reported"])
        self.assertEqual(by_id["back"]["function"], "Tastatur R")

    def test_every_layout_has_an_original_svg_asset(self):
        for schema in visuals.LAYOUTS.values():
            asset = ROOT / "assets" / schema["asset"]
            self.assertTrue(asset.is_file(), asset)
            text = asset.read_text(encoding="utf-8")
            self.assertIn("Original Open Hardware Control artwork", text)
            self.assertIn("<svg", text)


if __name__ == "__main__":
    unittest.main()

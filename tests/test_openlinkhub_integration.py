#!/usr/bin/env python3
"""Unit tests for the local, allow-listed OpenLinkHub adapter."""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import openlinkhub_integration as olh  # noqa: E402


class OpenLinkHubIntegrationTests(unittest.TestCase):
    def test_api_url_only_accepts_loopback(self):
        self.assertEqual(olh.validate_local_api_url("http://127.0.0.1:27003/"), "http://127.0.0.1:27003")
        self.assertEqual(olh.validate_local_api_url("http://localhost:27003"), "http://localhost:27003")
        self.assertEqual(olh.validate_local_api_url("http://[::1]:27003"), "http://[::1]:27003")
        for unsafe in (
            "https://localhost:27003", "http://192.168.1.2:27003", "http://localhost:27003/api/",
            "http://user:pass@localhost:27003", "http://localhost",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                olh.validate_local_api_url(unsafe)

    def test_summarizes_documented_device_shape_and_redacts_serial(self):
        payload = {
            "data": {"devices": {"abc": {
                "Product": "iCUE LINK System Hub",
                "Serial": "SECRET123456",
                "Firmware": "",
                "GetDevice": {"devices": [{
                    "Name": "QX120 #1", "Rpm": 1210, "Temperature": 31.4,
                    "Profile": "Balanced", "RGB": "rainbow", "Label": "Front",
                }], "firmware": "2.3.427"},
            }}}
        }
        devices = olh.summarize_devices(payload)
        self.assertEqual(devices[0]["product"], "iCUE LINK System Hub")
        self.assertEqual(devices[0]["serial_suffix"], "3456")
        self.assertEqual(devices[0]["firmware"], "2.3.427")
        self.assertNotIn("SECRET", json.dumps(devices))
        self.assertEqual(len(devices[0]["control_id"]), 64)
        self.assertEqual(devices[0]["channels"][0]["rpm"], 1210)
        self.assertEqual(devices[0]["channels"][0]["temperature"], 31.4)

    def test_mouse_assignments_are_bounded_and_redacted_for_the_gui(self):
        payload = {"devices": {"mouse": {
            "Product": "M75 Wireless",
            "Serial": "PRIVATE-MOUSE-SERIAL-123456",
            "GetDevice": {
                "KeyAssignments": [
                    {"ButtonIndex": 0, "ButtonName": "Left Click", "Action": {"Name": "Primary click"}},
                    {"ButtonIndex": 3, "ButtonName": "Back", "Function": "Keyboard R"},
                ]
            },
        }}}
        device = olh.summarize_devices(payload)[0]
        self.assertEqual(device["kind"], "mouse")
        self.assertEqual(len(device["mouse_assignments"]), 2)
        self.assertEqual(device["mouse_assignments"][0]["function"], "Primary click")
        self.assertEqual(device["mouse_assignments"][1]["label"], "Back")
        self.assertNotIn("PRIVATE-MOUSE", json.dumps(device))

    def test_mouse_assignment_without_reported_index_is_not_made_writable(self):
        payload = {"devices": {"mouse": {
            "Product": "M75 Wireless",
            "Serial": "PRIVATE-MOUSE-SERIAL-123456",
            "GetDevice": {"KeyAssignments": [{"ButtonName": "Back", "Function": "Keyboard R"}]},
        }}}
        assignment = olh.summarize_devices(payload)[0]["mouse_assignments"][0]
        self.assertEqual(assignment["index"], -1)

    def test_write_payloads_are_strict_and_bounded(self):
        control_id = olh._control_id("SERIAL123")
        clean = olh.validate_write_payload("speed-manual", {
            "control_id": control_id, "channel_id": 2, "value": 55, "endpoint": "/evil",
        })
        self.assertEqual(clean, {"_controlId": control_id, "channelId": 2, "value": 55})
        with self.assertRaises(ValueError):
            olh.validate_write_payload("speed-manual", {
                "control_id": control_id, "channel_id": 2, "value": 101,
            })
        with self.assertRaises(ValueError):
            olh.validate_write_payload("arbitrary", {"control_id": control_id})
        with self.assertRaises(ValueError):
            olh.validate_write_payload("label", {
                "control_id": control_id, "channel_id": 1, "device_type": 1, "label": "bad\nlabel",
            })

        assignment = olh.validate_write_payload("mouse-key-assignment", {
            "control_id": control_id,
            "key_index": 4,
            "default": 0,
            "press_and_hold": 0,
            "on_release": 1,
            "assignment_type": 3,
            "assignment_value": 55,
        })
        self.assertEqual(assignment["keyIndex"], 4)
        self.assertEqual(assignment["keyAssignmentType"], 3)
        self.assertTrue(assignment["onRelease"])
        with self.assertRaises(ValueError):
            olh.validate_write_payload("mouse-key-assignment", {
                "control_id": control_id,
                "key_index": 4,
                "default": 0,
                "press_and_hold": 1,
                "on_release": 1,
                "assignment_type": 3,
                "assignment_value": 55,
            })
        with self.assertRaises(ValueError):
            olh.validate_write_payload("macro-create-recording", {
                "control_id": control_id, "name": "x", "steps": [{"key": 55, "delay": 0}],
            })

    def test_sanitizes_input_and_macro_catalogs(self):
        inputs = olh._input_catalog({"data": {
            "0": {"Name": "None", "CommandCode": 0},
            "55": {"Name": "A", "CommandCode": 30},
        }})
        self.assertEqual(inputs[1], {"id": 55, "name": "A", "command_code": 30})
        macros = olh._macro_catalog({"data": {"7": {"name": "Arbeitsablauf", "actions": []}}})
        self.assertEqual(macros, [{"id": 7, "name": "Arbeitsablauf"}])

    @patch.object(olh, "_api_request")
    @patch.object(olh, "_api_get")
    def test_recorded_macro_uses_bounded_documented_steps(self, api_get, api_request):
        api_get.side_effect = [
            {"data": {"1": {"name": "Vorhanden"}}},
            {"data": {"1": {"name": "Vorhanden"}, "7": {"name": "Testmakro"}}},
        ]
        result = olh._create_recorded_macro(
            "http://127.0.0.1:27003",
            {"name": "Testmakro", "steps": [{"key": 55, "delay": 120}]},
            "private-device-id",
        )
        self.assertEqual(result["macro_id"], 7)
        calls = [call.kwargs for call in api_request.call_args_list]
        self.assertEqual(calls[0]["method"], "PUT")
        self.assertEqual(calls[0]["payload"], {"macroName": "Testmakro"})
        self.assertEqual(calls[1]["payload"], {
            "macroId": 7, "macroType": 5, "macroValue": 0, "macroDelay": 120,
        })
        self.assertEqual(calls[2]["payload"], {
            "macroId": 7, "macroType": 3, "macroValue": 55, "macroDelay": 0,
        })

    @patch.object(olh, "_api_request", return_value={"code": 200, "status": 1})
    @patch.object(olh, "_api_get")
    def test_write_resolves_private_serial_only_inside_helper(self, api_get, api_request):
        serial = "PRIVATE-SERIAL-123"
        api_get.return_value = {"devices": {serial: {"Product": "M75", "Serial": serial}}}
        result = olh.run_write_action("mouse-polling", {
            "control_id": olh._control_id(serial), "polling_rate": 4,
        })
        self.assertTrue(result["ok"])
        self.assertNotIn(serial, json.dumps(result))
        _, kwargs = api_request.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["payload"], {"pollingRate": 4, "deviceId": serial})
        self.assertNotIn(serial, json.dumps({"control_id": olh._control_id(serial)}))

    def test_error_text_redacts_long_device_ids(self):
        self.assertNotIn("PRIVATE-SERIAL-123456", olh._safe_error_text(RuntimeError("device PRIVATE-SERIAL-123456 failed")))

    @patch.object(olh, "_api_get", return_value={"data": {"devices": []}})
    @patch.object(olh, "installed_version", return_value="0.9.0-1")
    @patch.object(olh, "_service_state")
    def test_detects_system_context(self, service_state, _version, _api):
        service_state.side_effect = [
            {"available": True, "active": "inactive", "sub": "dead", "enabled": "disabled", "load": "loaded", "error": ""},
            {"available": True, "active": "active", "sub": "running", "enabled": "enabled", "load": "loaded", "error": ""},
        ]
        status = olh.collect_status()
        self.assertEqual(status.service_context, "system")
        self.assertTrue(status.api_reachable)

    @patch.object(olh, "_run")
    def test_service_actions_are_user_scoped(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = ""
        run.return_value.stderr = ""
        self.assertTrue(olh.run_user_service_action("restart")["ok"])
        self.assertEqual(run.call_args.args[0], ["systemctl", "--user", "restart", "OpenLinkHub.service"])
        with self.assertRaises(ValueError):
            olh.run_user_service_action("delete")


if __name__ == "__main__":
    unittest.main()

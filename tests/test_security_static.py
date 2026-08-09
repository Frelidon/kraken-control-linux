#!/usr/bin/env python3
"""Dependency-free static release checks for version 2.9.6."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "kraken_control.py").read_text(encoding="utf-8")
rule = (ROOT / "71-nzxt-kraken-2023.rules").read_text(encoding="utf-8")
installer = (ROOT / "install.sh").read_text(encoding="utf-8")
helper = (ROOT / "install-udev-rule.sh").read_text(encoding="utf-8")

assert 'APP_VERSION = "2.9.6"' in code
assert "class CurveEditor" in code
assert "class AnimatedBackgroundWidget" in code
assert "class SetupWizard" in code

assert 'scroll.setObjectName("settingsScrollArea")' in code
assert 'scroll.setWidgetResizable(True)' in code
assert 'scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)' in code
assert 'content.setMinimumWidth(820)' in code
assert 'migration/v292_settings_layout' in code
assert 'self.resize(1280, 880)' in code

assert "class InteractionAuditLogger" in code
assert "QImage.Format.Format_RGB32" in code
assert "WA_TransparentForMouseEvents" in code
assert "ensure_background_layer_order" in code
assert "self.background_widget.lower()" in code
assert "self.content_root.raise_()" in code
assert "content_rgba" in code
assert "QStackedLayout.StackingMode.StackAll" in code
assert "CPU-Offscreen-Renderer" in code
assert "save_application_log" in code
assert "self.log_char_limit = 10000" in code
assert "_trim_log_to_character_limit" in code
assert "app.installEventFilter(self._interaction_audit)" in code
assert "KLICK" in code and "ÄNDERUNG" in code and "NAVIGATION" in code
assert "PROFILES" not in code or "PROFILE_SCHEMA_VERSION" in code
assert "PROFILE_SCHEMA_VERSION = 1" in code
assert "make_profiles_tab" in code
assert "create_profile_from_current" in code
assert "export_selected_profile" in code
assert "import_profiles" in code
assert "apply_startup_profile" in code
assert "screen_summary" in code
assert "devicePixelRatio" in code
assert "21:9" in code and "32:9" in code
assert "DEFAULT_BACKGROUND_THEME" in code
assert "Sternenfeld" in code and "Kosmischer Nebel" in code and "Aurora" in code
assert "prozedural" in code.lower()
assert "Tab and Shift+Tab deliberately pass through" in code
assert "Ctrl+Shift+R" in code
assert "AM5_CPU_PROFILES" in code
assert "AMD Ryzen 7 9800X3D" in code
assert '"Ryzen 9000 X3D", 95' in code
assert '"Ryzen 7000 X3D", 89' in code
assert "read_amd_cpu_temperature" in code
assert 'def kraken_direct_args()' in code
assert '[LIQUIDCTL, "--direct-access", "--match", KRAKEN_MATCH]' in code
assert 'args = self.curve_args(channel, points)' in code
assert "k10temp" in code
assert "CPU-Tjmax" in code
assert "Kraken-Wassertemperatur" in code
assert "repair_permissions" in code
assert "show_permission_error" in code
assert "matching_hidraw_nodes" in code
assert 'SUBSYSTEM=="hidraw"' in rule
assert 'SUBSYSTEMS=="usb"' in rule
assert 'MODE="0660"' in rule
assert 'TAG+="uaccess"' in rule
assert "--subsystem-match=hidraw" in helper
assert "install-udev-rule.sh" in installer
assert "CPU_PROFILES.md" in installer
assert "COMPONENT_VERSIONS.md" in installer
assert "ANIMATED_BACKGROUNDS.md" in installer
assert "PROFILES.md" in installer
assert "FEATURES_BY_VERSION.md" in installer
assert "SOURCE_CODE.md" in installer
assert (ROOT / "CPU_PROFILES.md").exists()
assert (ROOT / "COMPONENT_VERSIONS.md").exists()
assert (ROOT / "ANIMATED_BACKGROUNDS.md").exists()
assert (ROOT / "PROFILES.md").exists()
assert (ROOT / "FEATURES_BY_VERSION.md").exists()
assert (ROOT / "SOURCE_CODE.md").exists()

assert "toggle_expert_mode" in code
assert "configure_expert_mode_controls" in code
assert "Aktiver Kühlmodus" in code
assert "set_cooling_mode" in code
assert "clock_auto_resend" in code
assert "send_clock_keepalive" in code

assert (ROOT / "install-dependencies.sh").exists()
dep_helper = (ROOT / "install-dependencies.sh").read_text(encoding="utf-8")
assert "python3-pyside6" in dep_helper
assert "python3-pillow" in dep_helper
assert "liquidctl" in dep_helper
assert "pkexec" in dep_helper
assert "install-dependencies.sh" in installer
assert "--check-and-install" in installer
assert "install_missing_dependencies" in code
assert "Fehlende Pakete &installieren" in code

readme = (ROOT / "README.md").read_text(encoding="utf-8")
last_devices = readme.rfind("## Unterstützte Geräte")
assert last_devices >= 0
assert "## " not in readme[last_devices + len("## Unterstützte Geräte"):]
assert "| NZXT 2023 RGB Controller | `1e71:2012` | Drei ARGB-Kanäle über liquidctl |" in readme[last_devices:]
assert "kraken_control_source_2_9_6.tar.gz" in readme or "kraken_control_source_2_9_6.tar.gz" in (ROOT / "SOURCE_CODE.md").read_text(encoding="utf-8")

print("Static release checks passed.")

# 2.9.6 regression: disabling must preserve the last animation theme.
assert 'def on_background_enabled_toggled' in code
assert 'self.background_last_theme' in code
segment = code[code.index('def disable_background'):code.index('def sync_design_controls')]
assert 'self.background_theme_combo.setCurrentText("Aus")' not in segment

# 2.9.6: all cooling writes use direct access and background permission errors stay non-modal.
assert 'Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)]' in code
assert code.count('Backend.kraken_direct_args() + ["set", "pump", "speed", str(pump)]') >= 2
assert code.count('Backend.kraken_direct_args() + ["set", "fan", "speed", str(fan)]') >= 2
assert "foreground = self.isVisible() and self.isActiveWindow()" in code
assert "permission_retry_after" in code

# 2.9.6 regression: LCD clock start must use the current clock_format combo box.
assert "self.clock_24h" not in code
assert 'str(self.clock_format.currentData()) == "24"' in code
assert "LCD-UHR: gestartet" in code
assert "LCD-UHR: Bild erfolgreich übertragen" in code

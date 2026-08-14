#!/usr/bin/env python3
"""Dependency-free static release checks for public version 3.0.9."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "kraken_control.py").read_text(encoding="utf-8")
rule = (ROOT / "71-nzxt-kraken-2023.rules").read_text(encoding="utf-8")
installer = (ROOT / "install.sh").read_text(encoding="utf-8")
helper = (ROOT / "install-udev-rule.sh").read_text(encoding="utf-8")

assert 'APP_VERSION = "3.0.9"' in code
assert 'APP_NAME = "Open Hardware Control"' in code
assert "make_navigation_sidebar" in code
assert "update_navigation_visibility" in code
assert "Nicht erkannte Geräte/Module anzeigen" in code
assert "make_openlinkhub_tab" in code
assert "refresh_openlinkhub_status" in code
assert "class MacroRecorderDialog" in code
assert "edit_selected_openlinkhub_mouse_button" in code
assert "record_openlinkhub_keyboard_macro" in code
assert "on_temperature_unit_changed" in code
assert "hardware_label_color" in code and "hardware_value_color" in code
assert 'OPENLINKHUB_API_URL = "http://127.0.0.1:27003"' in code
assert (ROOT / "openlinkhub_integration.py").exists()
assert (ROOT / "OPENLINKHUB_INTEGRATION.md").exists()
assert (ROOT / "Open_Hardware_Control_Projekt.md").exists()
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
assert 'def update_cpu_curve_control' in code
assert 'def interpolate_curve' in code
assert 'def apply_cpu_curve_targets' in code
assert 'CPU_CURVE_SAMPLE_MS = 1000' in code
assert 'Pumpenkurve nach CPU-Temperatur' in code
assert 'Lüfterkurve nach CPU-Temperatur' in code
assert 'table.setHorizontalHeaderLabels([f"CPU {temperature_symbol(self.temperature_unit)}", "Leistung %"])' in code
assert 'restore_safe_hardware_fallback_sync_on_quit' in code
assert 'SAFE_HARDWARE_PUMP_CURVE' in code and 'SAFE_HARDWARE_FAN_CURVE' in code
assert 'KURVEN-MIGRATION 3.0.5' in code
sensor_code = (ROOT / "kraken_sensors.py").read_text(encoding="utf-8")
assert "k10temp" in sensor_code
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
assert "Kraken_Control_Projekt.md" in installer
assert "USB_CAPTURE_FINDINGS.md" in installer
assert "kraken_cam_streamer.py" in installer
assert "kraken_lcd_designs.py" in installer
assert "kraken_sensors.py" in installer
assert "openlinkhub_integration.py" in installer
assert "Open_Hardware_Control_Projekt.md" in installer
assert "OPENLINKHUB_INTEGRATION.md" in installer
assert (ROOT / "kraken_lcd_designs.py").exists()
assert (ROOT / "kraken_sensors.py").exists()
assert (ROOT / "CPU_PROFILES.md").exists()
assert (ROOT / "COMPONENT_VERSIONS.md").exists()
assert (ROOT / "ANIMATED_BACKGROUNDS.md").exists()
assert (ROOT / "PROFILES.md").exists()
assert (ROOT / "FEATURES_BY_VERSION.md").exists()
assert (ROOT / "SOURCE_CODE.md").exists()
assert (ROOT / "Kraken_Control_Projekt.md").exists()
assert (ROOT / "USB_CAPTURE_FINDINGS.md").exists()
assert (ROOT / "tools" / "analyze_usbpcap.py").exists()

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
assert "qt6-qtsvg" in dep_helper
assert "liquidctl" in dep_helper
assert "pkexec" in dep_helper
assert "install-dependencies.sh" in installer
assert "--check-gui-and-install" in installer
assert "install_missing_dependencies" in code
assert "Fehlende Pakete &installieren" in code

readme = (ROOT / "README.md").read_text(encoding="utf-8")
assert "# Open Hardware Control by Frelidon 3.0.9 – NZXT Kraken & Corsair unter Linux" in readme
assert "Corsair · OpenLinkHub" in readme
assert "| NZXT 2023 RGB Controller | `1e71:2012`" in readme

print("Static release checks passed.")

# 2.9.6 regression: disabling must preserve the last animation theme.
assert 'def on_background_enabled_toggled' in code
assert 'self.background_last_theme' in code
segment = code[code.index('def disable_background'):code.index('def sync_design_controls')]
assert 'self.background_theme_combo.setCurrentText("Aus")' not in segment

# 2.9.6: all cooling writes use direct access and background permission errors stay non-modal.
assert 'Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)]' in code
assert code.count('Backend.kraken_direct_args() + ["set", "pump", "speed", str(pump)]') >= 1
assert code.count('Backend.kraken_direct_args() + ["set", "fan", "speed", str(fan)]') >= 1
assert "foreground = self.isVisible() and self.isActiveWindow()" in code
assert "permission_retry_after" in code

# 2.9.6 regression: LCD clock start must use the current clock_format combo box.
assert "self.clock_24h" not in code
assert 'str(self.clock_format.currentData()) == "24"' in code
assert "LCD-UHR: gestartet" in code
assert "LCD-UHR: Bild erfolgreich übertragen" in code


# 2.9.7 internal: persistent LCD acknowledgement, crash recovery and first localization stage.
assert 'SUPPORTED_UI_LANGUAGES = {"de": "Deutsch", "en": "English", "es": "Español", "fr": "Français"}' in code
assert 'def capture_translation_sources' in code
assert 'def apply_ui_language' in code
assert 'self.settings.setValue("ui/language", language)' in code
assert 'Experimentalhinweise zurücksetzen' in code
assert 'clock/experimental_warning_ack' in code
assert 'lcd/keepalive_warning_ack' in code
assert 'lcd/experimental_session_active' in code
assert 'lcd/recovery_required' in code
assert 'def activate_lcd_safe_mode' in code
assert 'def record_lcd_failure' in code
assert 'LCD_FAILURE_LIMIT = 3' in code
assert 'set", "lcd", "screen", "liquid"' in code
assert 'Unsauber beendete experimentelle LCD-Sitzung erkannt' in code
assert 'LCD-Bild-Fallback' in code
assert 'self.setWindowTitle(f"{DISPLAY_NAME} {APP_VERSION} — Linux")' in code
assert 'experimental_autostart_blocked' in code


# 2.9.8+ internal: GIF helper, LCD safety coordination and minimized autostart.
assert 'GIF_HELPER_NAME = "kraken_cam_streamer.py"' in code
assert 'def start_gif_stream' in code
assert 'def stop_gif_stream' in code
assert 'gif/experimental_warning_ack' in code
assert 'mark_experimental_lcd_active("hardware_animation" if self.gif_generated_hardware_mode else "gif")' in code
assert 'gif/fps' in code
assert 'Beim Systemstart minimiert/im Tray starten' in code
assert '"--autostart" in sys.argv' in code
assert 'exec_line += " --autostart"' in code
assert 'def should_start_minimized_from_autostart' in code
assert 'window.apply_initial_window_state()' in code
assert 'AUTOSTART_LCD_DELAY_MS = 5000' in code
assert '"mode": self.current_lcd_profile_mode()' in code
assert 'def resolve_profile_lcd_mode' in code
assert 'self.apply_profile_by_id(profile_id, startup=True)' in code
assert 'if not (startup and self.should_start_minimized_from_autostart())' in code
assert 'QTimer.singleShot(0, self.apply_initial_window_state)' in code
assert 'install_session_signal_handlers(window)' in code
assert 'gif_force_stop_timer' in code
assert 'Bewegungsglättung (Motion-Interpolation)' in code
assert 'for fps in (5, 8, 10, 12, 15, 20)' in code
assert 'CAM-nah · automatisch · empfohlen · max. 25 FPS' in code
assert 'Erweiterte GIF-Optionen anzeigen' in code
assert 'gif/show_advanced' in code
assert 'test-gifs' in installer
assert (ROOT / 'test-gifs' / '02_moving-bars_27fps.gif').exists()
assert (ROOT / 'tools' / 'generate_test_gifs.py').exists()

# 2.9.15 internal: replace 30/32-Hz experiments with CAM-near raw FW2 transport.
helper_code = (ROOT / "kraken_cam_streamer.py").read_text(encoding="utf-8")
assert 'CAM_TRANSPORT_FPS = 80.0 / 3.0' in helper_code
assert 'SAFE_TRANSPORT_FPS = 25.6' in helper_code
assert 'RGB565_FRAME_BYTES = LCD_SIZE[0] * LCD_SIZE[1] * 2' in helper_code
assert 'class CamRawTransport' in helper_code
assert 'START = [0x36, 0x01, 0x00, 0x01, 0x06]' in helper_code
assert 'END = [0x36, 0x02]' in helper_code
assert 'HEADER_PREFIX = [0x12, 0xFA' in helper_code
assert 'self.bulk_write(data)' in helper_code
assert 'estimate_global_motion' in helper_code
assert 'motion_interpolate' in helper_code
assert 'motion-compensated-global' in helper_code
assert 'Image.blend' in helper_code  # only fallback/merge after motion compensation
assert 'time.monotonic()' in helper_code
assert 'choices=("cam", "safe")' in helper_code
assert 'TRANSPORT_MODES = {' in helper_code
assert '"cam": CAM_TRANSPORT_FPS' in helper_code
assert '"safe": SAFE_TRANSPORT_FPS' in helper_code
assert '30 Hz · Smooth · mehr Zwischenbilder' not in code
assert '32 Hz · Experimental · höchste Glättung' not in code
assert 'CAM-Takt · 26,667 Hz · phasenstabil · Standard' in code
assert 'gif/transport_mode' in code
assert '"--transport", transport_mode' in code
assert 'LCD-Frame-Wiederholungen' in code
assert 'LCD-Frame-Sprünge' in code
assert 'P90' in code
assert 'startup_profile_owns_lcd' in code
assert 'clock_last_minute_upload_key' in code
assert 'def update_clock_lcd(self, force: bool = False)' in code
assert not (ROOT / 'kraken_gif_streamer.py').exists()
assert not (ROOT / 'test-gifs' / '02_moving-bars_30fps.gif').exists()
assert not (ROOT / 'test-gifs' / '02_moving-bars_32fps.gif').exists()

print("2.9.15 CAM-raw static checks passed.")

# 2.9.20 internal: exclusive Kraken ownership, matched ACKs and phase-stable playback.
assert 'GIF_STREAM_START_WAIT_SECONDS = 15.0' in code
assert 'GIF_STREAM_WATCHDOG_SECONDS = 12.0' in code
assert 'def is_idle(self)' in code
assert 'def pause_kraken_io_for_gif' in code
assert 'def resume_kraken_io_after_gif' in code
assert 'def kraken_command_blocked_by_gif' in code
assert 'def check_gif_stream_watchdog' in code
assert 'self.status_timer.stop()' in code
assert 'CPU-Kurven lesen Linux-hwmon weiter' in code
assert 'self.gif_process.terminate()' in code
assert 'HID_RESPONSE_READ_ATTEMPTS = 12' in helper_code
assert 'clear_enqueued_reports' in helper_code
assert '_command_with_matching_reply' in helper_code
assert 'expected = bytes(((data[0] + 1) & 0xFF, data[1]))' in helper_code
assert 'unrelated_hid_reports' in helper_code
assert 'ack_matching=True' in helper_code
assert 'CAM_ACK_GUARD_S = 0.0001' in helper_code
assert 'SAFE_DISPLAY_GUARD_S = 0.0002' in helper_code
assert 'next_phase_locked_start' in helper_code
assert 'MAX_PHASE_CORRECTION_STEP_S = 0.00025' in helper_code
assert 'lcd_index = (transport_frames + 1) % len(frames)' in helper_code
assert 'cam-raw-26.667hz-phase-locked' in helper_code
assert 'loop_transition_diagnostics' in helper_code
assert 'Der Loop dieser GIF-Datei enthält wahrscheinlich einen sichtbaren Übergang.' in code

print("2.9.20 exclusive matched-ACK/watchdog, phase-lock and loop-warning checks passed.")

# 2.9.21: rounded hardware dashboards, dGPU sensing and complete live i18n switching.
assert 'from kraken_lcd_designs import' in code
assert 'def read_amd_gpu_temperature' in code
assert 'mem_info_vram_total' in sensor_code
assert 'Hardwaredaten-Designs · Live' in code
assert 'hardware_lcd/active' in code
assert 'hardware_lcd/experimental_warning_ack' in code
assert 'mark_experimental_lcd_active("hardware")' in code
assert 'def refresh_dynamic_translations' in code
assert 'for menu in self.findChildren(QMenu)' in code
assert code.index('self.restore_settings()') < code.index('self.capture_translation_sources()', code.index('self.restore_settings()'))
for language in ('en', 'es', 'fr'):
    assert f'UI_TRANSLATIONS["{language}"].update' in code
assert 'DEFAULT_ACCENT = "#00c8ff"' in (ROOT / "kraken_lcd_designs.py").read_text(encoding="utf-8")

# 2.9.22: scalable text and generated animated sensor dashboards.
design_code = (ROOT / "kraken_lcd_designs.py").read_text(encoding="utf-8")
assert 'def render_hardware_animation' in design_code
assert 'font_scale_percent' in design_code
assert 'phase=index / frame_count' in design_code
assert 'Schrift- und Zahlen-Größe' in code
assert 'Animierte Hardwaredaten · Ringe und Orbits' in code
assert 'def start_hardware_animation' in code
assert 'generated_hardware=True' in code
assert 'mark_experimental_lcd_active("hardware_animation" if self.gif_generated_hardware_mode else "gif")' in code
assert 'hardware_animation/experimental_warning_ack' in code

# 2.9.23: CPU/GPU values refresh out-of-process while liquid stays the last safe Kraken value.
assert 'self.hardware_animation_spec_file' in code
assert '"--hardware-spec", str(self.hardware_animation_spec_file)' in code
assert 'CPU/GPU live · Wasser letzter sicherer Wert' in code
assert 'sensor_update' in code and 'sensor_update_error' in code
assert 'HARDWARE_SENSOR_INTERVAL_S = 2.0' in helper_code
assert 'ProcessPoolExecutor' in helper_code
assert 'multiprocessing.get_context("spawn")' in helper_code
assert 'def prepare_hardware_animation' in helper_code
assert 'def render_hardware_cache_worker' in helper_code
assert 'def frames_from_cache_file' in helper_code
assert 'read_amd_cpu_temperature' in helper_code and 'read_amd_gpu_temperature' in helper_code
assert 'live_sensor_status=True' in helper_code

# 3.0.1: coordinated cached-stream USB handoff for manual cooling writes.
assert 'def defer_cooling_action_for_gif' in code
assert 'def begin_deferred_gif_cooling_action' in code
assert 'def finish_gif_cooling_when_idle' in code
assert 'def complete_gif_cooling_transaction' in code
assert 'self.gif_process.write(b"PAUSE\\n")' in code
assert 'self.gif_process.write(b"RESUME\\n")' in code
assert 'elif kind == "paused"' in code
assert 'elif kind == "resumed"' in code
assert 'def read_control_command' in helper_code
assert 'command in {"STOP", "PAUSE", "RESUME"}' in helper_code
assert 'device_stack.close()' in helper_code
assert '"paused"' in helper_code and '"resumed"' in helper_code
assert (ROOT / "tests" / "test_gif_cooling_handoff.py").exists()

# 3.0.2: explicit per-channel switch between fixed/manual and hardware curve mode.
assert 'Betriebsart umschalten' in code
assert 'Manuell aktivieren' in code
assert 'Pumpenkurve aktivieren' in code
assert 'Lüfterkurve aktivieren' in code
assert 'button.setObjectName("coolingModeButton")' in code
assert 'def cooling_mode_kind' in code
assert 'def switch_cooling_mode' in code
assert 'def update_cooling_mode_buttons' in code
assert 'self.set_fixed_speed(channel, slider.value())' in code
assert 'self.apply_curve(channel, curve_table)' in code

# 3.0.3: stable active-mode colour without transient Qt check-state flicker.
assert 'button.setProperty("coolingState", "inactive")' in code
assert 'button.setCheckable(True)' not in code
assert 'QPushButton#coolingModeButton[coolingState="active"]' in code
assert 'button.style().unpolish(button)' in code
assert 'button.style().polish(button)' in code

# 3.0.4: allow-listed, session-gated OpenLinkHub device writes.
openlink_code = (ROOT / "openlinkhub_integration.py").read_text(encoding="utf-8")
assert 'WRITE_ENDPOINTS = {' in openlink_code
assert 'def validate_write_payload' in openlink_code
assert 'def run_write_action' in openlink_code
assert 'def _resolve_device_id' in openlink_code
assert 'hashlib.sha256' in openlink_code
assert '"speed-manual": ("POST", "/api/speed/manual")' in openlink_code
assert '"rgb-profile": ("POST", "/api/color")' in openlink_code
assert '"mouse-dpi": ("POST", "/api/mouse/dpi")' in openlink_code
assert '"mouse-key-assignment": ("POST", "/api/mouse/updateKeyAssignment")' in openlink_code
assert '"macro-create-recording": ("MULTI", "/api/macro/new")' in openlink_code
assert '"headset-anc": ("POST", "/api/headset/anc")' in openlink_code
assert '"keyboard-layout": ("POST", "/api/keyboard/layout")' in openlink_code
assert 'Direkte OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren' in code
assert 'def run_openlinkhub_write' in code
assert 'log_command=False' in code

# 3.0.9: orderly LCD reset and original interactive mouse schematics.
assert 'def restore_original_lcd_sync_on_quit' in code
assert code.count('self.restore_original_lcd_sync_on_quit()') == 2
assert 'Backend.kraken_args() + ["set", "lcd", "screen", "liquid"]' in code
assert code.index('self.shutdown_gif_stream_sync()') < code.index('self.restore_original_lcd_sync_on_quit()')
assert 'class MouseSchematicWidget' in code
assert 'Grafische Tastenbelegung' in code
assert 'def update_openlinkhub_mouse_visual' in code
assert 'openlinkhub_mouse_visuals.py' in installer
assert 'SOURCE_DIR/assets' in installer
mouse_visuals = (ROOT / 'openlinkhub_mouse_visuals.py').read_text(encoding='utf-8')
assert 'def classify_mouse_layout' in mouse_visuals
assert 'def visual_button_rows' in mouse_visuals
assert 'def _mouse_assignments' in openlink_code
for asset in ('mouse-compact.svg', 'mouse-ergonomic.svg', 'mouse-symmetric.svg', 'mouse-multi.svg', 'mouse-mmo.svg'):
    assert (ROOT / 'assets' / asset).exists()

# 3.0.9: verified mouse assignments/macros and complete temperature presentation.
assert 'class MacroRecorderDialog' in code
assert 'def edit_selected_openlinkhub_mouse_button' in code
assert 'def record_openlinkhub_keyboard_macro' in code
assert '"mouse-key-assignment": ("POST", "/api/mouse/updateKeyAssignment")' in openlink_code
assert '"macro-create-recording": ("MULTI", "/api/macro/new")' in openlink_code
assert '"macroType": 3' in openlink_code and '"macroType": 5' in openlink_code
assert 'display/temperature_unit' in code
assert 'def celsius_to_display' in code and 'def display_to_celsius' in code
assert 'hardware_lcd/label_color' in code and 'hardware_lcd/value_color' in code
assert 'hardware_lcd/label_scale' in code and 'hardware_lcd/value_scale' in code

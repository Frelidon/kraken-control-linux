# Quellcode und reproduzierbare Release-Pakete

Jeder weitergegebene Open-Hardware-Control-Stand soll vollständig nachvollziehbar bleiben.

Das öffentliche Installations-ZIP 3.0.9 enthält den direkt editierbaren Python-Quellcode:

- `kraken_control.py`
- `openlinkhub_integration.py` (lokale OpenLinkHub-API-, validierte Schreib- und Benutzerdienst-Anbindung)
- `openlinkhub_mouse_visuals.py` (Modellfamilien, lizenzfreie Schema-Geometrie und sichere Zuordnung gemeldeter Tastenbelegungen)
- `kraken_lcd_designs.py` (reiner Pillow-Renderer für fünf lokalisierte, skalierbare statische Layouts und nahtlose 20/25-FPS-Hardwareanimationen)
- `kraken_sensors.py` (gemeinsame, rein lesende k10temp-/amdgpu-Sensorauswahl für GUI und Streamer)
- `kraken_cam_streamer.py` (CAM-naher Firmware-2.x-Raw-LCD-Streamer mit Bewegungsglättung, eindeutiger ACK-Zuordnung, phasenstabiler Reihenfolge und GIF-Loop-Diagnose)
- alle Installations-, Diagnose- und udev-Skripte
- Desktopdatei, selbst erstelltes SVG-Symbol und fünf eigene Maus-SVGs unter `assets/`
- vollständige GPL-Lizenz
- deutsche und englische Dokumentation
- zentrale Projektdokumentation `Open_Hardware_Control_Projekt.md`
- OpenLinkHub-Moduldokumentation `OPENLINKHUB_INTEGRATION.md`
- historische NZXT-Moduldokumentation `Kraken_Control_Projekt.md`
- technische USB-Mitschnittauswertung `USB_CAPTURE_FINDINGS.md`
- reproduzierbares Standardbibliothek-Werkzeug `tools/analyze_usbpcap.py`
- statische, Stub-Laufzeit- und OpenLinkHub-Mauszuordnungstests
- selbst erzeugte 240×240-Test-GIFs für 24, 25, 26 und 27 FPS sowie das Generator-Skript
- `MANIFEST.sha256` mit Prüfsummen der Paketdateien

Zu jedem Release werden aus genau demselben Git-Stand erzeugt:

- `open_hardware_control_v3_0_9.zip` – universelles Benutzerpaket
- `open-hardware-control_3.0.9_all.deb` – Debian/Ubuntu/Linux-Mint-Paket
- `open-hardware-control-3.0.9-1.noarch.rpm` – Fedora/Nobara-Paket
- `open-hardware-control-3.0.9-source.tar.gz` – vollständiger Quellcode-Snapshot
- `Entwicklerpaket 3.0.9.zip` – vollständiger editierbarer Projektbaum einschließlich Tests, Werkzeuge und GitHub-Automatisierung
- `SHA256SUMS` – Prüfsummen aller Release-Dateien

Die enthaltenen Test-GIFs werden vollständig aus dem mitgelieferten GPL-Quellcode erzeugt und sind keine externen Mediendateien. `scripts/build_release.py` baut alle Pakete reproduzierbar aus dem ausgecheckten Quellbaum.

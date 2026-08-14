# Open Hardware Control by Frelidon 3.0.9 – NZXT Kraken & Corsair on Linux

<!-- project-badges -->
[![CI](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml) [![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](LICENSE) [![Release](https://img.shields.io/github/v/release/Frelidon/kraken-control-linux?display_name=tag)](https://github.com/Frelidon/kraken-control-linux/releases)
<!-- /project-badges -->

Open Hardware Control is a free Linux GUI for the **NZXT Kraken LCD**, pump, radiator fans and RGB, with **Corsair device integration through OpenLinkHub**. It targets Fedora, Nobara, Debian, Ubuntu, Linux Mint, Arch Linux, Manjaro, EndeavourOS and openSUSE.

![Open Hardware Control dashboard](docs/images/screenshots/01-dashboard-overview.png)

<!-- project-repository -->
Project repository: <https://github.com/Frelidon/kraken-control-linux>
<!-- /project-repository -->

Version 3.0.9 turns the OpenLinkHub mouse schematic into a direct assignment editor for safely reported buttons. It also adds a deliberately window-local keyboard macro recorder. Generated LCD hardware designs remove the small LIVE/program captions, offer independent label/value colours and sizes, and support a global Celsius/Fahrenheit setting across the UI, profiles, curves and regenerated animations.

Closing to the tray deliberately keeps LCD output and curve control running. A true quit stops the raw GIF streamer first, restores `lcd screen liquid`, then stores the conservative autonomous cooling fallback. Five in-project SVG families cover compact, ergonomic, symmetric, multi-button and MMO mice without vendor photos. Only buttons carrying a safe index reported by OpenLinkHub can be edited; the application never guesses one.

Mouse assignments use OpenLinkHub's documented assignment endpoint and remain locked until writes are explicitly enabled for the session. The macro recorder captures only individual keys and delays while its visible dialog has focus; it installs no global input hook. Cooling and safety logic continue to store Celsius internally, so switching the display to Fahrenheit cannot alter the physical thresholds.

Since 3.0.6, the active LCD mode is stored explicitly in full and LCD profiles. Legacy 3.0.5 profiles containing a GIF are migrated to GIF mode. A saved maximized window state can no longer reopen the hidden autostart window, while manual launches continue to open normally. Orderly desktop-session termination also clears the experimental crash marker before USB cleanup.

Both NZXT curves are now evaluated continuously from Linux hwmon. The controller interpolates between points, smooths short Ryzen temperature spikes, adds hysteresis and rate limits writes. It keeps reading the CPU during LCD GIF streaming and uses the coordinated USB handoff only for relevant duty changes. Existing liquid curves are migrated to safe CPU curves, all AM5 profiles provide updated CPU points, repeated sensor failure applies a 75% fallback, and a clean application exit stores conservative autonomous liquid curves in the Kraken.

CPU curves require the application to keep running. Closing to the system tray preserves control; a real exit installs the safe hardware fallback.

OpenLinkHub controls include reported cooling profiles and manual channel values, RGB profiles, brightness, labels, LCD rotation, mouse DPI/polling/sleep options, keyboard profile/layout/device values and headset ANC/sidetone options. Writes remain locked until explicitly enabled for the current application session.

Pump, radiator-fan, quick-profile and calculated CPU-curve writes use a short ownership handoff: the streamer finishes a frame and releases USB, the GUI sends the cooling transaction exclusively, and the same cached stream reconnects and continues automatically. Kraken status polling remains paused, while CPU sensing and CPU-curve evaluation continue through Linux hwmon.

## Highlights

- hierarchical left sidebar
- automatic device discovery and hardware-filtered modules
- optional display of undetected modules
- migration of existing Kraken Control settings
- OpenLinkHub installation, service-context and local-API detection
- Corsair device and telemetry view plus allow-listed documented write actions
- user-scoped OpenLinkHub start, stop and restart actions
- direct access to the local OpenLinkHub dashboard
- warnings for system context or two active services

## Installation

Fedora/Nobara RPM:

```bash
cd ~/Downloads
sudo dnf install ./open-hardware-control-3.0.9-1.noarch.rpm
```

Debian/Ubuntu/Linux Mint DEB:

```bash
cd ~/Downloads
sudo apt install ./open-hardware-control_3.0.9_all.deb
```

Universal ZIP for the supported distro families:

```bash
cd ~/Downloads
unzip open_hardware_control_v3_0_9.zip
cd open-hardware-control-3.0.9
chmod +x install.sh
./install.sh
```

The existing installation is updated in place and **Open Hardware Control by Frelidon** then appears in the application menu. See [INSTALL.md](INSTALL.md) for all distro-specific dependency commands.

The compatibility command `kraken-control` also launches the new application. OpenLinkHub is installed separately and is not bundled or modified by Open Hardware Control.

The OpenLinkHub adapter only accepts loopback URLs, exposes no full serial numbers in the UI or logs, validates every payload and never changes the system-wide service automatically. Complex macro editing, the full RGB editor and media operations remain in OpenLinkHub's local web dashboard.

See `Open_Hardware_Control_Projekt.md`, `OPENLINKHUB_INTEGRATION.md`, `SECURITY.md` and `SUPPORTED_DEVICES.md`. The complete NZXT module history remains in `Kraken_Control_Projekt.md` and `USB_CAPTURE_FINDINGS.md`.

Public experimental beta, provided without warranty. Independent project, not officially affiliated with NZXT, Corsair or OpenLinkHub. GPL-3.0-or-later.

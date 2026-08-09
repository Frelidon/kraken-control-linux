# Kraken Control by Frelidon 2.9.6 – Linux

<!-- project-badges -->
[![CI](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml) [![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](https://github.com/Frelidon/kraken-control-linux/blob/main/LICENSE) [![Release](https://img.shields.io/github/v/release/Frelidon/kraken-control-linux?display_name=tag)](https://github.com/Frelidon/kraken-control-linux/releases)
<!-- /project-badges -->

Independent open-source graphical control application for supported **NZXT Kraken (2023)** hardware on Linux.

> **Status:** experimental open-source beta. Use at your own risk. This project is independent from NZXT and is not endorsed or supported by NZXT.

Kraken Control uses [`liquidctl`](https://github.com/liquidctl/liquidctl) as its hardware backend. The application contains no telemetry, advertising, or automatic cloud service.

<!-- project-repository -->
Project repository: <https://github.com/Frelidon/kraken-control-linux>
<!-- /project-repository -->

## Release 2.9.6

2.9.6 is the real-hardware-tested build prepared for the first public GitHub release.

Highlights since 2.9.4:

- **2.9.6:** fixed the LCD clock start regression caused by the removed `clock_24h` widget; a regression test now guards this path.
- **2.9.5:** all pump and radiator-fan writes use the confirmed `liquidctl --direct-access` path.
- **2.9.5:** background permission failures no longer create repeated modal repair dialogs.
- **2.9.5:** the visible action log is capped at **10,000 characters**, removing the oldest complete lines first.
- **2.9.5:** more detailed logging for CPU detection/profiles, LCD clock, theme, and display changes.
- **2.9.4:** animated backgrounds can be re-enabled after being disabled and keep the last selected theme.
- **2.9.3:** stabilized light-theme/background rendering.
- **2.9.2:** settings are scrollable and the window adapts better to different screen sizes.

Full history: [`CHANGELOG.md`](CHANGELOG.md) and [`FEATURES_BY_VERSION.md`](FEATURES_BY_VERSION.md).

## Main features

- Kraken coolant, pump and radiator-fan monitoring
- fixed pump/fan output and graphical curves
- AMD AM5 CPU profiles and optional CPU assistance
- tray/background operation
- LCD images and experimental LCD clock
- NZXT 2023 RGB Controller support
- light, dark and system themes with custom accent color
- procedural animated backgrounds
- categorized full/cooling/LCD/RGB/design profiles
- monitor/DPI-aware app scaling without changing the Linux display resolution
- keyboard paths and accessibility labels
- dependency checks and controlled Fedora/Nobara installation
- udev repair through `pkexec`
- local redacted diagnostics

## Installation on Nobara/Fedora

Optional dependency installation:

```bash
sudo dnf install liquidctl python3-pyside6 python3-pillow polkit
```

From the extracted release directory:

```bash
chmod +x install.sh
./install.sh
```

Start:

```bash
~/.local/bin/kraken-control
```

Kraken Control itself is not run as root.

## Security and privacy

Kraken Control is an experimental hardware-control application. Low fixed cooling values require confirmation, background write failures are rate-limited, and diagnostics/logs should still be manually reviewed before public sharing.

See [`SECURITY.md`](SECURITY.md) and [`PRIVACY.md`](PRIVACY.md).

## Development

Run local checks with:

```bash
./scripts/check_release.sh
```

GitHub Actions runs static and stub runtime tests; CI does not perform real hardware writes.

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License and independence

Licensed under **GPL-3.0-or-later**. See [`LICENSE`](LICENSE).

Project lead and publisher: **Frelidon**. ChatGPT by OpenAI was used as a development assistant for coding, debugging, documentation, and test preparation; it is not a runtime component. See [`AI_ASSISTANCE.md`](AI_ASSISTANCE.md).

All product names and trademarks belong to their respective owners. Kraken Control is not official NZXT software.

## Documentation

- [`CHANGELOG.md`](CHANGELOG.md)
- [`FEATURES_BY_VERSION.md`](FEATURES_BY_VERSION.md)
- [`COMPONENT_VERSIONS.md`](COMPONENT_VERSIONS.md)
- [`CPU_PROFILES.en.md`](CPU_PROFILES.en.md)
- [`PROFILES.md`](PROFILES.md)
- [`ANIMATED_BACKGROUNDS.md`](ANIMATED_BACKGROUNDS.md)
- [`PROJECT_SCOPE.en.md`](PROJECT_SCOPE.en.md)
- [`SOFTWARE_AND_LINKS.en.md`](SOFTWARE_AND_LINKS.en.md)
- [`SOURCE_CODE.md`](SOURCE_CODE.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`SUPPORTED_DEVICES.en.md`](SUPPORTED_DEVICES.en.md)

## Supported devices

| Device | USB ID | Tested scope |
|---|---|---|
| NZXT Kraken RGB 360 (2023, Standard / Non-Elite; liquidctl: `NZXT Kraken 2023`) | `1e71:300e` | Coolant temperature, pump, Kraken-managed radiator fans, 240×240 LCD |
| NZXT 2023 RGB Controller | `1e71:2012` | Three ARGB channels through liquidctl |

Official Kraken specifications: <https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs>

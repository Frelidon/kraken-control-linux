# Kraken Control by Frelidon 2.9.6 – Linux

<!-- project-badges -->
[![CI](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/Frelidon/kraken-control-linux/actions/workflows/ci.yml) [![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](https://github.com/Frelidon/kraken-control-linux/blob/main/LICENSE) [![Release](https://img.shields.io/github/v/release/Frelidon/kraken-control-linux?display_name=tag)](https://github.com/Frelidon/kraken-control-linux/releases)
<!-- /project-badges -->

Unabhängige grafische Open-Source-Steuerung für unterstützte **NZXT Kraken (2023)**-Hardware unter Linux.

> **Status:** experimentelle Open-Source-Beta. Nutzung auf eigenes Risiko. Dieses Projekt ist nicht mit NZXT verbunden und wird nicht von NZXT unterstützt.

Kraken Control verwendet [`liquidctl`](https://github.com/liquidctl/liquidctl) als Hardware-Backend. Die Anwendung enthält keine Telemetrie, keine Werbung und keinen automatischen Cloud-Dienst.

<!-- project-repository -->
Projekt-Repository: <https://github.com/Frelidon/kraken-control-linux>
<!-- /project-repository -->

## Release 2.9.6

2.9.6 ist der für die erste öffentliche GitHub-Veröffentlichung vorbereitete, auf realer Kraken-Hardware getestete Stand.

Wichtigste Änderungen seit 2.9.4:

- **2.9.6:** LCD-Uhr startet wieder korrekt; Regression um das alte `clock_24h`-Widget behoben und durch einen Test abgesichert.
- **2.9.5:** alle Pumpen-/Lüfter-Schreibbefehle verwenden den bestätigten `liquidctl --direct-access`-Pfad.
- **2.9.5:** Berechtigungsfehler im Hintergrund erzeugen keine wiederholten modalen Reparaturfenster mehr.
- **2.9.5:** sichtbares Aktionslog ist auf **10.000 Zeichen** begrenzt; die ältesten vollständigen Zeilen werden zuerst entfernt.
- **2.9.5:** CPU-Erkennung, CPU-Profile, LCD-Uhr, Design und Anzeigeänderungen werden detaillierter protokolliert.
- **2.9.4:** Animationen lassen sich nach dem Ausschalten wieder aktivieren und behalten das zuletzt gewählte Thema.
- **2.9.3:** Light-Theme-/Hintergrund-Rendering stabilisiert.
- **2.9.2:** Einstellungen sind scrollbar und das Fenster passt sich besser an unterschiedliche Bildschirmgrößen an.

Vollständiger Verlauf: [`CHANGELOG.md`](CHANGELOG.md) und [`FEATURES_BY_VERSION.md`](FEATURES_BY_VERSION.md).

## Hauptfunktionen

- Live-Anzeige von Wassertemperatur, Pumpen- und Radiatorlüfterwerten
- feste Pumpen- und Lüfterleistung
- grafischer Pumpen-/Lüfter-Kurveneditor
- AMD-AM5-CPU-Profile und optionale CPU-Assistenz
- sicherer Hintergrundbetrieb mit Tray-Unterstützung
- LCD-Bilder und experimentelle LCD-Uhr
- RGB-Steuerung des separaten NZXT 2023 RGB Controllers
- Hell-, Dunkel- und Systemmodus
- eigene Akzentfarbe
- prozedurale animierte Hintergründe
- kategorisierte Gesamt-, Kühlungs-, LCD-, RGB- und Designprofile
- Monitor-/DPI-Anpassung ohne Änderung der Linux-Bildschirmauflösung
- Tastaturbedienung und Screenreader-Beschriftungen
- Abhängigkeitsprüfung und kontrollierte Fedora/Nobara-Installation
- udev-Berechtigungsreparatur über `pkexec`
- lokaler, redigierter Diagnosebericht

## Voraussetzungen

Für Nobara/Fedora werden verwendet:

```bash
liquidctl
python3-pyside6
python3-pillow
polkit
```

Optional vorab installieren:

```bash
sudo dnf install liquidctl python3-pyside6 python3-pillow polkit
```

Kraken Control selbst wird **nicht als root** gestartet.

## Installation

Release-ZIP entpacken und im entpackten Ordner ausführen:

```bash
chmod +x install.sh
./install.sh
```

Danach:

```bash
~/.local/bin/kraken-control
```

Die Anwendung kann fehlende unterstützte Fedora/Nobara-Pakete nach ausdrücklicher Bestätigung über DNF installieren.

## Hardwarezugriff

Die mitgelieferte udev-Regel erlaubt dem angemeldeten Desktop-Benutzer Zugriff auf die getesteten NZXT-Geräte. Falls nötig:

```bash
./install-udev-rule.sh
```

oder in der App **Einstellungen → Gerätezugriff → Berechtigungen reparieren**.

Für Kühlungs-Schreibzugriffe verwendet Kraken Control bei der getesteten Kraken 2023 bewusst `liquidctl --direct-access`, da der gebundene Linux-hwmon-Treiber auf manchen Systemen Lesezugriff erlaubt, Schreibattribute aber nicht für den normalen Benutzer freigibt.

## Sicherheit

- Niedrige feste Pumpen- und Lüfterwerte verlangen eine Bestätigung.
- Temperaturkurven dürfen bei steigender Temperatur nicht langsamer werden.
- Hardware-Schreibfehler werden im Hintergrund gedrosselt, statt Dialoge in Spielen oder Vollbildanwendungen zu erzwingen.
- Die automatische Schutzlogik ist **kein Ersatz für hardwareseitige Schutzfunktionen**.
- Wiederholte LCD-Uploads und die LCD-Uhr bleiben experimentell.
- Diagnoseberichte und exportierte Logs sollten vor einer öffentlichen Veröffentlichung immer kurz kontrolliert werden.

Details: [`SECURITY.md`](SECURITY.md) und [`PRIVACY.md`](PRIVACY.md).

## Diagnose

```bash
kraken-control-diagnostics
```

Der Bericht versucht Home-Pfade, Hostnamen, IDs und Seriennummern zu entfernen. Trotzdem vor dem Hochladen manuell prüfen.

## Entwicklung und Tests

Lokale Release-Prüfung:

```bash
./scripts/check_release.sh
```

Die GitHub-CI führt die statischen und Stub-Laufzeittests automatisch für unterstützte Python-Versionen aus. Reale Hardwarezugriffe werden in der CI bewusst nicht ausgeführt.

Mitmachen: [`CONTRIBUTING.md`](CONTRIBUTING.md)

## GitHub-Release bauen

```bash
./scripts/build_release.sh
```

Dabei entstehen unter `dist/`:

- das Linux-Release-ZIP,
- ein separater Quellcode-Snapshot,
- SHA-256-Prüfsummen.

Das Release-ZIP enthält zusätzlich einen einzelnen Quellcode-Snapshot und `MANIFEST.sha256`.

## Projektumfang

Kraken Control bleibt bewusst auf unterstützte Kraken-Kühlhardware begrenzt. Mainboard-, Gehäuse- und GPU-Lüfter sowie allgemeines System-Tuning gehören nicht in dieses Projekt.

Mehr dazu: [`PROJECT_SCOPE.md`](PROJECT_SCOPE.md).

## Lizenz und Unabhängigkeit

Kraken Control by Frelidon steht unter **GPL-3.0-or-later**. Siehe [`LICENSE`](LICENSE).

Projektleitung und Veröffentlichung: **Frelidon**. ChatGPT von OpenAI wurde als Entwicklungsassistenz für Code, Debugging, Dokumentation und Tests eingesetzt; es ist kein Laufzeitbestandteil. Details: [`AI_ASSISTANCE.md`](AI_ASSISTANCE.md).

Alle Produkt- und Markennamen gehören ihren jeweiligen Rechteinhabern. Kraken Control ist kein offizielles NZXT-Produkt.

## Dokumentation

- [`CHANGELOG.md`](CHANGELOG.md)
- [`FEATURES_BY_VERSION.md`](FEATURES_BY_VERSION.md)
- [`COMPONENT_VERSIONS.md`](COMPONENT_VERSIONS.md)
- [`CPU_PROFILES.md`](CPU_PROFILES.md)
- [`PROFILES.md`](PROFILES.md)
- [`ANIMATED_BACKGROUNDS.md`](ANIMATED_BACKGROUNDS.md)
- [`PROJECT_SCOPE.md`](PROJECT_SCOPE.md)
- [`SOFTWARE_AND_LINKS.md`](SOFTWARE_AND_LINKS.md)
- [`SOURCE_CODE.md`](SOURCE_CODE.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`SUPPORTED_DEVICES.md`](SUPPORTED_DEVICES.md)

## Deinstallation

```bash
./uninstall.sh
```

Benutzerprofile und die udev-Regel werden absichtlich nicht automatisch entfernt.

## Unterstützte Geräte

| Gerät | USB-ID | Getesteter Funktionsumfang |
|---|---|---|
| NZXT Kraken RGB 360 (2023, Standard / Non-Elite; liquidctl: `NZXT Kraken 2023`) | `1e71:300e` | Wassertemperatur, Pumpe, von der Kraken verwaltete Radiatorlüfter, LCD 240×240 |
| NZXT 2023 RGB Controller | `1e71:2012` | Drei ARGB-Kanäle über liquidctl |

Offizielle Kraken-Spezifikationen: <https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs>

# Verwendete Software, Quellcode, Lizenzen und Herstellerseiten

Stand: Kraken Control by Frelidon 2.9.6.

Diese Liste erklärt nachvollziehbar, welche Software und externen Projekte verwendet oder genannt werden. Kraken Control öffnet diese Seiten nur nach einem Klick im Standardbrowser. Die Anwendung besitzt keine Telemetrie und sendet beim bloßen Anzeigen des Über-Bereichs keine Daten.

## Kraken Control by Frelidon

- Aufgabe: grafische Linux-Steuerung für die unten aufgeführten Kraken-Geräte
- Lizenz: GNU General Public License v3.0 oder später (`GPL-3.0-or-later`)
- Lokale Lizenzdatei: `LICENSE`
- Offizielle GPL-Seite: https://www.gnu.org/licenses/gpl-3.0.html
<!-- project-repository -->
- Projekt-Repository: https://github.com/Frelidon/kraken-control-linux
<!-- /project-repository -->

## Laufzeitkomponenten

| Komponente | Verwendung | Offizielle Website / Dokumentation | Quellcode / GitHub | Lizenzinformation |
|---|---|---|---|---|
| liquidctl | Hardwarezugriff auf Kraken, Pumpe, Lüfter, RGB und LCD | https://liquidctl.readthedocs.io/ | https://github.com/liquidctl/liquidctl | GPL-3.0-or-later: https://github.com/liquidctl/liquidctl#license |
| Python | Programmiersprache und Laufzeitumgebung | https://www.python.org/ | https://github.com/python/cpython | PSF License 2: https://docs.python.org/3/license.html |
| PySide6 / Qt for Python | grafische Oberfläche, Timer, Einstellungen und Prozesssteuerung | https://doc.qt.io/qtforpython-6/ | https://github.com/pyside/pyside-setup | Lizenzübersicht: https://doc.qt.io/qtforpython-6/licenses.html |
| Pillow | Bildöffnung, Beschnitt, Skalierung und Erzeugung von LCD-Bildern | https://pillow.readthedocs.io/ | https://github.com/python-pillow/Pillow | Lizenzdatei: https://github.com/python-pillow/Pillow/blob/main/LICENSE |

## Entwicklungsunterstützung

ChatGPT wurde bei Programmierung, Dokumentation und Tests unterstützend eingesetzt. ChatGPT oder eine OpenAI-API werden nicht von der installierten Anwendung aufgerufen und sind kein Laufzeitbestandteil. Die Nennung ist keine offizielle Unterstützung oder Partnerschaft durch OpenAI.

- OpenAI: https://openai.com/
- ChatGPT: https://chatgpt.com/
- OpenAI auf GitHub: https://github.com/openai

## Unterstützte NZXT-Hardware

- NZXT Kraken RGB 360 (2023, Standard / Non-Elite)
  - liquidctl-Gerätename: `NZXT Kraken 2023`
  - USB-ID: `1e71:300e`
  - offizielles NZXT-Datenblatt und Produktinformationen: https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs
- NZXT 2023 RGB Controller
  - USB-ID: `1e71:2012`
  - auf der Kraken-(2023)-Seite bei den enthaltenen RGB-Lüftern und Controllern aufgeführt: https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs

Weitere Herstellerseiten:

- NZXT Wasserkühlungen / CPU-Kühler: https://nzxt.com/collections/cpu-coolers
- NZXT: https://nzxt.com/

## Unabhängigkeit und Marken

Kraken Control by Frelidon ist ein unabhängiges Open-Source-Projekt. Es ist nicht mit NZXT, OpenAI, The Qt Company, der Python Software Foundation, dem Pillow-Projekt oder dem liquidctl-Projekt verbunden und wird von diesen Organisationen nicht offiziell unterstützt. Alle Produktnamen und Marken gehören ihren jeweiligen Rechteinhabern und werden nur zur sachlichen Kompatibilitäts- und Quellenangabe genannt.

## Temperatur- und Berechtigungsquellen in Version 2.8

- AMD Prozessorspezifikationen: https://www.amd.com/en/products/specifications/processors.html
- Linux k10temp: https://docs.kernel.org/hwmon/k10temp.html
- Offizielle liquidctl-udev-Regeln: https://github.com/liquidctl/liquidctl/blob/main/extra/linux/71-liquidctl.rules

## Anzeige und High-DPI in Version 2.9

- Qt High-DPI-Übersicht: <https://doc.qt.io/qt-6/highdpi.html>
- PySide6 QScreen: <https://doc.qt.io/qtforpython-6/PySide6/QtGui/QScreen.html>

Die Hintergründe werden vollständig im GPL-Quellcode erzeugt. Es werden keine externen Stockmedien oder zusätzlichen Medienlizenzen benötigt.

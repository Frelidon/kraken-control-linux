# Projektumfang - Kraken Control by Frelidon 2.9.6

## Zweck

Kraken Control ist eine spezialisierte Linux-Anwendung für unterstützte NZXT-Kraken-Wasserkühlungen. Die klare Begrenzung reduziert Risiken, vereinfacht Tests und verhindert Konflikte mit BIOS, Mainboard-Tools oder GPU-Treibern.

## Gehört zu Kraken Control

- Wassertemperatur und Gerätestatus der unterstützten Kraken
- Kraken-Pumpe
- Radiatorlüfter, sofern sie über die Kraken selbst gemeldet oder gesteuert werden
- Kraken-LCD und statische LCD-Inhalte
- separater NZXT 2023 RGB Controller
- Diagnose ausschließlich für die unterstützte Kraken-Hardware

## Gehört nicht zu Kraken Control

- Mainboard-Anschlüsse wie CPU_FAN, SYS_FAN oder CHA_FAN
- zusätzliche Gehäuselüfter, die nicht über die Kraken gesteuert werden
- GPU-Lüfter und AMD-Grafiksteuerung
- allgemeine Sensor-, Übertaktungs- oder System-Tuning-Funktionen
- automatische Änderungen an BIOS- oder Mainboard-Lüfterprofilen

## Modulare Zukunft

Weitere Hardwarebereiche sollen als eigenständige Anwendungen mit eigenen Sicherheitsgrenzen entwickelt werden. Später kann eine gemeinsame Oberfläche diese Werkzeuge starten oder ihre Statusdaten zusammenführen, ohne dass die einzelnen Programme ihre klare Verantwortung verlieren.

## Ergänzung in Version 2.8

CPU-Temperaturen dürfen gelesen werden, soweit sie ausschließlich zur sicheren Regelung der unterstützten Kraken verwendet werden. Das macht Kraken Control nicht zu einem allgemeinen Mainboard-, GPU- oder System-Tuning-Werkzeug.

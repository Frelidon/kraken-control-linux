# Unterstützte Geräte - Version 2.9.6

## Getestet

| Gerät | USB-ID | Unterstützung | Offizielle Herstellerseite |
|---|---|---|---|
| NZXT Kraken RGB 360 (2023, Standard / Non-Elite; liquidctl: `NZXT Kraken 2023`) | `1e71:300e` | Temperatur, Pumpe, Radiatorlüfter, LCD 240×240 | [NZXT Kraken (2023) – Spezifikationen](https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs) |
| NZXT 2023 RGB Controller | `1e71:2012` | separate RGB-Kanäle über liquidctl | [NZXT Kraken (2023) – enthaltene Lüfter und Controller](https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs) |

Weitere offizielle NZXT-Seiten:

- [NZXT Wasserkühlungen und CPU-Kühler](https://nzxt.com/collections/cpu-coolers)
- [NZXT-Website](https://nzxt.com/)

Getestete Kombination: Kraken-Firmware `2.0.0`, liquidctl `1.16.x`, Nobara/Fedora Linux.

## Bewusste Begrenzung

Kraken Control steuert ausschließlich Komponenten der unterstützten Kraken-Kühlung. Dazu zählen die Kraken-Pumpe und Radiatorlüfter, die über das Kraken-Gerät selbst gemeldet beziehungsweise geregelt werden.

Nicht unterstützt werden Mainboard-Lüfteranschlüsse, zusätzliche Gehäuselüfter, GPU-Lüfter oder allgemeine Systemsteuerung. Diese Geräte werden weder automatisch getestet noch beschrieben.

## Hinweise

- Das Programm verwendet liquidctl als Hardware-Backend.
- Echte GIF-Animationen werden auf der Kraken 2023 Standard mit Firmware 2.x durch liquidctl derzeit nicht unterstützt.
- Statische Bilder und die Uhr werden als 240×240-Bilder übertragen.
- Weitere Geräte gelten erst nach einem Hardwaretest als unterstützt.
- Die Herstellerlinks dienen ausschließlich als Produkt- und Dokumentationsverweise. Kraken Control ist kein offizielles NZXT-Produkt.

## Diagnose für neue Modelle

Führe aus:

```bash
kraken-control-diagnostics
```

Der Bericht entfernt Seriennummern automatisch. Prüfe die Datei trotzdem vor dem Teilen auf persönliche Informationen.

# Unterstützte Geräte – Open Hardware Control 3.0.9

## Direkt getestetes NZXT-Modul

| Gerät | USB-ID | Backend | Umfang |
|---|---|---|---|
| NZXT Kraken 2023 | `1e71:300e` | liquidctl | Wasser, Pumpe, Radiatorlüfter, LCD |
| NZXT 2023 RGB Controller | `1e71:2012` | liquidctl | drei RGB-Kanäle |

Der Schwerpunkt bleibt die NZXT Kraken RGB 360 (2023, Standard / Non-Elite) mit Firmware 2.0.0. Andere Kraken-Varianten gelten erst nach realem Hardwaretest als bestätigt.

## Corsair über OpenLinkHub

Open Hardware Control besitzt keine eigene feste Corsair-USB-Geräteliste. Es zeigt die Geräte an, die der lokal installierte OpenLinkHub-Dienst über `/api/devices/` meldet. Damit folgt der Erkennungsumfang der tatsächlich installierten OpenLinkHub-Version.

Seit Version 3.0.4 gibt es direkte Einstellungen nur für Geräte, Kanäle und Profile, die der lokale OpenLinkHub-Dienst meldet. Kühlung, RGB/LCD, Maus, Tastatur und Headset besitzen getrennte, validierte Aktionen. Nicht gemeldete oder komplexe gerätespezifische Funktionen bleiben im Web-Dashboard. Die reale Kompatibilität muss mit OpenLinkHub 0.9.0 und den angeschlossenen Corsair-Geräten geprüft werden.

Version 3.0.9 ordnet erkannte Mäuse anhand des Produktnamens einem generischen SVG-Schema zu. Berücksichtigt werden insbesondere Scimitar-, M55-/M75-, M65-/Dark-Core-/Ironclaw-/Glaive-/Sabre-, Darkstar-/Nightsabre-, Katar- und Harpoon-Familien. Unbekannte Mäuse erhalten das kompakte Standardschema. Das ist eine visuelle Orientierung und keine Aussage über eine exakte Gehäusegeometrie.

Eine Maustaste ist direkt belegbar, wenn OpenLinkHub für sie einen eindeutigen Tastenindex meldet. Unterstützt werden Keine, Medien, DPI, Tastatur, Sniper-DPI, Maus und vorhandene Makros. Die fensterlokale Makroaufnahme erzeugt nur Tastatur-/Pausenschritte; komplexe Folgen bleiben im OpenLinkHub-Web-Dashboard. Welche Zuweisungen ein konkretes Modell tatsächlich annimmt, hängt von der installierten OpenLinkHub-Version und deren Gerätetreiber ab.

## Nicht enthalten

- Mainboard-Lüfteranschlüsse und allgemeines System-Tuning
- Firmwareaktualisierungen
- Open Radeon Control Center; dieses bleibt eigenständig
- ungetestete direkte USB-Schreibzugriffe auf Corsair-Geräte

Produktnamen dienen nur der Kompatibilitätsangabe. Open Hardware Control ist kein offizielles Produkt von NZXT, Corsair oder OpenLinkHub.

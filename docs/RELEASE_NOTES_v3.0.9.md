# Open Hardware Control by Frelidon v3.0.9

## Deutsch

Open Hardware Control 3.0.9 ist die neue öffentliche Linux-Version für NZXT Kraken 2023 und Corsair-Geräte über OpenLinkHub.

Wichtige Neuerungen:

- LCD-GIFs und generierte Hardwareanimationen laufen weiter, während Pumpen-, Lüfter- und CPU-Kurvenwerte über eine koordinierte USB-Übergabe geändert werden.
- Pumpen- und Lüfterkurven arbeiten nach CPU-Temperatur mit Glättung, Hysterese, Schreibbegrenzung und sicherem Hardware-Fallback beim Beenden.
- Gespeicherte LCD-Profile werden nach dem Desktop-Autostart mit fünf Sekunden Verzögerung wiederhergestellt; das Programm bleibt dabei im Tray minimiert.
- Beim echten Beenden wird die originale Kraken-Wassertemperaturanzeige wiederhergestellt.
- OpenLinkHub-Geräte können über eine feste, validierte lokale API-Aktionsliste gesteuert werden.
- Gemeldete Corsair-Maustasten lassen sich in eigenen GPL-Schemata anklicken und belegen; eine begrenzte fensterlokale Tastaturmakroaufnahme ist enthalten.
- LCD-Beschriftung und Temperaturzahl besitzen getrennte Farben und Größen; Celsius/Fahrenheit gilt global.
- Installationspakete stehen als Fedora/Nobara-RPM, Debian/Ubuntu/Mint-DEB und universelles ZIP bereit. Quellarchiv, `Entwicklerpaket 3.0.9` und SHA-256-Prüfsummen gehören zum Release.

Die OpenLinkHub-Schreibfunktion bleibt bis zur ausdrücklichen Freigabe pro Sitzung gesperrt. Firmware-Updates gehören nicht zum Funktionsumfang. Das Projekt ist eine experimentelle Beta und unabhängig von NZXT, Corsair und OpenLinkHub.

## English

Open Hardware Control 3.0.9 is the new public Linux release for NZXT Kraken 2023 and Corsair devices through OpenLinkHub.

Highlights:

- LCD GIF and generated hardware animation streaming can continue across coordinated pump, fan and CPU-curve USB updates.
- Pump and fan curves follow CPU temperature with smoothing, hysteresis, write rate limiting and a safe hardware fallback on exit.
- Saved LCD profiles are restored five seconds after desktop autostart while the application remains minimized to the tray.
- A true application exit restores the original Kraken liquid-temperature display.
- OpenLinkHub devices use a fixed, validated allow-list of local API actions.
- Reported Corsair mouse buttons can be selected on original GPL schematics and reassigned; a bounded window-local keyboard macro recorder is included.
- LCD labels and values have independent colours and sizes, with global Celsius/Fahrenheit display.
- Fedora/Nobara RPM, Debian/Ubuntu/Mint DEB and universal ZIP packages are attached together with the matching source archive, `Entwicklerpaket 3.0.9` and SHA-256 checksums.

OpenLinkHub writes remain locked until explicitly enabled for the current session. Firmware updates are out of scope. This is an experimental beta independent of NZXT, Corsair and OpenLinkHub.

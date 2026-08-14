# Profile – Version 3.0.9

## Kategorien

| Kategorie | Gespeicherte Bereiche |
|---|---|
| Gesamt | Kühlung, CPU-Kurven, Sicherheit, LCD, Uhr, RGB, Design, Hintergrund, Anzeige und Fenstergröße |
| Kühlung | feste Werte oder CPU-Temperaturkurven, Sicherheitsgrenzen und CPU-Profil |
| LCD | aktiver Modus, Bild/GIF, Helligkeit, Ausrichtung, Uhr, Hardwaredesign/-animation und Wiederholungsoptionen |
| RGB | Kanal, Effekt, Farben, Geschwindigkeit und Richtung |
| Design | Hell/Dunkel/System, Akzentfarbe, Animation, DPI-Skalierung und Layout |

## Aktionen

- neues Profil speichern
- ausgewähltes eigenes Profil aktualisieren
- Standard- oder eigenes Profil duplizieren
- eigenes Profil umbenennen oder löschen
- einzelnes Profil als JSON exportieren
- ein oder mehrere Profile aus JSON importieren
- Profil automatisch beim Start laden
- alternativ das zuletzt verwendete Profil laden

Beim Desktop-Autostart bleibt das Fenster im Tray. Der LCD-Anteil des Startprofils beginnt erst fünf Sekunden nach Anwendungsstart. Ein manuelles Anwenden eines Profils verwendet weiterhin die normale kurze Geräteverzögerung.

Beim echten Beenden wird unabhängig vom gespeicherten Startprofil zunächst ein laufender GIF-Streamer geschlossen und danach die originale Kraken-Wassertemperaturanzeige gesetzt. Das Profil bleibt gespeichert und wird beim nächsten Start wie vorgesehen wieder geladen. Schließen in den Tray löst diese Rückstellung nicht aus.

## Sicherheit

Standardprofile sind schreibgeschützt. Alte importierte Wassertemperaturkurven mit Endpunkten um 45–50 °C werden nicht als CPU-Kurven interpretiert, sondern durch sichere CPU-Standardkurven ersetzt. LCD-Profile aus 3.0.5 ohne Modusfeld erkennen GIF- und statische Bilddateien automatisch. Sicherheitsabfragen, Berechtigungsprüfung und serielle Befehlswarteschlange bleiben aktiv.

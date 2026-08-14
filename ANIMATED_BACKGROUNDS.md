# Animierte Hintergründe – Version 2.9.4

Kraken Control 2.9.4 enthält keine heruntergeladenen Videos, GIFs oder Stockbilder. Sämtliche Hintergründe werden zur Laufzeit mit Qt `QPainter` aus mathematischen Formen, Gradienten und Partikeln erzeugt.

## Vorteile

- keine unklaren Bild- oder Videolizenzen
- keine Internetverbindung
- keine zusätzlichen Codecs
- kleine Paketgröße
- Farbe passt sich an die Akzentfarbe an
- Quellcode unter GPL-3.0-or-later vollständig einsehbar

## Themen

1. Sternenfeld
2. Kosmischer Nebel
3. Aurora
4. Spiralgalaxie
5. Warp-Tunnel
6. Schwebende Partikel
7. Bokeh
8. Ozeanwellen
9. Digitaler Regen
10. Sonnenaufgang
11. Eisnebel
12. Minimaler Fluss

## Leistung

- 15 FPS: sparsam
- 30 FPS: empfohlener Standard
- 60 FPS: flüssiger, aber höherer Ressourcenverbrauch
- „Pausieren, wenn die App nicht aktiv ist“ sollte aktiviert bleiben

Die Animation ist rein dekorativ. Kühlungs- und Sicherheitsbefehle laufen weiterhin unabhängig über die serielle `QProcess`-Warteschlange.

## Kompatibilitätsrenderer ab 2.9.1

Die Animation wird in einem CPU-seitigen `QImage` mit begrenzter interner Auflösung erzeugt und anschließend auf die Fenstergröße skaliert. Hintergrund und Bedienoberfläche sind getrennte Ebenen. Diese Architektur verhindert, dass ein fehlerhaft dargestellter Hintergrund die Bedienelemente übermalt, und reduziert die Last auf Ultrawide- und HiDPI-Monitoren.

Tritt dennoch eine interne Renderausnahme auf, stoppt die App den Animationstimer, zeichnet die normale Designfarbe und schreibt den Fehler in das Programmlog.


## Version 2.9.4

„Animation ausschalten“ deaktiviert nur den Renderer. Das zuletzt gewählte Thema bleibt erhalten. Beim erneuten Aktivieren wird es wiederhergestellt; bei alten Einstellungen mit „Aus“ wird Sternenfeld als Standard verwendet.

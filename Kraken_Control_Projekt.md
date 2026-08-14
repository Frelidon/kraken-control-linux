# Kraken Control – zentrale Projektdokumentation

Stand: **2.9.23 INTERN**, 13. August 2026

> **Ergänzung in Open Hardware Control 3.0.9 INTERN:** Beim echten Programmende oder geordneten
> Desktop-Neustart wird nach dem Stop des GIF-Streamers synchron die originale Kraken-Anzeige der
> Wassertemperatur wiederhergestellt. Schließen in den Tray bleibt davon ausgenommen.

> **Ergänzung in Open Hardware Control 3.0.6 INTERN:** Gesamt- und LCD-Profile speichern nun den
> tatsächlich aktiven LCD-Modus einschließlich normalem GIF und generierter Hardwareanimation. Beim
> Desktop-Autostart bleibt das Hauptfenster zuverlässig im Tray; der LCD-Start wartet fünf Sekunden.
> Ein im Profil gespeicherter maximierter Fensterzustand kann den Hintergrundstart nicht mehr aufklappen.
> Geordnete Sitzungssignale räumen den LCD-Crashmarker rechtzeitig auf.

> **Ergänzung in Open Hardware Control 3.0.5 INTERN:** Die sichtbare Pumpen- und Lüfterkurve wurde
> vollständig auf CPU-Temperatur umgestellt. Open Hardware Control berechnet beide Kurven laufend über
> Linux-hwmon, glättet kurze Ryzen-Spitzen und schreibt nur relevante Prozentänderungen. Während des
> LCD-GIF-Streams bleibt das CPU-Sensing aktiv und verwendet für nötige Änderungen die koordinierte
> USB-Kurzpause. Die Wassertemperatur bleibt eine getrennte Sicherheitsgröße; beim echten Beenden werden
> konservative autonome Wasser-Hardwarekurven als Fallback hinterlegt.

> **Ergänzung in Open Hardware Control 3.0.4 INTERN:** Das separate Corsair-/OpenLinkHub-Modul unterstützt
> nun eine fest freigegebene Auswahl dokumentierter lokaler API-Schreibbefehle. Das historische NZXT-Modul,
> seine USB-Koordination und seine Sicherheitsregeln bleiben davon technisch getrennt und unverändert.

> **Ergänzung in Open Hardware Control 3.0.3 INTERN:** Die Aktivfarbe der manuellen und kurvengesteuerten
> Betriebsart wird nicht mehr aus dem sofort umspringenden Qt-Checkzustand abgeleitet. Eine feste grüne
> `coolingState`-Darstellung zeigt ausschließlich den zuletzt erfolgreich an die Kraken übertragenen Modus;
> Hover, Gedrückt-Zustand, Theme und Akzentfarbe können diese Markierung nicht mehr ausblenden.

> **Ergänzung in Open Hardware Control 3.0.2 INTERN:** Pumpe und Radiatorlüfter können in der Kühlungsansicht
> jeweils ausdrücklich zwischen einem manuellen festen Prozentwert und ihrer Wassertemperatur-Hardwarekurve
> umgeschaltet werden. Die Aktivmarkierung wechselt erst nach erfolgreicher Übertragung und bleibt mit den
> bisherigen Anwenden-Knöpfen, Profilen und der GIF-USB-Übergabe synchron.

> **Ergänzung in Open Hardware Control 3.0.1 INTERN:** Bei laufendem GIF oder einer generierten Hardwareanimation
> bleiben Kraken-Statusabfragen weiterhin pausiert. Manuelle Pumpen-, Lüfter- und Kurvenänderungen sind jetzt
> trotzdem möglich: Der langlebige Streamer beendet den aktuellen Frame, gibt HID/Bulk kurz frei, behält seinen
> vorbereiteten Framecache und setzt dieselbe Animation nach dem exklusiven Kühlbefehl automatisch fort.

## Projektziel

Kraken Control by Frelidon ist eine unabhängige, quelloffene Linux-Anwendung zur Steuerung der unterstützten NZXT-Kraken-Kühlhardware. Der aktuelle Schwerpunkt ist die NZXT Kraken RGB 360 (2023, Standard / Non-Elite) mit Firmware 2.0.0 und USB-ID `1e71:300e`.

Das Projekt steuert ausschließlich:

- Kraken-Wassertemperatur und Gerätestatus
- Kraken-Pumpe
- von der Kraken gemeldete beziehungsweise gesteuerte Radiatorlüfter
- Kraken-LCD 240×240
- separaten NZXT 2023 RGB Controller `1e71:2012`

Mainboard-, Gehäuse- und GPU-Lüfter, allgemeines System-Tuning und Firmwareaktualisierungen sind nicht Teil dieses Projekts.

## Aktueller Entwicklungsstand

Version 2.9.23 INTERN aktualisiert CPU- und GPU-Temperaturen nun auch in den animierten Ring-/Orbit-Designs. Der Streamer liest beide Werte alle zwei Sekunden rein lesend aus Linux-`hwmon`. Sobald sich die auf dem LCD sichtbare ganze Gradzahl ändert, erzeugt ein isolierter Spawn-Renderprozess einen neuen vollständigen Phasensatz und übergibt ihn atomar an den zeitkritischen USB-Prozess.

Die Wassertemperatur bleibt während der Animation bewusst der letzte sichere Kraken-Wert, weil der exklusive CAM-Raw-Streamer weiterhin keine parallelen Kraken-Statusabfragen zulässt. `LIVE`-/`LETZTER WERT`-Markierungen zeigen diesen Unterschied direkt auf dem LCD. Statische Designs aktualisieren weiterhin alle verfügbaren Werte im gewählten Intervall. Farbvorlagen, freier `#RRGGBB`-Wert und 70–150-%-Größenregler gelten gemeinsam für beide Bereiche.

Die Sprachumschaltung wurde für Deutsch, Englisch, Spanisch und Französisch neu geordnet. Erst werden gespeicherte Werte und dynamische Auswahlfelder wiederhergestellt, anschließend wird die komplette Oberfläche übersetzt. Menüs, Tabs, Schaltflächen, Gruppen, Tabellen, Platzhalter und datenbasierte Listen verwenden dadurch gemeinsam die gewählte Sprache.

Neu in 2.9.23:

- CPU-/GPU-Livewerte in animierten Designs mit zwei Sekunden Sensorintervall
- Wassertemperatur während Animation als klar gekennzeichneter letzter sicherer Kraken-Wert
- gemeinsames read-only Sensormodul `kraken_sensors.py` für GUI und Streamer
- isolierter Spawn-Renderprozess statt Zeichnen im zeitkritischen USB-Prozess
- vollständige neue RGB565-Phasensätze werden erst nach erfolgreichem Rendern atomar übernommen
- Fehler bei einer Livewert-Aktualisierung lassen den letzten vollständigen Cache weiterlaufen
- Statusmeldungen und Übersetzungen für Deutsch, Englisch, Spanisch und Französisch
- Sensor-, Renderer-, Phasen-, Prozessisolations- und Cacheübergabetests

Weiterhin enthalten aus 2.9.22:

- eigener Abschnitt `Animierte Hardwaredaten · Ringe und Orbits` mit Motiv, 20/25 FPS, Vorschau, Start und Stop
- alle fünf Motive als prozedural erzeugte, nahtlose Ring-/Orbit-GIFs
- gemeinsamer 70–150-%-Regler für Schrift- und Zahlen-Größe, Standard 125 Prozent
- animierte Qt-Vorschau vor der Übertragung
- unveränderte Übergabe an den abgesicherten exklusiven GIF-Streamer, ohne die ausgewählte eigene GIF-Datei zu überschreiben
- eigene Experimentalbestätigung sowie Einbindung in Crash-Marker, Watchdog und Flüssigkeitstemperatur-Sicherheitsfallback
- Speicherung von Größe, Animationsmotiv und Animationsrate in Einstellungen und Profilen

Weiterhin enthalten aus 2.9.21:

- `Wasser · Halo`, `CPU · Orbit`, `GPU · Arc`, `CPU + GPU · Dual` und `Wasser + CPU + GPU · Trio`
- reiner Pillow-Renderer `kraken_lcd_designs.py`, unabhängig von Qt und angeschlossener Hardware testbar
- Eisblau als Standard, sieben Farbvorlagen und eigener Hex-Farbwert im Format `#RRGGBB`
- Live-Aktualisierung von 5 bis 60 Sekunden mit Vorschau und explizitem Start/Stop
- gegenseitige Koordination mit statischem Bild, Wiederholungs-Fallback, LCD-Uhr und GIF-Streamer
- Experimentalbestätigung, Crash-Erkennung, dreistufige Upload-Fehlergrenze und Flüssigkeitstemperatur-Sicherheitsfallback
- GPU-Temperatur als zusätzliche Übersichtskarte
- vollständigerer Sprachwechsel einschließlich Menütitel und dynamischer Farbbeschriftungen

Weiterhin enthalten aus 2.9.20:

- normale GIF-Auswahl auf `CAM-nah · automatisch · empfohlen · max. 25 FPS`, 24 FPS und 25 FPS reduziert
- 5/8/10/12/15/20 FPS sowie 25,6-Hz-Rückfallmodus unter `Erweiterte GIF-Optionen anzeigen`
- 26 und 27 FPS aus der grafischen Auswahl entfernt; alte 30/32-Hz-Experimente bleiben entfernt
- nicht blockierende Warnung, wenn letzter und erster GIF-Frame wahrscheinlich einen sichtbaren Loop-Übergang bilden
- technische Moving-Bars-GIFs neu erzeugt; bei 25 FPS besitzen alle 50 Übergänge einschließlich letzter→erster Phase exakt vier Pixel Bewegung
- 2.9.19-Phasenfolge und sanfte Überlaufbehandlung durch Regressionstest und Zehn-Minuten-Simulation abgesichert

Bestätigt aus 2.9.19:

- LCD-Phasen werden streng `1, 2, 3 …` übertragen und nicht aus einer driftenden Echtzeitposition neu ausgewählt
- 26,667 Hz bleibt der CAM-nahe Zieltakt; die reale USB-Grenze am Testgerät liegt bei etwa 26,3 Hz
- einzelne Timingüberläufe werden nur bei echtem Spielraum und höchstens in 0,25-ms-Schritten abgebaut
- keine überlappenden Transfers, keine Catch-up-Bursts und keine Frame-Sprünge
- exklusive Kraken-Verbindung; Statusabfragen pausieren während des Streams
- ab Open Hardware Control 3.0.1 verwenden neue Kühlbefehle eine koordinierte USB-Kurzpause; gespeicherte Hardwarekurven laufen weiter
- eindeutige ACK-Zuordnung `37 01`/`37 02` und 12-Sekunden-Watchdog mit LCD-Sicherheitsfallback

## Bestätigtes LCD-Protokoll

Die vom Nutzer bereitgestellten CAM-USB-Aufzeichnungen bestätigen pro Frame:

1. HID-Ausgabe `36 01 00 01 06`
2. passende HID-Antwort `37 01`
3. 20-Byte-Bulk-Header `12 fa 01 e8 ab cd ef 98 76 54 32 10 06 00 00 00 00 c2 01 00`
4. exakt 115.200 Byte RGB565, Big Endian
5. HID-Ausgabe `36 02`
6. passende HID-Antwort `37 02`

Der lange CAM-Mitschnitt enthält 341 vollständige RGB565-Frames. Der kontinuierliche Hauptabschnitt erreicht 26,375 Hz; eine vollständige Transaktion dauert im Mittel rund 37,51 ms.

## Letzter Hardwaretest

Hardwarelog 2.9.19, Moving Bars, 25 FPS Inhalt, CAM-Takt:

- effektiv stabil rund 26,3 Hz
- Upload 37,8–37,9 ms, Maximum 38,9 ms
- 0 LCD-Frame-Wiederholungen
- 0 LCD-Frame-Sprünge
- 0 Inhalts-Sprünge
- 0 übersprungene Transportframes
- steigende `Zeitfenster voll`-Zahl erwartbar, weil 37,8 ms knapp über dem 37,5-ms-Ziel liegt
- sichtbare Restunruhe bei sehr dünnen Linien minimal; normale GIF-Animation sehr flüssig

Bewertung: Die Timing-Testphase ist abgeschlossen. Weitere Änderungen am Transport sollen nur mit neuem reproduzierbarem Fehlerbild erfolgen. Der Schwerpunkt wechselt zu eigenen 240×240-Designs mit 25 FPS und nahtlosen Loops.

## Sicherheitsregeln

- Keine Firmwareaktualisierung durchführen.
- Nur exakt USB `1e71:300e` und Firmware-Hauptversion 2 für den internen Raw-Streamer akzeptieren.
- Mehrere passende Kraken-Geräte führen zum Abbruch statt zu einer geratenen Auswahl.
- Kein paralleler Kraken-Zugriff während des Raw-Streams.
- Keine überlappenden Frame-Transfers und keine Aufhol-Bursts.
- Bei falscher oder fehlender ACK-Antwort abbrechen.
- Bei ausbleibendem Lebenszeichen Streamer beenden und Flüssigkeitstemperaturanzeige wiederherstellen.
- Niedrige Kühlwerte weiterhin nur nach ausdrücklicher Warnung und Bestätigung.
- Expertenmodus ändert keine Firmwaregrenzen und bleibt auf Nutzung auf eigenes Risiko beschränkt.

## Bekannte Grenzen

- Firmware 2.x bietet in liquidctl keinen nativen GIF-Modus; Animation wird durch wiederholte statische RGB565-Frames emuliert.
- Langzeitwirkungen sehr häufiger LCD-Uploads sind nicht ausreichend dokumentiert.
- Die private liquidctl-API kann sich in späteren Versionen ändern; fehlende Methoden führen zum sicheren Abbruch.
- Die Loop-Prüfung ist eine Wahrscheinlichkeitswarnung. Ein harter Übergang kann absichtlich Teil eines GIFs sein.
- Motive mit einzelnen sehr dünnen Linien zeigen Kamera-/LCD-Moiré und minimale Restunruhe stärker als normale Animationen.
- Die Wassertemperatur ist während eines laufenden Streams der letzte vor Streamstart sicher gelesene Kraken-Wert. CPU und GPU werden unabhängig davon über Linux-hwmon live aktualisiert.

## Release- und Quellcode-Regel

Interne Entwicklungsstände müssen nicht automatisch auf GitHub veröffentlicht werden. Versionsnummern dürfen übersprungen werden. Sobald ein Binär- oder Installationspaket an Tester oder öffentlich weitergegeben wird, muss der exakt passende, bearbeitbare Quellcode derselben Version verfügbar sein. Öffentlicher Download und veröffentlichter Quellcode müssen dieselbe Versionsnummer tragen. Die vollständige Git-Historie und verworfene Zwischenstände müssen nicht veröffentlicht werden.

Öffentliches Repository: <https://github.com/Frelidon/kraken-control-linux>

## Nächste Schritte

- Version 2.9.23 am realen Gerät mit jedem der fünf statischen und animierten Hardwaredesigns prüfen
- bei CPU-/GPU-Temperaturänderungen kontrollieren, ob der atomare Cachewechsel ohne sichtbaren Haken erfolgt
- prüfen, ob `LIVE` und `LETZTER WERT` bei 70, 100, 125 und 150 Prozent gut lesbar bleiben
- 20 und 25 FPS vergleichen und Ring-/Orbit-Loops auf sichtbare Sprünge kontrollieren
- Größenregler bei 70, 100, 125 und 150 Prozent auf dem realen 240×240-LCD auf Lesbarkeit prüfen
- GPU-Auswahl auf dem Zielsystem mit integrierter und dedizierter AMD-GPU gegenprüfen
- Sprachwechsel in allen vier Sprachen einmal vollständig durchklicken
- Aktualisierungsintervall zunächst konservativ bei sieben Sekunden belassen und LCD-Verhalten beobachten
- GIF-Loop-Warnung mit unterschiedlichen realen Dateien sammeln und bei Bedarf Schwelle nachjustieren
- Kraken-Statusabfragen während Animation weiterhin pausiert lassen; Wasser-Livewerte erst nach einem eigenen störungsfreien USB-Nachweis erwägen
- später sichere Unterstützung weiterer Kraken-/Herstellergeräte jeweils mit eigenen Geräteprofilen und Grenzen planen
- öffentliche Versionsnummer erst nach abgeschlossenem Design- und Stabilitätstest festlegen

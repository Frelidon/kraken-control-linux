# Open Hardware Control 3.0.9 – Maustasten/Makros, saubere LCD-Werte und Fahrenheit

- Erste öffentliche Open-Hardware-Control-Version auf Basis der vollständig geprüften internen 3.0.x-Reihe.
- Release-Artefakte für Fedora/Nobara (`.rpm`), Debian/Ubuntu/Mint (`.deb`), ein universelles Installations-ZIP sowie das vollständige `Entwicklerpaket 3.0.9`.
- Distributionsabhängige Installation für DNF, APT, Pacman und Zypper mit klaren Befehlen aus `~/Downloads`.
- Suchfreundliche Projektbeschreibung für NZXT Kraken, Kraken LCD, Linux, liquidctl, fan control, Corsair und OpenLinkHub.
- Gemeldete OpenLinkHub-Maustasten öffnen direkt aus SVG oder Tabelle einen Belegungsdialog.
- Dokumentierte API-Unterstützung für Medien-, DPI-, Tastatur-, Sniper-, Maus- und vorhandene Makrofunktionen sowie Originalfunktion, Gedrückthalten und Ausführen beim Loslassen.
- Neue Makroaufnahme für einzelne Tastendrücke und Pausen, begrenzt auf das sichtbare aktive Dialogfenster und 64 Schritte.
- Eingabekataloge und Makronamen werden über die dokumentierten lokalen Endpunkte gelesen, bereinigt und begrenzt.
- LCD-Hardwaredesigns entfernen kleine LIVE-/LETZTER-WERT-/KRAKEN-CONTROL-Zusätze.
- Beschriftung und Temperaturzahl besitzen getrennte Hex-Farben und getrennte Größen von 60 bis 200 Prozent.
- Celsius/Fahrenheit ist eine globale, profilfähige Anzeigeeinstellung für Dashboard, Status, Kurven, Sicherheitsgrenzen und LCD-Hardwareanimationen.
- Kurven- und Sicherheitslogik bleiben intern in Celsius, damit ein Einheitenwechsel die Hardwarewirkung nicht verändert.
- Eine laufende generierte Hardwareanimation wird beim Einheitenwechsel kontrolliert beendet, neu gerendert und wieder gestartet.

---

# Open Hardware Control 3.0.6 – LCD-Profilstart und zuverlässiger Tray-Autostart

- Profile speichern nun ausdrücklich den aktiven LCD-Modus: Einzelbild, Bild-Wiederholung, Uhr, statisches Hardwaredesign, Hardwareanimation oder normales GIF.
- Ein beim Aktualisieren des Profils laufendes GIF wird beim nächsten Start wieder als Animation geladen und nicht nur als erstes Standbild.
- Vorhandene 3.0.5-LCD-Profile ohne Modusfeld migrieren `.gif`-Dateien automatisch zum GIF-Streamer und statische Dateien zum Einzelbildmodus.
- Beim Desktop-Autostart wird die LCD-Wiederherstellung bis fünf Sekunden nach Programmstart verzögert; der normale manuelle Start behält die bisherige kurze Verzögerung.
- Gesamtprofile dürfen ihren gespeicherten maximierten/normalen Fensterzustand während des Tray-Autostarts nicht anwenden. Dadurch bleibt das Hauptfenster zuverlässig verborgen beziehungsweise minimiert.
- Nach dem Laden des Startprofils wird der gewünschte Autostart-Fensterzustand nochmals abgesichert.
- Nur Startprofile mit einem tatsächlichen LCD-Anteil besitzen beim Start das Display; reine Kühl- oder Designprofile blockieren die globale LCD-Wiederherstellung nicht mehr.
- SIGTERM und SIGINT werden in einen geordneten Qt-Abschluss überführt. Der Crashmarker wird vor möglicherweise längerem USB-Aufräumen gelöscht, damit ein normaler Desktop-Neustart nicht als LCD-Absturz behandelt wird.
- CPU-Kurvenregelung, GIF-USB-Koordination, OpenLinkHub-Steuerung und alle Sicherheitsfallbacks bleiben erhalten.

---

# Open Hardware Control 3.0.5 – CPU-Temperaturkurven

- Sichtbare Pumpen- und Radiatorlüfterkurve von Kraken-Wassertemperatur auf CPU-Temperatur umgestellt.
- Eigenständiger 1-Sekunden-Regeltimer liest AMD-CPU-Sensoren direkt über Linux-hwmon und bleibt während des LCD-GIF-Streams aktiv.
- Lineare Kurveninterpolation, EMA-Glättung, 2-%-Quantisierung und asymmetrische Hysterese verhindern hörbares Pendeln und unnötige USB-Übergaben.
- Steigende Kühlanforderungen reagieren schneller als fallende; der 100-%-Endpunkt wird ohne Absenkverzögerung übernommen.
- Pumpe und Lüfter werden bei gleichzeitiger Änderung in einem gemeinsamen koordinierten GIF-USB-Fenster gesetzt.
- Alle AMD-AM5-Profile besitzen CPU-Temperaturpunkte mit 100 % bei 90 °C beziehungsweise 85 °C für Ryzen 7000 X3D.
- Alte gespeicherte 20–50-°C-Wasserkurven und Profilkurven werden beim Upgrade nicht als CPU-Werte missverstanden, sondern sicher migriert.
- Bei fünf aufeinanderfolgenden CPU-Sensorfehlern setzt die Regelung aktive Kurvenkanäle auf 75 %.
- Die Wassertemperatur bleibt als unabhängige 42/50-°C-Sicherheitsüberwachung erhalten.
- Beim echten Programmende werden aktive CPU-Kanäle auf konservative autonome Wasser-Hardwarekurven zurückgestellt; Tray-Betrieb lässt die CPU-Regelung weiterlaufen.
- OpenLinkHub-Steuerung, Manuell-/Kurven-Schaltflächen, LCD-Streamer, ACK-Prüfung und Framecache bleiben erhalten.

---

# Open Hardware Control 3.0.4 – direkte OpenLinkHub-Gerätesteuerung

- Fest freigegebene, dokumentierte OpenLinkHub-Schreibaktionen für Kühlung, RGB/LCD, Maus, Tastatur und Headset ergänzt.
- Temperatur- und RGB-Profile werden aus der lokalen API gelesen und in den passenden Geräteauswahlen angeboten.
- Direkte Schreibzugriffe müssen für jede Programmsitzung ausdrücklich bestätigt werden und bleiben bei zwei aktiven Diensten gesperrt.
- Wertebereiche, Geräte-, Kanal- und Profilangaben werden vor jedem Befehl validiert; beliebige API-Pfade oder JSON-Nutzlasten sind ausgeschlossen.
- Vollständige Seriennummern verlassen das Hilfsmodul nicht. Die Oberfläche erhält nur gekürzte Suffixe und nicht rückrechenbare Steuerkennungen.
- Erfolg wird aus Prozess- und API-Antwort bestätigt; danach werden Gerätewerte automatisch neu eingelesen.
- Komplexe Makrofolgen, vollständiger RGB-Editor und neue LCD-Mediendateien verbleiben zunächst im OpenLinkHub-Web-Dashboard.
- NZXT-Kraken-Steuerung und GIF-USB-Handoff bleiben unverändert.

---

# Open Hardware Control 3.0.3 – stabile Farbmarkierung der Kühlungsbetriebsart

- Qt-Checkzustand der vier Modusschaltflächen entfernt, damit die Oberfläche nicht schon beim Klick vor dem Geräteergebnis umspringt.
- Eigene dynamische Eigenschaft `coolingState` bildet ausschließlich den zuletzt bestätigten Kraken-Modus ab.
- Aktiver Modus besitzt feste grüne Normal-, Hover- und Gedrückt-Farben; Theme und Akzentfarbe können die Markierung nicht mehr ausblenden.
- Ein fehlgeschlagener oder noch laufender Schreibbefehl lässt die bisherige Aktivmarkierung unverändert.
- Keine Änderung an liquidctl-Befehlen, Kurvenregeln, Profilen oder der koordinierten GIF-USB-Übergabe.
- Optionales `OHC_INSTALL_HOME` ermöglicht einen isolierten Installertest; die normale Installation nach `~/.local` bleibt unverändert.
- Reale 3.0.2-Hardwarebestätigung dokumentiert: Lüfterkurve mit fünf Punkten bei laufendem GIF übertragen, Animation nach 258 ms fortgesetzt; Schnellprofile nach 317–351 ms fortgesetzt, ohne LCD-Frame-Sprünge.

---

# Open Hardware Control 3.0.2 – eindeutige Kühlungsbetriebsarten

- Neue kanalgetrennte Schaltflächen für **Manuell aktivieren** und **Pumpen-/Lüfterkurve aktivieren**.
- Ein Modusschalter wird erst nach einem erfolgreich abgeschlossenen Kraken-Schreibbefehl als aktiv markiert.
- Der manuelle Modus überträgt den jeweiligen Schieberegler als feste Drehzahl; der Kurvenmodus validiert und überträgt die angezeigte Hardwarekurve.
- Bestehende Anwenden-Knöpfe, Schnellprofile, Sicherheitsprofil, gespeicherte Profile und CPU-Assistenz aktualisieren dieselbe Modusanzeige.
- Umschaltungen bei laufender GIF-/Hardwareanimation verwenden unverändert die bestätigte PAUSE-/RESUME-USB-Übergabe aus 3.0.1.
- Reale Kraken-3.0.1-Bestätigung dokumentiert: Lüfter 100 % mit 240-ms-Pause und Pumpe 100 % mit 251-ms-Pause; Stream danach ohne LCD-Frame-Sprünge fortgesetzt.

---

# Open Hardware Control 3.0.1 – Kühlung-während-GIF-Version

- Manuelle Pumpen-, Lüfter- und Kurvenänderungen sind jetzt bei laufender GIF- oder generierter Hardwareanimation möglich.
- Schnellprofile, Sicherheitsprofil und gespeicherte Kühlprofile verwenden denselben koordinierten Übergabepfad.
- Neuer PAUSE-/RESUME-Kanal zwischen GUI und dem langlebigen CAM-Raw-Streamer.
- Der Streamer beendet zuerst den aktuellen Frame, schließt HID/Bulk, behält den vorbereiteten RGB565-Cache im Speicher und bestätigt erst dann die USB-Freigabe.
- Nach vollständig abgeschlossenem liquidctl-Direct-Access-Befehl verbindet sich derselbe Streamer neu, primt die vorgemerkte Cachephase zweimal und setzt die Animation fort.
- Niemals zwei gleichzeitige Kraken-Schreiber; normale Statusabfragen bleiben während des Streams pausiert.
- Zeitlimits für Freigabe und Wiederaufnahme sowie bestehender Watchdog, ACK-Abgleich und LCD-Sicherheitsfallback bleiben aktiv.
- Neuer isolierter Regressionstest für Freigabe, Neuverbindung, Cacheerhalt und Befehlsreihenfolge.

---

# Open Hardware Control 3.0.0 – interne Multi-Hardware-Version

- Kraken Control 2.9.23 vollständig als eingebautes NZXT-Modul übernommen.
- Hierarchische linke Navigation mit hardwareabhängiger Sichtbarkeit ergänzt.
- Option „Nicht erkannte Geräte/Module anzeigen“ ergänzt.
- Erste sichere Corsair-/OpenLinkHub-Integration: Installation, Benutzer-/Systemdienst, lokale API, Geräteliste und Telemetrie.
- OpenLinkHub-Dienstaktionen auf `systemctl --user` und eine feste Aktionsliste begrenzt.
- Warnung bei Systemkontext oder zwei aktiven Diensten; systemweite Migration bleibt ausdrücklich manuell.
- Bestehende Kraken-Control-Einstellungen werden beim ersten Start in den neuen Anwendungsschlüssel übernommen.
- Neue zentrale Projektdokumentation und separates OpenLinkHub-Integrationsdokument.
- Open Radeon Control Center bleibt ein eigenständiges Projekt.

---

# Kraken Control 2.9.23 – interne Live-Hardwareanimations-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Animierte CPU- und GPU-Anzeigen aktualisieren ihre sichtbaren Temperaturwerte alle zwei Sekunden rein lesend über Linux-`hwmon`.
- Die Wassertemperatur bleibt während des exklusiven Streams der letzte sichere Kraken-Wert; parallele Kraken-Statusabfragen bleiben aus Sicherheits- und Stabilitätsgründen deaktiviert.
- Ein isolierter Spawn-Renderprozess erzeugt bei sichtbaren Temperaturänderungen einen vollständigen neuen 20/25-FPS-Phasensatz. Erst nach erfolgreicher Fertigstellung wird der Cache atomar übernommen.
- Der USB-Prozess zeichnet keine Frames selbst und behält die bestätigte phasenstabile CAM-nahe Reihenfolge ohne Überlappung oder Catch-up-Bursts.
- Lokalisierte `LIVE`-/`LETZTER WERT`-Markierungen in allen vier Render-Sprachen.
- Neue UI-Statusereignisse für erfolgreiche und fehlgeschlagene Livewert-Aktualisierungen; bei einem Renderfehler bleibt der letzte vollständige Cache aktiv.
- CPU-/GPU-Sensorlogik in das gemeinsame read-only Modul `kraken_sensors.py` ausgelagert.
- Neue Tests für Sensorpriorität, dynamische Phasensätze, atomare Cacheübergabe und einen real separat gestarteten Spawn-Renderprozess.
- Keine Firmwareaktualisierung.

---

# Kraken Control 2.9.22 – interne animierte Hardwaredesign-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Fünf nahtlose Hardwaredaten-GIFs mit echten, prozedural gezeichneten Ring-, Halo-, Orbit-, Dual- und Trio-Bewegungen.
- Neuer eigener UI-Abschnitt für animierte Hardwaredaten mit Motivwahl, 20/25 FPS, animierter Vorschau, Start und Stop.
- Schrift- und Zahlen-Größe für statische und animierte Designs von 70 bis 150 Prozent einstellbar; Standard auf 125 Prozent angehoben.
- Animationsgenerator verwendet dieselben vier Sprachen, Farbvorlagen und freien `#RRGGBB`-Werte wie die statischen Designs.
- Generierte Animation wird ohne Änderung der ausgewählten eigenen GIF-Datei an den vorhandenen CAM-Raw-Streamer übergeben.
- Animationen verwenden bewusst den letzten Sensorstand als Start-Momentaufnahme, da der exklusive GIF-Stream Kraken-Statusabfragen pausiert.
- Eigene dauerhafte Experimentalwarnung und Einbindung in Crash-Erkennung, Watchdog und LCD-Sicherheitsfallback.
- Einstellungen und Profile speichern Schriftgröße, Animationsmotiv und Animationsrate.
- Keine Firmwareaktualisierung.

---

# Kraken Control 2.9.21 – interne Hardwaredesign-/Sprachversion

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Fünf runde Live-Hardwaredesigns für Wasser, CPU, GPU, CPU+GPU und Wasser+CPU+GPU.
- Neues eigenständiges, mit Pillow getestetes 240×240-Renderermodul `kraken_lcd_designs.py`.
- Eisblau als Standard; sieben Vorlagen plus eigener `#RRGGBB`-Wert mit Validierung und Farbdialog.
- AMD-GPU-Temperatur über `amdgpu`/hwmon ergänzt; dedizierte GPU wird über den größten VRAM-Wert bevorzugt.
- GPU-Temperatur als sechste Dashboardkarte ergänzt.
- Live-Modus mit 5–60 Sekunden Intervall, Vorschau, Start/Stop, exklusiver Koordination mit Bild, Uhr, GIF und Fallback.
- Experimentalbestätigung, Crash-Marker, dreistufige Fehlergrenze und Flüssigkeitstemperatur-Sicherheitsfallback auf den neuen Modus erweitert.
- Sprachumschaltung nach der Einstellungswiederherstellung angeordnet und um Menütitel, dynamische Farbtasten sowie datenbasierte RGB-/Profil-Auswahlen ergänzt.
- Sichtbare Grundoberfläche für Deutsch, Englisch, Spanisch und Französisch vervollständigt.
- Keine Firmwareaktualisierung.

---

# Kraken Control 2.9.20 – interne UI-/Loop-Diagnose-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Normale GIF-Bildraten auf `CAM-nah · automatisch · empfohlen · max. 25 FPS`, 24 FPS und 25 FPS reduziert.
- 5/8/10/12/15/20 FPS sowie der 25,6-Hz-Rückfallmodus bleiben unter `Erweiterte GIF-Optionen anzeigen` verfügbar.
- 26 und 27 FPS aus der grafischen Auswahl entfernt; alte 30/32-Hz-Experimente bleiben entfernt.
- Neuer nicht blockierender Hinweis, wenn der letzte→erste Bildwechsel im Vergleich zu normalen Nachbarübergängen wahrscheinlich sichtbar ist.
- Moving-Bars-Test-GIFs neu erzeugt. Im 25-FPS-Test sind alle 50 Übergänge einschließlich Loop exakt vier Pixel breit.
- Phasenstabile 2.9.19-Folge durch zusätzliche Regressionstests und Zehn-Minuten-Simulation abgesichert.
- Realen 2.9.19-Hardwaretest dokumentiert: etwa 26,3 Hz, 37,8–37,9 ms Upload, keine LCD-Frame-Wiederholungen/-Sprünge und keine übersprungenen Transportframes.
- Keine Firmwareaktualisierung.

---

# Kraken Control 2.9.19 – interne phasenstabile CAM-Taktversion

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Vorbereitete LCD-Phasen werden streng `1, 2, 3 …` übertragen. Ein knappes USB-Zeitfenster kann keine spätere Bildphase mehr auswählen.
- CAM-naher Zieltakt 26,667 Hz; wenn die reale USB-Transaktion länger als 37,5 ms dauert, folgt der nächste vollständige Frame erst nach dem passenden ACK.
- Einzelne Überläufe werden nur aus echtem freien Zeitbudget und höchstens in 0,25-ms-Schritten abgebaut; keine Catch-up-Bursts.
- Moving-Bars-25-FPS-Loop korrigiert: alter regelmäßiger Sprung am 2-Sekunden-Übergang entfernt.
- Keine Firmwareaktualisierung.

---

# Kraken Control 2.9.17 – interne ACK-Sync-/Tearing-Testversion

> **INTERNER HARDWARE-TESTSTAND – nicht automatisch als öffentlicher GitHub-Release vorgesehen.**

- Das neue Hardwarevideo von 2.9.16 wurde frameweise ausgewertet. Die Animation füllt das LCD nun vollständig und läuft deutlich flüssiger; sichtbar bleiben eine horizontale Versatzkante durch gemischte Bildphasen sowie leichtes Haken.
- Der CAM-Mitschnitt wurde gezielt auf die Pause zwischen passendem `37 02`-End-ACK und folgendem `36 01`-Start untersucht: Median 0,113 ms, Minimum 0,070 ms. CAM wartet dort nicht zusätzlich auf eine starre 26,67-Hz-Zeitmarke.
- Der Standardtransport `cam` ist deshalb jetzt **ACK-synchronisiert**. Nach einem vollständig bestätigten Frame startet der nächste nach 0,10 ms. Die Kraken-Antwort bestimmt den realen Takt und unnötig wechselnde Zusatzwartezeiten entfallen.
- Die sichtbare GIF-Zeit bleibt an `time.monotonic()` gekoppelt. Auch der neue Pfad überlappt keine Transfers, holt keine Frames in Bursts nach und akzeptiert weiterhin ausschließlich die passenden Antworten `37 01` und `37 02`.
- Der feste **25,6-Hz-Rückfallmodus** bleibt unverändert erhalten und verwendet weiterhin 0,2 ms Schutzabstand.
- Oberfläche und Log kennzeichnen den neuen Standard als `CAM-synchronisiert · ACK-getaktet` beziehungsweise `cam-raw-ack-paced`. Effektive Rate, P90, Maximum, Wiederholungen, Sprünge und fremde HID-Berichte bleiben sichtbar.
- Exklusiver Kraken-Zugriff, pausierte Status-/Kühlbefehle, autonome Hardwarekurven, automatische Wiederfreigabe und 12-Sekunden-Watchdog bleiben unverändert.
- 2.9.17 führt **keine Firmwareaktualisierung** aus.

---

# Kraken Control 2.9.16 – interne Exclusive-ACK-/Watchdog-Version

> **INTERNER HARDWARE-TESTSTAND – nicht automatisch als öffentlicher GitHub-Release vorgesehen.**

- Die fünf erneut bereitgestellten USBPcap-Aufzeichnungen wurden direkt ausgewertet. Die in 2.9.17 korrigierte datensatzgenaue Zählung weist im langen CAM-GIF-Mitschnitt 341 vollständige 240×240-RGB565-Nutzdatenübertragungen aus; der kontinuierliche Hauptabschnitt erreicht 26,375 Hz. 25,6 Hz bleibt als konservativer Rückfall erhalten.
- Die CAM-Framefolge wurde byte- und zeitgenau bestätigt: `36 01` → `37 01` → 20-Byte-Bulk-Header → 115.200 Byte RGB565 → `36 02` → `37 02`. Eine vollständige CAM-Transaktion dauert im Mittel rund 37,34 ms; der vorhandene 0,2-ms-Schutzabstand bleibt erhalten.
- Neue eindeutige ACK-Zuordnung im `kraken_cam_streamer.py`: Vor jedem Start-/Endbefehl werden alte HID-Berichte verworfen. Der Streamer akzeptiert ausschließlich die passende Antwort `37 01` beziehungsweise `37 02`; ungefragte `75 02`-Statusberichte werden nicht mehr versehentlich als ACK verwendet.
- Hintergrund: liquidctl 1.16.0 gibt in seinem privaten `_write_then_read()` bislang das nächste eingehende HID-Paket zurück, ohne es der gesendeten Anfrage zuzuordnen. Der noch offene liquidctl-Upstream-PR #916 vom 22. Juli 2026 bestätigt genau dieses Problem. Kraken Control verwendet für den internen Streamer deshalb eine lokal begrenzte, strenge Lösung, ohne liquidctl systemweit zu verändern.
- Der GIF-Streamer übernimmt die Kraken jetzt exklusiv. Vor dem Start wird der normale Status-Timer gestoppt und ein bereits laufender oder wartender liquidctl-Befehl höchstens 15 Sekunden sauber abgewartet. Erst danach öffnet der Streamer seine dauerhafte Geräteverbindung.
- Während der Animation werden keine neuen Kraken-Statusabfragen und keine neuen Pumpen-/Radiatorlüfterbefehle gestartet. Die bereits in der Kraken-Firmware gespeicherten Hardwarekurven laufen unabhängig von der App weiter.
- Nach sauberem Stop werden Statusabfragen und Kühlbefehle automatisch wieder freigegeben; nach 0,5 Sekunden wird der Status neu eingelesen.
- Neuer äußerer 12-Sekunden-Watchdog: Bleiben nach Beginn des Hardwarezugriffs Lebenszeichen aus, wird der Helfer beendet und der vorhandene LCD-Sicherheitsfallback stellt die Flüssigkeitstemperaturanzeige wieder her.
- Diagnose erweitert um `ack_matching` und die Anzahl während der ACK-Suche übersprungener fremder HID-Berichte.
- Neue zentrale Projektdokumentation `Kraken_Control_Projekt.md` und technische Mitschnittauswertung `USB_CAPTURE_FINDINGS.md` werden mitinstalliert und liegen im Entwicklerpaket vollständig bei.
- 2.9.16 führt **keine Firmwareaktualisierung** aus. Es bleibt eine experimentelle Beta für Kraken 2023 Standard / Non-Elite mit Firmware 2.0.0 und muss am realen Gerät getestet werden.

---

# Kraken Control 2.9.15 – interne CAM-Raw-LCD-Streamer-/Motion-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Der experimentelle GIF-/LCD-Transport wurde gezielt neu aufgebaut. Die in 2.9.14 getesteten **30-Hz- und 32-Hz-Transportmodi wurden entfernt**, weil der Hardware-/Videotest trotz guter USB-Messwerte sichtbares Haken und partielle Bildversätze zeigte.
- Neuer Standardpfad **CAM-nah · 26,67 Hz**. Als sicherer Vergleichs-/Rückfallmodus bleibt **25,6 Hz** erhalten. Es gibt keine Auto-Regelung, kein 25→27→25-Hz-Pendeln und keine Catch-up-Bursts.
- Neuer `kraken_cam_streamer.py`: Der Helfer besitzt die Firmware-2.x-Frame-Transaktion jetzt explizit selbst: `36 01 …` → Geräteantwort → 20-Byte-Bulk-Header → exakt **115.200 Byte RGB565** → `36 02` → Geräteantwort. Die vollständige Kraken-Verbindung bleibt während der Animation offen.
- Der alte `kraken_gif_streamer.py` wurde aus dem internen Paket und Installer entfernt, damit nicht versehentlich der verworfene 30/32-Hz-Pfad gestartet wird.
- Die bisherige reine Crossfade-Zwischenbildmethode wurde ersetzt. Die neue **Motion-Interpolation** schätzt eine konservative globale Bildverschiebung zwischen benachbarten Frames und verschiebt beide Bilder vor dem Überblenden. Bei nicht eindeutig erkennbarer Bewegung fällt sie automatisch auf einen normalen Blend zurück.
- Für Scroll-/Balkenbewegungen entstehen dadurch echte Zwischenpositionen, statt zwei versetzte Balken nur transparent übereinanderzulegen.
- GIF-Inhaltszeit bleibt weiterhin an `time.monotonic()` gekoppelt. Langsame USB-Transfers dürfen einen vollständigen Frame etwas länger halten; Transfers werden niemals überlappt.
- Das Firmware-2.x-Framebuffer-Priming bleibt bei zwei identischen ersten Frames. Danach beginnt erst die eigentliche Wiedergabezeitachse.
- Diagnose erweitert um Kennzeichnung des **CAM-Raw-Pfads**, Anzahl erkannter Bewegungs-Paare, Motion-Interpolationsmodus sowie eindeutige vorbereitete LCD-Frames. P90, EMA, Maximum, Überlauf, Jitter und Frame-Sprungzähler bleiben erhalten.
- Die Oberfläche wurde vereinfacht: LCD-Transport bietet nur noch `CAM-nah · 26,67 Hz · Standard` und `25,6 Hz · Sicher · bewährt`. Die alte 30/32-Hz-Auswahl wurde entfernt.
- Die technischen Test-GIFs 30/32 FPS wurden aus dem Paket entfernt; mitgeliefert bleiben 24/25/26/27-FPS-Tests sowie Diagonal- und Checker-Scroll-Tests.
- Persistente Experimentalbestätigungen, LCD-Crash-Fallback auf Flüssigkeitstemperatur, Uhr-Schutz, minimierter Tray-Autostart, Mehrsprachen-Oberfläche, Direct Access und alle bisherigen Kühl-/Sicherheitsfunktionen bleiben enthalten.

---

# Kraken Control 2.9.14 – interne Smooth-LCD-Transport-/Zwischenbild-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Der in 2.9.13 bewährte **25,6-Hz-LCD-Transport** bleibt unverändert als tearing-armer Sicherheits-/Referenzmodus erhalten.
- Zwei neue feste physische LCD-Transportmodi: **30 Hz · Smooth** und **32 Hz · Experimental**. Es gibt weiterhin keine Auto-Regelung und kein 25→27→25-Hz-Pendeln.
- **GIF-Inhaltsrate und LCD-Transportrate sind jetzt vollständig getrennte Einstellungen.** Ein 25-FPS-GIF behält seine ursprüngliche Laufzeit, kann aber mit 25,6, 30 oder 32 LCD-Updates pro Sekunde ausgegeben werden.
- Bei aktivierter **Zwischenbild-Interpolation** wird für zusätzliche LCD-Transportzeitpunkte ein echtes Mischbild zwischen den benachbarten logischen Inhaltsframes vorbereitet. 25-FPS-Inhalt bei 30 Hz erzeugt dadurch 30 zeitlich verteilte LCD-Phasenbilder pro Sekunde statt nur zusätzliche Duplikate.
- Die Vorbereitung verwendet eine phasenbasierte LCD-Bildtabelle pro GIF-Schleife. Der physische Scheduler bleibt auf dem gewählten 25,6/30/32-Hz-Takt, während die sichtbare GIF-Position weiterhin aus `time.monotonic()` abgeleitet wird.
- Die tearing-arme Übertragungsstrategie aus 2.9.13 bleibt erhalten: vollständige synchrone liquidctl-/ACK-Transfers, **0,2-ms-Schutzabstand**, keine überlappenden Bildtransfers und keine Catch-up-Bursts. Ein langsamer Transfer hält lieber ein vollständiges Bild etwas länger.
- Neue Diagnosewerte unterscheiden **LCD-Frame-Wiederholungen/-Sprünge** von rein logischen Inhaltsphasen. Dadurch lässt sich erkennen, ob der physische 30/32-Hz-Ausgabepfad wirklich neue Bilder liefert.
- Oberfläche erweitert um **LCD-Transport** mit den Modi `25,6 Hz · Sicher · bewährt`, `30 Hz · Smooth · mehr Zwischenbilder` und `32 Hz · Experimental · höchste Glättung`.
- 32 FPS ist zusätzlich als Inhalts-Teststufe verfügbar. Die mitgelieferten Test-GIFs wurden um **32-FPS-Farbzyklus** und **32-FPS-Bewegungsbalken** erweitert.
- Persistente Experimentalhinweise, LCD-Crash-Fallback auf Flüssigkeitstemperatur, Uhr-Schutz, Direct Access, Mehrsprachen-Oberfläche und minimierter Tray-Autostart bleiben enthalten.

---

# Kraken Control 2.9.13 – interne 25,6-Hz-Phasenentkopplungs-Version

> **INTERNER TESTSTAND – nicht als öffentlicher GitHub-Release vorgesehen.**

- Langzeittest von 2.9.12 ausgewertet: Bei exakt **25,000 Hz** waren USB-Timing, P90, Überlauf und Transportstatistik praktisch perfekt, das physische LCD wirkte trotzdem überwiegend stehend. Das spricht gegen einen reinen Python-/Schedulerfehler und für eine ungünstige wiederkehrende Display-/Framebuffer-Phase.
- Für **25/26/27-FPS-Inhalte sowie Adaptiv** ist der physische LCD-Transport deshalb jetzt fest auf **25,6 Hz** gesetzt. 24-FPS-Inhalt bleibt bei 24 Hz.
- Keine Auto-Regelung und kein 25→27→25-Hz-Sägezahn: 25,6 Hz bleibt während des gesamten Laufs konstant.
- Die GIF-Inhaltszeit bleibt weiterhin an `time.monotonic()` gekoppelt. Ein 25-FPS-GIF behält dadurch seine reale Laufzeit; der leicht schnellere LCD-Transport wiederholt bei Bedarf kontrolliert vollständige Inhaltsframes, statt die Animation zu beschleunigen.
- Der 25,6-Hz-Versatz ist bewusst gewählt, damit die Startphase der USB-Bildübertragung relativ zur internen LCD-/Framebuffer-Phase fortlaufend wandert, statt bei exakt 25 Hz immer denselben ungünstigen Punkt zu treffen.
- Der synchrone liquidctl-/ACK-Pfad, der **0,2-ms-Schutzabstand**, das Verbot von Catch-up-Bursts, Jitter-/P90-/Überlaufmessung und der Sicherheitsfallback auf Flüssigkeitstemperatur bleiben erhalten.
- Logmodus für 25/26/27 FPS lautet jetzt `stabil-detuned-25.6hz-wallclock`; die Oberfläche kennzeichnet 25 FPS als **„25,6 Hz LCD entkoppelt · empfohlen“**.
- Alle bisherigen 2.9.x-Funktionen bleiben enthalten: persistente Experimentalhinweise, LCD-Crash-Erkennung, Uhr-Fallback, Mehrsprachen-Oberfläche, Direct Access für Kühlbefehle und minimierter Tray-Autostart.

---

# Kraken Control 2.9.12 – interne Stable-Lock-GIF-Version

> **Interner Entwicklungs- und Teststand. Nicht als öffentlicher GitHub-Release vorgesehen.**

- Langzeitlogs aus 2.9.11 ausgewertet: Die bisherige Auto-Stabilisierung pendelte wiederholt von etwa 25 Hz Richtung 27 Hz, traf dann den beobachteten 39–40-ms-Transfercluster und fiel erneut auf etwa 25 Hz zurück. Dieses Sägezahnverhalten konnte als leichtes periodisches Haken sichtbar werden.
- Die selbsttätige Hoch-/Runterregelung wurde für die stabilen GIF-Modi entfernt. **25-FPS-Inhalt läuft jetzt fest mit 25 Hz LCD-Transport**, 24 FPS fest mit 24 Hz.
- 26- und 27-FPS-Inhalte bleiben bewusst Testmodi, verwenden aber ebenfalls einen **stabilen 25-Hz-LCD-Transport**. Da die Inhaltsrate höher als der physische Transport ist, können dort weiterhin zeitbasierte Inhalts-Sprünge auftreten; die GIF-Gesamtgeschwindigkeit bleibt korrekt.
- Adaptiv-Modus bereitet Inhalt jetzt höchstens mit 25 FPS auf und orientiert sich an der durchschnittlichen Quellbildrate, statt standardmäßig 27 FPS Inhalt zu erzeugen.
- Kein Catch-up, kein Burst und kein Feedback-Retuning während des Streams. Vollständige liquidctl-/ACK-Transfers werden seriell abgeschlossen; die nächste Übertragung startet ausgehend vom letzten tatsächlichen Startzeitpunkt.
- Post-ACK-/Framebuffer-Schutzabstand von 0,8 ms auf **0,2 ms** reduziert. Der vollständige synchrone liquidctl-Transfer bleibt abgeschlossen, aber 39–40-ms-Transfers werden bei 25 Hz nicht unnötig zusätzlich verlängert.
- Neue Diagnosewerte **Überlauf gesamt** und **max. Überlauf** zeigen, wie weit einzelne abgeschlossene Transfers das feste Zeitfenster tatsächlich überschritten haben. P90, EMA, Maximum und Jitter-Histogramm bleiben erhalten.
- Das Log kennzeichnet den neuen Modus als `stabil-lock-wallclock`; bei 25 FPS bleibt das LCD-Ziel während des gesamten Laufs konstant bei 25 Hz.
- Wallclock-Inhaltszeit, RGB565-Vorbereitung, doppelte Framebuffer-Initialisierung, Experimentalhinweise, LCD-Crash-Fallback, Uhr-Schutz, Direct Access, Mehrsprachen-Oberfläche und minimierter Tray-Autostart bleiben erhalten.

# Kraken Control 2.9.11 – interne Wallclock-/Auto-Stabil-GIF-Version

> **Interner Entwicklungs- und Teststand. Nicht als öffentlicher GitHub-Release vorgesehen.**

- GIF-Inhaltszeit folgt jetzt direkt `time.monotonic()` und damit der real verstrichenen Wiedergabezeit. Die Abspielgeschwindigkeit hängt nicht mehr davon ab, wie viele USB-Transfers die Kraken physisch pro Sekunde schafft.
- Der in 2.9.10 beobachtete Effekt, dass 25-FPS-Inhalt bei real etwa 25,2-Hz-LCD-Transport langsam auseinanderlaufen konnte, ist damit beseitigt.
- Neue selbsttätige LCD-Transportregelung für 24/25/26/27-FPS-Inhalte und Adaptiv-Modus. Der Transport startet konservativ und lernt aus den letzten USB-Übertragungszeiten; Obergrenze bleibt 27 Hz.
- Die Regelung verwendet das 90. Perzentil der jüngsten Uploadzeiten statt einzelne 38–41-ms-Transfers als dauernden Fehler/Re-Sync zu behandeln. Sinkt die sichere Rate, wird sofort reduziert; Erhöhungen erfolgen bewusst nur langsam.
- Der Framebuffer-Schutzabstand wurde nach dem langen 2.9.10-Hardwaretest von 2,0 ms auf 0,8 ms reduziert. Dadurch werden häufige ~39-ms-Transfers bei 25 FPS nicht künstlich auf >41 ms verlängert.
- Scheduler vollständig auf Start-zu-Start-Taktung umgestellt. Es gibt keine alte globale Deadline, keine Catch-up-Bursts und keine wiederholten Phase-Resets mehr. Wenn ein Transfer das Zeitfenster füllt, beginnt der nächste erst nach Abschluss plus kleinem Schutzabstand.
- 25-FPS-Inhalt startet mit 25-Hz-LCD-Ziel; 26/27-FPS- und Adaptiv-Inhalt starten konservativ bei 25 Hz und können bei genügend USB-Spielraum schrittweise bis 27 Hz ansteigen. 30 FPS bleibt ein expliziter Belastungstest.
- Neue Diagnosewerte im GIF-Log: aktuelles LCD-Ziel, Upload-EMA, P90-Uploadzeit, Maximum, gefüllte Zeitfenster, Inhaltswiederholungen, Inhalts-Sprünge sowie Jitter-Histogramm `<20`, `20–30`, `30–35`, `35–42` und `≥42 ms`.
- `Transportframes übersprungen` bleibt 0. Falls der physische LCD-Takt kurz unter der Inhaltsrate liegt, wird der korrekte GIF-Zeitpunkt aus der Echtzeit gewählt; dadurch kann transparent ein Inhaltsframe übersprungen werden, ohne die komplette Animation zu verlangsamen.
- Framebuffer-Priming bleibt vor dem Start der Wiedergabezeitachse. Der experimentelle Sicherheitsfallback auf Flüssigkeitstemperatur, Uhr-Schutz, Start-LCD-Arbitrierung, Direct Access, Sprachen und minimierter Tray-Autostart bleiben erhalten.

# Kraken Control 2.9.10 – interne GIF-Transport- und Tearing-Schutz-Version

> **Interner Entwicklungs- und Teststand. Nicht als öffentlicher GitHub-Release vorgesehen.**

- GIF-Inhaltsrate und physischer LCD-Transport sind jetzt voneinander getrennt.
- 24-, 25-, 26- und 27-FPS-Inhalte werden CAM-nah mit 27 Hz an die Kraken übertragen; die ursprüngliche GIF-Laufzeit bleibt dabei erhalten.
- 30 FPS bleibt als separater Belastungstest mit 30-Hz-LCD-Transport verfügbar.
- Der 25-FPS-Testpfad verwendet damit nicht mehr zwingend einen problematischen 25-Hz-Displaytakt; 25-FPS-Inhalte werden vollständig und zeitlich korrekt über 27-Hz-Transport abgebildet.
- Der Wiedergabezeitgeber startet erst **nach** den beiden einmaligen Firmware-2.x-Framebuffer-Priming-Transfers. Dadurch entfällt der bisher direkt nach jedem Start auftretende künstliche erste Frame-Verlust.
- Aggressives Catch-up und hartes Überspringen verspäteter Frames wurden entfernt. Ein langsamer USB-Transfer wird vollständig beendet und die nächste Übertragung anschließend sanft neu getaktet.
- Bei Transfers, die in das nächste Zeitfenster hineinreichen, wird ein kurzer 2-ms-Schutzabstand verwendet. Ziel ist weniger Mikroruckeln und weniger tearing-artige Bildversätze bei den beobachteten 38–40-ms-Ausreißern.
- Der Inhaltszeitgeber springt bei einem langsamen Transfer nicht mehrere Bilder vor. Stattdessen wird ein vollständiges Bild minimal länger gehalten; die Animation kann sich bei einem Ausreißer um wenige Millisekunden strecken, bleibt aber visuell kontinuierlicher.
- Neue GIF-Messwerte im Log: Inhalts-FPS, physischer LCD-Transport in Hz, letzter/EMA/maximaler Upload, langsame Transfers, sanfte Re-Syncs und erwartete Inhaltswiederholungen.
- `übersprungen` bleibt im neuen sanften Scheduler bei 0; der Streamer versucht keine Burst-Aufholjagd mehr.
- Neue 26-FPS-Teststufe zwischen 25 und 27 FPS.
- Die technischen Test-GIFs liegen jetzt für 24/25/26/27/30 FPS vor; Farbzyklus und bewegte Balken eignen sich besonders zum Vergleich von Mikroruckeln und tearing-artigen Versätzen.
- Startkonflikt zwischen globaler LCD-Wiederherstellung und einem automatischen Startprofil entschärft: Wenn ein Startprofil aktiv ist, bestimmt dieses den LCD-Zustand, statt parallel noch ein global gespeichertes Bild zu senden.
- Doppelte LCD-Uhr-Minutenupdates werden unterdrückt. Manuelle Änderungen an der Uhr können weiterhin einen erzwungenen Upload im selben Minutenfenster auslösen.
- Dauerhafte Experimentalbestätigungen, LCD-Crash-Fallback auf Flüssigkeitstemperatur, Sprachen Deutsch/Englisch/Spanisch/Französisch, Direct Access, Tray-Autostart und alle bisherigen Sicherheitsfunktionen bleiben erhalten.

# Kraken Control 2.9.9 – interne CAM-27-FPS- und GIF-Timing-Version

> **Interner Entwicklungsstand – nicht für die öffentliche Veröffentlichung vorgesehen.**

- GIF-Streamer auf einen **CAM-nahen Zielbereich bis 27 FPS** erweitert; zusätzliche feste Testmodi **24, 25, 27 und 30 FPS** ergänzen die bisherigen 5, 8, 10, 12, 15 und 20 FPS.
- Adaptiv-Modus zielt nun auf bis zu **27 FPS** statt 15 FPS und bleibt an einer monotonen Zeitachse verankert.
- Feste FPS verändern nicht mehr versehentlich die Abspielgeschwindigkeit des GIFs: Die ursprüngliche GIF-Schleifendauer bleibt erhalten und wird auf den gewählten LCD-Ausgabetakt neu abgetastet.
- Neue standardmäßig aktivierte Option **„Zwischenbilder glätten (Interpolation)“** erzeugt beim Vorbereiten echte Mischbilder zwischen Quellframes. Dadurch können GIFs mit niedriger Quellbildrate bei 24–30 FPS sichtbar flüssiger wirken.
- Frame-Pacing vollständig auf absolute `time.monotonic()`-Zeitpunkte umgestellt. Uploaddauer wird dadurch nicht mehr von Frame zu Frame aufaddiert; bei echtem Rückstand werden veraltete Frames übersprungen statt als Burst nachgesendet.
- Stop/Start-Race behoben: Der alte 3,5-Sekunden-Notfalltimer ist jetzt ein abbrechbarer `QTimer` und kann keinen bereits neu gestarteten GIF-Prozess mehr versehentlich beenden.
- Pillow-12.3-Warnung für `Image.Image.getdata()` beseitigt; auf aktuellen Pillow-Versionen wird `get_flattened_data()` verwendet, mit kompatiblem Fallback für ältere Versionen.
- GIF-Log erweitert: Quellframes, vorbereitete Ausgabeframes, Quelllaufzeit, Zieltakt, Interpolationsstatus, effektive FPS, Uploadzeit und übersprungene Frames werden protokolliert.
- Zehn selbst erzeugte **240×240-Test-GIFs** liegen unter `test-gifs/`: Farbzyklus und bewegte Balken jeweils mit exakt gemittelten 24/25/27/30 FPS sowie ein 27-FPS-Diagonal-Sweep und ein 27-FPS-Checker-Scroll.
- Die GIF-Testdateien verwenden ausschließlich im GIF-Format darstellbare 10-ms-Zeitstufen; ihre Frameverteilung ist so gewählt, dass die jeweilige Schleife im Mittel exakt 24, 25, 27 bzw. 30 Bilder pro Sekunde erreicht.
- Das Generator-Skript `tools/generate_test_gifs.py` liegt vollständig im Quellcode bei; der Installer kopiert die fertigen Test-GIFs zusätzlich nach `~/.local/share/kraken-control/test-gifs/`.
- Minimierter Tray-Autostart, dauerhafte Experimentalbestätigungen, LCD-Crash-Fallback, Direct-Access-Kühlung, Mehrsprachen-Oberfläche und alle Sicherheitsfunktionen aus 2.9.8 bleiben enthalten.

# Kraken Control 2.9.8 – interne Smooth-GIF- und Autostart-Version

> **Interner Entwicklungsstand – nicht für die öffentliche Veröffentlichung vorgesehen.**

- Experimenteller Firmware-2.x-GIF-Streamer vollständig überarbeitet: ein separater, langlebiger `QProcess` hält eine einzige liquidctl-Verbindung offen, statt für jedes GIF-Bild einen neuen CLI-Prozess zu starten.
- GIF-Frames werden vor dem Start auf 240×240 vorbereitet und einmalig in den von liquidctl für Firmware 2.x verwendeten RGB565-Datenstrom konvertiert.
- Erster Frame wird entsprechend dem liquidctl-Firmware-2.x-Verhalten einmalig doppelt übertragen; Folgeframes werden nur einmal gesendet.
- Neue Zeitsteuerung mit `time.monotonic()`: **Adaptiv** misst die reale Uploadzeit und streckt das Timing bei Bedarf gleichmäßig, damit möglichst keine Frames verloren gehen; feste FPS-Modi überspringen bei Rückstand veraltete Frames statt sie als Burst nachzusenden.
- GIF-Bildrate wählbar: adaptives Original-Timing bis maximal 15 FPS sowie feste 5, 8, 10, 12, 15 oder 20 FPS.
- GIF-Status und Log zeigen vorbereitete Frames, effektive Bildrate, letzte Uploadzeit, Taktungsmodus und übersprungene Frames; dadurch lässt sich die tatsächliche Streamleistung auf der Testhardware messen.
- LCD-Modi sind jetzt gegenseitig koordiniert: Uhr, statischer Fallback, Einzelbild, LCD-Ausrichtung und Flüssigkeitstemperatur stoppen einen laufenden GIF-Stream zuerst sauber, statt mit „Kraken verarbeitet gerade einen anderen Befehl“ zu kollidieren.
- Eigener dauerhaft speicherbarer Experimentalhinweis für den GIF-Streamer; „Experimentalhinweise zurücksetzen“ setzt Uhr-, Fallback- und GIF-Bestätigung gemeinsam zurück.
- Crash-Marker und LCD-Sicherheitsfallback gelten nun auch für GIF-Streaming. Ein unerwarteter Stream-Abbruch führt zurück zur Flüssigkeitstemperatur; GIF wird nach unsauberem Ende nicht automatisch fortgesetzt.
- Neue Option **„Beim Systemstart minimiert/im Tray starten“**. Nach abgeschlossenem Erstsetup startet Kraken Control bei Desktop-Autostart standardmäßig im Tray; ein manueller Start öffnet das Fenster weiterhin normal.
- Bestehende Autostart-Dateien werden auf den neuen `--autostart`-Startmarker migriert.
- Deutsch, Englisch, Spanisch und Französisch bleiben als erste interne Sprachstufe enthalten; neue GIF- und Autostart-Bedienelemente sind ebenfalls übersetzt.
- Direct-Access-Kühlungssteuerung, 10.000-Zeichen-Loglimit, LCD-Uhr-Sicherheit, Hintergründe und alle Fixes aus 2.9.7 bleiben erhalten.

# Kraken Control 2.9.7 – interne Sprach- und LCD-Sicherheitsversion

> **Interner Entwicklungsstand – nicht für die öffentliche Veröffentlichung vorgesehen.**

- LCD-Uhr-Hinweis wird nach einmaliger Zustimmung dauerhaft gespeichert und erscheint nach normalen Neustarts nicht erneut.
- Auch die Warnung für den experimentellen LCD-Wiederholungs-Fallback kann dauerhaft bestätigt werden.
- Neuer Punkt **„Experimentalhinweise zurücksetzen“** in den Einstellungen setzt beide Bestätigungen bewusst zurück.
- Neue Crash-Erkennung für experimentelle LCD-Modi: Während Uhr oder Wiederholungs-Fallback aktiv sind, wird ein persistenter Sitzungsmarker gesetzt.
- Bei normalem Programm-/Systemende wird der Marker sauber entfernt; bleibt er nach einem Absturz erhalten, startet die experimentelle LCD-Funktion beim nächsten Start nicht automatisch.
- Nach erkanntem unsauberen Ende wird automatisch die Standardanzeige **Flüssigkeitstemperatur** angefordert. Falls das Gerät gerade nicht verfügbar ist, bleibt die Wiederherstellung vorgemerkt und wird beim nächsten erfolgreichen Geräteaufbau erneut versucht.
- LCD-Rendererfehler lösen sofort den sicheren Flüssigkeitstemperatur-Fallback aus.
- Wiederholte LCD-/Uhr-Uploadfehler werden gezählt; nach drei aufeinanderfolgenden Fehlern wird die experimentelle LCD-Funktion beendet und auf Flüssigkeitstemperatur zurückgeschaltet.
- Verlust der Kraken-Verbindung während eines experimentellen LCD-Modus aktiviert ebenfalls die sichere Wiederherstellung.
- Erste Mehrsprachen-Unterstützung unter **Einstellungen → Sprache**. Verfügbar: **Deutsch, Englisch, Spanisch und Französisch**.
- Die gewählte Sprache wird dauerhaft gespeichert und die statische Hauptoberfläche kann ohne Neustart umgeschaltet werden.
- Diese erste interne Lokalisierungsstufe übersetzt zentrale Tabs, Menüs, Bedienelemente und Einstellungsbereiche. Technische Laufzeit-, Hardware- und Logmeldungen bleiben teilweise Deutsch, damit die Testprotokolle zwischen den Sprachen eindeutig vergleichbar bleiben.
- Direct-Access-Kühlungssteuerung, 10.000-Zeichen-Loglimit, Hintergrund-Hotfixes und alle Sicherheitsfunktionen aus 2.9.6 bleiben enthalten.

# Kraken Control 2.9.6 – LCD-Uhr-Hotfix

- Regression in „Uhr starten“ behoben: Der Startpfad verwendete noch das entfernte Widget `clock_24h`.
- Das Zeitformat wird jetzt korrekt aus `clock_format` gelesen (`24` bzw. `12`).
- „Uhr starten“ protokolliert wieder Startmodus und erfolgreiche/fehlgeschlagene LCD-Uploads.
- Statischer Regressionstest stellt sicher, dass `clock_24h` nicht erneut in den Quellcode gelangt.
- Alle Direct-Access-, Hintergrund-, Scroll-, Profil- und 10.000-Zeichen-Log-Fixes aus 2.9.5 bleiben enthalten.

# Kraken Control 2.9.5 – Direct-Access- und Hintergrund-Hotfix

- Alle Pumpen-/Lüfter-Schreibbefehle verwenden Direct Access, einschließlich fester Werte und CPU-Assistenz.
- Berechtigungsfehler im Hintergrund erzeugen keine wiederholten modalen Reparaturdialoge.
- Sichtbares Log ist auf 10.000 Zeichen begrenzt; alte vollständige Zeilen werden zuerst entfernt.
- CPU-, LCD-Uhr-, Design- und Anzeigeaktionen werden detaillierter protokolliert.

# Kraken Control 2.9.4

- Animierte Hintergründe lassen sich nach „Animation ausschalten“ wieder direkt einschalten.
- Ausschalten löscht das zuletzt gewählte Animationsthema nicht mehr.
- „Animation aktivieren“ stellt bei alten Einstellungen mit Thema „Aus“ automatisch ein gültiges Thema wieder her.
- Aktivieren/Deaktivieren wird sofort angewendet und im Aktionslog protokolliert.

# Kraken Control 2.9.2 – Einstellungs- und Layout-Hotfix

- Der komplette Bereich **Einstellungen** ist jetzt vertikal und bei Bedarf horizontal scrollbar.
- Design-, DPI-, Hintergrund-, Programm-, Abhängigkeits- und Gerätezugriffsoptionen bleiben auch bei 105–180 % App-Skalierung erreichbar.
- Inhaltsbereich der Einstellungen besitzt eine sinnvolle Mindestbreite und transparente Darstellung über animierten Hintergründen.
- Standardfenster auf 1280×880 vergrößert; Mindestgröße auf 820×600 angepasst; kleinere Fenster bleiben dank Scrollbereich bedienbar.
- Einmalige Migration vergrößert auch eine aus 2.9/2.9.1 gespeicherte kleine Fenstergeometrie, begrenzt auf die verfügbare Monitorfläche.
- Scrollbereich ist per Tastatur fokussierbar und besitzt eine Screenreader-Beschriftung.
- CPU-Offscreen-Renderer, vollständiges Aktionsprotokoll und alle Hardwarefixes aus 2.9.1 bleiben enthalten.

# Kraken Control 2.9.1 – Grafik- und Protokoll-Hotfix

- Darstellungsfehler mit vollflächigen vertikalen Farbstreifen bei animierten Hintergründen behoben.
- Animationen werden nicht mehr direkt auf dem zentralen Inhaltswidget gezeichnet.
- Neue getrennte Ebenen: Hintergrund unten, vollständige Bedienoberfläche immer darüber.
- Sicherer CPU-Offscreen-Renderer über `QImage` mit begrenzter interner Auflösung für Wayland, HiDPI, 21:9 und 32:9.
- Bei einem Renderfehler wird die Animation automatisch gestoppt und die Oberfläche bleibt mit normaler Hintergrundfarbe bedienbar.
- Jeder Mausklick auf interaktive Bedienelemente wird im Log protokolliert.
- Zusätzlich werden Tastaturaktionen, Tabwechsel, Menüaktionen und vom Benutzer geänderte Auswahl-, Regler-, Zahlen-, Text- und Tabellenwerte protokolliert.
- Log-Kapazität auf 10.000 Einträge erhöht.
- Log kann kopiert, geleert und als `.log`/`.txt` gespeichert werden.
- Private Pfade und eindeutige Kennungen werden weiterhin vor der Anzeige bereinigt.

# Kraken Control 2.9 – Einrichtung, Profile und adaptive Oberfläche

- Ersteinrichtungsassistent mit Design, Akzentfarbe, Hintergrund, Monitorprüfung und Start-Kühlprofil.
- Heller Modus ist bei neuen Installationen der Standard.
- Zwölf prozedural erzeugte animierte Hintergründe ohne fremde Mediendateien.
- Einstellbare Bildrate, Intensität und Pause bei inaktiver Anwendung.
- Monitor-, DPI-, Gerätepixel- und Seitenverhältniserkennung.
- Responsive Layoutvorgaben für 16:10, 16:9, 21:9 und 32:9.
- App-Skalierung von 80 bis 180 Prozent.
- Neuer Hauptbereich Profile mit Kategorien Gesamt, Kühlung, LCD, RGB und Design.
- Profile erstellen, aktualisieren, duplizieren, umbenennen, löschen, importieren und exportieren.
- Optionales Startprofil oder zuletzt verwendetes Profil.
- Gesamtprofile speichern auch Hintergrund, Anzeige, Fenstergröße und relevante Hardwareeinstellungen.
- Vollständiger Quellcode-Snapshot und Datei-Prüfsummen im Release.
- Dokumentation und Tests auf Version 2.9 aktualisiert.

# Kraken Control 2.8.1 - Abhängigkeits-Assistent

- Startskript prüft liquidctl, PySide6 und Pillow vor dem Programmstart.
- Fehlende Pakete können nach ausdrücklicher Bestätigung über DNF und die normale polkit-Administratorabfrage installiert werden.
- Keine stillen Installationen und keine zusätzlichen oder fremden Paketquellen.
- Neuer Bereich unter Einstellungen zeigt den Zustand aller Laufzeitabhängigkeiten.
- Abhängigkeiten können dort erneut geprüft und repariert werden.
- Falls PySide6 fehlt, übernimmt das Shell-Startskript die Prüfung, bevor die Python-Oberfläche geladen wird.
- Automatische Paketinstallation ist zunächst bewusst auf Nobara/Fedora-Systeme mit DNF begrenzt.

# Kraken Control 2.8

- Expertenmodus für frei einstellbare Kraken-Wassertemperatur-Warn- und Kritisch-Grenzen.
- Deutliche Warnung vor dem Aktivieren; sichere Standardbereiche lassen sich jederzeit wiederherstellen.
- Klare Anzeige, ob Pumpe und Radiatorlüfter zuletzt als feste Drehzahl, Temperaturkurve oder CPU-Assistenz gesetzt wurden.
- Kühlmodus wird gespeichert und beim nächsten Start angezeigt.
- LCD-Uhr kann das aktuelle Minutenbild zusätzlich automatisch in einem frei wählbaren Intervall erneut senden.
- Minutenaktualisierung und Wiederholungs-Fallback der Uhr arbeiten unabhängig voneinander.
- Kurven-Direct-Access-Hotfix aus 2.7.1 bleibt enthalten.

# Kraken Control 2.7.1 - Kurven-Hotfix

- Pumpen- und Lüfterkurven werden gezielt mit `liquidctl --direct-access` übertragen.
- Behebt `insufficient permissions`, wenn feste PWM-Werte über hwmon funktionieren, die hwmon-Kurvenattribute aber nur für root beschreibbar sind.
- Wiederherstellung der Wasserkurven nach CPU-Assistenz und beim Beenden nutzt denselben Direktzugriff.
- Die udev-Reparatur bleibt für den HID-Schreibzugriff erhalten, wird aber nicht mehr fälschlich als alleinige Lösung für gesperrte hwmon-Auto-Point-Dateien dargestellt.

# Kraken Control 2.7 - Tastatur, AM5-Profile und Berechtigungsreparatur

- Vollständige Tastaturwege mit Menüs und globalen Tastenkombinationen.
- Der grafische Kurveneditor gibt Tab/Umschalt+Tab wieder frei; Strg+Links/Rechts wählt Punkte.
- CPU-Temperaturanzeige über den Linux-k10temp-Treiber mit Tctl/Tdie-Priorität.
- Einzelne AMD-AM5-Profile für ausgewählte Ryzen-7000-, 8000G- und 9000-Modelle.
- Sichtbare Trennung zwischen CPU-Tjmax (89/95 °C) und Kraken-Wassertemperatur (42/50 °C).
- Optionale CPU-Temperatur-Assistenz: verstärkte Kraken-Kühlung ab profilspezifischem Wert, 100 % vor Tjmax.
- Empfohlene Kraken-Wasserkurven je CPU-Profil und automatische CPU-Erkennung.
- Schreibzugriffsprüfung für /dev/hidraw vor Lüfter- und Kurvenänderungen.
- Reparaturschaltfläche mit polkit/pkexec sowie aktualisierte udev-Regel und gezieltes USB-/hidraw-Triggern.
- Laufzeitübersicht für Kraken Control, Python, PySide6, Qt, liquidctl, Pillow, Distribution und Kernel.
- Neue Dateien CPU_PROFILES.md, CPU_PROFILES.en.md und COMPONENT_VERSIONS.md.

# Kraken Control 2.6 - Grafischer Kurveneditor und Design-Einstellungen

- Interaktiver grafischer Editor für Pumpen- und Radiatorlüfterkurven.
- Kurvenpunkte können per Maus oder Tastatur verschoben werden.
- Tabellenwerte und Diagramm bleiben vollständig synchron.
- Die aktuelle Wassertemperatur wird als Marker in beiden Diagrammen angezeigt.
- Sicherheitsregeln bleiben erhalten: steigende Temperaturen, nicht sinkende Leistung und spätestens bei 50 °C 100 %.
- Kurvenwerte werden gespeichert und beim nächsten Start wiederhergestellt.
- Neue Darstellungsmodi: System, Hell und Dunkel.
- Frei wählbare Akzentfarbe als Hex-Code sowie fünf Farbvoreinstellungen.
- Akzentfarbe gilt für Tabs, Schaltflächen, Fokusrahmen, Regler, LCD-Rahmen und Kurvendiagramme.
- Design-Einstellungen werden sofort angewendet und dauerhaft gespeichert.
- README, englische Dokumentation, Desktop-Eintrag, Diagnosebericht, Tests und Projektverlauf wurden auf Version 2.6 aktualisiert.

# Kraken Control 2.5 - Klarer Projektumfang und modulare Ausrichtung

- Kraken Control bleibt bewusst eine spezialisierte Anwendung für die NZXT-Kraken-Wasserkühlung.
- Unterstützt bleiben Wassertemperatur, Kraken-Pumpe, direkt von der Kraken verwaltete Radiatorlüfter, LCD und der separate NZXT 2023 RGB Controller.
- Mainboard-, Gehäuse- und GPU-Lüfter werden ausdrücklich nicht erkannt oder gesteuert.
- AMD-Grafiksteuerung, allgemeines System-Tuning und externe Lüfterverwaltung sind für eigenständige Werkzeuge vorgesehen.
- Der Über-Bereich zeigt den enthaltenen und ausgeschlossenen Funktionsumfang jetzt deutlich an.
- Die Geräteliste erklärt, dass nur die zur Kraken-Kühlung gehörenden Lüfter unterstützt werden.
- Neue Dateien `PROJECT_SCOPE.md` und `PROJECT_SCOPE.en.md` dokumentieren die Modulgrenzen.
- Versionsanzeige, Installer, Desktop-Eintrag, Diagnosebericht, README, Sicherheitsdokumentation und statische Tests wurden auf 2.5 aktualisiert.

# Kraken Control 2.4 - Transparente Links und Herstellerverweise

- Der Über-Bereich wurde scrollbar und deutlich ausführlicher gestaltet.
- Für liquidctl, Python, PySide6/Qt for Python und Pillow werden Aufgabe, offizielle Website/Dokumentation, GitHub-Quellcode und Lizenzseite angezeigt.
- OpenAI-, ChatGPT- und OpenAI-GitHub-Seiten sind bei der KI-Unterstützung verlinkt; ChatGPT wird ausdrücklich als Entwicklungsunterstützung und nicht als Laufzeitbestandteil bezeichnet.
- Die eigene Projektseite wird nicht erfunden: GitHub/Codeberg bleiben sichtbar als „noch nicht veröffentlicht“, bis eine echte Repository-Adresse feststeht.
- In der Liste der unterstützten Geräte ist die offizielle NZXT-Seite für Kraken (2023) direkt beim unterstützten Kühler verlinkt.
- Zusätzlich sind die NZXT-Kühlerübersicht und die NZXT-Hauptseite erreichbar.
- Neue deutsche und englische Dateien `SOFTWARE_AND_LINKS.md` / `SOFTWARE_AND_LINKS.en.md` dokumentieren alle verwendeten Komponenten, Herstellerseiten, Quellcode- und Lizenzadressen auch außerhalb der Anwendung.
- Versionsanzeige, Desktop-Eintrag, Installer, README und Sicherheitsdokumentation auf 2.4 aktualisiert.

# Kraken Control 2.3.1 - Sicherheitsupdate

- Programmstatus deutlich als **experimentelle Open-Source-Beta** gekennzeichnet.
- Pumpenwerte unter 30 % und Lüfterwerte unter 20 % erfordern eine ausdrückliche Bestätigung.
- Kühlkurven müssen streng ansteigende Temperaturen, nicht sinkende Leistung und spätestens bei 50 °C einen 100-%-Endpunkt besitzen.
- Neue Schaltfläche für ein sicheres Standardprofil mit 65 % Pumpe, 65 % Lüfter und aktivierter kritischer Schutzumschaltung.
- Warn- und kritische Temperaturgrenzen können sich nicht mehr überschneiden.
- Wiederholter LCD-Fallback und LCD-Uhr werden beim ersten Start nach dem Update vorsorglich deaktiviert.
- Vor dem Aktivieren von LCD-Fallback oder Uhr erscheint eine Warnung zu den unbekannten Langzeitwirkungen häufiger Uploads.
- Diagnosewerkzeug arbeitet jetzt ausschließlich lesend; `liquidctl initialize all` wurde entfernt.
- Diagnosebericht entfernt zusätzlich Home-Pfade, Benutzerkennungen, Hostnamen, Machine-ID und Boot-ID.
- Kopierbare Programmlogs anonymisieren Home-Pfade und typische eindeutige Kennungen.
- Neue Sicherheitsdokumentation `SECURITY.md`.

# Kraken Control 2.3

- Programmname sichtbar zu **Kraken Control by Frelidon** erweitert.
- Neuer **Über**-Bereich mit Projektstatus, unabhängiger Markenkennzeichnung, KI-Unterstützung, GPL-Lizenz und unterstützten Geräten.
- Neue LCD-Uhr mit 24-Stunden- und 12-Stunden-/AM-PM-Format.
- Optionale Datumsanzeige, einstellbare Schriftgröße sowie frei wählbare Text- und Hintergrundfarben.
- Die Uhr erzeugt ein statisches 240×240-Bild und aktualisiert es gezielt zum nächsten Minutenwechsel; Sekunden werden nicht übertragen.
- Uhrmodus wird gespeichert und kann beim nächsten Programmstart automatisch fortgesetzt werden.
- Runde LCD-Vorschau mit kreisförmigem Beschnitt und sichtbarem Displayrahmen.
- Lange LCD-Einstellungen in einen scrollbareren Bereich verschoben.
- Startmenü-Symbol robuster installiert: absolute Symbolreferenz plus Aktualisierung des KDE/Plasma-Caches.
- Neues datenschutzfreundliches Diagnosewerkzeug `kraken-control-diagnostics` für zukünftige Geräteunterstützung.
- Englische Grunddokumentation und separate Liste unterstützter Geräte ergänzt.
- Lizenz auf **GPL-3.0-or-later** festgelegt.

# Kraken Control 2.2

- LCD-Bedienung an das tatsächliche Verhalten der Kraken-Firmware 2.0.0 angepasst.
- Die missverständliche Option **„Bild dauerhaft anzeigen“** wurde durch **„Automatisch erneut senden (Fallback)“** ersetzt.
- Ein statisches Bild kann bewusst einmal übertragen werden; die Oberfläche erklärt, dass es auf Firmware 2.0.0 bereits ohne Wiederholung dauerhaft sichtbar bleiben kann.
- Der LCD-Fallback startet erst, nachdem der erste Bild-Upload erfolgreich abgeschlossen wurde.
- Bei einem fehlgeschlagenen Upload wird der Fallback automatisch wieder deaktiviert.
- Intervallsteuerung ist nur aktiv, solange der Fallback eingeschaltet ist.
- Neuer sichtbarer LCD-Status für Einzelübertragung, Fallback und Flüssigkeitstemperaturmodus.
- **„Zur Flüssigkeitstemperatur zurück“** beendet den Fallback zuverlässig und setzt den gespeicherten Zustand zurück.

# Kraken Control 2.1

- Absturz unter Python 3.14 / PySide6 6.11 behoben.
- QThreadPool und QRunnable entfernt.
- Serielle, asynchrone QProcess-Warteschlange hinzugefügt.
- Sauberes Beenden laufender Prozesse beim Programmende.

# Kraken Control 2.0

- Oberfläche vollständig neu strukturiert.
- Kraken und separater RGB-Controller korrekt getrennt.
- Live-Dashboard, Profile, Pumpen-/Lüfterkurven und Sicherheitsfunktionen ergänzt.
- LCD-Vorschau, Bildübertragung, Autostart, System-Tray, Installer und Deinstaller ergänzt.

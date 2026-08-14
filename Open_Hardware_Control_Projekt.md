# Open Hardware Control – zentrale Projektdokumentation

Stand: **3.0.9**, 14. August 2026

## Zielbild

Open Hardware Control by Frelidon ist die gemeinsame, modular erweiterbare Linux-Oberfläche für unterstützte Hardware. Die komplette bisherige NZXT-Kraken-Anwendung bleibt als fest eingebautes NZXT-Modul erhalten. Corsair-Hardware wird über OpenLinkHub eingebunden. Spätere Gerätefamilien können als weitere Module hinzukommen, ohne die Navigation mit einer langen Reihe von Hauptreitern zu überladen.

Open Radeon Control Center bleibt ein eigenständiges Projekt. Es wird weder technisch noch organisatorisch in Open Hardware Control verschmolzen.

## Version 3.0.9

Das OpenLinkHub-Mausmodul verbindet die in 3.0.7 eingeführten eigenen GPL-SVG-Schemata nun mit der dokumentierten Tastenbelegung. Ein Klick auf eine von OpenLinkHub gemeldete physische Taste öffnet einen Dialog für Originalfunktion, Keine, Medien, DPI, Tastatur, Sniper-DPI, Maus oder ein vorhandenes Makro. Die Zuordnung wird erst nach ausdrücklicher Schreibfreigabe und ausschließlich über den fest erlaubten Endpunkt `/api/mouse/updateKeyAssignment` übertragen. Fehlt ein sicher gemeldeter Tastenindex, bleibt das Schema absichtlich nur lesbar.

Ein begrenzter Tastaturmakro-Recorder erstellt OpenLinkHub-Makros aus Einzeltasten und Pausen. Er erfasst nur Eingaben im sichtbaren, fokussierten Dialog, höchstens 64 Tasten und höchstens fünf Sekunden Pause je Schritt. Es gibt keinen globalen Tastatur-Hook und keine verdeckte Aufnahme außerhalb der Anwendung.

Die generierten LCD-Hardwaredesigns zeigen keine kleinen `LIVE`-, `LETZTER WERT`- oder `KRAKEN CONTROL`-Zusätze mehr. Akzentfarbe, Beschriftungsfarbe und Zahlenfarbe sind getrennt einstellbar; Beschriftung und Temperaturzahl besitzen jeweils eine eigene Größe. Eine globale Celsius-/Fahrenheit-Auswahl gilt für Oberfläche, Kurveneditor, Sicherheitsgrenzen, Profile sowie neue statische und animierte LCD-Hardwarebilder. Kühlkurven und Sicherheitslogik speichern intern weiterhin Celsius, damit ein Einheitenwechsel keine Regelwerte verändert.

Beim Wechsel der Temperatureinheit wird ein laufender generierter Hardwareanimationsmodus kontrolliert mit dem neuen Zahlenformat aufgebaut. Benutzerprofile speichern Einheit und neue Darstellungswerte; ältere Profile übernehmen sichere Standardwerte. Die Wiederherstellung der originalen Kraken-Flüssigkeitstemperaturanzeige beim echten Beenden, der verzögerte LCD-Autostart und die CPU-Kurvenregelung bleiben erhalten.

## Version 3.0.7 INTERN

Beim echten Beenden wird zuerst ein laufender CAM-Raw-GIF-Streamer vollständig geschlossen. Anschließend überträgt der Hauptprozess synchron den liquidctl-Befehl für die originale Kraken-Flüssigkeitstemperaturanzeige. Erst danach folgt der autonome Flüssigkeitstemperatur-Kühlfallback für aktive CPU-Kurvenkanäle. Dieser Ablauf gilt auch für geordnete Sitzungssignale beim Abmelden, Neustarten oder Herunterfahren. Das normale Schließen in den System-Tray läuft nicht durch diesen Pfad; dort bleiben LCD-Ausgabe und CPU-Kurvenregelung aktiv.

Das OpenLinkHub-Mausmodul erhielt erstmals eine grafische Zuordnung zwischen physischer Taste und Funktion. Fünf vollständig im Projekt gezeichnete GPL-SVGs decken kompakte, ergonomische, symmetrische, Mehrknopf- und MMO-Formen ab. Die Auswahl erfolgt aus dem Produktnamen, ohne zu behaupten, ein exaktes Hersteller-Rendering zu sein. Anklickbare Qt-Hotspots liegen über dem SVG und sind mit einer dreispaltigen Tabelle für Nummer, Position und Funktion gekoppelt.

## Version 3.0.6 INTERN

Der Profilstart stellt nun auch den tatsächlich aktiven LCD-Modus vollständig wieder her. Gesamt- und LCD-Profile speichern neben Datei, Ausrichtung und Helligkeit einen eindeutigen Modus für Einzelbild, wiederholtes Bild, Uhr, statisches Hardwaredesign, generierte Hardwareanimation oder normales GIF. Profile aus 3.0.5 besitzen dieses Feld noch nicht; eine dort gespeicherte `.gif`-Datei wird deshalb sicher als GIF-Modus migriert, ein statisches Bild als einmalige Bildübertragung.

Beim Desktop-Autostart markiert `--autostart` weiterhin den Hintergrundstart. Das Hauptfenster bleibt nach abgeschlossenem Erstsetup im Tray beziehungsweise ohne verfügbaren Tray minimiert. Ein im Gesamtprofil gespeicherter maximierter Fensterzustand wird nur beim manuellen Anwenden, niemals beim automatischen Hintergrundstart berücksichtigt. Nach dem Laden des Startprofils wird der versteckte Zustand zusätzlich nochmals angewendet.

Die LCD-Wiederherstellung wartet beim Desktop-Autostart bis fünf Sekunden nach dem Anwendungsstart. Erst danach beginnt der gespeicherte Bild-, Uhr-, Hardware- oder GIF-Modus. So können Plasma, System-Tray, udev-Zugriff und andere Desktopdienste zuerst anlaufen. Ein manueller Programmstart verwendet weiterhin nur die normale kurze Geräteverzögerung.

Geordnete Sitzungssignale (`SIGTERM`, `SIGINT`) werden in den Qt-Abschlussweg überführt. Der experimentelle LCD-Crashmarker wird vor längerem Stream- und USB-Aufräumen gelöscht. Ein echter Absturz behält unverändert die Sicherheitswiederherstellung; ein normaler Neustart des Desktops blockiert das gespeicherte LCD-Profil nicht mehr fälschlich.

## Version 3.0.5 INTERN

Die beiden sichtbaren NZXT-Kurven verwenden jetzt ausschließlich die CPU-Temperatur als Eingangsgröße. Die Kraken-Firmware kann selbst nur ihre Flüssigkeitstemperatur auswerten; deshalb berechnet Open Hardware Control die CPU-Kurven als laufende Software-Regelung und überträgt das jeweilige Ergebnis als festen Pumpen- beziehungsweise Lüfterwert.

Ein eigener 1-Sekunden-Timer liest `k10temp` über Linux-hwmon, unabhängig von Kraken-Statusabfragen und USB-Eigentum. Die Regelung interpoliert linear zwischen den fünf Punkten, glättet kurze Ryzen-Temperatursprünge per EMA, quantisiert auf 2-Prozent-Stufen und verwendet getrennte Mindeständerungen und Sperrzeiten: steigende Kühlanforderungen reagieren schneller, fallende Werte werden bewusst verzögert. Erreichen Rohwert oder Kurve den letzten Punkt, werden sofort 100 Prozent angefordert.

Während des exklusiven CAM-Raw-LCD-Streams bleibt das CPU-Sensing aktiv. Eine tatsächlich notwendige Änderung verwendet die in 3.0.1 eingeführte PAUSE-/RESUME-Übergabe; Pumpe und Lüfter werden innerhalb desselben USB-Fensters nacheinander gesetzt. Der Streamer und sein Framecache bleiben dabei erhalten.

Alle AM5-Profile wurden auf CPU-Punkte umgestellt. Profile für 95-°C-Tjmax erreichen bei 90 °C 100 Prozent, Ryzen-7000-X3D-Profile bei 85 °C. Alte gespeicherte Wasserpunkte mit Endwert um 45 bis 50 °C werden beim Upgrade niemals als CPU-Kurve übernommen. Sie werden durch die passende neue CPU-Kurve ersetzt.

Die Wassertemperatur bleibt unabhängig als Sicherheitsgröße mit Warnung bei 42 °C, kritischem Grenzwert bei 50 °C und optionaler 100-Prozent-Umschaltung erhalten. Nach fünf aufeinanderfolgenden CPU-Sensorfehlern setzt die Software aktive Kurvenkanäle vorsorglich auf 75 Prozent. Beim echten Beenden – nicht beim Minimieren in den Tray – schreibt die Anwendung konservative autonome Flüssigkeitstemperaturkurven in die Kraken, weil eine CPU-Softwarekurve ohne laufenden Prozess nicht weiterregeln kann.

## Version 3.0.4 INTERN

Das Corsair-/OpenLinkHub-Modul erhält erstmals direkte Gerätesteuerung innerhalb der gemeinsamen Oberfläche. Die App liest vorhandene Temperatur- und RGB-Profile sowie Geräte- und Kanalfähigkeiten aus der lokalen API. Für passende Geräte stehen Kühlprofile/manuelle Leistung, RGB-Profil, Helligkeit, Kanalbezeichnung, LCD-Ausrichtung, Maus-DPI und -Optionen, Tastaturprofile und gerätespezifische Werte sowie Headset-ANC/Sidetone bereit.

Die Schreibseite bleibt beim Start immer gesperrt und muss ausdrücklich für die aktuelle Programmsitzung bestätigt werden. Bei zwei gleichzeitig aktiven OpenLinkHub-Diensten oder nicht erreichbarer Loopback-API ist keine Freigabe möglich. Das Hilfsmodul besitzt eine feste Zuordnung aus Aktionsnamen zu dokumentierten API-Pfaden und baut jede Nutzlast nach strenger Typ-, Bereichs- und Textprüfung neu auf. Weder die GUI noch ein Kommandozeilenargument können einen beliebigen API-Pfad bestimmen.

Vollständige Corsair-Seriennummern werden weiterhin nicht an Oberfläche oder Log übergeben. Die Statusabfrage erzeugt eine SHA-256-Steuerkennung; unmittelbar vor einem Befehl ordnet das Hilfsmodul diese gegen die aktuelle lokale Geräteliste eindeutig zu. Damit kann die App das Gerät lokal steuern, ohne seine vollständige Kennung in kopierbaren Diagnosedaten zu führen.

Komplexe Makrofolgen, freie Tastenbelegungen, der vollständige RGB-Editor sowie das Anlegen und Hochladen neuer LCD-Medien verblieben in dieser Version zunächst im OpenLinkHub-Web-Dashboard. Die NZXT-Kraken- und GIF-Funktionen blieben unverändert.

## Version 3.0.3 INTERN

Die sichtbare Modusmarkierung in der Kühlungsansicht verwendet keinen `checkable`-Zustand der Qt-Schaltfläche mehr. Dieser Zustand wechselte bereits beim Klick und konnte deshalb während des asynchronen Gerätebefehls kurz den falschen Modus beziehungsweise eine kaum lesbare Theme-Farbe zeigen. Stattdessen erhalten die vier Schaltflächen jetzt eine explizite Eigenschaft `coolingState`. Nur der zuletzt erfolgreich auf die Kraken übertragene Modus wird fest grün dargestellt; Normal-, Hover- und Gedrückt-Zustand besitzen jeweils ausdrücklich definierte Farben.

Die Änderung ist rein visuell und zustandsbezogen. Liquidctl-Befehle, Kurvenvalidierung, Profile und die koordinierte USB-Übergabe bei laufender Animation bleiben unverändert. Während ein neuer Befehl läuft oder fehlschlägt, bleibt der vorher bestätigte Modus sichtbar aktiv.

Der reale Hardwaretest von 3.0.2 bestätigt zusätzlich die in 3.0.2 eingeführte Kurvenumschaltung: Bei laufender 25-FPS-Hardwareanimation wurde die Lüfterkurve `25/25, 30/35, 35/50, 40/75, 45/100` übertragen und dieselbe Animation nach 258 Millisekunden aus dem bestehenden Cache fortgesetzt. Die Schnellprofile Pumpe/Lüfter `45/35`, `100/100` und erneut `45/35` wurden nach 351, 335 beziehungsweise 317 Millisekunden fortgesetzt. Der Stream blieb bei ungefähr 26,3 Hz mit 37,8 bis 38,8 Millisekunden Uploadzeit; es gab keine LCD-Frame-Sprünge, übersprungenen Transportframes, Watchdog- oder Sicherheitsstopps. Die liquidctl-Hinweise zum vorhandenen `nzxt_kraken3`-Kernel-Treiber waren Warnmeldungen, keine fehlgeschlagenen Befehle.

## Version 3.0.2 INTERN

Pumpe und Radiatorlüfter besitzen jetzt jeweils eine eindeutige Umschaltung zwischen **Manuell aktivieren** und der passenden **Hardwarekurve aktivieren**. Der manuelle Schalter überträgt den aktuellen Prozentwert als feste Drehzahl. Der Kurvenschalter prüft die angezeigten Punkte mit den bestehenden Sicherheitsregeln und überträgt die vollständige Wassertemperaturkurve. Erst ein erfolgreich abgeschlossener Kraken-Schreibbefehl markiert den neuen Modus als aktiv.

Die Modusanzeige ist mit allen vorhandenen Schreibwegen verbunden: manuelle Anwenden-Knöpfe, einzelne Kurven, Schnellprofile, Sicherheitsprofil, gespeicherte Profile und CPU-Assistenz aktualisieren denselben Zustand. Bei einer laufenden GIF- oder Hardwareanimation benutzen beide neuen Schalter die PAUSE-/RESUME-USB-Übergabe aus 3.0.1; es entsteht kein paralleler Kraken-Schreiber.

Der reale Hardwaretest von 3.0.1 an der NZXT Kraken 2023 mit Firmware 2.0.0 bestätigt die Übergabe für feste Werte. Bei laufender 25-FPS-Hardwareanimation wurden der Radiatorlüfter auf 100 Prozent und die Pumpe auf 100 Prozent gesetzt. Die Animation setzte sich nach 240 beziehungsweise 251 Millisekunden aus dem bestehenden Cache fort. Der Stream blieb bei ungefähr 26,3 Hz, ohne LCD-Frame-Sprünge, Watchdog- oder Sicherheitsstopp. Die liquidctl-Hinweise zum vorhandenen `nzxt_kraken3`-Kernel-Treiber waren Warnmeldungen, keine fehlgeschlagenen Befehle.

## Version 3.0.1 INTERN

Die wichtigste Änderung ist die koordinierte Kühlungssteuerung bei laufender Kraken-GIF- oder Hardwareanimation. Ein zweiter Prozess schreibt weiterhin niemals parallel auf dieselbe Kraken. Stattdessen führt die App eine kurze Eigentumsübergabe durch:

1. Die GUI sendet `PAUSE` an den langlebigen Streamer.
2. Der Streamer beendet den aktuellen vollständigen Frame, schließt HID- und Bulk-Verbindung und bestätigt `paused`.
3. Die GUI überträgt exklusiv feste Pumpen-/Lüfterwerte, Kurven oder ein Kühlprofil über liquidctl Direct Access.
4. Erst wenn die gesamte serielle Befehlswarteschlange leer ist, sendet die GUI `RESUME`.
5. Der gleiche Streamer verbindet sich erneut, primt die bei der Pause vorgemerkte Cachephase zweimal und setzt seinen bereits vorbereiteten RGB565-Stream fort.

Der GIF-Prozess und sein Framecache werden dabei nicht beendet. Die Anzeige kann für die Dauer des liquidctl-Befehls kurz stehen, muss aber nicht neu decodiert oder vollständig neu gerendert werden. Die Übergabe besitzt getrennte Zeitlimits für USB-Freigabe und Wiederaufnahme. Fehler führen zum bestehenden Sicherheitsstopp und zur Wiederherstellung der Flüssigkeitstemperaturanzeige.

Unterstützt werden manuelle Pumpen-/Lüfterwerte, einzelne Pumpen-/Lüfterkurven, Schnellprofile, das Sicherheitsprofil, gespeicherte Kühlprofile und der vorhandene CPU-Assistenz-Schreibpfad. Normale Kraken-Statusabfragen bleiben während der Animation pausiert; die Wassertemperatur ist deshalb weiterhin der letzte sichere Wert. Eine sichere, autonom in der Kraken gespeicherte Hardwarekurve bleibt Voraussetzung.

## Version 3.0.0 INTERN

Diese Version ist der Übergang von Kraken Control 2.9.23 zu Open Hardware Control:

- linke, hierarchische Navigation statt sichtbarer Haupt-Tabs
- automatische Hardwareerkennung beim Start
- nicht erkannte Gerätemodule standardmäßig ausgeblendet
- Einstellung **„Nicht erkannte Geräte/Module anzeigen“**
- vollständiges NZXT-Kraken-Modul aus 2.9.23 mit Kühlung, RGB, LCD, Profilen, Sprachen und den abgesicherten LCD-Experimenten
- neues Corsair-/OpenLinkHub-Modul
- Erkennung von RPM-Installation sowie Benutzer- und Systemdienst
- ausschließlich lokale API unter `http://127.0.0.1:27003`
- Geräteliste und Telemetrie aus `GET /api/devices/`
- Start, Stopp und Neustart ausschließlich für `OpenLinkHub.service` im Benutzerkontext
- direkter Aufruf des lokalen OpenLinkHub-Web-Dashboards
- klare Warnung bei Systemkontext oder zwei gleichzeitig aktiven Diensten
- automatische Übernahme vorhandener Kraken-Control-Einstellungen beim ersten Start

## Navigationsmodell

Die Hauptbereiche sind hierarchisch angeordnet:

1. Übersicht
2. Geräte
   - NZXT Kraken 2023
     - Kühlung
     - RGB
     - LCD
   - Corsair · OpenLinkHub
3. Profile
4. Einstellungen
5. Diagnose
   - Log
   - Über

Gerätefamilien erscheinen nur, wenn passende Hardware, ein passender Dienst oder eine lokale API erkannt wurde. Für Entwicklung und Fehlersuche lassen sich alle Module einblenden.

## OpenLinkHub-Sicherheitsgrenze

Open Hardware Control spricht OpenLinkHub nur über eine validierte Loopback-Adresse an. Externe Hosts, HTTPS-Adressen, Zugangsdaten im URL-Text und API-Unterpfade werden vom Integrationsmodul abgelehnt. Seriennummern werden in der Oberfläche nur mit den letzten vier Zeichen dargestellt.

Seit Version 3.0.4 werden ausschließlich dokumentierte, fest freigegebene Corsair-Schreibaktionen verwendet. Version 3.0.9 ergänzt die dokumentierte Maustastenbelegung und eine begrenzte, fensterlokale Makroaufnahme. Nicht sicher aus der allgemeinen Geräteliste ableitbare Funktionen bleiben im lokalen OpenLinkHub-Web-Dashboard.

Dienstaktionen sind auf `systemctl --user` begrenzt. Der systemweite Dienst wird niemals automatisch angehalten, deaktiviert oder überschrieben. Bei einer Migration in den Benutzerkontext muss zuerst sichergestellt werden, dass nur eine OpenLinkHub-Instanz gleichzeitig auf die Hardware zugreift.

## NZXT-Modul

Der Funktionsstand der Kraken-Control-Version 2.9.23 bleibt enthalten:

- Kraken-Wassertemperatur, Pumpe und Radiatorlüfter
- feste Werte und softwaregeregelte CPU-Temperaturkurven über liquidctl Direct Access
- AMD-AM5-Profile mit eigenen Pumpen- und Lüfterkurven
- unabhängige Wassertemperatur-Sicherheitsüberwachung und autonomer Hardware-Fallback beim echten Beenden
- separater NZXT 2023 RGB Controller
- statische Bilder, Uhr, Live-Hardwaredesigns und animierte LCD-Designs
- CAM-naher, exklusiver Firmware-2.x-Rohbildpfad mit ACK-Prüfung, Watchdog und Sicherheitsfallback
- CPU-/GPU-Livewerte im isolierten Renderprozess
- Profile, vier Oberflächensprachen, adaptive Skalierung, Hintergrunddesigns und Diagnoseprotokoll

Die technische Vorgängerdokumentation `Kraken_Control_Projekt.md` und `USB_CAPTURE_FINDINGS.md` bleiben als Modulhistorie vollständig im Entwicklerpaket.

## Installation und Aktualisierung

```bash
chmod +x install.sh
./install.sh
```

Start:

```bash
~/.local/bin/open-hardware-control
```

Der bisherige Befehl `kraken-control` bleibt als Kompatibilitätsstarter erhalten. Das Installationsskript entfernt nur den alten Menüeintrag, nicht die frühere Programmdatei. Dadurch bleibt eine manuelle Rückkehr zur Vorgängerversion möglich.

## Noch zu testen

- 3.0.9 beim echten Beenden, Abmelden und Neustarten mit laufendem GIF prüfen: Nach USB-Freigabe muss die originale Wassertemperaturanzeige erscheinen
- normales Schließen in den Tray prüfen: Animation und CPU-Kurvenregelung müssen weiterlaufen und die Originalanzeige darf noch nicht erzwungen werden
- grafische Ansicht mit den tatsächlich angeschlossenen Corsair-Mausmodellen prüfen; gemeldete Belegungen und Hotspotpositionen vergleichen
- 3.0.6-Verhalten beim echten Plasma-Autostart erneut prüfen: Fenster muss im Tray bleiben und der gespeicherte LCD-/GIF-Modus darf frühestens fünf Sekunden nach Programmstart beginnen
- vorhandenes 3.0.5-Gesamtprofil mit ausgewählter GIF-Datei prüfen; die Animation muss ohne erneutes Profilaktualisieren automatisch migriert und gestartet werden
- normales Abmelden/Neustarten mit laufendem GIF prüfen; der nächste Start darf nicht fälschlich den LCD-Absturzfallback aktivieren

- OpenLinkHub 0.9.0 auf dem Zielsystem im aktuell aktiven Systemkontext erkennen
- Anzeige der tatsächlich angeschlossenen Corsair-Geräte und ihrer Kanalwerte
- Migration zum Benutzerdienst anhand der offiziellen OpenLinkHub-Anleitung
- Benutzeraktionen Start, Stopp und Neustart nach vorhandener User-Service-Installation
- gleichzeitige Nutzung des NZXT- und OpenLinkHub-Moduls ohne USB-Konflikte
- direkte OpenLinkHub-Steuerung an den tatsächlich angeschlossenen Corsair-Geräten prüfen und gemeldete Gerätefelder protokollieren
- überprüfen, welche Maus-, Tastatur- und Headset-Fähigkeiten OpenLinkHub 0.9.0 je Modell in `/api/devices/` ausgibt
- die neue feste grüne Aktivfarbe beim mehrfachen Wechsel zwischen Manuell und Kurve in hellem, dunklem und eigenem Akzent-Theme visuell prüfen
- 3.0.5 an der realen Kraken prüfen: CPU-Kurven für Pumpe und Lüfter einzeln und gemeinsam aktivieren
- Lastwechsel des Ryzen 7 9800X3D prüfen und Logwerte für Glättung, Hysterese und USB-Pausen vergleichen
- CPU-Kurvenregelung während eines 25-FPS-GIFs mindestens zehn Minuten prüfen; die Animation darf nur bei relevanten Prozentänderungen kurz pausieren
- echtes Beenden prüfen: konservative Wasser-Hardwarekurven müssen danach autonom weiterlaufen; Neustart muss die gespeicherten CPU-Modi wieder übernehmen
- prüfen, dass die Aktivmarkierung bei einem absichtlich fehlgeschlagenen Gerätebefehl im vorher bestätigten Zustand bleibt

## Lizenz und Unabhängigkeit

Open Hardware Control steht unter GPL-3.0-or-later. OpenLinkHub und liquidctl sind eigenständige Open-Source-Projekte und keine Bestandteile dieses Quellcodes. Produktnamen dienen ausschließlich der sachlichen Kompatibilitätsangabe. Das Projekt ist nicht offiziell mit NZXT, Corsair, OpenLinkHub oder OpenAI verbunden.

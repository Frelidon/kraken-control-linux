# Kraken Control 2.9.6 – LCD-Uhr-Hotfix

- GitHub-Veröffentlichungsstruktur, CI, Issue-/PR-Vorlagen und reproduzierbarer Release-Build für den ersten öffentlichen Quellcode-Release ergänzt.
- Der Über-Hinweis zum Projekt-Repository wurde so formuliert, dass er auch nach der Veröffentlichung nicht veraltet ist.
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

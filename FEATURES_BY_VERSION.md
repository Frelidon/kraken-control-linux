# Funktionsübersicht nach Version

| Version | Erstmals hinzugekommene Hauptfunktionen |
|---|---|
| 1.0 | Erste Grundsteuerung der NZXT Kraken über liquidctl. |
| 2.0 | PySide6-Oberfläche, Live-Status, feste Pumpen-/Lüfterwerte, Schnellprofile, Kurven, Sicherheitsumschaltung, RGB, LCD-Bilder, Einstellungen, Autostart, Tray, Installer und Deinstaller. |
| 2.1 | Serielle asynchrone QProcess-Warteschlange; Entfernung des absturzanfälligen QThreadPool/QRunnable-Aufbaus. |
| 2.2 | Eindeutige LCD-Einzelübertragung und optionaler Wiederholungs-Fallback. |
| 2.3 | LCD-Uhr, runde Vorschau, Frelidon-Branding, Über-Bereich, GPL-Lizenz, Diagnosewerkzeug und englische Grunddokumentation. |
| 2.3.1 | Sicherheitsbestätigungen, sichere Kurvenprüfung, 65/65-Standardprofil, stärkere Anonymisierung und SECURITY.md. |
| 2.4 | Transparente Links zu Websites, Quellcode und Lizenzen; offizieller NZXT-Gerätelink. |
| 2.5 | Klare Beschränkung auf Kraken, zugehörige Radiatorlüfter, LCD und separaten NZXT-RGB-Controller. |
| 2.6 | Grafischer Kurveneditor, Live-Temperaturmarker, Hell/Dunkel/System und Hex-Akzentfarben. |
| 2.7 | Tastaturbedienung, AMD-AM5-Profile, CPU-Temperatur und -Assistenz, udev-Reparatur und dynamische Komponentenstände. |
| 2.7.1 | Direct-Access-Hotfix für Pumpen- und Lüfterkurven. |
| 2.8 | Expertenmodus, Anzeige des aktiven Kühlmodus und automatisches erneutes Senden der LCD-Uhr. |
| 2.8.1 | Abhängigkeitsprüfung vor PySide6-Start und kontrollierte DNF-Installation. |
| 2.9 | Ersteinrichtungsassistent, zwölf prozedurale Animationen, adaptive DPI-/Monitorlayouts, kategorisierte Profile, Import/Export, Startprofile und vollständiger Quellcode-Snapshot. |
| 2.9.1 | CPU-Offscreen-Renderer und getrennte Hintergrund-/Inhaltsebenen; vollständigeres Klick-, Änderungs-, Menü-, Tastatur- und Navigationsprotokoll mit Log-Export. |
| 2.9.2 | Scrollbare Einstellungen, größeres Hauptfenster und einmalige Layoutmigration für bestehende Installationen. |
| 2.9.3 | Light-Theme-/Hintergrund-Hotfix für stabile Ebenenreihenfolge und RGB32-Rendering. |
| 2.9.4 | Animationen lassen sich nach dem Ausschalten wieder aktivieren; letztes Thema bleibt erhalten. |
| 2.9.5 | Direct Access für alle Kühlungswrites, stiller Hintergrundbetrieb bei Berechtigungsfehlern und 10.000-Zeichen-Loglimit. |
| 2.9.6 | LCD-Uhr-Regression beim Start behoben und durch Regressionstest abgesichert. |

## Funktionen nach Kategorien

### Kühlung

- Live-Wassertemperatur, Pumpen- und Lüfterwerte – 2.0
- feste Werte und Schnellprofile – 2.0
- Temperaturkurven – 2.0
- grafischer Kurveneditor – 2.6
- AMD-AM5-CPU-Assistenz – 2.7
- Direct Access für Kurven – 2.7.1
- Expertenmodus und aktive Modusanzeige – 2.8
- kategorisierte Kühl- und Gesamtprofile – 2.9

### LCD

- statische Bilder, Helligkeit und Ausrichtung – 2.0
- eindeutiger Wiederholungs-Fallback – 2.2
- Uhr, Datum und runde Vorschau – 2.3
- automatisches erneutes Senden der Uhr – 2.8
- LCD- und Gesamtprofile – 2.9

### Design und Anzeige

- Hell, Dunkel, System und Hex-Akzent – 2.6
- Ersteinrichtungsassistent – 2.9
- zwölf animierte prozedurale Hintergründe – 2.9
- DPI-/Monitorerkennung, 16:10, 16:9, 21:9 und 32:9 – 2.9
- UI-Skalierung 80–180 Prozent – 2.9
- Design- und Gesamtprofile – 2.9
- sicherer CPU-Offscreen-Hintergrundrenderer – 2.9.1
- scrollbare Einstellungen und vergrößertes Hauptfenster – 2.9.2

### Installation und Dokumentation

- Installer, Desktopdatei und Deinstaller – 2.0
- Diagnosewerkzeug – 2.3
- Sicherheitsdokumentation – 2.3.1
- Software-, Quellcode- und Lizenzlinks – 2.4
- Komponentenstände – 2.7
- Abhängigkeitsinstallation – 2.8.1
- zusätzlicher Quellcode-Snapshot und Manifest – 2.9
- detailliertes Benutzeraktionsprotokoll und Log-Export – 2.9.1


### 2.9.4
- Reaktivierbare Hintergrundanimationen mit gespeichertem letzten Thema.

# Corsair-/OpenLinkHub-Integration in 3.0.9

## Unterstützter Umfang

Open Hardware Control erkennt eine lokale OpenLinkHub-Installation, den aktiven Dienstkontext und die lokale API. Es liest `GET /api/devices/`, zeigt Geräte, Firmware, Kanäle, Temperatur, Drehzahl, Profil und RGB-Bezeichnung an und öffnet das Web-Dashboard unter `http://127.0.0.1:27003`.

Die App kann einen bereits installierten Benutzerdienst starten, stoppen oder neu starten. Sie führt keine systemweiten Dienständerungen aus und installiert OpenLinkHub nicht selbst.

Nach ausdrücklicher Freigabe für die aktuelle Programmsitzung kann die App dokumentierte OpenLinkHub-Befehle für Kühlkanäle, RGB/LCD, Maus, Tastatur, Headset und Netzteil übertragen. Angezeigt werden nur erkannte Geräte und die von der API gemeldeten Kanäle beziehungsweise Profile. Der vollständige RGB-Editor und LCD-Mediendateien bleiben im Web-Dashboard.

## Grafische Mausansicht in 3.0.9

Für erkannte Corsair-Mäuse wählt die Anwendung eines von fünf eigenen schematischen SVG-Layouts: kompakt, ergonomisch, symmetrisch, Mehrknopf oder MMO. Diese Grafiken wurden vollständig für Open Hardware Control erstellt, stehen mit dem übrigen Projekt unter GPL-3.0-or-later und kopieren weder Herstellerfotografie noch OpenLinkHub-Bildmaterial.

Über den SVGs liegen anklickbare und per Tastatur erreichbare Hotspots. Eine Auswahl markiert gleichzeitig die Tabellenzeile mit Tastennummer, verständlicher Position und Funktion. Modellnamen wie Scimitar, M55/M75, M65/Dark Core/Ironclaw, Darkstar/Nightsabre, Katar und Harpoon werden einer geeigneten generischen Form zugeordnet. Die Darstellung ist ausdrücklich ein Orientierungsschema, kein maßstabgetreues Produktbild.

Soweit die lokale `/api/devices/`-Antwort Belegungscontainer enthält, übernimmt das Hilfsmodul höchstens 32 kurze Einträge. Unbekannte Rohfelder, lange Gerätekennungen und vollständige Seriennummern werden nicht an die Oberfläche weitergegeben. Liefert die installierte OpenLinkHub-Version keine auslesbare Belegung, werden die üblichen Grundfunktionen klar als Rückfallansicht gezeigt.

Ein Klick auf eine gemeldete Taste öffnet den Belegungsdialog. Unterstützt werden die offiziellen Zuweisungstypen Keine, Medien, DPI, Tastatur, Sniper-DPI, Maus und vorhandenes Makro. Originalfunktion, Gedrückthalten und Ausführen beim Loslassen werden ebenfalls übertragen. Fehlt ein von OpenLinkHub gemeldeter Tastenindex, bleibt die schematische Taste absichtlich nicht beschreibbar; die App rät keinen Index.

Der Makro-Recorder erfasst einzelne Tastendrücke und ihre Pausen nur innerhalb seines sichtbaren aktiven Dialogs. Er greift nicht systemweit auf Eingabegeräte zu und zeichnet keine Passwörter, Mausbewegungen oder gehaltenen Modifikatorkombinationen auf. Pro Aufnahme gelten höchstens 64 Tastenschritte und höchstens fünf Sekunden Pause je Schritt. Danach steht das Makro als vorhandenes OpenLinkHub-Makro für eine Maustaste bereit.

## System- und Benutzerkontext

Medienwiedergabe und virtuelles Audio benötigen laut OpenLinkHub-API-Dokumentation den Benutzerkontext. Bei erkanntem Systemdienst zeigt Open Hardware Control deshalb einen Migrationshinweis und verlinkt die offizielle Benutzerinstallation.

Vor dem Start des Benutzerdiensts muss der systemweite Dienst beendet und deaktiviert werden. Zwei aktive OpenLinkHub-Instanzen dürfen nicht gleichzeitig auf dieselbe Corsair-Hardware zugreifen.

## Datenschutz und Sicherheit

- API-Zugriff nur über IPv4-/IPv6-Loopback oder `localhost`
- keine Zugangsdaten in der API-Adresse
- maximal 4 MiB JSON-Antwort
- kurze Netzwerk- und Prozesszeitlimits
- Seriennummern nur als vierstelliger Suffix
- feste Aktionsliste statt frei wählbarer API-Pfade oder Methoden
- strenge Wertebereiche und erneute Zuordnung gegen die aktuelle lokale Geräteliste
- vollständige Seriennummern bleiben im Hilfsprozess; die GUI erhält nur Suffix und SHA-256-Steuerkennung
- Tastenbelegungen auf höchstens 32 bereinigte Kurzdatensätze begrenzt
- Makroaufnahmen auf 64 Einzeltasten mit begrenzten Pausen beschränkt
- Schreibfreigabe nur für die aktuelle Programmsitzung und Sperre bei Dienstkonflikt
- fest begrenzte User-Service-Aktionen

## Offizielle Quellen

- Projekt und Installation: <https://github.com/jurkovic-nikola/OpenLinkHub>
- API: <https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/api/README.md>
- Benutzerinstallation: <https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/install-user-space.sh>

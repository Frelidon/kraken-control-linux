# USB-Mitschnittauswertung – Kraken 2023 Firmware 2.0.0

Auswertung fortgeführt für Kraken Control **2.9.20 INTERN**, 12. August 2026

## Verwendete Mitschnitte

- `01_Rot_voll(1).pcap`
- `03_gruen_240(1).pcap`
- `04_blau_240(1).pcap`
- `05_Quadranten(1).pcap`
- `06_GIF_Rot_Blau(2).pcap`

Die großen PCAP-Dateien werden nicht in das Anwendungs- oder Entwicklerpaket kopiert. Diese Datei bewahrt die für die Weiterentwicklung relevanten Ergebnisse.

## Bestätigte Endpunkte

| Zweck | Endpunkt | Transfer | Richtung |
|---|---:|---|---|
| HID-Befehle | `0x01` | Interrupt | Host → Kraken |
| HID-Antworten/Status | `0x81` | Interrupt | Kraken → Host |
| LCD-Header und RGB565 | `0x02` | Bulk | Host → Kraken |

## Bestätigte Frame-Transaktion

| Schritt | Nutzdaten |
|---|---|
| Start | `36 01 00 01 06` in einem 64-Byte-HID-Bericht |
| Start-ACK | Präfix `37 01` |
| Bulk-Header | `12 fa 01 e8 ab cd ef 98 76 54 32 10 06 00 00 00 00 c2 01 00` |
| Bild | exakt 115.200 Byte RGB565 |
| Ende | `36 02` in einem 64-Byte-HID-Bericht |
| Ende-ACK | Präfix `37 02` |

`00 c2 01 00` ist die Little-Endian-Längenangabe für 115.200 Byte. Die Pixeldaten selbst entsprechen dem verifizierten RGB565-Big-Endian-Layout.

## Langer CAM-GIF-Mitschnitt

`06_GIF_Rot_Blau(2).pcap` enthält nach erneuter datensatzgenauer Auswertung:

- 342 Startbefehle `36 01`
- 342 passende Startantworten `37 01`
- 341 RGB565-Nutzdatenblöcke mit je 115.200 Byte
- 341 Endbefehle und Endantworten; die Aufzeichnung beginnt beziehungsweise endet außerhalb einer vollständigen Framefolge

Der kontinuierliche Hauptabschnitt enthält 339 Starts über 12,815 Sekunden und erreicht **26,375 Hz**. Eine ältere Projektnotiz hatte fragmentierte USBPcap-Datensätze fälschlich als vollständige Frames gezählt; die Werte hier stammen ausschließlich aus vollständigen 115.200-Byte-RGB565-Nutzdatenblöcken.

| Messwert | Ergebnis |
|---|---:|
| Start → Start, Mittel | 37,915 ms |
| Start → Start, Median | 37,464 ms |
| Start → Start, P90 | 39,017 ms |
| Start → Start, Maximum | 75,847 ms |
| vollständige Transaktion, Mittel | 37,509 ms |
| vollständige Transaktion, Median | 36,923 ms |
| vollständige Transaktion, P90 | 38,891 ms |
| vollständige Transaktion, Maximum | 39,313 ms |
| End-ACK → nächster Start, Median | 0,113 ms |
| End-ACK → nächster Start, Minimum | 0,070 ms |
| End-ACK → nächster Start, P90 | 0,595 ms |

Diese Werte bestätigen eine CAM-nahe effektive Rate. Nach einem passenden `37 02`-End-ACK beginnt CAM den nächsten Frame im Median nach 0,113 ms, im schnellsten beobachteten Fall nach 0,070 ms. Der Standardmodus behält deshalb 0,10 ms ACK-Schutz, verwendet seit 2.9.19 aber wieder den 26,667-Hz-CAM-Zieltakt und überträgt die vorbereiteten Phasen streng der Reihe nach. Ist ein 37,5-ms-Zeitfenster vollständig belegt, beginnt der nächste vollständige Frame nach dem ACK, ohne eine Bildphase zu überspringen. Der feste 25,6-Hz-Rückfallmodus behält 0,2 ms Schutzabstand.

## Gleichzeitige HID-Berichte

Während des CAM-Streams treten ungefragte Statusberichte mit Präfix `75 02` auf. Zusätzlich sendet CAM im langen Mitschnitt jeweils 78 Pumpen- und 78 Lüfterkurvenbefehle mit Präfix `72 01` beziehungsweise `72 02` zwischen Frame-Transaktionen.

Kraken Control 2.9.20 übernimmt diese Kurvenwiederholungen bewusst nicht. Vor dem Stream ist bereits eine Hardwarekurve in der Kraken gespeichert; sie läuft ohne weitere Hostbefehle weiter. Zusätzliche Status- oder Kühlbefehle aus einem zweiten Prozess würden den exklusiven Linux-Gerätezugriff komplizieren und waren im Video eine plausible Ursache für Stillstände und Teilbilder.

## liquidctl-1.16-Risiko

liquidctl 1.16.0 implementiert `_write_then_read()` als Senden plus blindes Lesen des nächsten Berichts. Ungefragte Statuspakete oder alte ACKs können dadurch einer falschen Anfrage zugeordnet werden. Der am 22. Juli 2026 geöffnete Upstream-PR [liquidctl #916](https://github.com/liquidctl/liquidctl/pull/916) beschreibt dasselbe Problem und schlägt vor, die Warteschlange vor dem Senden zu leeren und Antwortpräfixe zuzuordnen.

Kraken Control 2.9.20 verwendet diese Schutzidee ausschließlich im eigenen experimentellen Streamer:

- HID-Warteschlange vor `36 01` und `36 02` leeren
- bis zu zwölf Berichte lesen
- nur `37 01` beziehungsweise `37 02` akzeptieren
- fremde Berichte zählen
- bei ausbleibender passender Antwort abbrechen

Das systemweit installierte liquidctl wird dabei nicht verändert.

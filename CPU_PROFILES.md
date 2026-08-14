# AMD-AM5-Prozessorprofile in Open Hardware Control 3.0.9

Die Profile steuern ausschließlich die unterstützte NZXT-Kraken-Kühlung. Pumpen- und Lüfterkurve verwenden jetzt direkt die CPU-Temperatur. CPU-Tjmax und Kraken-Wassertemperatur bleiben getrennte Größen.

## Regeln

- Ryzen 9000, Ryzen 8000G und die aufgenommenen normalen Ryzen-7000-Modelle: AMD-Tjmax 95 °C, verstärkte Kühlung ab 80 °C, beide CPU-Kurven bei 90 °C auf 100 %.
- Ryzen 7000 X3D: AMD-Tjmax 89 °C, verstärkte Kühlung ab 75 °C, beide CPU-Kurven bei 85 °C auf 100 %.
- Zwischen den fünf CPU-Punkten wird linear interpoliert. Eine EMA glättet kurze Spitzen; steigende Werte reagieren schneller als fallende.
- Kraken-Flüssigkeit: Warnung standardmäßig 42 °C, kritisch 50 °C, optional bei kritisch automatisch 100 %.
- Beim echten Beenden der Anwendung werden konservative Flüssigkeitstemperaturkurven als autonomer Hardware-Fallback gespeichert.

## Enthaltene Einzelprofile

- Ryzen 9000 X3D: 9950X3D2, 9950X3D, 9900X3D, 9850X3D, 9800X3D
- Ryzen 9000: 9950X, 9900X, 9700X, 9600X, 9600
- Ryzen 8000G: 8700G, 8600G
- Ryzen 7000 X3D: 7950X3D, 7900X3D, 7800X3D, 7700X3D, 7600X3D
- Ryzen 7000: 7950X, 7900X, 7700X, 7600

## Primärquellen

- AMD Prozessorspezifikationen: https://www.amd.com/en/products/specifications/processors.html
- Linux k10temp: https://docs.kernel.org/hwmon/k10temp.html

Jedes Profil enthält zusätzlich die konkrete offizielle AMD-Produktseite im Quellcode. Profile sind konservative Anwendungsvorgaben und keine Garantie für jede Gehäuse-, Raum- oder Lastsituation.

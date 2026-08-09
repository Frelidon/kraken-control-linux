# AMD-AM5-Prozessorprofile in Kraken Control 2.9.6

Die Profile steuern ausschließlich die unterstützte NZXT-Kraken-Kühlung. CPU-Tjmax und Kraken-Wassertemperatur sind getrennte Größen.

## Regeln

- Ryzen 9000, Ryzen 8000G und die aufgenommenen normalen Ryzen-7000-Modelle: AMD-Tjmax 95 °C, verstärkte Kraken-Kühlung ab 80 °C, 100 % ab 90 °C.
- Ryzen 7000 X3D: AMD-Tjmax 89 °C, verstärkte Kraken-Kühlung ab 75 °C, 100 % ab 85 °C.
- Kraken-Flüssigkeit: Warnung standardmäßig 42 °C, kritisch 50 °C; Wasserkurven erreichen spätestens bei 45 °C 100 %.
- Die CPU-Assistenz verwendet 5 °C Hysterese und stellt anschließend die gewählten Wasserkurven wieder her.

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

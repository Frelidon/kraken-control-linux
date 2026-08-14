# AMD AM5 processor profiles in Open Hardware Control 3.0.9

The profiles only control the supported NZXT Kraken cooling hardware. Pump and radiator-fan curves now use CPU temperature directly. CPU Tjmax and Kraken liquid temperature remain separate quantities.

## Rules

- Ryzen 9000, Ryzen 8000G and listed standard Ryzen 7000 models: AMD Tjmax 95 °C, stronger cooling from 80 °C, both CPU curves at 100% by 90 °C.
- Ryzen 7000 X3D: AMD Tjmax 89 °C, stronger cooling from 75 °C, both CPU curves at 100% by 85 °C.
- The controller interpolates linearly between five CPU points. An EMA smooths brief spikes; rising demand reacts faster than falling demand.
- Kraken liquid: warning at 42 °C, critical at 50 °C, optional automatic 100% at the critical threshold.
- A clean application exit stores conservative liquid-temperature curves as an autonomous hardware fallback.

## Included profiles

- Ryzen 9000 X3D: 9950X3D2, 9950X3D, 9900X3D, 9850X3D, 9800X3D
- Ryzen 9000: 9950X, 9900X, 9700X, 9600X, 9600
- Ryzen 8000G: 8700G, 8600G
- Ryzen 7000 X3D: 7950X3D, 7900X3D, 7800X3D, 7700X3D, 7600X3D
- Ryzen 7000: 7950X, 7900X, 7700X, 7600

## Primary sources

- AMD processor specifications: https://www.amd.com/en/products/specifications/processors.html
- Linux k10temp: https://docs.kernel.org/hwmon/k10temp.html

Each profile also contains the corresponding official AMD product page in source code. Profiles are conservative application defaults, not a guarantee for every case, ambient temperature or workload.

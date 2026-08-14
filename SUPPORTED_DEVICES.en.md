# Supported devices – Open Hardware Control 3.0.9

## NZXT module

| Device | USB ID | Backend | Scope |
|---|---|---|---|
| NZXT Kraken 2023 | `1e71:300e` | liquidctl | liquid, pump, radiator fans, LCD |
| NZXT 2023 RGB Controller | `1e71:2012` | liquidctl | three RGB channels |

The reference device remains the NZXT Kraken RGB 360 (2023, Standard / Non-Elite) with firmware 2.0.0.

## Corsair through OpenLinkHub

Open Hardware Control displays devices reported by the locally installed OpenLinkHub service through `/api/devices/`; it does not maintain a separate fixed Corsair USB list. Validated controls added in version 3.0.4 remain available for reported cooling, RGB/LCD, mouse, keyboard and headset devices. Complex device-specific settings remain in the local dashboard.

Version 3.0.9 maps reported mice to original generic GPL SVG schematics. A physical button can be edited only when OpenLinkHub reports an unambiguous button index. None, media, DPI, keyboard, sniper-DPI, mouse and existing macro assignments are supported. The recorder creates bounded keyboard/delay macros only while its dialog has focus; complex sequences remain in the OpenLinkHub dashboard.

Real-hardware validation with OpenLinkHub 0.9.0 and the connected Corsair devices is still required. Firmware updates, motherboard controls, Open Radeon Control Center and untested direct Corsair USB writes are out of scope.

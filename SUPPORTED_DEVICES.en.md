# Supported devices - Version 2.9.6

## Tested

| Device | USB ID | Support | Official manufacturer page |
|---|---|---|---|
| NZXT Kraken RGB 360 (2023, Standard / Non-Elite; liquidctl: `NZXT Kraken 2023`) | `1e71:300e` | liquid temperature, pump, radiator fans, 240x240 LCD | [NZXT Kraken (2023) specifications](https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs) |
| NZXT 2023 RGB Controller | `1e71:2012` | separate RGB channels through liquidctl | [NZXT Kraken (2023) included fans and controllers](https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs) |

Additional official NZXT pages:

- [NZXT liquid coolers and CPU coolers](https://nzxt.com/collections/cpu-coolers)
- [NZXT website](https://nzxt.com/)

Tested combination: Kraken firmware `2.0.0`, liquidctl `1.16.x`, Nobara/Fedora Linux.

Further devices are considered supported only after hardware testing. The manufacturer links are factual product and documentation references; Kraken Control is not an official NZXT product.

## Deliberate scope boundary

Kraken Control controls only components that belong to the supported Kraken cooling system. This includes the Kraken pump and radiator fans reported or controlled through the Kraken device itself.

Motherboard fan headers, additional chassis fans, GPU fans and general system controls are not supported and are neither probed nor written by this application.

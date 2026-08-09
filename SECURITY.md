# Security – Kraken Control by Frelidon 2.9.6

## Supported version

Security fixes are currently developed for the latest public release only.

| Version | Supported |
|---|---|
| 2.9.6 | Yes |
| older releases | No; update first when possible |

## Project status

Kraken Control is an **experimental open-source beta**. It controls physical cooling hardware and is provided without warranty. It does not replace firmware-level protections, motherboard monitoring or normal system thermal safeguards.

## Security model

- The GUI runs as the normal desktop user and does not require the whole application to run as root.
- Hardware commands are passed directly to `liquidctl` via Qt `QProcess`, not through an interpolated shell command.
- The included udev rule is limited to the tested NZXT USB IDs and uses `0660` plus `uaccess`.
- Administrative actions use an explicit `pkexec` prompt.
- The application contains no telemetry, automatic cloud upload or silent remote-control feature.
- Diagnostic reports are generated locally and saved with restrictive permissions.

## Cooling safety

- Fixed pump values below 30% and fixed fan values below 20% require explicit confirmation.
- Curves may not slow down as temperature rises.
- A configured curve must reach 100% by the configured high-temperature end of the safe range.
- CPU assistance and background safety logic are software helpers only; they are not hardware fail-safes.
- Version 2.9.5 and later use `liquidctl --direct-access` for Kraken pump/fan writes on the tested setup to avoid non-writable kernel hwmon attributes.
- Repeated write failures in background mode are rate-limited and do not repeatedly interrupt fullscreen applications with modal repair dialogs.

## LCD

Repeated LCD uploads and the LCD clock remain experimental. The long-term behavior of frequent display-memory writes is not fully characterized for every firmware revision. Use repeat/fallback features only when needed.

## Profiles

Profile files are local JSON data and do not execute arbitrary commands. Imported hardware values still pass through Kraken Control's validation and safety paths. Review profiles from unknown sources before applying them.

## Diagnostics and privacy

`kraken-control-diagnostics` performs read-only collection. It attempts to redact home-directory names, usernames, hostnames, machine/boot IDs and device serial numbers. The in-app log also applies redaction and is capped at 10,000 visible characters. Always manually review any log or diagnostic report before publishing it.

## Reporting a vulnerability

Please do **not** post exploit details or private diagnostic data in a normal public issue.

If GitHub private vulnerability reporting is enabled for this repository, use the repository's **Security** reporting form. If that option is not available yet, open a minimal public issue asking the maintainer for a private contact method **without including the vulnerability details**.

Include, when safe to do so:

- affected Kraken Control version;
- affected hardware and firmware;
- impact and reproducibility;
- whether physical cooling behavior can be changed unexpectedly;
- a minimal proof of concept with personal data removed.

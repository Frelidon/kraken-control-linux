# Kraken Control by Frelidon v2.9.6

First public GitHub release.

## What changed

### LCD clock regression fixed

Version 2.9.5 still referenced the removed `clock_24h` widget when starting the LCD clock. That could raise a Python exception before the first clock frame was transmitted. Version 2.9.6 reads the selected value from `clock_format` and includes a regression test for this path.

### Direct Access for Kraken cooling writes

The 2.9.5 fixes remain included: fixed pump/fan output, cooling curves, quick profiles and CPU assistance use the tested `liquidctl --direct-access` path. This prevents the repeated `insufficient permissions` behavior seen when the kernel hwmon interface exposes status but not writable cooling attributes to the desktop user.

### Quiet background behavior

Permission failures while the app is in the background are logged and rate-limited instead of repeatedly opening modal repair dialogs over games or fullscreen applications.

### Logging improvements

- visible log capped at 10,000 characters;
- oldest complete lines are removed first;
- more detailed CPU/profile, LCD-clock, theme and display logging.

### UI/background fixes retained

This release also contains the 2.9.2–2.9.4 fixes for scrollable settings, light-theme rendering and animation reactivation.

## Tested hardware

- NZXT Kraken RGB 360 (2023 Standard / Non-Elite), USB `1e71:300e`, firmware `2.0.0`
- NZXT 2023 RGB Controller, USB `1e71:2012`, firmware `1.5.0`

See `SUPPORTED_DEVICES.md` for the exact supported scope.

## Important notes

Kraken Control is an independent experimental open-source project, not official NZXT software. Hardware-control changes should be tested cautiously. LCD repeat/clock uploads remain experimental.

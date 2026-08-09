# Contributing to Kraken Control by Frelidon

Thanks for helping improve Kraken Control.

## Before opening an issue

1. Check existing issues first.
2. Include the exact Kraken Control version.
3. Include the exact Kraken model and USB ID when hardware is involved.
4. For detection problems, run `kraken-control-diagnostics` and manually review the report before uploading it.
5. Never post passwords, private tokens, full serial numbers, personal email addresses or unrelated system logs.

## Project scope

Keep Kraken Control focused on supported NZXT Kraken cooling hardware. Motherboard, chassis and GPU fan control belongs in separate projects.

## Development rules

- Do not bypass the existing safety confirmations for cooling writes.
- Do not add telemetry, analytics or silent network uploads.
- Do not require the GUI itself to run as root.
- Do not add proprietary images, videos, fonts, logos or other assets without documented redistribution rights.
- Prefer `liquidctl` and documented Linux interfaces over custom raw USB protocols.
- Hardware-changing code must fail safely.

## Local checks

Run before a pull request:

```bash
./scripts/check_release.sh
```

The script compiles the Python source, validates shell syntax and runs the dependency-free static/stub tests.

## Pull requests

Explain:

- what changed;
- why it changed;
- how it was tested;
- whether real Kraken hardware was used;
- whether permissions, cooling, LCD or RGB behavior is affected.

By contributing, you agree that your contribution is provided under GPL-3.0-or-later.

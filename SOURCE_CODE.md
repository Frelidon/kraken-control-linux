# Source code and reproducibility

Kraken Control releases are intended to remain auditable and reproducible from the public repository.

For version 2.9.6 the repository contains:

- `kraken_control.py`;
- all installer, dependency, diagnostics and udev scripts;
- desktop entry template and original SVG icon;
- GPL-3.0-or-later license text;
- German and English documentation;
- dependency-free static and stub runtime tests;
- GitHub CI and release automation.

Running:

```bash
./scripts/build_release.sh
```

creates a release under `dist/` containing:

- `Kraken-Control-by-Frelidon-2.9.6-linux.zip`;
- `Kraken-Control-Source-v2.9.6.tar.gz`;
- `SHA256SUMS`.

The Linux ZIP itself also contains:

- `kraken_control_source_2_9_6.tar.gz` as a single-file source snapshot;
- `MANIFEST.sha256` with checksums for every packaged file except the manifest itself.

Build products, caches and Git metadata are not committed to the repository.

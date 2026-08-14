# Open Hardware Control 3.0.9 auf GitHub veröffentlichen

Repository: <https://github.com/Frelidon/kraken-control-linux>

## Suchbeschreibung und Topics

Empfohlene Repository-Beschreibung:

> Open-source NZXT Kraken LCD, pump, fan and RGB control for Linux with Corsair/OpenLinkHub integration.

Empfohlene GitHub-Topics:

`linux`, `nzxt`, `nzxt-kraken`, `kraken`, `kraken-lcd`, `aio-cooler`, `liquidctl`, `fan-control`, `lcd-display`, `hardware-control`, `openlinkhub`, `corsair`, `python`, `pyside6`, `fedora`

Mit angemeldeter GitHub CLI:

```bash
gh repo edit Frelidon/kraken-control-linux \
  --description "Open-source NZXT Kraken LCD, pump, fan and RGB control for Linux with Corsair/OpenLinkHub integration." \
  --add-topic linux \
  --add-topic nzxt \
  --add-topic nzxt-kraken \
  --add-topic kraken \
  --add-topic kraken-lcd \
  --add-topic aio-cooler \
  --add-topic liquidctl \
  --add-topic fan-control \
  --add-topic lcd-display \
  --add-topic hardware-control \
  --add-topic openlinkhub \
  --add-topic corsair \
  --add-topic python \
  --add-topic pyside6 \
  --add-topic fedora
```

## Release lokal prüfen

```bash
./scripts/check_release.sh
sudo apt install rpm
./scripts/build_release.sh 3.0.9
cd dist
sha256sum -c SHA256SUMS
```

Erwartete Dateien:

- `open_hardware_control_v3_0_9.zip`
- `open-hardware-control_3.0.9_all.deb`
- `open-hardware-control-3.0.9-1.noarch.rpm`
- `open-hardware-control-3.0.9-source.tar.gz`
- `Entwicklerpaket 3.0.9.zip`
- `SHA256SUMS`

## Veröffentlichung

Nach einem grünen Pull Request und sauberem `main`:

```bash
git tag -a v3.0.9 -m "Open Hardware Control v3.0.9"
git push origin v3.0.9
```

Der Workflow `.github/workflows/release.yml` führt die Tests erneut aus, baut sämtliche Release-Dateien aus demselben Tag und erstellt anschließend das öffentliche GitHub-Release mit `docs/RELEASE_NOTES_v3.0.9.md`.

Kontrolle:

```bash
gh release view v3.0.9 --web
```

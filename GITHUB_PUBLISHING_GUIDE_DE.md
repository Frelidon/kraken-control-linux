# Kraken Control by Frelidon 2.9.6 auf GitHub veröffentlichen

Diese Anleitung ist für das vorbereitete Repository-Paket gedacht. Du brauchst kein GitHub-Token in ChatGPT einzufügen und sollst Passwörter oder Tokens niemals in Issues, Logs oder Chatnachrichten posten.

## Was das Paket schon vorbereitet

- GPL-3.0-or-later-Lizenz
- deutsche und englische README
- Changelog, Security-, Privacy-, Contribution- und Support-Dokumentation
- GitHub Issue Forms und Pull-Request-Vorlage
- Dependabot für GitHub Actions
- CI für Python 3.13 und 3.14
- automatischer Release-Workflow für Tags wie `v2.9.6`
- lokale Release-Prüfung und reproduzierbarer Release-Build
- Quellcode-Snapshot und SHA-256-Prüfsummen im Release

## 1. Repository-Paket entpacken

```bash
cd ~/Downloads
unzip Kraken-Control-GitHub-Repository-v2.9.6.zip
cd kraken-control-linux
```

## 2. Git und GitHub CLI installieren

Auf Nobara/Fedora:

```bash
sudo dnf install git gh
```

## 3. Bei GitHub anmelden

```bash
gh auth login --web
```

Bei den Abfragen kannst du `GitHub.com` und für Git-Operationen `HTTPS` wählen. Die Anmeldung erfolgt im Browser.

Prüfen:

```bash
gh auth status
```

## 4. Git-Name und Commit-E-Mail einstellen

Name:

```bash
git config --global user.name "Frelidon"
```

Für die E-Mail solltest du entweder eine E-Mail verwenden, die deinem GitHub-Konto zugeordnet ist, oder deine GitHub-`noreply`-Adresse aus **GitHub → Settings → Emails** verwenden.

Beispiel:

```bash
git config --global user.email "DEINE_GITHUB_NOREPLY_ADRESSE"
```

Prüfen:

```bash
git config --global user.name
git config --global user.email
```

## 5. Vor dem Upload lokal prüfen

```bash
./scripts/check_release.sh
```

Erwartete letzte Zeile:

```text
All repository release checks passed.
```

Optional den Release-Build schon lokal testen:

```bash
./scripts/build_release.sh
```

Die Dateien liegen danach unter `dist/`.

## 6. Öffentliches GitHub-Repository erstellen und hochladen

Der vorbereitete Helfer erkennt automatisch deinen angemeldeten GitHub-Benutzernamen und erstellt standardmäßig das Repository `kraken-control-linux`:

```bash
./scripts/publish_github.sh
```

Das Skript zeigt die endgültige URL und fragt **vor** dem öffentlichen Erstellen noch einmal nach. Es überschreibt absichtlich kein bereits existierendes Repository.

Anderer Repository-Name, falls gewünscht:

```bash
./scripts/publish_github.sh mein-repository-name
```

Beim Publish werden die echte Repository-URL in die README-/Link-Dokumentation eingetragen, Git initialisiert, der erste Commit erstellt, das öffentliche Repository angelegt, `main` gepusht, Themen gesetzt und die vorbereiteten Labels angelegt.

## 7. GitHub-Seite kontrollieren

Öffne anschließend dein Repository im Browser und prüfe:

- README wird korrekt angezeigt;
- Lizenz wird von GitHub als GPL erkannt;
- **Actions** zeigt den Workflow `CI`;
- der erste CI-Lauf ist grün;
- unter **Issues → New issue** erscheinen Bug-, Feature- und Hardware-Formulare.

Solange CI rot ist, noch keinen Release veröffentlichen.

## 8. Sicherheit auf GitHub aktivieren

Für ein öffentliches Open-Source-Projekt empfehlenswert:

1. Im Repository **Security and quality** öffnen.
2. **Private vulnerability reporting** aktivieren, damit Sicherheitsforscher Details privat melden können.
3. Die bereits vorhandene `SECURITY.md` kontrollieren.
4. Optional einen Branch-Ruleset beziehungsweise Branch Protection für `main` einrichten, wenn später weitere Mitwirkende dazukommen. Mindestens CI vor dem Merge verlangen.

GitHub führt Secret Scanning für öffentliche Repositories automatisch aus; Push Protection kann zusätzlich vor versehentlich gepushten Zugangsdaten schützen.

## 9. Version 2.9.6 veröffentlichen

Wenn der CI-Lauf auf `main` erfolgreich ist:

```bash
./scripts/create_release.sh
```

Das Skript:

1. prüft den Quellstand erneut;
2. baut lokal die Release-Dateien;
3. fragt vor dem Tag noch einmal nach;
4. erstellt den signierten/annotierten Git-Tag `v2.9.6`;
5. pusht den Tag zu GitHub.

Der GitHub-Release-Workflow erstellt daraus automatisch den öffentlichen Release und lädt die Dateien aus `dist/` hoch.

Erwartete Release-Assets:

```text
Kraken-Control-by-Frelidon-2.9.6-linux.zip
Kraken-Control-Source-v2.9.6.tar.gz
SHA256SUMS
```

GitHub stellt außerdem automatisch seine eigenen Source-Code-Archive für den Tag bereit.

## 10. Release kontrollieren

```bash
gh release view v2.9.6 --web
```

Kontrolliere im Browser:

- Tag `v2.9.6`;
- Release-Titel;
- Release Notes;
- alle drei Assets;
- SHA-256-Datei;
- dass v2.9.6 als aktueller Release angezeigt wird.

## Falls der automatische Release-Workflow fehlschlägt

Zuerst unter **Actions** die Fehlermeldung lesen. Nichts löschen, bevor die Ursache klar ist.

Wenn der Tag bereits existiert, der Build lokal erfolgreich war und nur das Erstellen des GitHub-Releases fehlgeschlagen ist, kannst du nach der Fehlerbehebung die Assets auch manuell erstellen:

```bash
./scripts/build_release.sh
```

und anschließend:

```bash
gh release create v2.9.6 dist/* \
  --title "Kraken Control v2.9.6" \
  --notes-file docs/RELEASE_NOTES_v2.9.6.md \
  --verify-tag
```

## Für spätere Updates

Für 2.9.7, 3.0.0 usw. zuerst Versionen/Changelog aktualisieren und testen, Änderungen committen und pushen. Danach den neuen Tag erstellen. Ein GitHub Release basiert auf einem Git-Tag; veröffentliche deshalb niemals denselben Versions-Tag für unterschiedlichen Quellcode erneut.

## Was du nicht veröffentlichen solltest

- persönliche Logs ohne Prüfung
- Tokens, Passwörter oder SSH/private Schlüssel
- Seriennummern und unnötige Hardwarekennungen
- fremde NZXT-Logos oder Medien ohne Lizenz
- alte Test-ZIPs im Git-Repository
- lokale Profile oder persönliche Konfigurationsdateien

Das Repository-Paket enthält dafür bereits `.gitignore`, Datenschutzregeln und einen einfachen Secret-/Pfad-Check.

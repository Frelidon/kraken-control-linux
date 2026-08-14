# Entwicklerpaket 3.0.9

Das Entwicklerpaket enthält:

- den vollständigen editierbaren Quellbaum von Open Hardware Control 3.0.9
- alle Python-, Shell-, Test-, Dokumentations- und GitHub-Workflow-Dateien
- den reproduzierbaren Builder für ZIP, DEB, RPM, Quellarchiv und Prüfsummen
- die fünf eigenen OpenLinkHub-Maus-SVGs und ihre Zuordnungslogik
- zentrale Projekt- und OpenLinkHub-Dokumentation
- SHA-256-Prüfsummen

Die Anwendung wird direkt aus `kraken_control.py` gestartet. Der Dateiname bleibt intern erhalten, weil er das vollständige historische NZXT-Modul trägt; der sichtbare Programmname und der installierte Starter lauten `Open Hardware Control` beziehungsweise `open-hardware-control`.

Kompletter Release-Test:

```bash
./scripts/check_release.sh
```

Einzelne Regressionstests:

```bash
python3 tests/test_security_static.py
python3 tests/test_runtime_logic_stub.py
python3 tests/test_gif_streamer_logic.py
python3 tests/test_lcd_designs.py
python3 tests/test_sensors.py
python3 tests/test_live_render_worker.py
python3 -m unittest tests/test_gif_cooling_handoff.py -v
python3 -m unittest tests/test_openlinkhub_integration.py -v
python3 -m unittest tests/test_openlinkhub_mouse_visuals.py -v
```

Für einen echten GUI-Test werden PySide6 und eine Desktop-Sitzung benötigt. Schreibtests des NZXT- oder OpenLinkHub-Moduls dürfen nur an der passenden Testhardware erfolgen. Die OpenLinkHub-Schreibaktionen sind fest freigegeben, validiert und standardmäßig bis zur Sitzungsbestätigung gesperrt.

Der Installer kann für einen isolierten Pakettest mit `OHC_INSTALL_HOME=/absoluter/testpfad ./install.sh` in ein separates Benutzerverzeichnis schreiben. Ohne diese optionale Variable verwendet er unverändert das normale Benutzerverzeichnis.

Alle Release-Artefakte werden mit folgendem Befehl gebaut. Auf Debian/Ubuntu muss zusätzlich das Paket `rpm` für den Fedora-RPM-Build installiert sein:

```bash
./scripts/build_release.sh 3.0.9
```

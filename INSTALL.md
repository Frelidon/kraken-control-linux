# Installation unter Linux

Diese Anleitung gilt für Open Hardware Control by Frelidon 3.0.9. Lade die gewünschte Datei zuerst von der [GitHub-Release-Seite](https://github.com/Frelidon/kraken-control-linux/releases/latest) in `~/Downloads`.

## Fedora und Nobara

Empfohlenes RPM-Paket:

```bash
cd ~/Downloads
sudo dnf install ./open-hardware-control-3.0.9-1.noarch.rpm
```

Alternativ das universelle ZIP verwenden. Die benötigten Pakete lauten:

```bash
sudo dnf install liquidctl python3-pyside6 python3-pillow qt6-qtsvg polkit
```

## Debian, Ubuntu und Linux Mint

Empfohlenes DEB-Paket:

```bash
cd ~/Downloads
sudo apt install ./open-hardware-control_3.0.9_all.deb
```

Alternativ das universelle ZIP verwenden. Die benötigten Pakete lauten:

```bash
sudo apt update
sudo apt install liquidctl python3-pyside6.qtwidgets python3-pyside6.qtsvg python3-pil policykit-1
```

## Arch Linux, Manjaro und EndeavourOS

```bash
sudo pacman -S --needed liquidctl pyside6 python-pillow qt6-svg polkit unzip
cd ~/Downloads
unzip open_hardware_control_v3_0_9.zip
cd open-hardware-control-3.0.9
chmod +x install.sh
./install.sh
```

## openSUSE Tumbleweed und Leap

```bash
sudo zypper install liquidctl python3-pyside6 python3-Pillow libQt6Svg6 polkit unzip
cd ~/Downloads
unzip open_hardware_control_v3_0_9.zip
cd open-hardware-control-3.0.9
chmod +x install.sh
./install.sh
```

Die verfügbaren Python-Paketnamen können sich zwischen Leap- und Tumbleweed-Versionen unterscheiden. Falls `zypper` einen Namen nicht findet, suche mit `zypper search pyside6`, `zypper search Pillow` und `zypper search liquidctl` nach dem Namen deiner installierten Ausgabe. Das Installationsskript zeigt fehlende Komponenten an und fügt keine fremden Paketquellen hinzu.

## Universelles Installationspaket

Für alle oben genannten Distributionen:

```bash
cd ~/Downloads
unzip open_hardware_control_v3_0_9.zip
cd open-hardware-control-3.0.9
chmod +x install.sh
./install.sh
```

Die vorhandene Version wird aktualisiert. Danach findest du **Open Hardware Control by Frelidon** im Anwendungsmenü.

Start im Terminal:

```bash
~/.local/bin/open-hardware-control
```

## NZXT-USB-Zugriff

Wenn die Kraken erkannt wird, Schreibbefehle aber wegen fehlender Rechte scheitern:

```bash
~/.local/share/open-hardware-control/install-udev-rule.sh
```

Danach die USB-Verbindung der Kraken neu herstellen oder den PC neu starten.

## Deinstallation

Beim universellen ZIP im entpackten Paketordner:

```bash
chmod +x uninstall.sh
./uninstall.sh
```

Bei RPM oder DEB:

```bash
sudo dnf remove open-hardware-control
```

oder:

```bash
sudo apt remove open-hardware-control
```

Persönliche Profile und Einstellungen im Benutzerverzeichnis werden bei einer normalen Paketentfernung nicht gelöscht.

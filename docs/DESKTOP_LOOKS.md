# Desktop-Look in Open Hardware Control

Dieses Modul ergänzt Open Hardware Control um einen neuen Menüpunkt **Desktop-Look**.

## Ziel

Der Benutzer kann auf Fedora KDE / Plasma 6 per Klick einen Desktop-Look anwenden:

- **Windows 11**: Fluent-KDE, Fluent-Icons, runde Fenster, Blur, zentrierter Taskleistenbereich.
- **macOS**: WhiteSur-KDE, WhiteSur-Icons, WhiteSur-Cursor, obere Menüleiste und Dock-ähnliche untere Leiste.
- **Wiederherstellen**: stellt das letzte automatisch erzeugte KDE-Backup wieder her.

## Dateien

- `scripts/desktop-look-fedora-kde.sh`
- `desktop_look_manager.py`

## Einbau in die bestehende PySide6-GUI

Minimaler Einbau in `kraken_control.py`:

```python
from desktop_look_manager import DesktopLookPage, show_desktop_look_dialog
```

### Variante A: als eigener Tab / eigene Seite

Wenn die Anwendung einen `QTabWidget` nutzt:

```python
self.tabs.addTab(DesktopLookPage(self), "Desktop-Look")
```

Wenn die Anwendung eine Seiten-Navigation mit `QStackedWidget` nutzt:

```python
self.desktop_look_page = DesktopLookPage(self)
self.stack.addWidget(self.desktop_look_page)
# Navigationsbutton: "Desktop-Look" -> self.stack.setCurrentWidget(self.desktop_look_page)
```

### Variante B: als Menüpunkt

Wenn es ein Menü `Ansicht` oder `Extras` gibt:

```python
desktop_look_action = QAction("Desktop-Look …", self)
desktop_look_action.triggered.connect(lambda: show_desktop_look_dialog(self))
tools_menu.addAction(desktop_look_action)
```

Oder mit dem Helper:

```python
from desktop_look_manager import create_desktop_look_action
create_desktop_look_action(self, tools_menu)
```

## Sicherheit

- Vor jeder Änderung wird ein Backup in `~/.local/state/open-hardware-control/desktop-look/backups/` angelegt.
- Das Theme-Skript ändert KDE/Plasma-Dateien im Benutzerprofil.
- Hardwareprofile, Lüfterkurven, RGB-Profile und LCD-Einstellungen werden nicht verändert.
- Die Funktion ist nur für Fedora KDE gedacht und zeigt in der GUI einen Hinweis, wenn kein Fedora-KDE erkannt wird.

## Release-Hinweis

Für die nächste Version sollte der Menüpunkt unter einem klaren Hauptbereich wie **Werkzeuge → Desktop-Look** oder **Einstellungen → Desktop-Look** erscheinen. Da es eine System-/Desktop-Optik-Funktion ist, sollte sie nicht unter NZXT, Corsair oder Geräte-Steuerung einsortiert werden.

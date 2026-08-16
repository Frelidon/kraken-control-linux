#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Frelidon contributors
"""Desktop look integration for Open Hardware Control.

This module provides a small PySide6 page/dialog that can be plugged into the
Open Hardware Control navigation as "Desktop-Look". It intentionally launches a
separate helper script because changing Plasma themes/panels is a desktop-level
operation and should not run inside the hardware-control event loop.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_TITLE = "Desktop-Look"
SCRIPT_NAME = "desktop-look-fedora-kde.sh"


def bundled_script_path() -> Path:
    """Return the most likely path of the bundled desktop-look helper."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "scripts" / SCRIPT_NAME,
        here / SCRIPT_NAME,
        Path("/usr/share/open-hardware-control/scripts") / SCRIPT_NAME,
        Path("/usr/local/share/open-hardware-control/scripts") / SCRIPT_NAME,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def is_fedora_kde() -> bool:
    os_release = Path("/etc/os-release")
    if not os_release.exists():
        return False
    text = os_release.read_text(encoding="utf-8", errors="replace").casefold()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "")
    kde_session = os.environ.get("KDE_FULL_SESSION", "")
    return "fedora" in text and ("KDE" in desktop or kde_session == "true")


class DesktopLookWorker(QThread):
    output = Signal(str)
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, mode: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode = mode

    def run(self) -> None:
        script = bundled_script_path()
        if not script.exists():
            self.failed.emit(f"Helper-Skript nicht gefunden: {script}")
            return

        if not os.access(script, os.X_OK):
            try:
                script.chmod(script.stat().st_mode | 0o755)
            except OSError as exc:
                self.failed.emit(f"Helper-Skript ist nicht ausführbar: {exc}")
                return

        args = [str(script)]
        if self.mode == "windows11":
            args.append("--windows11")
        elif self.mode == "macos":
            args.append("--macos")
        elif self.mode == "restore":
            args.append("--restore")
        else:
            self.failed.emit(f"Unbekannter Modus: {self.mode}")
            return

        try:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy(),
            )
        except OSError as exc:
            self.failed.emit(str(exc))
            return

        assert process.stdout is not None
        for line in process.stdout:
            self.output.emit(line.rstrip())

        code = process.wait()
        if code == 0:
            self.finished_ok.emit()
        else:
            self.failed.emit(f"Desktop-Look-Skript beendet mit Code {code}.")


class DesktopLookPage(QWidget):
    """Clickable Open Hardware Control page for KDE desktop styling."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.worker: DesktopLookWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel("Desktop-Look")
        title.setObjectName("sectionTitle")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            "Fedora KDE per Klick wie Windows 11 oder macOS aussehen lassen. "
            "Vor jeder Änderung wird automatisch ein KDE-Backup erstellt."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("opacity: 0.82;")
        root.addWidget(subtitle)

        if not is_fedora_kde():
            warning = QLabel(
                "Hinweis: Diese Funktion ist für Fedora KDE / Plasma 6 gedacht. "
                "Auf anderen Desktops bitte nicht anwenden."
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #f6c177;")
            root.addWidget(warning)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        root.addLayout(cards)

        cards.addWidget(self._card(
            "Windows 11",
            "Zentrierte Taskleiste, Fluent-Theme, runde Fenster, Blur und Fluent-Icons.",
            "Windows-11-Look anwenden",
            "windows11",
        ))
        cards.addWidget(self._card(
            "macOS",
            "Top-Bar, Dock-ähnliche Leiste, WhiteSur-Theme, Icons und Cursor.",
            "macOS-Look anwenden",
            "macos",
        ))

        restore = QPushButton("Letztes Desktop-Look-Backup wiederherstellen")
        restore.clicked.connect(lambda: self.start_mode("restore"))
        root.addWidget(restore)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Ausgabe des Theme-Skripts …")
        self.log.setMinimumHeight(170)
        root.addWidget(self.log, 1)

        note = QLabel(
            "Nach dem Anwenden bitte einmal abmelden und wieder anmelden. "
            "Das ändert nur KDE/Plasma-Optik, keine Hardwareprofile."
        )
        note.setWordWrap(True)
        note.setStyleSheet("opacity: 0.72;")
        root.addWidget(note)

    def _card(self, title: str, text: str, button_text: str, mode: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("QFrame { border-radius: 14px; padding: 10px; }")
        layout = QVBoxLayout(card)
        head = QLabel(title)
        head.setStyleSheet("font-size: 18px; font-weight: 700;")
        body = QLabel(text)
        body.setWordWrap(True)
        button = QPushButton(button_text)
        button.clicked.connect(lambda: self.start_mode(mode))
        layout.addWidget(head)
        layout.addWidget(body, 1)
        layout.addWidget(button)
        return card

    def start_mode(self, mode: str) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, APP_TITLE, "Es läuft bereits eine Desktop-Look-Änderung.")
            return

        label = {
            "windows11": "Windows-11-Look",
            "macos": "macOS-Look",
            "restore": "Wiederherstellung",
        }.get(mode, mode)

        answer = QMessageBox.question(
            self,
            APP_TITLE,
            f"{label} jetzt anwenden?\n\nEs wird vorher automatisch ein Backup erstellt.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.log.appendPlainText(f">>> Starte {label} …")
        self.worker = DesktopLookWorker(mode, self)
        self.worker.output.connect(self.log.appendPlainText)
        self.worker.finished_ok.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _done(self) -> None:
        self.log.appendPlainText(">>> Fertig. Bitte einmal abmelden und wieder anmelden.")
        QMessageBox.information(self, APP_TITLE, "Fertig. Bitte einmal von KDE abmelden und wieder anmelden.")

    def _failed(self, message: str) -> None:
        self.log.appendPlainText(f">>> Fehler: {message}")
        QMessageBox.warning(self, APP_TITLE, message)


class DesktopLookDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Hardware Control – Desktop-Look")
        self.resize(860, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(DesktopLookPage(self))


def show_desktop_look_dialog(parent: QWidget | None = None) -> DesktopLookDialog:
    dialog = DesktopLookDialog(parent)
    dialog.show()
    return dialog


def create_desktop_look_action(parent: QWidget, menu) -> QAction:
    """Convenience helper for adding the page as a clickable menu item."""
    action = QAction("Desktop-Look …", parent)
    action.triggered.connect(lambda: show_desktop_look_dialog(parent))
    menu.addAction(action)
    return action

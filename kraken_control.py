#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Frelidon contributors
"""Kraken Control by Frelidon — Linux

A focused PySide6 GUI for NZXT Kraken 2023 + NZXT 2023 RGB Controller.
It manages only the Kraken cooling loop and its directly associated radiator fans, RGB and LCD.
Motherboard, chassis and GPU fans are intentionally outside this application.
It uses liquidctl as the hardware backend and intentionally does not speak raw USB.
"""

from __future__ import annotations

import json
import math
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

try:
    import PIL
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # handled in the GUI
    PIL = None
    Image = None
    ImageDraw = None
    ImageFont = None

from PySide6 import __version__ as PYSIDE_VERSION
from PySide6.QtCore import QEvent, QObject, QPointF, QProcess, QRectF, QSettings, QSize, Qt, QTimer, Signal, QStandardPaths, qVersion
from PySide6.QtGui import QAction, QBrush, QColor, QCloseEvent, QFont, QIcon, QImage, QKeyEvent, QKeySequence, QLinearGradient, QMouseEvent, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QAbstractButton,
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QInputDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedLayout,
    QStackedWidget,
    QSystemTrayIcon,
    QTabBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QWidget,
    QPlainTextEdit,
)

APP_NAME = "Kraken Control"
DISPLAY_NAME = "Kraken Control by Frelidon"
APP_VERSION = "2.9.6"
ORG_NAME = "FloriLinuxTools"
LIQUIDCTL = shutil.which("liquidctl") or "liquidctl"
KRAKEN_MATCH = "NZXT Kraken 2023"
RGB_MATCH = "NZXT 2023 RGB Controller"
DEFAULT_LCD_INTERVAL = 7
LOW_PUMP_WARNING = 30
LOW_FAN_WARNING = 20
SAFE_PROFILE_PUMP = 65
SAFE_PROFILE_FAN = 65
DEPENDENCY_PACKAGES = ("liquidctl", "python3-pyside6", "python3-pillow")
PROFILE_SCHEMA_VERSION = 1
DEFAULT_UI_SCALE = 100
DEFAULT_BACKGROUND_THEME = "Sternenfeld"

# Official dependency and hardware pages shown in the About tab.
NZXT_KRAKEN_2023_URL = "https://support.nzxt.com/hc/en-us/articles/47207322896923-Kraken-2023-Specs"
NZXT_COOLERS_URL = "https://nzxt.com/collections/cpu-coolers"
NZXT_WEBSITE_URL = "https://nzxt.com/"
LIQUIDCTL_DOCS_URL = "https://liquidctl.readthedocs.io/"
LIQUIDCTL_GITHUB_URL = "https://github.com/liquidctl/liquidctl"
LIQUIDCTL_LICENSE_URL = "https://github.com/liquidctl/liquidctl#license"
PYTHON_WEBSITE_URL = "https://www.python.org/"
PYTHON_GITHUB_URL = "https://github.com/python/cpython"
PYTHON_LICENSE_URL = "https://docs.python.org/3/license.html"
PYSIDE_DOCS_URL = "https://doc.qt.io/qtforpython-6/"
PYSIDE_GITHUB_URL = "https://github.com/pyside/pyside-setup"
PYSIDE_LICENSE_URL = "https://doc.qt.io/qtforpython-6/licenses.html"
PILLOW_DOCS_URL = "https://pillow.readthedocs.io/"
PILLOW_GITHUB_URL = "https://github.com/python-pillow/Pillow"
PILLOW_LICENSE_URL = "https://github.com/python-pillow/Pillow/blob/main/LICENSE"
GPL_URL = "https://www.gnu.org/licenses/gpl-3.0.html"
OPENAI_WEBSITE_URL = "https://openai.com/"
CHATGPT_URL = "https://chatgpt.com/"
OPENAI_GITHUB_URL = "https://github.com/openai"
AMD_PROCESSOR_SPECS_URL = "https://www.amd.com/en/products/specifications/processors.html"
K10TEMP_DOCS_URL = "https://docs.kernel.org/hwmon/k10temp.html"
LIQUIDCTL_UDEV_URL = "https://github.com/liquidctl/liquidctl/blob/main/extra/linux/71-liquidctl.rules"

DEFAULT_PUMP_CURVE = ((25, 35), (30, 45), (35, 60), (40, 75), (45, 100))
DEFAULT_FAN_CURVE = ((25, 25), (30, 35), (35, 50), (40, 75), (45, 100))
AM5_95_PUMP_CURVE = ((25, 40), (30, 50), (35, 65), (40, 85), (45, 100))
AM5_95_FAN_CURVE = ((25, 30), (30, 42), (35, 62), (40, 86), (45, 100))
AM5_X3D_89_PUMP_CURVE = ((25, 45), (30, 55), (35, 72), (40, 92), (45, 100))
AM5_X3D_89_FAN_CURVE = ((25, 35), (30, 48), (35, 68), (40, 92), (45, 100))


@dataclass(frozen=True)
class CPUProfile:
    model: str
    family: str
    tjmax: int
    boost_temp: int
    critical_temp: int
    boost_pump: int
    boost_fan: int
    pump_curve: tuple[tuple[int, int], ...]
    fan_curve: tuple[tuple[int, int], ...]
    source_url: str


def cpu_profile(
    model: str,
    family: str,
    tjmax: int,
    source_url: str,
    *,
    boost_temp: int | None = None,
    critical_temp: int | None = None,
) -> CPUProfile:
    is_old_x3d = tjmax == 89
    return CPUProfile(
        model=model,
        family=family,
        tjmax=tjmax,
        boost_temp=boost_temp if boost_temp is not None else (75 if is_old_x3d else 80),
        critical_temp=critical_temp if critical_temp is not None else (85 if is_old_x3d else 90),
        boost_pump=80 if is_old_x3d else 72,
        boost_fan=88 if is_old_x3d else 80,
        pump_curve=AM5_X3D_89_PUMP_CURVE if is_old_x3d else AM5_95_PUMP_CURVE,
        fan_curve=AM5_X3D_89_FAN_CURVE if is_old_x3d else AM5_95_FAN_CURVE,
        source_url=source_url,
    )


AM5_CPU_PROFILES = (
    cpu_profile("AMD Ryzen 9 9950X3D2 Dual Edition", "Ryzen 9000 X3D", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x3d2-dual-edition.html"),
    cpu_profile("AMD Ryzen 9 9950X3D", "Ryzen 9000 X3D", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x3d.html"),
    cpu_profile("AMD Ryzen 9 9900X3D", "Ryzen 9000 X3D", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9900x3d.html"),
    cpu_profile("AMD Ryzen 7 9850X3D", "Ryzen 9000 X3D", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-7-9850x3d.html"),
    cpu_profile("AMD Ryzen 7 9800X3D", "Ryzen 9000 X3D", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-7-9800x3d.html"),
    cpu_profile("AMD Ryzen 9 9950X", "Ryzen 9000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9950x.html"),
    cpu_profile("AMD Ryzen 9 9900X", "Ryzen 9000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-9-9900x.html"),
    cpu_profile("AMD Ryzen 7 9700X", "Ryzen 9000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-7-9700x.html"),
    cpu_profile("AMD Ryzen 5 9600X", "Ryzen 9000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-5-9600x.html"),
    cpu_profile("AMD Ryzen 5 9600", "Ryzen 9000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/9000-series/amd-ryzen-5-9600.html"),
    cpu_profile("AMD Ryzen 7 8700G", "Ryzen 8000G", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/8000-series/amd-ryzen-7-8700g.html"),
    cpu_profile("AMD Ryzen 5 8600G", "Ryzen 8000G", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/8000-series/amd-ryzen-5-8600g.html"),
    cpu_profile("AMD Ryzen 9 7950X3D", "Ryzen 7000 X3D", 89, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7950x3d.html"),
    cpu_profile("AMD Ryzen 9 7900X3D", "Ryzen 7000 X3D", 89, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7900x3d.html"),
    cpu_profile("AMD Ryzen 7 7800X3D", "Ryzen 7000 X3D", 89, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7800x3d.html"),
    cpu_profile("AMD Ryzen 7 7700X3D", "Ryzen 7000 X3D", 89, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700x3d.html"),
    cpu_profile("AMD Ryzen 5 7600X3D", "Ryzen 7000 X3D", 89, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600x3d.html"),
    cpu_profile("AMD Ryzen 9 7950X", "Ryzen 7000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7950x.html"),
    cpu_profile("AMD Ryzen 9 7900X", "Ryzen 7000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-9-7900x.html"),
    cpu_profile("AMD Ryzen 7 7700X", "Ryzen 7000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700x.html"),
    cpu_profile("AMD Ryzen 5 7600", "Ryzen 7000", 95, "https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-5-7600.html"),
)
CPU_PROFILE_BY_MODEL = {profile.model: profile for profile in AM5_CPU_PROFILES}


def redact_private_text(text: str) -> str:
    """Remove common personal identifiers before text reaches the copyable log."""
    if not text:
        return text
    home = str(Path.home())
    if home and home != "/":
        text = text.replace(home, "~")
    text = re.sub(r"/home/[^/\s]+", "/home/[USER]", text)
    text = re.sub(r"(?im)^(\s*(?:serial(?: number)?|id_serial(?:_short)?)[=:]\s*).*$", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(machine-id|boot-id)(\s*[:=]\s*)[0-9a-f-]+", r"\1\2[REDACTED]", text)
    return text


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    elapsed: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def combined(self) -> str:
        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


class PendingCommand:
    """A single queued liquidctl invocation."""

    def __init__(
        self,
        args: list[str],
        callback: Callable[[CommandResult], None] | None,
        error_callback: Callable[[str], None] | None,
        timeout: int,
        log_command: bool,
        log_output: bool,
    ):
        self.args = args
        self.callback = callback
        self.error_callback = error_callback
        self.timeout = timeout
        self.log_command = log_command
        self.log_output = log_output


class Backend(QObject):
    """Runs liquidctl sequentially with QProcess in Qt's main event loop.

    Version 2.0 used Python QRunnable objects in QThreadPool.  On the
    Python 3.14 / PySide6 6.11 combination this could race with Shiboken
    object destruction and crash the entire application.  QProcess is
    asynchronous without Python worker threads and also guarantees that
    callbacks update widgets only from the GUI thread.
    """

    log = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._queue: list[PendingCommand] = []
        self._current: PendingCommand | None = None
        self._process: QProcess | None = None
        self._started_at = 0.0
        self._timed_out = False
        self._shutting_down = False
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)

    @staticmethod
    def kraken_args() -> list[str]:
        return [LIQUIDCTL, "--match", KRAKEN_MATCH]

    @staticmethod
    def kraken_direct_args() -> list[str]:
        """Use HID direct access for profile writes.

        With the nzxt-kraken3 kernel driver bound, liquidctl normally writes
        curves through hwmon.  Some distributions expose fixed PWM controls
        to the desktop user but keep the auto-point files root-only.  Direct
        access uses the already udev-authorized hidraw device and avoids that
        split-permission failure.
        """
        return [LIQUIDCTL, "--direct-access", "--match", KRAKEN_MATCH]

    @staticmethod
    def rgb_args() -> list[str]:
        return [LIQUIDCTL, "--match", RGB_MATCH]

    def run_async(
        self,
        args: list[str],
        callback: Callable[[CommandResult], None] | None = None,
        error_callback: Callable[[str], None] | None = None,
        timeout: int = 45,
        log_command: bool = True,
        log_output: bool = True,
    ) -> None:
        if self._shutting_down:
            return
        command = PendingCommand(
            args=list(args),
            callback=callback,
            error_callback=error_callback,
            timeout=max(1, int(timeout)),
            log_command=log_command,
            log_output=log_output,
        )
        self._queue.append(command)
        self._start_next()

    def _start_next(self) -> None:
        if self._shutting_down or self._process is not None or not self._queue:
            return

        self._current = self._queue.pop(0)
        command = self._current
        if command.log_command:
            self.log.emit(redact_private_text("$ " + " ".join(command.args)))

        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_process_error)
        self._process = process
        self._started_at = time.monotonic()
        self._timed_out = False
        self._timeout_timer.start(command.timeout * 1000)
        process.start(command.args[0], command.args[1:])

    def _on_timeout(self) -> None:
        process = self._process
        command = self._current
        if process is None or command is None:
            return
        self._timed_out = True
        self.log.emit(redact_private_text(f"Zeitüberschreitung nach {command.timeout} Sekunden: {' '.join(command.args)}"))
        process.kill()

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        # Most runtime errors are followed by finished(); FailedToStart is not
        # guaranteed to be, so complete it explicitly on the next event turn.
        if error == QProcess.ProcessError.FailedToStart:
            QTimer.singleShot(0, self._finish_failed_start)

    def _finish_failed_start(self) -> None:
        if self._process is None or self._current is None:
            return
        self._complete(127, "", self._process.errorString())

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        process = self._process
        if process is None:
            return
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="replace")
        if self._timed_out:
            exit_code = 124
            timeout_msg = f"Zeitüberschreitung nach {self._current.timeout if self._current else '?'} Sekunden"
            stderr = "\n".join(part for part in (stderr.strip(), timeout_msg) if part)
        self._complete(int(exit_code), stdout, stderr)

    def _complete(self, returncode: int, stdout: str, stderr: str) -> None:
        self._timeout_timer.stop()
        command = self._current
        process = self._process
        elapsed = time.monotonic() - self._started_at

        self._current = None
        self._process = None
        self._timed_out = False

        if process is not None:
            process.deleteLater()

        if command is not None:
            result = CommandResult(
                args=command.args,
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                elapsed=elapsed,
            )
            if command.log_output and result.combined:
                self.log.emit(redact_private_text(result.combined))
            try:
                if command.callback is not None:
                    command.callback(result)
                elif not result.ok and command.error_callback is not None:
                    command.error_callback(result.combined or "Unbekannter Prozessfehler")
            except RuntimeError:
                # The window may already have been closed while a process ended.
                pass
            except Exception as exc:  # noqa: BLE001
                self.log.emit(f"Callback-Fehler: {exc}")
                if command.error_callback is not None:
                    command.error_callback(str(exc))

        if not self._shutting_down:
            QTimer.singleShot(0, self._start_next)

    def shutdown(self) -> None:
        self._shutting_down = True
        self._queue.clear()
        self._timeout_timer.stop()
        if self._process is not None:
            self._process.kill()
            self._process.waitForFinished(1000)
            self._process.deleteLater()
            self._process = None
        self._current = None


class ValueCard(QFrame):
    def __init__(self, title: str, value: str, hint: str = ""):
        super().__init__()
        self.setObjectName("valueCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")
        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("cardHint")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str | None = None) -> None:
        self.value_label.setText(value)
        if hint is not None:
            self.hint_label.setText(hint)


class CurveEditor(QWidget):
    """Interactive, safety-aware temperature curve editor.

    Points can be dragged with the mouse or adjusted with the arrow keys. The
    editor keeps temperatures strictly increasing and duties non-decreasing.
    The final point remains fixed at 100 percent and cannot move beyond 50 °C.
    """

    pointsChanged = Signal(object)

    def __init__(self, points: list[tuple[int, int]], minimum_duty: int, channel_label: str):
        super().__init__()
        self._points = [(int(temp), int(duty)) for temp, duty in points]
        self._minimum_duty = int(minimum_duty)
        self._channel_label = channel_label
        self._accent = QColor("#00aaff")
        self._current_temperature: float | None = None
        self._drag_index: int | None = None
        self._selected_index = 0
        self.setMinimumSize(360, 250)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setObjectName("curveEditor")
        self.setAccessibleName(f"Grafischer Kurveneditor für {channel_label}")
        self.setToolTip(
            "Punkte mit der Maus ziehen oder mit den Pfeiltasten verschieben. "
            "Der letzte Punkt bleibt aus Sicherheitsgründen bei 100 %."
        )

    def points(self) -> list[tuple[int, int]]:
        return list(self._points)

    def set_points(self, points: list[tuple[int, int]], emit: bool = False) -> None:
        normalized = [(int(temp), int(duty)) for temp, duty in points]
        if len(normalized) < 2:
            return
        self._points = normalized
        self._selected_index = min(self._selected_index, len(self._points) - 1)
        self.update()
        if emit:
            self.pointsChanged.emit(self.points())

    def set_accent_color(self, color: QColor) -> None:
        if color.isValid():
            self._accent = QColor(color)
            self.update()

    def set_current_temperature(self, temperature: float | None) -> None:
        self._current_temperature = temperature
        self.update()

    def _plot_rect(self) -> QRectF:
        return QRectF(54.0, 18.0, max(120.0, self.width() - 78.0), max(100.0, self.height() - 70.0))

    def _to_canvas(self, temp: float, duty: float) -> QPointF:
        rect = self._plot_rect()
        x = rect.left() + ((temp - 20.0) / 30.0) * rect.width()
        y = rect.bottom() - (duty / 100.0) * rect.height()
        return QPointF(x, y)

    def _from_canvas(self, point: QPointF) -> tuple[int, int]:
        rect = self._plot_rect()
        temp = 20.0 + ((point.x() - rect.left()) / max(1.0, rect.width())) * 30.0
        duty = ((rect.bottom() - point.y()) / max(1.0, rect.height())) * 100.0
        return int(round(temp)), int(round(duty))

    def _move_selected(self, delta_temp: int, delta_duty: int) -> None:
        if not self._points:
            return
        index = self._selected_index
        temp, duty = self._points[index]
        self._set_point(index, temp + delta_temp, duty + delta_duty)

    def _set_point(self, index: int, temp: int, duty: int) -> None:
        previous_temp = self._points[index - 1][0] + 1 if index > 0 else 20
        next_temp = self._points[index + 1][0] - 1 if index < len(self._points) - 1 else 50
        previous_duty = self._points[index - 1][1] if index > 0 else self._minimum_duty
        next_duty = self._points[index + 1][1] if index < len(self._points) - 1 else 100

        temp = max(previous_temp, min(next_temp, int(temp)))
        if index == len(self._points) - 1:
            duty = 100
        else:
            duty = max(previous_duty, min(next_duty, int(duty)))

        updated = list(self._points)
        updated[index] = (temp, duty)
        if updated == self._points:
            return
        self._points = updated
        self.update()
        self.pointsChanged.emit(self.points())

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self._plot_rect()
        palette = self.palette()
        text_color = palette.color(QPalette.ColorRole.Text)
        muted = palette.color(QPalette.ColorRole.Mid)
        grid = palette.color(QPalette.ColorRole.Midlight)
        background = palette.color(QPalette.ColorRole.Base)

        painter.setPen(QPen(grid, 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 9, 9)

        # Grid and axis labels.
        font = painter.font()
        font.setPointSize(max(8, font.pointSize() - 1))
        painter.setFont(font)
        for duty in range(0, 101, 20):
            p1 = self._to_canvas(20, duty)
            p2 = self._to_canvas(50, duty)
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(p1, p2)
            painter.setPen(muted)
            painter.drawText(QRectF(2, p1.y() - 10, 46, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{duty}%")
        for temp in range(20, 51, 5):
            p1 = self._to_canvas(temp, 0)
            p2 = self._to_canvas(temp, 100)
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(p1, p2)
            painter.setPen(muted)
            painter.drawText(QRectF(p1.x() - 20, rect.bottom() + 7, 40, 20), Qt.AlignmentFlag.AlignHCenter, f"{temp}°")

        # Current coolant temperature marker.
        if self._current_temperature is not None:
            current = max(20.0, min(50.0, float(self._current_temperature)))
            x = self._to_canvas(current, 0).x()
            warning = QColor("#d49b21")
            painter.setPen(QPen(warning, 2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setPen(warning)
            painter.drawText(QRectF(x - 42, rect.top() + 3, 84, 20), Qt.AlignmentFlag.AlignHCenter, f"Aktuell {self._current_temperature:.1f}°")

        # Curve path.
        canvas_points = [self._to_canvas(temp, duty) for temp, duty in self._points]
        if canvas_points:
            path = QPainterPath(canvas_points[0])
            for point in canvas_points[1:]:
                path.lineTo(point)
            painter.setPen(QPen(self._accent, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # Draggable points and labels.
        for index, ((temp, duty), point) in enumerate(zip(self._points, canvas_points)):
            selected = index == self._selected_index
            radius = 8 if selected else 6
            painter.setPen(QPen(self._accent, 2))
            painter.setBrush(palette.color(QPalette.ColorRole.Window) if selected else self._accent)
            painter.drawEllipse(point, radius, radius)
            painter.setPen(text_color)
            label_rect = QRectF(point.x() - 37, point.y() - 30, 74, 20)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter, f"{temp}° / {duty}%")

        painter.setPen(muted)
        painter.drawText(
            QRectF(rect.left(), self.height() - 25, rect.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            "Pfeile: ändern · Strg+Links/Rechts: Punkt wählen · Tab: weiter",
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        position = event.position()
        distances = [((position.x() - p.x()) ** 2 + (position.y() - p.y()) ** 2, i) for i, p in enumerate(
            self._to_canvas(temp, duty) for temp, duty in self._points
        )]
        distance, index = min(distances, default=(999999.0, 0))
        if distance <= 18 ** 2:
            self._selected_index = index
            self._drag_index = index
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.update()
        else:
            self._drag_index = None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_index is None:
            return super().mouseMoveEvent(event)
        temp, duty = self._from_canvas(event.position())
        self._set_point(self._drag_index, temp, duty)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_index = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Left:
            self._selected_index = (self._selected_index - 1) % len(self._points)
            self.update()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Right:
            self._selected_index = (self._selected_index + 1) % len(self._points)
            self.update()
        elif key == Qt.Key.Key_Home:
            self._selected_index = 0
            self.update()
        elif key == Qt.Key.Key_End:
            self._selected_index = len(self._points) - 1
            self.update()
        elif key == Qt.Key.Key_Left:
            self._move_selected(-1, 0)
        elif key == Qt.Key.Key_Right:
            self._move_selected(1, 0)
        elif key == Qt.Key.Key_Up:
            self._move_selected(0, 1)
        elif key == Qt.Key.Key_Down:
            self._move_selected(0, -1)
        else:
            # Tab and Shift+Tab deliberately pass through for normal focus traversal.
            return super().keyPressEvent(event)
        event.accept()


class InteractionAuditLogger(QObject):
    """Logs user clicks and user-driven control changes without blocking the UI."""

    def __init__(self, owner: "KrakenControl"):
        super().__init__(owner)
        self.owner = owner

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("&", " ")).strip()

    def _widget_name(self, widget: QObject) -> str:
        accessible = ""
        if hasattr(widget, "accessibleName"):
            try:
                accessible = self._clean(str(widget.accessibleName()))
            except RuntimeError:
                accessible = ""
        if accessible:
            return accessible
        if isinstance(widget, QWidget):
            current = widget
            for _depth in range(4):
                parent = current.parentWidget()
                if parent is None:
                    break
                layout = parent.layout()
                if isinstance(layout, QFormLayout):
                    label = layout.labelForField(current)
                    if isinstance(label, QLabel):
                        text = self._clean(label.text())
                        if text:
                            return text
                current = parent
        if isinstance(widget, QAbstractButton):
            return self._clean(widget.text()) or widget.__class__.__name__
        if isinstance(widget, QComboBox):
            return self._clean(widget.objectName()) or "Auswahlliste"
        if isinstance(widget, QSlider):
            return self._clean(widget.objectName()) or "Regler"
        if isinstance(widget, QSpinBox):
            return self._clean(widget.objectName()) or "Zahlenfeld"
        if isinstance(widget, QLineEdit):
            return self._clean(widget.placeholderText()) or self._clean(widget.objectName()) or "Textfeld"
        if isinstance(widget, QTableWidget):
            return self._clean(widget.accessibleName()) or "Tabelle"
        return self._clean(widget.objectName()) or widget.__class__.__name__

    def _describe_click(self, widget: QObject, event: QMouseEvent) -> str | None:
        if widget is getattr(self.owner, "log_view", None):
            return None
        if isinstance(widget, QTabBar):
            try:
                index = widget.tabAt(event.position().toPoint())
                if index >= 0:
                    return f"Tab '{self._clean(widget.tabText(index))}'"
            except RuntimeError:
                return "Tab-Leiste"
        if isinstance(widget, QCheckBox):
            return f"Kontrollkästchen '{self._widget_name(widget)}'"
        if isinstance(widget, QAbstractButton):
            return f"Schaltfläche '{self._widget_name(widget)}'"
        if isinstance(widget, QComboBox):
            return f"Auswahlliste '{self._widget_name(widget)}'"
        if isinstance(widget, QSlider):
            return f"Regler '{self._widget_name(widget)}' bei {widget.value()}"
        if isinstance(widget, QSpinBox):
            return f"Zahlenfeld '{self._widget_name(widget)}' bei {widget.value()}"
        if isinstance(widget, QLineEdit):
            return f"Textfeld '{self._widget_name(widget)}'"
        if isinstance(widget, QLabel) and widget.openExternalLinks():
            plain = re.sub(r"<[^>]+>", "", widget.text())
            return f"Externer Link '{self._clean(plain)}'"
        if isinstance(widget, QTableWidget):
            try:
                item = widget.itemAt(event.position().toPoint())
                if item is not None:
                    return f"{self._widget_name(widget)} · Zeile {item.row() + 1}, Spalte {item.column() + 1}"
            except RuntimeError:
                pass
            return self._widget_name(widget)
        return None

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        try:
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if event.button() == Qt.MouseButton.LeftButton:
                    description = self._describe_click(watched, event)
                    if description:
                        self.owner.log_user_action("KLICK", description)
            elif event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                    if isinstance(watched, (QAbstractButton, QComboBox, QSlider, QSpinBox, QLineEdit)):
                        self.owner.log_user_action("TASTATUR", self._widget_name(watched))
        except (RuntimeError, AttributeError):
            pass
        return False


class AnimatedBackgroundWidget(QWidget):
    """Procedural background rendered to a CPU-side QImage for Wayland/HiDPI safety."""

    THEMES = (
        "Aus",
        "Sternenfeld",
        "Kosmischer Nebel",
        "Aurora",
        "Spiralgalaxie",
        "Warp-Tunnel",
        "Schwebende Partikel",
        "Bokeh",
        "Ozeanwellen",
        "Digitaler Regen",
        "Sonnenaufgang",
        "Eisnebel",
        "Minimaler Fluss",
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("backgroundRoot")
        # Decorative-only layer: never intercept input and avoid backing-store flags
        # that produced scanline artifacts on some Wayland/HiDPI combinations.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._enabled = False
        self._theme = "Aus"
        self._fps = 30
        self._intensity = 40
        self._pause_inactive = True
        self._phase = 0.0
        self._frame = QImage()
        self._pixmap = QPixmap()
        self._frame_dirty = True
        self._render_error_reported = False
        rng = random.Random(2900)
        self._particles = [
            (rng.random(), rng.random(), rng.uniform(0.25, 1.0), rng.uniform(0.4, 2.2), rng.random())
            for _ in range(180)
        ]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def configure(self, *, enabled: bool, theme: str, fps: int, intensity: int, pause_inactive: bool) -> None:
        self._enabled = bool(enabled) and theme != "Aus"
        self._theme = theme if theme in self.THEMES else DEFAULT_BACKGROUND_THEME
        self._fps = max(10, min(60, int(fps)))
        self._intensity = max(5, min(100, int(intensity)))
        self._pause_inactive = bool(pause_inactive)
        self._timer.setInterval(max(16, round(1000 / self._fps)))
        self._frame_dirty = True
        if self._enabled:
            self._timer.start()
        else:
            self._timer.stop()
            self._frame = QImage()
            self._pixmap = QPixmap()
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: ANN001, N802
        self._frame_dirty = True
        super().resizeEvent(event)

    def _tick(self) -> None:
        app = QApplication.instance()
        if self._pause_inactive and app is not None and app.applicationState() != Qt.ApplicationState.ApplicationActive:
            return
        self._phase = (self._phase + 1.0 / self._fps) % 100000.0
        self._frame_dirty = True
        self.update()

    @staticmethod
    def _mix(a: QColor, b: QColor, ratio: float, alpha: int = 255) -> QColor:
        ratio = max(0.0, min(1.0, ratio))
        return QColor(
            round(a.red() * (1 - ratio) + b.red() * ratio),
            round(a.green() * (1 - ratio) + b.green() * ratio),
            round(a.blue() * (1 - ratio) + b.blue() * ratio),
            alpha,
        )

    def _render_size(self) -> tuple[int, int]:
        width = max(2, self.width())
        height = max(2, self.height())
        # Bounded offscreen frame keeps 21:9/32:9 and HiDPI monitors efficient.
        factor = min(1.0, 960.0 / width, 540.0 / height)
        return max(2, round(width * factor)), max(2, round(height * factor))

    def _report_render_error(self, message: str) -> None:
        if self._render_error_reported:
            return
        self._render_error_reported = True
        window = self.window()
        if hasattr(window, "log_message"):
            QTimer.singleShot(0, lambda: window.log_message(f"HINTERGRUND-FEHLER: {message}"))

    def _render_frame(self) -> None:
        rw, rh = self._render_size()
        base = self.palette().color(QPalette.ColorRole.Window)
        # RGB32 is deliberately used instead of premultiplied ARGB.  The
        # background is opaque anyway, and RGB32 avoids channel/stride artifacts
        # observed with Qt 6.11 on Wayland when a scaled premultiplied image was
        # painted repeatedly in the light theme.
        image = QImage(rw, rh, QImage.Format.Format_RGB32)
        image.fill(base)
        if not self._enabled or self._theme == "Aus":
            self._frame = image
            self._pixmap = QPixmap.fromImage(image)
            self._frame_dirty = False
            return

        painter = QPainter(image)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self._paint_scene(painter, rw, rh, base)
        except Exception as exc:  # noqa: BLE001
            image.fill(base)
            self._enabled = False
            self._timer.stop()
            self._report_render_error(str(exc))
        finally:
            painter.end()
        self._frame = image
        self._pixmap = QPixmap.fromImage(image)
        self._frame_dirty = False

    def paintEvent(self, _event) -> None:  # noqa: ANN001, N802
        painter = QPainter(self)
        base = self.palette().color(QPalette.ColorRole.Window)
        painter.fillRect(self.rect(), base)
        if not self._enabled or self._theme == "Aus":
            return
        if self._frame_dirty or self._frame.isNull():
            self._render_frame()
        if not self._pixmap.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawPixmap(self.rect(), self._pixmap)

    def _paint_scene(self, painter: QPainter, w: int, h: int, base: QColor) -> None:
        canvas = QRectF(0, 0, w, h)
        accent = self.palette().color(QPalette.ColorRole.Highlight)
        dark = QColor("#07111f") if base.lightness() < 150 else QColor("#dcefff")
        alpha_scale = self._intensity / 100.0
        t = self._phase

        if self._theme == "Sternenfeld":
            painter.fillRect(canvas, self._mix(base, QColor("#030714"), 0.78))
            painter.setPen(Qt.PenStyle.NoPen)
            for x0, y0, speed, size, twinkle in self._particles:
                y = ((y0 + t * 0.018 * speed) % 1.0) * h
                x = x0 * w
                glow = 0.45 + 0.55 * abs(math.sin(t * 2.1 + twinkle * 9))
                painter.setBrush(QColor(220, 235, 255, int(70 + 175 * glow * alpha_scale)))
                painter.drawEllipse(QPointF(x, y), size + glow, size + glow)

        elif self._theme in {"Kosmischer Nebel", "Eisnebel"}:
            painter.fillRect(canvas, self._mix(base, QColor("#080b18"), 0.65))
            colors = [accent, QColor("#7c3aed"), QColor("#06b6d4")]
            if self._theme == "Eisnebel":
                colors = [QColor("#5ee7ff"), QColor("#7aa2ff"), QColor("#d8f5ff")]
            for index, color in enumerate(colors):
                cx = w * (0.2 + 0.32 * index) + math.sin(t * (0.18 + index * 0.04)) * w * 0.10
                cy = h * (0.35 + 0.12 * index) + math.cos(t * (0.15 + index * 0.03)) * h * 0.16
                radius = max(w, h) * (0.34 + index * 0.05)
                gradient = QRadialGradient(QPointF(cx, cy), radius)
                c0 = QColor(color)
                c0.setAlpha(int(85 * alpha_scale))
                c1 = QColor(color)
                c1.setAlpha(0)
                gradient.setColorAt(0.0, c0)
                gradient.setColorAt(1.0, c1)
                painter.setBrush(QBrush(gradient))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx, cy), radius, radius)

        elif self._theme == "Aurora":
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, self._mix(base, QColor("#061225"), 0.8))
            gradient.setColorAt(1, self._mix(base, QColor("#07150f"), 0.7))
            painter.fillRect(canvas, QBrush(gradient))
            for band, color in enumerate((QColor("#37f6a3"), accent, QColor("#9b5cff"))):
                path = QPainterPath(QPointF(0, h * (0.30 + 0.12 * band)))
                for x in range(0, w + 20, 20):
                    y = h * (0.30 + 0.12 * band) + math.sin(x / 115 + t * (0.7 + band * 0.12)) * h * 0.08
                    path.lineTo(x, y)
                pen = QPen(QColor(color.red(), color.green(), color.blue(), int(85 * alpha_scale)), 18 + band * 7)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawPath(path)

        elif self._theme == "Spiralgalaxie":
            painter.fillRect(canvas, self._mix(base, QColor("#050612"), 0.82))
            center = QPointF(w / 2, h / 2)
            painter.setPen(Qt.PenStyle.NoPen)
            arms = 4
            for i in range(250):
                r = (i / 250) * min(w, h) * 0.48
                angle = i * 0.19 + t * 0.22 + (i % arms) * (math.tau / arms)
                x = center.x() + math.cos(angle) * r
                y = center.y() + math.sin(angle) * r * 0.48
                color = self._mix(accent, QColor("#ffffff"), (i % 17) / 20, int((45 + 120 * (1 - i / 250)) * alpha_scale))
                painter.setBrush(color)
                painter.drawEllipse(QPointF(x, y), 1.2 + (i % 5) * 0.25, 1.2 + (i % 5) * 0.25)

        elif self._theme == "Warp-Tunnel":
            painter.fillRect(canvas, self._mix(base, QColor("#02040a"), 0.85))
            center = QPointF(w / 2, h / 2)
            for x0, y0, speed, size, twinkle in self._particles[:120]:
                angle = x0 * math.tau
                distance = ((y0 + t * 0.23 * speed) % 1.0) ** 2
                x1 = center.x() + math.cos(angle) * distance * w * 0.75
                y1 = center.y() + math.sin(angle) * distance * h * 0.75
                trail = 0.035 + 0.06 * speed
                x2 = center.x() + math.cos(angle) * max(0, distance - trail) * w * 0.75
                y2 = center.y() + math.sin(angle) * max(0, distance - trail) * h * 0.75
                painter.setPen(QPen(QColor(210, 235, 255, int(160 * alpha_scale)), max(1.0, size)))
                painter.drawLine(QPointF(x2, y2), QPointF(x1, y1))

        elif self._theme in {"Schwebende Partikel", "Bokeh"}:
            painter.fillRect(canvas, self._mix(base, dark, 0.38))
            painter.setPen(Qt.PenStyle.NoPen)
            for x0, y0, speed, size, twinkle in self._particles[:100]:
                x = ((x0 + math.sin(t * 0.11 + twinkle * 6) * 0.025) % 1.0) * w
                y = ((y0 - t * 0.007 * speed) % 1.0) * h
                radius = size * 2.2 if self._theme == "Schwebende Partikel" else size * 8.0 + 4
                color = self._mix(accent, QColor("#ffffff"), twinkle * 0.55, int((55 if self._theme == "Bokeh" else 120) * alpha_scale))
                painter.setBrush(color)
                painter.drawEllipse(QPointF(x, y), radius, radius)

        elif self._theme == "Ozeanwellen":
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, self._mix(base, QColor("#071a2e"), 0.75))
            gradient.setColorAt(1, self._mix(base, QColor("#006a86"), 0.52))
            painter.fillRect(canvas, QBrush(gradient))
            for wave in range(7):
                path = QPainterPath(QPointF(0, h * (0.42 + wave * 0.075)))
                for x in range(0, w + 16, 16):
                    y = h * (0.42 + wave * 0.075) + math.sin(x / (75 + wave * 10) + t * (0.55 + wave * 0.05)) * (10 + wave * 2)
                    path.lineTo(x, y)
                painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), int((80 - wave * 6) * alpha_scale)), 2.5))
                painter.drawPath(path)

        elif self._theme == "Digitaler Regen":
            painter.fillRect(canvas, self._mix(base, QColor("#020805"), 0.88))
            painter.setPen(QPen(QColor(75, 255, 140, int(125 * alpha_scale)), 1.5))
            for index, (x0, y0, speed, size, twinkle) in enumerate(self._particles[:85]):
                x = x0 * w
                y = ((y0 + t * 0.08 * speed) % 1.15) * h
                length = 20 + 55 * size
                painter.drawLine(QPointF(x, y - length), QPointF(x, y))
                if index % 4 == 0:
                    painter.drawText(QPointF(x + 2, y), chr(0x30A0 + (index * 13) % 80))

        elif self._theme == "Sonnenaufgang":
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, QColor("#1d2850"))
            gradient.setColorAt(0.55, QColor("#ed6a5a"))
            gradient.setColorAt(1, QColor("#ffc76b"))
            painter.fillRect(canvas, QBrush(gradient))
            sun_y = h * (0.68 + math.sin(t * 0.08) * 0.025)
            sun = QRadialGradient(QPointF(w * 0.72, sun_y), h * 0.24)
            sun.setColorAt(0, QColor(255, 245, 185, int(220 * alpha_scale)))
            sun.setColorAt(1, QColor(255, 150, 80, 0))
            painter.setBrush(QBrush(sun))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(w * 0.72, sun_y), h * 0.24, h * 0.24)

        else:  # Minimaler Fluss
            painter.fillRect(canvas, self._mix(base, dark, 0.18))
            for lane in range(9):
                y0 = h * (lane + 1) / 10
                path = QPainterPath(QPointF(0, y0))
                for x in range(0, w + 20, 20):
                    y = y0 + math.sin(x / 130 + t * 0.45 + lane) * (5 + lane % 3 * 3)
                    path.lineTo(x, y)
                painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), int(45 * alpha_scale)), 1.5))
                painter.drawPath(path)

        veil = QColor(base)
        veil.setAlpha(38 if base.lightness() < 150 else 58)
        painter.fillRect(canvas, veil)


class SetupWizard(QWizard):
    """First-run assistant for appearance, display scaling and a starter cooling profile."""

    def __init__(self, owner: "KrakenControl"):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(f"{DISPLAY_NAME} · Ersteinrichtung")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.resize(720, 520)

        welcome = QWizardPage()
        welcome.setTitle("Willkommen")
        wl = QVBoxLayout(welcome)
        intro = QLabel(
            "Dieser Assistent richtet Design, Monitoranpassung und ein erstes Kühlprofil ein. "
            "Alle Einstellungen lassen sich später ändern."
        )
        intro.setWordWrap(True)
        wl.addWidget(intro)
        wl.addStretch()
        self.addPage(welcome)

        design = QWizardPage()
        design.setTitle("Design")
        df = QFormLayout(design)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Hell (Standard)", "light")
        self.theme_combo.addItem("Dunkel", "dark")
        self.theme_combo.addItem("Systemmodus", "system")
        self.accent_input = QLineEdit(owner.accent_hex)
        self.accent_input.setPlaceholderText("#00aaff")
        self.background_combo = QComboBox()
        self.background_combo.addItems(AnimatedBackgroundWidget.THEMES)
        self.background_combo.setCurrentText(DEFAULT_BACKGROUND_THEME)
        df.addRow("Darstellung", self.theme_combo)
        df.addRow("Akzentfarbe", self.accent_input)
        df.addRow("Animierter Hintergrund", self.background_combo)
        self.addPage(design)

        display = QWizardPage()
        display.setTitle("Monitor und Skalierung")
        dfl = QFormLayout(display)
        self.display_summary = QLabel(owner.screen_summary())
        self.display_summary.setWordWrap(True)
        self.auto_scale = QCheckBox("Automatisch an Monitor und Seitenverhältnis anpassen")
        self.auto_scale.setChecked(True)
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(80, 180)
        self.scale_spin.setValue(DEFAULT_UI_SCALE)
        self.scale_spin.setSuffix(" %")
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("Automatisch", "auto")
        self.layout_combo.addItem("Kompakt · 16:10", "16:10")
        self.layout_combo.addItem("Standard · 16:9", "16:9")
        self.layout_combo.addItem("Ultrawide · 21:9", "21:9")
        self.layout_combo.addItem("Super-Ultrawide · 32:9", "32:9")
        dfl.addRow(self.display_summary)
        dfl.addRow(self.auto_scale)
        dfl.addRow("App-Skalierung", self.scale_spin)
        dfl.addRow("Layout", self.layout_combo)
        self.addPage(display)

        devices = QWizardPage()
        devices.setTitle("Systemprüfung")
        dl = QVBoxLayout(devices)
        missing = owner.missing_dependency_packages()
        system_text = (
            "Abhängigkeiten vollständig." if not missing
            else "Fehlende Pakete: " + ", ".join(missing) + ". Sie können später in den Einstellungen installiert werden."
        )
        self.system_label = QLabel(system_text)
        self.system_label.setWordWrap(True)
        dl.addWidget(self.system_label)
        dl.addWidget(QLabel("Kraken und RGB-Controller werden nach Abschluss des Assistenten erkannt."))
        dl.addStretch()
        self.addPage(devices)

        cooling = QWizardPage()
        cooling.setTitle("Startprofil")
        cf = QFormLayout(cooling)
        self.cooling_combo = QComboBox()
        self.cooling_combo.addItem("Leise · 45 % / 35 %", "quiet")
        self.cooling_combo.addItem("Ausgeglichen · 55 % / 50 %", "balanced")
        self.cooling_combo.addItem("Leistung · 75 % / 75 %", "performance")
        self.cooling_combo.addItem("Sicher · 65 % / 65 %", "safe")
        self.cooling_combo.setCurrentIndex(1)
        note = QLabel("Das Profil wird nach erfolgreicher Geräteerkennung angewendet.")
        note.setWordWrap(True)
        cf.addRow("Kühlprofil", self.cooling_combo)
        cf.addRow(note)
        self.addPage(cooling)

        finish = QWizardPage()
        finish.setTitle("Bereit")
        fl = QVBoxLayout(finish)
        summary = QLabel(
            "Die App startet standardmäßig im hellen Modus. Prozedurale Hintergründe benötigen keine externen Downloads "
            "und können jederzeit abgeschaltet werden."
        )
        summary.setWordWrap(True)
        fl.addWidget(summary)
        fl.addStretch()
        self.addPage(finish)

    def selected_values(self) -> dict[str, object]:
        return {
            "theme": self.theme_combo.currentData(),
            "accent": self.accent_input.text().strip(),
            "background": self.background_combo.currentText(),
            "auto_scale": self.auto_scale.isChecked(),
            "scale": self.scale_spin.value(),
            "layout": self.layout_combo.currentData(),
            "cooling": self.cooling_combo.currentData(),
        }


class KrakenControl(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORG_NAME, APP_NAME)
        self.system_palette = QPalette(QApplication.palette())
        self.theme_mode = str(self.settings.value("design/theme", "light"))
        if self.theme_mode not in {"system", "light", "dark"}:
            self.theme_mode = "light"
        self.accent_hex = self.normalize_accent_hex(str(self.settings.value("design/accent", "#00aaff"))) or "#00aaff"
        self.base_font = QFont(QApplication.font())
        self.ui_scale_percent = max(80, min(180, int(self.settings.value("display/ui_scale", DEFAULT_UI_SCALE))))
        self.display_auto = self.settings.value("display/auto", True, type=bool)
        self.display_layout = str(self.settings.value("display/layout", "auto"))
        self.background_enabled = self.settings.value("background/enabled", False, type=bool)
        self.background_theme = str(self.settings.value("background/theme", DEFAULT_BACKGROUND_THEME))
        self.background_last_theme = str(self.settings.value("background/last_theme", self.background_theme))
        if self.background_last_theme not in AnimatedBackgroundWidget.THEMES or self.background_last_theme == "Aus":
            self.background_last_theme = DEFAULT_BACKGROUND_THEME
        self.background_fps = int(self.settings.value("background/fps", 30))
        self.background_intensity = int(self.settings.value("background/intensity", 40))
        self.background_pause_inactive = self.settings.value("background/pause_inactive", True, type=bool)
        self.pending_setup_profile = str(self.settings.value("setup/pending_profile", ""))
        self.user_profiles: list[dict[str, object]] = []
        self.current_profile_id = str(self.settings.value("profiles/current", ""))
        self._syncing_curve = False
        self.current_cpu_temp: float | None = None
        self.cpu_sensor_label = "Nicht erkannt"
        self.cpu_assist_level = "curve"
        self.cpu_restore_pending = False
        self.selected_cpu_profile: CPUProfile | None = None
        self.expert_mode_enabled = self.settings.value("safety/expert_mode", False, type=bool)
        self.permission_retry_after = 0.0
        self.permission_notice_last = 0.0
        self.permission_dialog_open = False
        self.cooling_modes: dict[str, tuple[str, str]] = {
            "pump": ("unbekannt", "Noch nicht durch Kraken Control gesetzt"),
            "fan": ("unbekannt", "Noch nicht durch Kraken Control gesetzt"),
        }
        self.backend = Backend(self)
        self.backend.log.connect(self.log_message)

        self.status_busy = False
        self.lcd_busy = False
        self.kraken_write_busy = False
        self.devices_ready = False
        self.last_status_ok = False
        self.selected_lcd_file: Path | None = None
        self.prepared_lcd_file: Path | None = None
        self.temp_dir = Path(tempfile.gettempdir()) / "kraken-control"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle(f"{DISPLAY_NAME} {APP_VERSION} — Linux")
        self.resize(1280, 880)
        self.setMinimumSize(820, 600)
        icon_path = Path(__file__).with_name("kraken-control.svg")
        app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon.fromTheme("preferences-system-cooling")
        self.setWindowIcon(app_icon)

        self.build_ui()
        self.build_menu_bar()
        self.configure_accessibility()
        self.apply_theme()

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(3000)
        self.status_timer.timeout.connect(self.refresh_status)

        self.lcd_keepalive_timer = QTimer(self)
        self.lcd_keepalive_timer.timeout.connect(self.send_lcd_keepalive)

        self.clock_timer = QTimer(self)
        self.clock_timer.setSingleShot(True)
        self.clock_timer.timeout.connect(self.update_clock_lcd)

        self.clock_keepalive_timer = QTimer(self)
        self.clock_keepalive_timer.timeout.connect(self.send_clock_keepalive)
        self.clock_active = False
        self.clock_text_hex = "ffffff"
        self.clock_background_hex = "10141c"
        self.clock_image_file = self.temp_dir / "lcd-clock.png"
        self.clock_render_key = ""
        self.keepalive_warning_acknowledged = False
        self.clock_warning_acknowledged = False

        self.restore_settings()
        self.setup_tray()
        self.enable_interaction_logging()
        self.log_message("START: Kraken Control 2.9.6 gestartet · LCD-Uhr-/Direct-Access-Hotfix aktiv")
        missing_dependencies = self.check_dependencies()
        if not missing_dependencies:
            self.initialize_devices()
        else:
            self.connection_label.setText("● Abhängigkeiten fehlen")
            self.connection_label.setObjectName("connectionPending")
            self.footer_status.setText("Bitte fehlende Abhängigkeiten installieren")
        QTimer.singleShot(0, self.refresh_display_info)
        QTimer.singleShot(250, self.maybe_show_setup_wizard)

    # ---------- UI ----------
    def build_menu_bar(self) -> None:
        file_menu = self.menuBar().addMenu("&Datei")
        quit_action = QAction("&Beenden", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.quit_app)
        file_menu.addAction(quit_action)

        device_menu = self.menuBar().addMenu("&Gerät")
        refresh_action = QAction("Geräte &aktualisieren", self)
        refresh_action.setShortcut(QKeySequence("F5"))
        refresh_action.triggered.connect(self.initialize_devices)
        device_menu.addAction(refresh_action)
        safe_action = QAction("&Sicheres Profil anwenden", self)
        safe_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        safe_action.triggered.connect(self.apply_safe_profile)
        device_menu.addAction(safe_action)
        repair_action = QAction("&Berechtigungen reparieren", self)
        repair_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        repair_action.triggered.connect(self.repair_permissions)
        device_menu.addAction(repair_action)

        view_menu = self.menuBar().addMenu("&Ansicht")
        tab_names = ("Übersicht", "Kühlung", "RGB", "LCD", "Einstellungen", "Profile", "Über", "Log")
        for index, tab_name in enumerate(tab_names):
            action = QAction(tab_name, self)
            action.setShortcut(QKeySequence(f"Alt+{index + 1}"))
            action.triggered.connect(lambda _checked=False, i=index: self.tabs.setCurrentIndex(i))
            view_menu.addAction(action)

        profile_menu = self.menuBar().addMenu("&Profile")
        open_profiles_action = QAction("Profile verwalten", self)
        open_profiles_action.setShortcut(QKeySequence("Ctrl+P"))
        open_profiles_action.triggered.connect(lambda: self.tabs.setCurrentIndex(5))
        profile_menu.addAction(open_profiles_action)
        for profile_id, title in (("builtin-quiet", "Leise"), ("builtin-balanced", "Ausgeglichen"), ("builtin-performance", "Leistung"), ("builtin-safe", "Sicher")):
            action = QAction(title, self)
            action.triggered.connect(lambda _checked=False, pid=profile_id: self.apply_profile_by_id(pid))
            profile_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Hilfe")
        keyboard_action = QAction("&Tastaturbedienung", self)
        keyboard_action.setShortcut(QKeySequence("F1"))
        keyboard_action.triggered.connect(self.show_keyboard_help)
        help_menu.addAction(keyboard_action)
        about_action = QAction("Zum Bereich &Über", self)
        about_action.setShortcut(QKeySequence("Ctrl+I"))
        about_action.triggered.connect(lambda: self.tabs.setCurrentIndex(6))
        help_menu.addAction(about_action)

    def configure_accessibility(self) -> None:
        self.tabs.setAccessibleName("Hauptbereiche von Kraken Control")
        self.refresh_button.setAccessibleName("Kraken-Geräte aktualisieren")
        self.pump_slider.setAccessibleName("Manuelle Pumpenleistung in Prozent")
        self.fan_slider.setAccessibleName("Manuelle Radiatorlüfterleistung in Prozent")
        self.warning_temp.setAccessibleName("Warnschwelle der Kraken-Wassertemperatur")
        self.critical_temp.setAccessibleName("Kritische Schwelle der Kraken-Wassertemperatur")
        self.cpu_profile_combo.setAccessibleName("AMD-AM5-Prozessorprofil")
        self.cpu_assist_checkbox.setAccessibleName("CPU-Temperatur-Assistenz für die Kraken")
        self.pump_curve_table[1].setAccessibleName("Tabelle der Pumpenkurve nach Wassertemperatur")
        self.fan_curve_table[1].setAccessibleName("Tabelle der Radiatorlüfterkurve nach Wassertemperatur")

    def show_keyboard_help(self) -> None:
        QMessageBox.information(
            self,
            "Tastaturbedienung",
            "F5: Geräte aktualisieren\n"
            "Alt+1 bis Alt+8: Hauptbereiche öffnen\n"
            "Strg+Umschalt+S: sicheres Kühlprofil\n"
            "Strg+Umschalt+R: Geräteberechtigungen reparieren\n"
            "Strg+P: Profile verwalten\n"
            "Strg+I: Über-Bereich\n"
            "Strg+Q: Beenden\n\n"
            "Kurveneditor: Pfeiltasten ändern den gewählten Punkt. Strg+Links/Rechts wählt einen anderen "
            "Punkt, Pos1/Ende wählen ersten/letzten Punkt. Tab und Umschalt+Tab wechseln normal zum nächsten Element."
        )

    def build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        stack = QStackedLayout(central)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self.background_widget = AnimatedBackgroundWidget(central)
        self.content_root = QWidget(central)
        self.content_root.setObjectName("contentRoot")
        self.content_root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stack.addWidget(self.background_widget)
        stack.addWidget(self.content_root)
        stack.setCurrentWidget(self.content_root)
        self.background_widget.lower()
        self.content_root.raise_()

        root = QVBoxLayout(self.content_root)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("💧 Kraken Control by Frelidon")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Unabhängige Open-Source-Steuerung · NZXT Kraken 2023 · liquidctl")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.connection_label = QLabel("● Suche Geräte …")
        self.connection_label.setObjectName("connectionPending")
        self.refresh_button = QPushButton("↻ &Aktualisieren")
        self.refresh_button.clicked.connect(self.initialize_devices)
        header.addWidget(self.connection_label)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        self.tabs.addTab(self.make_dashboard_tab(), "Übersicht")
        self.tabs.addTab(self.make_cooling_tab(), "Kühlung")
        self.tabs.addTab(self.make_rgb_tab(), "RGB")
        self.tabs.addTab(self.make_lcd_tab(), "LCD")
        self.tabs.addTab(self.make_settings_tab(), "Einstellungen")
        self.tabs.addTab(self.make_profiles_tab(), "Profile")
        self.tabs.addTab(self.make_about_tab(), "Über")
        self.tabs.addTab(self.make_log_tab(), "Log")

        footer = QHBoxLayout()
        self.footer_status = QLabel("Bereit")
        self.footer_status.setObjectName("footerStatus")
        footer.addWidget(self.footer_status)
        footer.addStretch()
        self.version_label = QLabel(f"{DISPLAY_NAME} {APP_VERSION}")
        self.version_label.setObjectName("muted")
        footer.addWidget(self.version_label)
        root.addLayout(footer)

    def make_dashboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        cards = QGridLayout()
        self.dashboard_cards_layout = cards
        cards.setSpacing(12)
        self.temp_card = ValueCard("Kraken-Wassertemperatur", "— °C", "Sensor in der Pumpeneinheit")
        self.cpu_temp_card = ValueCard("CPU-Temperatur", "— °C", "AMD k10temp · Tctl/Tdie")
        self.pump_card = ValueCard("Pumpe", "— rpm", "— % Leistung")
        self.fan_card = ValueCard("Radiatorlüfter", "— rpm", "— % Leistung")
        self.firmware_card = ValueCard("Firmware", "—", "LCD 240 × 240")
        cards.addWidget(self.temp_card, 0, 0)
        cards.addWidget(self.cpu_temp_card, 0, 1)
        cards.addWidget(self.pump_card, 0, 2)
        cards.addWidget(self.fan_card, 1, 0)
        cards.addWidget(self.firmware_card, 1, 1)
        self.dashboard_cards = [self.temp_card, self.cpu_temp_card, self.pump_card, self.fan_card, self.firmware_card]
        layout.addLayout(cards)

        warning_box = QGroupBox("Systemzustand")
        warning_layout = QHBoxLayout(warning_box)
        self.health_label = QLabel("Gerät wird geprüft …")
        self.health_label.setObjectName("healthNeutral")
        self.health_label.setWordWrap(True)
        warning_layout.addWidget(self.health_label)
        warning_layout.addStretch()
        init_btn = QPushButton("Geräte initialisieren")
        init_btn.clicked.connect(self.initialize_devices)
        warning_layout.addWidget(init_btn)
        layout.addWidget(warning_box)

        quick = QGroupBox("Schnellprofile")
        ql = QGridLayout(quick)
        profiles = [
            ("Leise", "Pumpe 45 % · Lüfter 35 %", 45, 35),
            ("Ausgeglichen", "Pumpe 55 % · Lüfter 50 %", 55, 50),
            ("Leistung", "Pumpe 75 % · Lüfter 75 %", 75, 75),
            ("Maximum", "Pumpe 100 % · Lüfter 100 %", 100, 100),
        ]
        for col, (name, desc, pump, fan) in enumerate(profiles):
            frame = QFrame()
            frame.setObjectName("profileCard")
            fl = QVBoxLayout(frame)
            title = QLabel(name)
            title.setObjectName("profileTitle")
            details = QLabel(desc)
            details.setObjectName("muted")
            details.setWordWrap(True)
            button = QPushButton("Anwenden")
            button.clicked.connect(lambda _=False, p=pump, f=fan, n=name: self.apply_quick_profile(n, p, f))
            fl.addWidget(title)
            fl.addWidget(details)
            fl.addStretch()
            fl.addWidget(button)
            ql.addWidget(frame, 0, col)
        layout.addWidget(quick)
        layout.addStretch()
        return page

    def make_cooling_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        manual = QGroupBox("Manuelle Steuerung")
        mg = QGridLayout(manual)
        self.pump_slider, self.pump_percent = self.make_percent_slider(20, 100, 52)
        self.fan_slider, self.fan_percent = self.make_percent_slider(0, 100, 52)
        mg.addWidget(QLabel("Pumpe"), 0, 0)
        mg.addWidget(self.pump_slider, 0, 1)
        mg.addWidget(self.pump_percent, 0, 2)
        pump_apply = QPushButton("&Pumpe anwenden")
        pump_apply.clicked.connect(lambda: self.set_fixed_speed("pump", self.pump_slider.value()))
        mg.addWidget(pump_apply, 0, 3)
        mg.addWidget(QLabel("Radiatorlüfter"), 1, 0)
        mg.addWidget(self.fan_slider, 1, 1)
        mg.addWidget(self.fan_percent, 1, 2)
        fan_apply = QPushButton("&Lüfter anwenden")
        fan_apply.clicked.connect(lambda: self.set_fixed_speed("fan", self.fan_slider.value()))
        mg.addWidget(fan_apply, 1, 3)
        layout.addWidget(manual)

        mode_box = QGroupBox("Aktiver Kühlmodus")
        mode_layout = QVBoxLayout(mode_box)
        self.cooling_mode_label = QLabel(
            "Zuletzt durch Kraken Control gesetzt: Pumpe unbekannt · Radiatorlüfter unbekannt"
        )
        self.cooling_mode_label.setWordWrap(True)
        self.cooling_mode_label.setObjectName("infoText")
        self.cooling_mode_hint = QLabel(
            "Ein fester Prozentwert oder ein Schnellprofil ersetzt die jeweilige Kurve in der Kraken-Firmware."
        )
        self.cooling_mode_hint.setWordWrap(True)
        self.cooling_mode_hint.setObjectName("muted")
        mode_layout.addWidget(self.cooling_mode_label)
        mode_layout.addWidget(self.cooling_mode_hint)
        layout.addWidget(mode_box)

        curves = QHBoxLayout()
        self.pump_curve_table = self.make_curve_group(
            "Pumpenkurve nach Wassertemperatur",
            list(DEFAULT_PUMP_CURVE),
            "pump",
        )
        self.fan_curve_table = self.make_curve_group(
            "Lüfterkurve nach Wassertemperatur",
            list(DEFAULT_FAN_CURVE),
            "fan",
        )
        curves.addWidget(self.pump_curve_table[0])
        curves.addWidget(self.fan_curve_table[0])
        layout.addLayout(curves)

        cpu_box = QGroupBox("AMD-AM5-Prozessorprofil und CPU-Temperatur-Assistenz")
        cpu_form = QFormLayout(cpu_box)
        self.cpu_profile_combo = QComboBox()
        self.cpu_profile_combo.addItem("Bitte Prozessor auswählen", "")
        current_family = ""
        for profile in AM5_CPU_PROFILES:
            if profile.family != current_family:
                self.cpu_profile_combo.insertSeparator(self.cpu_profile_combo.count())
                current_family = profile.family
            self.cpu_profile_combo.addItem(profile.model, profile.model)
        self.cpu_profile_combo.currentIndexChanged.connect(self.update_cpu_profile_preview)

        detect_cpu = QPushButton("CPU &automatisch erkennen")
        detect_cpu.clicked.connect(self.detect_and_select_cpu)
        apply_cpu = QPushButton("Profil und empfohlene Kraken-Kurven &laden")
        apply_cpu.clicked.connect(self.apply_selected_cpu_profile)
        self.cpu_assist_checkbox = QCheckBox(
            "Bei hoher CPU-Temperatur Kraken automatisch verstärken (mit 5 °C Hysterese)"
        )
        self.cpu_assist_checkbox.toggled.connect(self.on_cpu_assist_toggled)
        self.cpu_profile_info = QLabel(
            "Die CPU-Tjmax ist nicht die Wassertemperatur. Für die Kraken-Flüssigkeit gelten die separaten Grenzen unten."
        )
        self.cpu_profile_info.setWordWrap(True)
        self.cpu_profile_info.setObjectName("infoText")
        self.cpu_current_label = QLabel("CPU-Sensor: wird gesucht …")
        self.cpu_current_label.setWordWrap(True)
        self.cpu_current_label.setObjectName("muted")
        cpu_buttons = QWidget()
        cpu_buttons_layout = QHBoxLayout(cpu_buttons)
        cpu_buttons_layout.setContentsMargins(0, 0, 0, 0)
        cpu_buttons_layout.addWidget(detect_cpu)
        cpu_buttons_layout.addWidget(apply_cpu)
        cpu_form.addRow("Prozessor", self.cpu_profile_combo)
        cpu_form.addRow(cpu_buttons)
        cpu_form.addRow(self.cpu_assist_checkbox)
        cpu_form.addRow(self.cpu_profile_info)
        cpu_form.addRow(self.cpu_current_label)
        layout.addWidget(cpu_box)

        safety = QGroupBox("Kraken-Wassertemperatur – Sicherheitsgrenzen")
        sf = QFormLayout(safety)
        self.warning_temp = QSpinBox()
        self.warning_temp.setRange(35, 48)
        self.warning_temp.setValue(42)
        self.critical_temp = QSpinBox()
        self.critical_temp.setRange(40, 55)
        self.critical_temp.setValue(50)
        self.auto_max_checkbox = QCheckBox("Bei kritischer Wassertemperatur automatisch 100 % setzen")
        self.auto_max_checkbox.setChecked(True)
        self.expert_mode_checkbox = QCheckBox(
            "Expertenmodus: Sicherheitsgrenzen frei einstellen"
        )
        self.expert_mode_checkbox.setToolTip(
            "Hebt die vorsichtigen App-Bereiche für Warn- und Kritisch-Grenze auf. "
            "Die Hardwaregrenzen der Kraken werden dadurch nicht verändert."
        )
        self.expert_mode_checkbox.toggled.connect(self.toggle_expert_mode)
        self.warning_temp.valueChanged.connect(self.sync_safety_thresholds)
        self.critical_temp.valueChanged.connect(self.sync_safety_thresholds)
        self.safety_note = QLabel(
            "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. "
            "Eine CPU-Tjmax von 89 oder 95 °C darf niemals als Wassergrenze übernommen werden. "
            "Im normalen Modus bleiben vorsichtige Einstellbereiche aktiv."
        )
        self.safety_note.setWordWrap(True)
        self.safety_note.setObjectName("warningText")
        safe_profile = QPushButton("Sicheres Standardprofil anwenden · 65 % / 65 %")
        safe_profile.clicked.connect(self.apply_safe_profile)
        sf.addRow(self.expert_mode_checkbox)
        sf.addRow("Warnung ab", self.warning_temp)
        sf.addRow("Kritisch ab", self.critical_temp)
        sf.addRow(self.auto_max_checkbox)
        sf.addRow(self.safety_note)
        sf.addRow(safe_profile)
        layout.addWidget(safety)

        layout.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    def make_curve_group(
        self, title: str, defaults: list[tuple[int, int]], channel: str
    ) -> tuple[QGroupBox, QTableWidget, CurveEditor]:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        minimum_duty = 20 if channel == "pump" else 0
        channel_label = "Pumpe" if channel == "pump" else "Radiatorlüfter"
        editor = CurveEditor(defaults, minimum_duty, channel_label)
        editor.set_accent_color(QColor(self.accent_hex))

        table = QTableWidget(len(defaults), 2)
        table.setHorizontalHeaderLabels(["Wasser °C", "Leistung %"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(180)
        for row, (temp, duty) in enumerate(defaults):
            table.setItem(row, 0, QTableWidgetItem(str(temp)))
            table.setItem(row, 1, QTableWidgetItem(str(duty)))

        editor.pointsChanged.connect(lambda points, t=table: self.update_curve_table(t, points))
        table.itemChanged.connect(lambda _item, t=table, e=editor: self.update_curve_editor_from_table(t, e))

        buttons = QHBoxLayout()
        reset_btn = QPushButton("&Standardwerte")
        reset_btn.clicked.connect(lambda _=False, e=editor, t=table, p=list(defaults): self.reset_curve_editor(e, t, p))
        apply_btn = QPushButton("Kurve &anwenden")
        apply_btn.clicked.connect(lambda: self.apply_curve(channel, table))
        buttons.addWidget(reset_btn)
        buttons.addStretch()
        buttons.addWidget(apply_btn)

        layout.addWidget(editor)
        layout.addWidget(table)
        layout.addLayout(buttons)
        return group, table, editor

    def update_curve_table(self, table: QTableWidget, points: list[tuple[int, int]]) -> None:
        if self._syncing_curve:
            return
        self._syncing_curve = True
        try:
            table.blockSignals(True)
            table.setRowCount(len(points))
            for row, (temp, duty) in enumerate(points):
                table.setItem(row, 0, QTableWidgetItem(str(temp)))
                table.setItem(row, 1, QTableWidgetItem(str(duty)))
        finally:
            table.blockSignals(False)
            self._syncing_curve = False

    def update_curve_editor_from_table(self, table: QTableWidget, editor: CurveEditor) -> None:
        if self._syncing_curve:
            return
        points: list[tuple[int, int]] = []
        try:
            for row in range(table.rowCount()):
                points.append((int(table.item(row, 0).text()), int(table.item(row, 1).text())))
        except (AttributeError, ValueError):
            return
        temperatures = [temp for temp, _ in points]
        duties = [duty for _, duty in points]
        if any(b <= a for a, b in zip(temperatures, temperatures[1:])):
            return
        if any(b < a for a, b in zip(duties, duties[1:])):
            return
        editor.set_points(points)

    def reset_curve_editor(
        self, editor: CurveEditor, table: QTableWidget, points: list[tuple[int, int]]
    ) -> None:
        editor.set_points(points)
        self.update_curve_table(table, points)

    def make_rgb_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        info = QLabel(
            "Die drei F140/F120-RGB-Core-Lüfter werden über den separaten NZXT 2023 RGB Controller gesteuert."
        )
        info.setWordWrap(True)
        info.setObjectName("infoText")
        layout.addWidget(info)

        box = QGroupBox("Beleuchtung")
        form = QFormLayout(box)
        self.rgb_channel = QComboBox()
        self.rgb_channel.addItems(["sync", "led1", "led2", "led3"])
        self.rgb_mode = QComboBox()
        self.rgb_modes = {
            "Aus": ("off", 0),
            "Statisch": ("fixed", 1),
            "Überblenden": ("fading", 2),
            "Pulsieren": ("pulse", 1),
            "Atmen": ("breathing", 1),
            "Kerze": ("candle", 1),
            "Sternennacht": ("starry-night", 1),
            "Spektrum-Welle": ("spectrum-wave", 0),
            "Regenbogenfluss": ("rainbow-flow", 0),
            "Super-Regenbogen": ("super-rainbow", 0),
            "Regenbogen-Puls": ("rainbow-pulse", 0),
            "Marquee": ("marquee-4", 1),
            "Abwechselnd": ("alternating-4", 2),
            "Bewegend abwechselnd": ("moving-alternating-4", 2),
            "Flügel": ("wings", 1),
        }
        self.rgb_mode.addItems(self.rgb_modes.keys())
        self.rgb_mode.currentTextChanged.connect(self.update_rgb_controls)

        color_row = QWidget()
        color_layout = QHBoxLayout(color_row)
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color1_hex = "00aaff"
        self.color2_hex = "ffffff"
        self.color1_button = QPushButton("Farbe 1 · #00aaff")
        self.color2_button = QPushButton("Farbe 2 · #ffffff")
        self.color1_button.clicked.connect(lambda: self.pick_color(1))
        self.color2_button.clicked.connect(lambda: self.pick_color(2))
        color_layout.addWidget(self.color1_button)
        color_layout.addWidget(self.color2_button)

        self.rgb_speed = QComboBox()
        self.rgb_speed.addItems(["slowest", "slower", "normal", "faster", "fastest"])
        self.rgb_speed.setCurrentText("normal")
        self.rgb_direction = QComboBox()
        self.rgb_direction.addItems(["forward", "backward"])

        form.addRow("Kanal", self.rgb_channel)
        form.addRow("Effekt", self.rgb_mode)
        form.addRow("Farben", color_row)
        form.addRow("Geschwindigkeit", self.rgb_speed)
        form.addRow("Richtung", self.rgb_direction)
        apply_btn = QPushButton("RGB anwenden")
        apply_btn.clicked.connect(self.apply_rgb)
        form.addRow(apply_btn)
        layout.addWidget(box)

        quick = QGroupBox("Schnellfarben")
        qg = QHBoxLayout(quick)
        for label, color in [
            ("Eisblau", "00aaff"),
            ("Weiß", "ffffff"),
            ("Rot", "ff2030"),
            ("Lila", "9b5cff"),
            ("Grün", "40ff80"),
            ("Orange", "ff8a20"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, c=color: self.apply_quick_color(c))
            qg.addWidget(btn)
        layout.addWidget(quick)
        layout.addStretch()
        self.update_rgb_controls()
        return page

    def make_lcd_tab(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(18)

        preview_box = QGroupBox("Runde LCD-Vorschau · 240 × 240")
        pv = QVBoxLayout(preview_box)
        self.preview = QLabel("Kein Bild ausgewählt")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setFixedSize(300, 300)
        self.preview.setObjectName("lcdPreview")
        self.preview.setScaledContents(False)
        pv.addWidget(self.preview, alignment=Qt.AlignCenter)
        self.file_name_label = QLabel("—")
        self.file_name_label.setAlignment(Qt.AlignCenter)
        self.file_name_label.setWordWrap(True)
        self.file_name_label.setObjectName("muted")
        pv.addWidget(self.file_name_label)
        preview_hint = QLabel(
            "Die Hardware nimmt ein quadratisches 240×240-Bild an. Die Vorschau zeigt den tatsächlich sichtbaren runden Bereich."
        )
        preview_hint.setWordWrap(True)
        preview_hint.setObjectName("infoText")
        pv.addWidget(preview_hint)
        layout.addWidget(preview_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_widget = QWidget()
        controls = QVBoxLayout(controls_widget)
        controls.setContentsMargins(4, 4, 8, 4)

        display_box = QGroupBox("Displayeinstellungen")
        form = QFormLayout(display_box)
        self.lcd_brightness, self.lcd_brightness_label = self.make_percent_slider(0, 100, 100)
        bright_row = QWidget()
        br = QHBoxLayout(bright_row)
        br.setContentsMargins(0, 0, 0, 0)
        br.addWidget(self.lcd_brightness)
        br.addWidget(self.lcd_brightness_label)
        self.lcd_orientation = QComboBox()
        self.lcd_orientation.addItems(["0", "90", "180", "270"])
        apply_display = QPushButton("Helligkeit und Ausrichtung anwenden")
        apply_display.clicked.connect(self.apply_lcd_display_settings)
        form.addRow("Helligkeit", bright_row)
        form.addRow("Ausrichtung", self.lcd_orientation)
        form.addRow(apply_display)
        controls.addWidget(display_box)

        image_box = QGroupBox("Eigenes Bild")
        il = QVBoxLayout(image_box)
        choose = QPushButton("PNG, JPG oder GIF auswählen")
        choose.clicked.connect(self.choose_lcd_file)
        send = QPushButton("Bild einmal übertragen")
        send.clicked.connect(self.send_lcd_now)
        liquid = QPushButton("Zur Flüssigkeitstemperatur zurück")
        liquid.clicked.connect(self.show_liquid_screen)

        self.lcd_mode_label = QLabel("LCD-Modus: bereit")
        self.lcd_mode_label.setObjectName("infoText")
        self.lcd_mode_label.setWordWrap(True)

        self.keep_lcd_checkbox = QCheckBox("Automatisch erneut senden (Fallback)")
        self.keep_lcd_checkbox.setToolTip(
            "Nur aktivieren, wenn die Kraken nach einigen Sekunden selbstständig zum Standardbild zurückwechselt."
        )
        self.keep_lcd_checkbox.toggled.connect(self.toggle_lcd_keepalive)
        interval_row = QHBoxLayout()
        self.keepalive_interval_label = QLabel("Erneut senden alle")
        interval_row.addWidget(self.keepalive_interval_label)
        self.lcd_interval = QSpinBox()
        self.lcd_interval.setRange(5, 60)
        self.lcd_interval.setValue(DEFAULT_LCD_INTERVAL)
        self.lcd_interval.setSuffix(" s")
        self.lcd_interval.valueChanged.connect(self.update_keepalive_interval)
        interval_row.addWidget(self.lcd_interval)
        interval_row.addStretch()

        self.keepalive_notice = QLabel(
            "Sicherheitshinweis: Der Fallback sendet das Bild wiederholt an die Kraken. Langzeitwirkungen auf den "
            "Displayspeicher sind nicht ausreichend bekannt. Nur aktivieren, wenn das Display wirklich zurückspringt; "
            "standardmäßig bleibt diese Funktion ausgeschaltet."
        )
        self.keepalive_notice.setWordWrap(True)
        self.keepalive_notice.setObjectName("infoText")

        self.gif_notice = QLabel(
            "Firmware 2.x unterstützt über liquidctl kein echtes GIF. Die App verwendet bei GIF-Dateien das erste Bild."
        )
        self.gif_notice.setWordWrap(True)
        self.gif_notice.setObjectName("warningText")
        il.addWidget(choose)
        il.addWidget(send)
        il.addWidget(liquid)
        il.addWidget(self.lcd_mode_label)
        il.addWidget(self.keep_lcd_checkbox)
        il.addLayout(interval_row)
        il.addWidget(self.keepalive_notice)
        il.addWidget(self.gif_notice)
        controls.addWidget(image_box)

        clock_box = QGroupBox("Uhr auf dem LCD")
        cf = QFormLayout(clock_box)
        self.clock_format = QComboBox()
        self.clock_format.addItem("24 Stunden · 13:30", "24")
        self.clock_format.addItem("12 Stunden · 1:30 PM", "12")
        self.clock_show_date = QCheckBox("Datum unter der Uhrzeit anzeigen")
        self.clock_show_date.setChecked(True)
        self.clock_font_size = QSpinBox()
        self.clock_font_size.setRange(42, 88)
        self.clock_font_size.setValue(64)
        self.clock_font_size.setSuffix(" px")
        self.clock_auto_resend = QCheckBox("Uhr automatisch erneut senden")
        self.clock_auto_resend.setChecked(True)
        self.clock_auto_resend.setToolTip(
            "Sendet das aktuelle Minutenbild zusätzlich regelmäßig erneut, falls die Kraken zum Standardbild zurückspringt."
        )
        self.clock_auto_resend.toggled.connect(self.update_clock_keepalive_controls)
        self.clock_resend_interval = QSpinBox()
        self.clock_resend_interval.setRange(5, 60)
        self.clock_resend_interval.setValue(DEFAULT_LCD_INTERVAL)
        self.clock_resend_interval.setSuffix(" s")
        self.clock_resend_interval.valueChanged.connect(self.update_clock_keepalive_interval)

        color_row = QWidget()
        clr = QHBoxLayout(color_row)
        clr.setContentsMargins(0, 0, 0, 0)
        self.clock_text_button = QPushButton("Text · #ffffff")
        self.clock_background_button = QPushButton("Hintergrund · #10141c")
        self.clock_text_button.clicked.connect(lambda: self.pick_clock_color("text"))
        self.clock_background_button.clicked.connect(lambda: self.pick_clock_color("background"))
        clr.addWidget(self.clock_text_button)
        clr.addWidget(self.clock_background_button)

        clock_buttons = QWidget()
        cb = QHBoxLayout(clock_buttons)
        cb.setContentsMargins(0, 0, 0, 0)
        preview_clock = QPushButton("Vorschau")
        start_clock = QPushButton("Uhr starten")
        stop_clock = QPushButton("Uhr anhalten")
        preview_clock.clicked.connect(self.preview_clock_image)
        start_clock.clicked.connect(self.start_clock_mode)
        stop_clock.clicked.connect(self.stop_clock_mode)
        cb.addWidget(preview_clock)
        cb.addWidget(start_clock)
        cb.addWidget(stop_clock)

        self.clock_status_label = QLabel(
            "Experimentell: Die Uhr überträgt einmal pro Minute ein neues statisches Bild. Langzeitwirkungen häufiger "
            "LCD-Uploads sind nicht ausreichend bekannt; Sekunden werden bewusst nicht übertragen."
        )
        self.clock_status_label.setWordWrap(True)
        self.clock_status_label.setObjectName("infoText")
        cf.addRow("Zeitformat", self.clock_format)
        cf.addRow(self.clock_show_date)
        cf.addRow("Schriftgröße", self.clock_font_size)
        cf.addRow("Farben", color_row)
        cf.addRow(self.clock_auto_resend)
        cf.addRow("Erneut senden alle", self.clock_resend_interval)
        cf.addRow(clock_buttons)
        cf.addRow(self.clock_status_label)
        controls.addWidget(clock_box)

        startup_box = QGroupBox("Automatisches Wiederherstellen")
        sl = QVBoxLayout(startup_box)
        self.restore_lcd_checkbox = QCheckBox("Gewähltes Bild beim Programmstart wieder anzeigen")
        sl.addWidget(self.restore_lcd_checkbox)
        controls.addWidget(startup_box)
        controls.addStretch()
        scroll.setWidget(controls_widget)
        layout.addWidget(scroll, 1)
        return page

    def make_settings_tab(self) -> QWidget:
        page = QWidget()
        page.setObjectName("settingsPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        scroll.setAccessibleName("Scrollbare Einstellungen")
        scroll.viewport().setAutoFillBackground(False)

        content = QWidget()
        content.setObjectName("settingsContent")
        content.setMinimumWidth(820)
        content.setAutoFillBackground(False)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 14, 22, 22)
        layout.setSpacing(16)

        design_box = QGroupBox("Design")
        design_form = QFormLayout(design_box)
        self.theme_mode_combo = QComboBox()
        self.theme_mode_combo.addItem("Systemmodus", "system")
        self.theme_mode_combo.addItem("Hell", "light")
        self.theme_mode_combo.addItem("Dunkel", "dark")
        mode_index = max(0, self.theme_mode_combo.findData(self.theme_mode))
        self.theme_mode_combo.setCurrentIndex(mode_index)

        accent_row = QWidget()
        accent_layout = QHBoxLayout(accent_row)
        accent_layout.setContentsMargins(0, 0, 0, 0)
        self.accent_hex_input = QLineEdit(self.accent_hex)
        self.accent_hex_input.setMaxLength(7)
        self.accent_hex_input.setPlaceholderText("#00aaff")
        self.accent_hex_input.setAccessibleName("Akzentfarbe als Hex-Code")
        accent_picker = QPushButton("Farbe auswählen")
        accent_picker.clicked.connect(self.pick_theme_accent)
        accent_layout.addWidget(self.accent_hex_input)
        accent_layout.addWidget(accent_picker)

        presets = QWidget()
        preset_layout = QHBoxLayout(presets)
        preset_layout.setContentsMargins(0, 0, 0, 0)
        for label, color in [("Eisblau", "#00aaff"), ("Blau", "#3b82f6"), ("Grün", "#22c55e"), ("Lila", "#a855f7"), ("Orange", "#f97316")]:
            button = QPushButton(label)
            button.setToolTip(color)
            button.clicked.connect(lambda _=False, c=color: self.set_accent_preset(c))
            preset_layout.addWidget(button)

        self.design_preview = QLabel("Akzentvorschau · Schaltflächen, Tabs, Regler und Kurven")
        self.design_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.design_preview.setMinimumHeight(42)
        self.design_preview.setObjectName("designPreview")
        apply_design = QPushButton("Design anwenden")
        apply_design.clicked.connect(self.apply_design_settings)
        self.theme_mode_combo.currentIndexChanged.connect(self.apply_design_settings)
        self.accent_hex_input.returnPressed.connect(self.apply_design_settings)

        design_form.addRow("Darstellung", self.theme_mode_combo)
        design_form.addRow("Eigene Akzentfarbe", accent_row)
        design_form.addRow("Voreinstellungen", presets)
        design_form.addRow(self.design_preview)
        design_form.addRow(apply_design)
        layout.addWidget(design_box)

        display_box = QGroupBox("Anzeige und DPI")
        display_form = QFormLayout(display_box)
        self.display_info_label = QLabel("Monitor wird erkannt …")
        self.display_info_label.setWordWrap(True)
        self.display_auto_checkbox = QCheckBox("Automatisch an Monitor und Seitenverhältnis anpassen")
        self.display_auto_checkbox.setChecked(self.display_auto)
        self.ui_scale_spin = QSpinBox()
        self.ui_scale_spin.setRange(80, 180)
        self.ui_scale_spin.setValue(self.ui_scale_percent)
        self.ui_scale_spin.setSuffix(" %")
        self.display_layout_combo = QComboBox()
        self.display_layout_combo.addItem("Automatisch", "auto")
        self.display_layout_combo.addItem("Kompakt · 16:10", "16:10")
        self.display_layout_combo.addItem("Standard · 16:9", "16:9")
        self.display_layout_combo.addItem("Ultrawide · 21:9", "21:9")
        self.display_layout_combo.addItem("Super-Ultrawide · 32:9", "32:9")
        display_index = self.display_layout_combo.findData(self.display_layout)
        self.display_layout_combo.setCurrentIndex(max(0, display_index))
        display_buttons = QWidget()
        display_buttons_layout = QHBoxLayout(display_buttons)
        display_buttons_layout.setContentsMargins(0, 0, 0, 0)
        detect_display = QPushButton("Monitor neu erkennen")
        detect_display.clicked.connect(self.refresh_display_info)
        apply_display = QPushButton("Anzeige anwenden")
        apply_display.clicked.connect(self.apply_display_settings)
        display_buttons_layout.addWidget(detect_display)
        display_buttons_layout.addWidget(apply_display)
        display_note = QLabel(
            "Die App ändert nicht die Linux-Bildschirmauflösung. Qt arbeitet mit geräteunabhängigen Pixeln; "
            "hier werden App-Skalierung und responsives Layout angepasst."
        )
        display_note.setWordWrap(True)
        display_note.setObjectName("muted")
        display_form.addRow(self.display_info_label)
        display_form.addRow(self.display_auto_checkbox)
        display_form.addRow("App-Skalierung", self.ui_scale_spin)
        display_form.addRow("Layoutvorgabe", self.display_layout_combo)
        display_form.addRow(display_buttons)
        display_form.addRow(display_note)
        layout.addWidget(display_box)

        background_box = QGroupBox("Animierter Hintergrund")
        background_form = QFormLayout(background_box)
        self.background_enabled_checkbox = QCheckBox("Animation aktivieren")
        self.background_enabled_checkbox.setChecked(self.background_enabled)
        self.background_enabled_checkbox.setAccessibleName("Animation aktivieren")
        self.background_theme_combo = QComboBox()
        self.background_theme_combo.addItems(AnimatedBackgroundWidget.THEMES)
        self.background_theme_combo.setCurrentText(
            self.background_theme if self.background_theme in AnimatedBackgroundWidget.THEMES else DEFAULT_BACKGROUND_THEME
        )
        self.background_theme_combo.setAccessibleName("Hintergrundthema")
        self.background_enabled_checkbox.toggled.connect(self.on_background_enabled_toggled)
        self.background_fps_combo = QComboBox()
        for fps in (15, 30, 60):
            self.background_fps_combo.addItem(f"{fps} FPS", fps)
        fps_index = self.background_fps_combo.findData(self.background_fps)
        self.background_fps_combo.setCurrentIndex(max(0, fps_index))
        self.background_intensity_slider, self.background_intensity_label = self.make_percent_slider(5, 100, self.background_intensity)
        self.background_pause_checkbox = QCheckBox("Pausieren, wenn die App nicht aktiv ist")
        self.background_pause_checkbox.setChecked(self.background_pause_inactive)
        background_buttons = QWidget()
        background_buttons_layout = QHBoxLayout(background_buttons)
        background_buttons_layout.setContentsMargins(0, 0, 0, 0)
        apply_background = QPushButton("Hintergrund anwenden")
        apply_background.clicked.connect(self.apply_background_settings)
        disable_background = QPushButton("Animation ausschalten")
        disable_background.clicked.connect(self.disable_background)
        background_buttons_layout.addWidget(apply_background)
        background_buttons_layout.addWidget(disable_background)
        background_note = QLabel(
            "Alle zwölf Animationen werden prozedural aus dem GPL-Quellcode erzeugt. Version 2.9.6 rendert sie "
            "in einer sicheren CPU-Offscreen-Ebene hinter der Bedienoberfläche. Beim Ausschalten bleibt das zuletzt "
            "gewählte Thema gespeichert und kann direkt wieder aktiviert werden. Es werden keine fremden Videos, "
            "Bilder oder Online-Downloads mitgeliefert."
        )
        background_note.setWordWrap(True)
        background_note.setObjectName("muted")
        background_form.addRow(self.background_enabled_checkbox)
        background_form.addRow("Thema", self.background_theme_combo)
        background_form.addRow("Bildrate", self.background_fps_combo)
        background_form.addRow("Intensität", self.background_intensity_slider)
        background_form.addRow(self.background_pause_checkbox)
        background_form.addRow(background_buttons)
        background_form.addRow(background_note)
        layout.addWidget(background_box)

        app_box = QGroupBox("Programm")
        form = QFormLayout(app_box)
        self.autostart_checkbox = QCheckBox("Mit dem Desktop starten")
        self.autostart_checkbox.toggled.connect(self.set_autostart)
        self.tray_checkbox = QCheckBox("Beim Schließen im Infobereich weiterlaufen")
        self.tray_checkbox.setChecked(True)
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 30)
        self.refresh_interval.setValue(3)
        self.refresh_interval.setSuffix(" s")
        self.refresh_interval.valueChanged.connect(self.update_status_interval)
        form.addRow(self.autostart_checkbox)
        form.addRow(self.tray_checkbox)
        form.addRow("Status-Aktualisierung", self.refresh_interval)
        rerun_setup = QPushButton("Einrichtungsassistent erneut starten")
        rerun_setup.clicked.connect(lambda: self.maybe_show_setup_wizard(force=True))
        form.addRow(rerun_setup)
        layout.addWidget(app_box)

        dependency_box = QGroupBox("Abhängigkeiten")
        dependency_layout = QVBoxLayout(dependency_box)
        self.dependency_status = QLabel("Wird geprüft …")
        self.dependency_status.setWordWrap(True)
        dependency_buttons = QHBoxLayout()
        check_dependencies_button = QPushButton("Abhängigkeiten &prüfen")
        check_dependencies_button.clicked.connect(self.refresh_dependency_status)
        install_dependencies_button = QPushButton("Fehlende Pakete &installieren")
        install_dependencies_button.clicked.connect(self.install_missing_dependencies)
        dependency_buttons.addWidget(check_dependencies_button)
        dependency_buttons.addWidget(install_dependencies_button)
        dependency_buttons.addStretch()
        dependency_note = QLabel(
            "Auf Nobara/Fedora installiert Kraken Control ausschließlich die fest vorgegebenen Pakete "
            "liquidctl, python3-pyside6 und python3-pillow über DNF. Vorher erscheint eine Bestätigung "
            "und anschließend die normale Administratorabfrage. Es werden keine fremden Paketquellen hinzugefügt."
        )
        dependency_note.setWordWrap(True)
        dependency_note.setObjectName("muted")
        dependency_layout.addWidget(self.dependency_status)
        dependency_layout.addLayout(dependency_buttons)
        dependency_layout.addWidget(dependency_note)
        layout.addWidget(dependency_box)

        device_box = QGroupBox("Gerätezugriff")
        dl = QVBoxLayout(device_box)
        self.access_status = QLabel("Wird geprüft …")
        self.access_status.setWordWrap(True)
        test_access = QPushButton("Zugriff ohne sudo &testen")
        test_access.clicked.connect(self.test_access)
        repair_access = QPushButton("Berechtigungen mit Administratorabfrage &reparieren")
        repair_access.clicked.connect(self.repair_permissions)
        permission_note = QLabel(
            "Schreibzugriff auf /dev/hidraw ist für Pumpen-, Lüfter- und Kurvenänderungen erforderlich. "
            "Nach einer neuen udev-Regel kann Ab- und Anstecken oder ein Neustart nötig sein."
        )
        permission_note.setWordWrap(True)
        permission_note.setObjectName("muted")
        dl.addWidget(self.access_status)
        dl.addWidget(test_access)
        dl.addWidget(repair_access)
        dl.addWidget(permission_note)
        dl.addWidget(self.make_external_link("Offizielle liquidctl-udev-Regeln", LIQUIDCTL_UDEV_URL))
        layout.addWidget(device_box)

        about_box = QGroupBox("Hinweis")
        al = QVBoxLayout(about_box)
        about = QLabel(
            "Experimentelle Open-Source-Beta: Nutzung auf eigenes Risiko. Die Anwendung nutzt ausschließlich liquidctl. "
            "Die automatische Temperatursicherung wirkt nur, solange Programm, USB-Verbindung und Statusabfrage funktionieren. "
            "Wiederholte LCD-Uploads sind standardmäßig deaktiviert."
        )
        about.setWordWrap(True)
        al.addWidget(about)
        layout.addWidget(about_box)
        layout.addStretch()

        scroll.setWidget(content)
        page_layout.addWidget(scroll, 1)
        return page

    def make_profiles_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        intro = QLabel(
            "Profile speichern Einstellungen kategorisiert. Gesamtprofile können Kühlung, LCD, RGB, Design, "
            "Hintergrund und Anzeige gemeinsam wiederherstellen."
        )
        intro.setWordWrap(True)
        intro.setObjectName("infoText")
        outer.addWidget(intro)

        startup_box = QGroupBox("Profil beim Start")
        startup_form = QFormLayout(startup_box)
        self.profile_startup_combo = QComboBox()
        self.profile_startup_combo.currentIndexChanged.connect(self.profile_startup_changed)
        startup_form.addRow("Automatisch laden", self.profile_startup_combo)
        startup_note = QLabel("Kühlungsprofile werden erst nach erfolgreicher Kraken-Erkennung übertragen.")
        startup_note.setWordWrap(True)
        startup_note.setObjectName("muted")
        startup_form.addRow(startup_note)
        outer.addWidget(startup_box)

        editor = QGroupBox("Profil erstellen oder aktualisieren")
        form = QFormLayout(editor)
        self.profile_name_input = QLineEdit()
        self.profile_name_input.setPlaceholderText("z. B. Gaming, Leise Nacht oder Sommer")
        self.profile_category_combo = QComboBox()
        self.profile_category_combo.addItems(["Gesamt", "Kühlung", "LCD", "RGB", "Design"])
        self.profile_description_input = QLineEdit()
        self.profile_description_input.setPlaceholderText("Kurze Beschreibung")
        profile_editor_buttons = QWidget()
        peb = QHBoxLayout(profile_editor_buttons)
        peb.setContentsMargins(0, 0, 0, 0)
        create_profile = QPushButton("Als neues Profil speichern")
        create_profile.clicked.connect(self.create_profile_from_current)
        update_profile = QPushButton("Ausgewähltes Profil aktualisieren")
        update_profile.clicked.connect(self.update_selected_profile)
        peb.addWidget(create_profile)
        peb.addWidget(update_profile)
        form.addRow("Name", self.profile_name_input)
        form.addRow("Kategorie", self.profile_category_combo)
        form.addRow("Beschreibung", self.profile_description_input)
        form.addRow(profile_editor_buttons)
        outer.addWidget(editor)

        self.profiles_table = QTableWidget(0, 4)
        self.profiles_table.setHorizontalHeaderLabels(["Name", "Kategorie", "Beschreibung", "Typ"])
        self.profiles_table.verticalHeader().setVisible(False)
        self.profiles_table.horizontalHeader().setStretchLastSection(True)
        self.profiles_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.profiles_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.profiles_table.itemSelectionChanged.connect(self.on_profile_selection_changed)
        self.profiles_table.doubleClicked.connect(lambda _index: self.apply_selected_profile())
        outer.addWidget(self.profiles_table, 1)

        buttons = QHBoxLayout()
        apply_profile = QPushButton("Profil anwenden")
        apply_profile.clicked.connect(self.apply_selected_profile)
        duplicate_profile = QPushButton("Duplizieren")
        duplicate_profile.clicked.connect(self.duplicate_selected_profile)
        rename_profile = QPushButton("Umbenennen")
        rename_profile.clicked.connect(self.rename_selected_profile)
        delete_profile = QPushButton("Löschen")
        delete_profile.clicked.connect(self.delete_selected_profile)
        import_profile = QPushButton("Importieren")
        import_profile.clicked.connect(self.import_profiles)
        export_profile = QPushButton("Exportieren")
        export_profile.clicked.connect(self.export_selected_profile)
        for button in (apply_profile, duplicate_profile, rename_profile, delete_profile, import_profile, export_profile):
            buttons.addWidget(button)
        buttons.addStretch()
        outer.addLayout(buttons)

        self.profile_status_label = QLabel("Noch kein Profil ausgewählt.")
        self.profile_status_label.setWordWrap(True)
        self.profile_status_label.setObjectName("muted")
        outer.addWidget(self.profile_status_label)
        self.load_profiles()
        self.refresh_profiles_table()
        return page

    @staticmethod
    def make_external_link(text: str, url: str) -> QLabel:
        """Create an accessible link that opens in the system browser."""
        label = QLabel(f'<a href="{url}">{text}</a>')
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setToolTip(url)
        label.setAccessibleName(f"{text}: {url}")
        label.setWordWrap(True)
        return label

    @staticmethod
    def runtime_component_versions() -> list[tuple[str, str]]:
        liquidctl_version = "nicht erkannt"
        try:
            completed = subprocess.run(
                [LIQUIDCTL, "--version"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            liquidctl_version = (completed.stdout or completed.stderr).strip() or "unbekannt"
        except (OSError, subprocess.SubprocessError):
            pass
        distro = "Linux"
        try:
            values = {}
            for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value.strip().strip('"')
            distro = values.get("PRETTY_NAME", distro)
        except OSError:
            pass
        return [
            ("Kraken Control", APP_VERSION),
            ("Python", platform.python_version()),
            ("PySide6", PYSIDE_VERSION),
            ("Qt", qVersion()),
            ("liquidctl", liquidctl_version),
            ("Pillow", getattr(PIL, "__version__", "nicht installiert") if PIL is not None else "nicht installiert"),
            ("Linux-Distribution", distro),
            ("Kernel", platform.release()),
        ]

    def make_about_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        project = QGroupBox("Kraken Control by Frelidon")
        pl = QVBoxLayout(project)
        title = QLabel(f"Kraken Control by Frelidon · Version {APP_VERSION}")
        title.setObjectName("mainTitle")
        description = QLabel(
            "Unabhängige grafische Open-Source-Steuerung ausschließlich für unterstützte NZXT-Kraken-Geräte unter Linux. "
            "Die Anwendung verwaltet den Kraken-Kühlkreislauf, die Pumpe, direkt zugehörige Radiatorlüfter, LCD und RGB. "
            "Version 2.9 ergänzt Ersteinrichtung, responsive Anzeige-/DPI-Anpassung, prozedurale Animationen und kategorisierte Profile. "
            "Version 2.9.6 verhindert Berechtigungsdialog-Spam im Hintergrund, nutzt Direct Access für alle Kraken-Kühlungswrites und behält alle Grafik-, Scroll-, Profil- und Logging-Fixes bei. "
            "Der Kurven-Direktzugriff aus 2.7.1 bleibt enthalten. "
            "Mainboard-, Gehäuse- und GPU-Lüfter gehören bewusst nicht zum Funktionsumfang. "
            "Status: experimentelle Beta, Nutzung auf eigenes Risiko. Dieses Projekt ist nicht mit NZXT verbunden, "
            "wird nicht von NZXT unterstützt und verwendet keine NZXT-Logos. Ein Dank gilt NZXT für die Entwicklung "
            "der zugrunde liegenden Kühlhardware."
        )
        description.setWordWrap(True)
        repo_notice = QLabel(
            "Projekt-Repository und aktueller Quellcode: siehe README.md beziehungsweise die Seite, von der "
            "diese Version bezogen wurde."
        )
        repo_notice.setWordWrap(True)
        repo_notice.setObjectName("muted")
        pl.addWidget(title)
        pl.addWidget(description)
        pl.addWidget(repo_notice)
        layout.addWidget(project)

        scope_box = QGroupBox("Projektumfang – bewusst auf die Kraken begrenzt")
        scope_layout = QVBoxLayout(scope_box)
        scope_included = QLabel(
            "<b>Enthalten:</b> Wassertemperatur, Kraken-Pumpe, von der Kraken gemeldete beziehungsweise "
            "gesteuerte Radiatorlüfter, LCD sowie der separate NZXT 2023 RGB Controller."
        )
        scope_included.setWordWrap(True)
        scope_excluded = QLabel(
            "<b>Nicht enthalten:</b> Mainboard-Lüfteranschlüsse, zusätzliche Gehäuselüfter, GPU-Lüfter, "
            "AMD-Grafiksteuerung sowie allgemeines System-Tuning. Solche Funktionen sollen in eigenständigen "
            "Werkzeugen entstehen und können später über eine gemeinsame Oberfläche verbunden werden."
        )
        scope_excluded.setWordWrap(True)
        scope_excluded.setObjectName("muted")
        scope_layout.addWidget(scope_included)
        scope_layout.addWidget(scope_excluded)
        layout.addWidget(scope_box)

        credits = QGroupBox("Entwicklung und KI-Unterstützung")
        cl = QGridLayout(credits)
        credit_text = QLabel(
            "Projektleitung und Veröffentlichung: Frelidon. Mit Unterstützung von ChatGPT (GPT-5.6 Thinking) "
            "von OpenAI bei Programmierung, Dokumentation und Tests. ChatGPT ist kein Laufzeitbestandteil der App. "
            "Die Nennung stellt keine offizielle Unterstützung oder Partnerschaft durch OpenAI dar."
        )
        credit_text.setWordWrap(True)
        cl.addWidget(credit_text, 0, 0, 1, 4)
        cl.addWidget(self.make_external_link("OpenAI", OPENAI_WEBSITE_URL), 1, 0)
        cl.addWidget(self.make_external_link("ChatGPT", CHATGPT_URL), 1, 1)
        cl.addWidget(self.make_external_link("OpenAI auf GitHub", OPENAI_GITHUB_URL), 1, 2)
        cl.setColumnStretch(3, 1)
        layout.addWidget(credits)

        software_box = QGroupBox("Verwendete Software – Website, Quellcode und Lizenz")
        sg = QGridLayout(software_box)
        headers = ("Komponente", "Aufgabe", "Website / Dokumentation", "Quellcode", "Lizenz")
        for column, header in enumerate(headers):
            header_label = QLabel(f"<b>{header}</b>")
            sg.addWidget(header_label, 0, column)

        software = [
            (
                "liquidctl",
                "Hardwarezugriff auf Kraken, Pumpe, Lüfter, RGB und LCD",
                ("Dokumentation", LIQUIDCTL_DOCS_URL),
                ("GitHub", LIQUIDCTL_GITHUB_URL),
                ("GPL-3.0-or-later", LIQUIDCTL_LICENSE_URL),
            ),
            (
                "Python",
                "Programmiersprache und Laufzeitumgebung",
                ("python.org", PYTHON_WEBSITE_URL),
                ("CPython auf GitHub", PYTHON_GITHUB_URL),
                ("PSF License 2", PYTHON_LICENSE_URL),
            ),
            (
                "PySide6 / Qt for Python",
                "Grafische Oberfläche, Timer, Einstellungen und Prozesse",
                ("Qt-Dokumentation", PYSIDE_DOCS_URL),
                ("GitHub", PYSIDE_GITHUB_URL),
                ("Qt-for-Python-Lizenzen", PYSIDE_LICENSE_URL),
            ),
            (
                "Pillow",
                "Vorbereitung, Beschnitt und Erzeugung der LCD-Bilder",
                ("Dokumentation", PILLOW_DOCS_URL),
                ("GitHub", PILLOW_GITHUB_URL),
                ("Lizenzdatei", PILLOW_LICENSE_URL),
            ),
        ]
        for row, (name, purpose, website, source, license_info) in enumerate(software, start=1):
            name_label = QLabel(f"<b>{name}</b>")
            purpose_label = QLabel(purpose)
            purpose_label.setWordWrap(True)
            sg.addWidget(name_label, row, 0)
            sg.addWidget(purpose_label, row, 1)
            sg.addWidget(self.make_external_link(*website), row, 2)
            sg.addWidget(self.make_external_link(*source), row, 3)
            sg.addWidget(self.make_external_link(*license_info), row, 4)
        sg.setColumnStretch(1, 2)
        layout.addWidget(software_box)

        versions_box = QGroupBox("Komponenten- und Laufzeitversionen")
        versions_layout = QGridLayout(versions_box)
        for column, header in enumerate(("Komponente", "Erkannte Version")):
            versions_layout.addWidget(QLabel(f"<b>{header}</b>"), 0, column)
        for row, (component, version) in enumerate(self.runtime_component_versions(), start=1):
            versions_layout.addWidget(QLabel(component), row, 0)
            value = QLabel(version)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | Qt.TextInteractionFlag.TextSelectableByMouse)
            versions_layout.addWidget(value, row, 1)
        versions_layout.setColumnStretch(1, 1)
        layout.addWidget(versions_box)

        cpu_sources = QGroupBox("AMD-AM5-Temperaturprofile")
        cpu_sources_layout = QVBoxLayout(cpu_sources)
        cpu_sources_text = QLabel(
            "Die auswählbaren CPU-Profile nutzen die von AMD veröffentlichte maximale Betriebstemperatur (Tjmax). "
            "Ryzen 9000, Ryzen 8000G und normale Ryzen-7000-Modelle sind in den aufgenommenen Profilen mit 95 °C "
            "hinterlegt; Ryzen 7000 X3D mit 89 °C. Die Kraken-Wassergrenzen bleiben davon unabhängig."
        )
        cpu_sources_text.setWordWrap(True)
        cpu_sources_layout.addWidget(cpu_sources_text)
        cpu_sources_layout.addWidget(self.make_external_link("AMD Prozessorspezifikationen", AMD_PROCESSOR_SPECS_URL))
        cpu_sources_layout.addWidget(self.make_external_link("Linux-k10temp-Dokumentation", K10TEMP_DOCS_URL))
        layout.addWidget(cpu_sources)

        license_box = QGroupBox("Lizenz von Kraken Control")
        ll = QHBoxLayout(license_box)
        license_text = QLabel(
            "Kraken Control by Frelidon steht unter GNU General Public License v3.0 oder später "
            "(GPL-3.0-or-later). Die vollständige Lizenz liegt dem Paket als LICENSE bei."
        )
        license_text.setWordWrap(True)
        ll.addWidget(license_text, 1)
        ll.addWidget(self.make_external_link("Offizielle GPL-3.0-Seite", GPL_URL))
        layout.addWidget(license_box)

        devices = QGroupBox("Unterstützte Geräte und offizielle Herstellerseiten")
        dg = QGridLayout(devices)
        device_title = QLabel("<b>NZXT Kraken RGB 360 (2023, Standard / Non-Elite)</b>")
        device_details = QLabel(
            "liquidctl-Gerätename: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · "
            "Temperatur, Pumpe, Radiatorlüfter und LCD"
        )
        device_details.setWordWrap(True)
        dg.addWidget(device_title, 0, 0, 1, 2)
        dg.addWidget(device_details, 1, 0, 1, 2)
        dg.addWidget(self.make_external_link("Offizielle NZXT Kraken-(2023)-Spezifikationen", NZXT_KRAKEN_2023_URL), 2, 0)
        dg.addWidget(self.make_external_link("NZXT Wasserkühlungen / CPU-Kühler", NZXT_COOLERS_URL), 2, 1)

        controller_title = QLabel("<b>NZXT 2023 RGB Controller</b>")
        controller_details = QLabel(
            "USB 1e71:2012 · separate RGB-Steuerung über liquidctl. Der Controller wird auf der offiziellen "
            "Kraken-(2023)-Seite als Bestandteil der RGB-Varianten aufgeführt."
        )
        controller_details.setWordWrap(True)
        dg.addWidget(controller_title, 3, 0, 1, 2)
        dg.addWidget(controller_details, 4, 0, 1, 2)
        dg.addWidget(self.make_external_link("NZXT-Website", NZXT_WEBSITE_URL), 5, 0)
        dg.addWidget(self.make_external_link("Offizielle Kraken-(2023)-Geräteseite", NZXT_KRAKEN_2023_URL), 5, 1)
        scope_note = QLabel(
            "Unterstützt werden nur Lüfter, die als Teil der Kraken-Kühlung über das Kraken-Gerät gemeldet und "
            "gesteuert werden. Andere im PC eingebaute Lüfter werden von Kraken Control nicht angesprochen."
        )
        scope_note.setWordWrap(True)
        scope_note.setObjectName("muted")
        dg.addWidget(scope_note, 6, 0, 1, 2)
        layout.addWidget(devices)

        note = QLabel(
            "Alle Links öffnen sich im Standardbrowser. Das bloße Anzeigen dieser Seite überträgt keine Daten; "
            "erst das Anklicken eines Links öffnet die jeweilige externe Internetseite."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)
        return page

    def make_log_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        note = QLabel(
            "Dieses Protokoll erfasst Hardwarebefehle, Fehler, Schaltflächenklicks, Tastaturaktionen und "
            "vom Benutzer geänderte Einstellungen. Private Pfade und Kennungen werden weiterhin bereinigt."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_char_limit = 10000
        self.log_counter_label = QLabel("Log: 0 / 10.000 Zeichen")
        self.log_counter_label.setObjectName("muted")
        buttons = QHBoxLayout()
        clear = QPushButton("Log leeren")
        clear.clicked.connect(self.clear_application_log)
        copy = QPushButton("Alles kopieren")
        copy.clicked.connect(self.copy_application_log)
        save = QPushButton("Log speichern")
        save.clicked.connect(self.save_application_log)
        buttons.addWidget(clear)
        buttons.addWidget(copy)
        buttons.addWidget(save)
        buttons.addStretch()
        buttons.addWidget(self.log_counter_label)
        layout.addLayout(buttons)
        layout.addWidget(self.log_view)
        return page

    @staticmethod
    def make_percent_slider(minimum: int, maximum: int, value: int) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        label = QLabel(f"{value} %")
        label.setMinimumWidth(48)
        slider.valueChanged.connect(lambda v: label.setText(f"{v} %"))
        return slider, label

    @staticmethod
    def normalize_accent_hex(value: str) -> str | None:
        value = value.strip()
        if not value.startswith("#"):
            value = "#" + value
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            return None
        return value.lower()

    def pick_theme_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.accent_hex), self, "Akzentfarbe auswählen")
        if not color.isValid():
            return
        self.accent_hex_input.setText(color.name())
        self.apply_design_settings()

    def set_accent_preset(self, color: str) -> None:
        self.accent_hex_input.setText(color)
        self.apply_design_settings()

    def apply_design_settings(self) -> None:
        mode = self.theme_mode_combo.currentData() if hasattr(self, "theme_mode_combo") else self.theme_mode
        accent_text = self.accent_hex_input.text() if hasattr(self, "accent_hex_input") else self.accent_hex
        accent = self.normalize_accent_hex(accent_text)
        if accent is None:
            if hasattr(self, "accent_hex_input"):
                self.accent_hex_input.setText(self.accent_hex)
            self.show_error("Ungültige Akzentfarbe. Bitte einen Hex-Code wie #00aaff verwenden.")
            return
        self.theme_mode = str(mode)
        self.accent_hex = accent
        if hasattr(self, "accent_hex_input"):
            self.accent_hex_input.setText(accent)
        self.settings.setValue("design/theme", self.theme_mode)
        self.settings.setValue("design/accent", self.accent_hex)
        self.settings.setValue("display/ui_scale", self.ui_scale_percent)
        self.settings.setValue("display/auto", self.display_auto)
        self.settings.setValue("display/layout", self.display_layout)
        self.settings.setValue("background/enabled", self.background_enabled)
        self.settings.setValue("background/theme", self.background_theme)
        self.settings.setValue("background/last_theme", self.background_last_theme)
        self.settings.setValue("background/fps", self.background_fps)
        self.settings.setValue("background/intensity", self.background_intensity)
        self.settings.setValue("background/pause_inactive", self.background_pause_inactive)
        self.settings.setValue("profiles/current", self.current_profile_id)
        self.apply_theme()
        if hasattr(self, "log_view"):
            self.log_message(f"DESIGN: Modus={self.theme_mode} · Akzent={self.accent_hex}")

    def apply_theme(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        accent = QColor(self.accent_hex)
        if not accent.isValid():
            accent = QColor("#00aaff")
            self.accent_hex = accent.name()

        if self.theme_mode == "light":
            palette = QPalette()
            colors = {
                QPalette.ColorRole.Window: "#f4f6f8",
                QPalette.ColorRole.WindowText: "#18202a",
                QPalette.ColorRole.Base: "#ffffff",
                QPalette.ColorRole.AlternateBase: "#eef2f6",
                QPalette.ColorRole.ToolTipBase: "#ffffff",
                QPalette.ColorRole.ToolTipText: "#18202a",
                QPalette.ColorRole.Text: "#18202a",
                QPalette.ColorRole.Button: "#ffffff",
                QPalette.ColorRole.ButtonText: "#18202a",
                QPalette.ColorRole.BrightText: "#ffffff",
                QPalette.ColorRole.Mid: "#667085",
                QPalette.ColorRole.Midlight: "#d0d5dd",
                QPalette.ColorRole.Dark: "#344054",
                QPalette.ColorRole.PlaceholderText: "#98a2b3",
            }
            for role, value in colors.items():
                palette.setColor(role, QColor(value))
        elif self.theme_mode == "dark":
            palette = QPalette()
            colors = {
                QPalette.ColorRole.Window: "#11161d",
                QPalette.ColorRole.WindowText: "#eef2f7",
                QPalette.ColorRole.Base: "#191f29",
                QPalette.ColorRole.AlternateBase: "#202834",
                QPalette.ColorRole.ToolTipBase: "#202834",
                QPalette.ColorRole.ToolTipText: "#eef2f7",
                QPalette.ColorRole.Text: "#eef2f7",
                QPalette.ColorRole.Button: "#202834",
                QPalette.ColorRole.ButtonText: "#eef2f7",
                QPalette.ColorRole.BrightText: "#ffffff",
                QPalette.ColorRole.Mid: "#98a2b3",
                QPalette.ColorRole.Midlight: "#344054",
                QPalette.ColorRole.Dark: "#090d12",
                QPalette.ColorRole.PlaceholderText: "#667085",
            }
            for role, value in colors.items():
                palette.setColor(role, QColor(value))
        else:
            palette = QPalette(self.system_palette)

        palette.setColor(QPalette.ColorRole.Highlight, accent)
        palette.setColor(QPalette.ColorRole.Link, accent)
        highlighted_text = QColor("#111111") if accent.lightness() > 155 else QColor("#ffffff")
        palette.setColor(QPalette.ColorRole.HighlightedText, highlighted_text)
        app.setPalette(palette)

        scale = self.ui_scale_percent / 100.0
        app_font = QFont(self.base_font)
        base_point = self.base_font.pointSizeF() if self.base_font.pointSizeF() > 0 else 10.0
        app_font.setPointSizeF(max(8.0, base_point * scale))
        app.setFont(app_font)
        hover = accent.lighter(118) if self.theme_mode == "dark" else accent.darker(108)
        pressed = accent.darker(125)
        is_dark_palette = palette.color(QPalette.ColorRole.Window).lightness() < 150
        surface_rgba = "rgba(25, 31, 41, 232)" if is_dark_palette else "rgba(255, 255, 255, 242)"
        # Light mode gets a stronger frosted sheet so text/controls stay readable
        # over bright animations; dark/system keep a slightly more transparent veil.
        content_rgba = "rgba(17, 22, 29, 166)" if is_dark_palette else "rgba(244, 246, 248, 214)"
        base_px = max(11, round(14 * scale))
        title_px = max(22, round(27 * scale))
        card_px = max(20, round(25 * scale))
        self.setStyleSheet(
            f"""
            QWidget {{ font-size: {base_px}px; color: palette(window-text); }}
            QMainWindow {{ background: palette(window); }}
            QWidget#backgroundRoot {{ background: transparent; }}
            QWidget#contentRoot {{ background: {content_rgba}; }}
            QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
            QLabel#mainTitle {{ font-size: {title_px}px; font-weight: 750; }}
            QLabel#subtitle, QLabel#muted, QLabel#cardHint {{ color: palette(mid); }}
            QLabel#connectionPending {{ color: #d49b21; font-weight: 700; }}
            QLabel#connectionOk {{ color: #2fbf71; font-weight: 700; }}
            QLabel#connectionBad {{ color: #e05a5a; font-weight: 700; }}
            QLabel#cardTitle {{ color: palette(mid); font-size: 13px; }}
            QLabel#cardValue {{ font-size: {card_px}px; font-weight: 750; }}
            QLabel#healthGood {{ color: #2fbf71; font-weight: 700; }}
            QLabel#healthWarn {{ color: #d49b21; font-weight: 700; }}
            QLabel#healthCritical {{ color: #e05a5a; font-weight: 800; }}
            QLabel#healthNeutral {{ color: palette(mid); }}
            QLabel#warningText {{ color: #d49b21; }}
            QLabel#infoText {{ color: palette(mid); }}
            QLabel#designPreview {{
                border: 2px solid {accent.name()};
                border-radius: 8px;
                background: palette(base);
                color: {accent.name()};
                font-weight: 700;
                padding: 8px;
            }}
            QFrame#valueCard, QFrame#profileCard {{
                border: 1px solid palette(midlight);
                border-radius: 10px;
                background: {surface_rgba};
            }}
            QLabel#profileTitle {{ font-size: 17px; font-weight: 700; }}
            QLabel#lcdPreview {{
                background: #101010;
                border: 3px solid {accent.name()};
                border-radius: 150px;
                color: #aaaaaa;
            }}
            CurveEditor#curveEditor {{
                border: 1px solid palette(midlight);
                border-radius: 10px;
                background: palette(base);
            }}
            QGroupBox {{
                border: 1px solid palette(midlight);
                border-radius: 10px;
                margin-top: 14px;
                padding: 12px;
                font-weight: 700;
                background: {surface_rgba};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; }}
            QPushButton {{
                padding: 8px 13px;
                border: 1px solid palette(midlight);
                border-radius: 7px;
                background: palette(button);
            }}
            QPushButton:hover {{ border-color: {hover.name()}; color: {accent.name()}; }}
            QPushButton:pressed {{ border-color: {pressed.name()}; background: palette(midlight); }}
            QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTableWidget:focus {{
                border: 2px solid {accent.name()};
            }}
            QTabWidget::pane {{ border: 1px solid palette(midlight); border-radius: 8px; background: {surface_rgba}; }}
            QScrollArea#settingsScrollArea {{ border: none; background: transparent; }}
            QScrollArea#settingsScrollArea > QWidget > QWidget {{ background: transparent; }}
            QWidget#settingsContent {{ background: transparent; }}
            QTabBar::tab {{ padding: 9px 16px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ font-weight: 700; color: {accent.name()}; border-bottom-color: {accent.name()}; }}
            QTableWidget {{ border: 1px solid palette(midlight); border-radius: 6px; gridline-color: palette(midlight); }}
            QLineEdit, QComboBox, QSpinBox {{
                padding: 6px;
                border: 1px solid palette(midlight);
                border-radius: 6px;
                background: palette(base);
            }}
            QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: palette(midlight); }}
            QSlider::sub-page:horizontal {{ background: {accent.name()}; border-radius: 3px; }}
            QSlider::handle:horizontal {{
                width: 17px; margin: -6px 0; border-radius: 8px;
                background: {accent.name()}; border: 2px solid palette(base);
            }}
            """
        )
        if hasattr(self, "pump_curve_table"):
            self.pump_curve_table[2].set_accent_color(accent)
        if hasattr(self, "fan_curve_table"):
            self.fan_curve_table[2].set_accent_color(accent)
        if hasattr(self, "design_preview"):
            self.design_preview.setText(
                f"{self.theme_mode_combo.currentText()} · Akzent {self.accent_hex} · Skalierung {self.ui_scale_percent} %"
            )
        if hasattr(self, "background_widget"):
            self.background_widget.configure(
                enabled=self.background_enabled,
                theme=self.background_theme,
                fps=self.background_fps,
                intensity=self.background_intensity,
                pause_inactive=self.background_pause_inactive,
            )
            self.ensure_background_layer_order()
        if hasattr(self, "dashboard_cards_layout"):
            self.adapt_dashboard_layout()

    def ensure_background_layer_order(self) -> None:
        """Keep the decorative background behind every interactive widget."""
        if hasattr(self, "background_widget") and hasattr(self, "content_root"):
            self.background_widget.lower()
            self.content_root.raise_()

    @staticmethod
    def serialize_curve(points: list[tuple[int, int]]) -> str:
        return ";".join(f"{temp}:{duty}" for temp, duty in points)

    @staticmethod
    def deserialize_curve(value: str, fallback: list[tuple[int, int]]) -> list[tuple[int, int]]:
        try:
            points = []
            for part in value.split(";"):
                if not part:
                    continue
                temp_text, duty_text = part.split(":", 1)
                points.append((int(temp_text), int(duty_text)))
            temperatures = [temp for temp, _ in points]
            duties = [duty for _, duty in points]
            valid = (
                len(points) >= 2
                and all(20 <= temp <= 50 for temp in temperatures)
                and all(0 <= duty <= 100 for duty in duties)
                and all(b > a for a, b in zip(temperatures, temperatures[1:]))
                and all(b >= a for a, b in zip(duties, duties[1:]))
                and points[-1][0] <= 50
                and points[-1][1] == 100
            )
            return points if valid else list(fallback)
        except (TypeError, ValueError):
            return list(fallback)

    # ---------- display, background, setup and profiles ----------
    @staticmethod
    def profiles_file() -> Path:
        config = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation))
        return config / "profiles.json"

    @staticmethod
    def builtin_profiles() -> list[dict[str, object]]:
        return [
            {"id": "builtin-quiet", "name": "Leise", "category": "Kühlung", "description": "Pumpe 45 %, Lüfter 35 %", "builtin": True,
             "payload": {"cooling": {"pump_mode": "fixed", "fan_mode": "fixed", "pump": 45, "fan": 35}}},
            {"id": "builtin-balanced", "name": "Ausgeglichen", "category": "Kühlung", "description": "Pumpe 55 %, Lüfter 50 %", "builtin": True,
             "payload": {"cooling": {"pump_mode": "fixed", "fan_mode": "fixed", "pump": 55, "fan": 50}}},
            {"id": "builtin-performance", "name": "Leistung", "category": "Kühlung", "description": "Pumpe und Lüfter 75 %", "builtin": True,
             "payload": {"cooling": {"pump_mode": "fixed", "fan_mode": "fixed", "pump": 75, "fan": 75}}},
            {"id": "builtin-safe", "name": "Sicher", "category": "Kühlung", "description": "Pumpe und Lüfter 65 %", "builtin": True,
             "payload": {"cooling": {"pump_mode": "fixed", "fan_mode": "fixed", "pump": 65, "fan": 65}}},
            {"id": "builtin-dark-space", "name": "Weltraum dunkel", "category": "Design", "description": "Dunkles Design mit Sternenfeld", "builtin": True,
             "payload": {"design": {"theme": "dark", "accent": "#00aaff", "background_enabled": True, "background_theme": "Sternenfeld", "background_fps": 30, "background_intensity": 42}}},
            {"id": "builtin-light-clean", "name": "Hell und ruhig", "category": "Design", "description": "Helles Design ohne Animation", "builtin": True,
             "payload": {"design": {"theme": "light", "accent": "#3b82f6", "background_enabled": False, "background_theme": "Aus", "background_fps": 30, "background_intensity": 30}}},
        ]

    def load_profiles(self) -> None:
        self.user_profiles = []
        file_path = self.profiles_file()
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("schema") == PROFILE_SCHEMA_VERSION and isinstance(data.get("profiles"), list):
                self.user_profiles = [profile for profile in data["profiles"] if isinstance(profile, dict)]
        except (OSError, json.JSONDecodeError):
            self.user_profiles = []

    def save_profiles(self) -> None:
        file_path = self.profiles_file()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": PROFILE_SCHEMA_VERSION, "profiles": self.user_profiles}
        temporary = file_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(file_path)

    def all_profiles(self) -> list[dict[str, object]]:
        return self.builtin_profiles() + self.user_profiles

    def refresh_profiles_table(self) -> None:
        if not hasattr(self, "profiles_table"):
            return
        profiles = self.all_profiles()
        self.profiles_table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            values = (
                str(profile.get("name", "Unbenannt")),
                str(profile.get("category", "Gesamt")),
                str(profile.get("description", "")),
                "Standard" if profile.get("builtin") else "Eigenes Profil",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, str(profile.get("id", "")))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.profiles_table.setItem(row, column, item)
        self.profiles_table.resizeColumnsToContents()
        if hasattr(self, "profile_startup_combo"):
            saved_startup = str(self.settings.value("profiles/startup", "none"))
            self.profile_startup_combo.blockSignals(True)
            self.profile_startup_combo.clear()
            self.profile_startup_combo.addItem("Kein automatisches Profil", "none")
            self.profile_startup_combo.addItem("Zuletzt verwendetes Profil", "last")
            for profile in profiles:
                self.profile_startup_combo.addItem(str(profile.get("name", "Profil")), str(profile.get("id", "")))
            startup_index = self.profile_startup_combo.findData(saved_startup)
            self.profile_startup_combo.setCurrentIndex(max(0, startup_index))
            self.profile_startup_combo.blockSignals(False)
        if self.current_profile_id:
            for row in range(self.profiles_table.rowCount()):
                item = self.profiles_table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == self.current_profile_id:
                    self.profiles_table.selectRow(row)
                    break

    def apply_profile_by_id(self, profile_id: str) -> None:
        profile = next((item for item in self.all_profiles() if str(item.get("id")) == profile_id), None)
        if profile is not None:
            self.current_profile_id = profile_id
            payload = profile.get("payload", {})
            if isinstance(payload, dict):
                self.apply_profile_payload(payload, str(profile.get("name", "Profil")))

    def profile_startup_changed(self) -> None:
        if hasattr(self, "profile_startup_combo"):
            self.settings.setValue("profiles/startup", self.profile_startup_combo.currentData() or "none")

    def apply_startup_profile(self) -> None:
        startup = str(self.settings.value("profiles/startup", "none"))
        if startup == "none" or self.pending_setup_profile:
            return
        profile_id = self.current_profile_id if startup == "last" else startup
        if profile_id:
            self.apply_profile_by_id(profile_id)

    def selected_profile(self) -> dict[str, object] | None:
        if not hasattr(self, "profiles_table"):
            return None
        row = self.profiles_table.currentRow()
        if row < 0:
            return None
        item = self.profiles_table.item(row, 0)
        profile_id = str(item.data(Qt.ItemDataRole.UserRole)) if item else ""
        return next((profile for profile in self.all_profiles() if str(profile.get("id")) == profile_id), None)

    def on_profile_selection_changed(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            self.profile_status_label.setText("Noch kein Profil ausgewählt.")
            return
        self.profile_name_input.setText(str(profile.get("name", "")))
        self.profile_description_input.setText(str(profile.get("description", "")))
        category_index = self.profile_category_combo.findText(str(profile.get("category", "Gesamt")))
        self.profile_category_combo.setCurrentIndex(max(0, category_index))
        profile_type = "Standardprofil" if profile.get("builtin") else "eigenes Profil"
        self.profile_status_label.setText(f"Ausgewählt: {profile.get('name')} · {profile_type}")

    def capture_profile_payload(self, category: str) -> dict[str, object]:
        result: dict[str, object] = {}
        if category in {"Gesamt", "Kühlung"}:
            result["cooling"] = {
                "pump": self.pump_slider.value(),
                "fan": self.fan_slider.value(),
                "pump_mode": self.cooling_modes["pump"][0],
                "fan_mode": self.cooling_modes["fan"][0],
                "pump_curve": self.pump_curve_table[2].points(),
                "fan_curve": self.fan_curve_table[2].points(),
                "warning": self.warning_temp.value(),
                "critical": self.critical_temp.value(),
                "expert": self.expert_mode_checkbox.isChecked(),
                "auto_max": self.auto_max_checkbox.isChecked(),
                "cpu_profile": self.cpu_profile_combo.currentData() or "",
                "cpu_assist": self.cpu_assist_checkbox.isChecked(),
            }
        if category in {"Gesamt", "LCD"}:
            result["lcd"] = {
                "file": str(self.selected_lcd_file or ""),
                "brightness": self.lcd_brightness.value(),
                "orientation": self.lcd_orientation.currentText(),
                "keepalive": self.keep_lcd_checkbox.isChecked(),
                "interval": self.lcd_interval.value(),
                "clock_active": self.clock_active,
                "clock_format": self.clock_format.currentData(),
                "clock_show_date": self.clock_show_date.isChecked(),
                "clock_font_size": self.clock_font_size.value(),
                "clock_text_color": self.clock_text_hex,
                "clock_background_color": self.clock_background_hex,
                "clock_auto_resend": self.clock_auto_resend.isChecked(),
                "clock_resend_interval": self.clock_resend_interval.value(),
            }
        if category in {"Gesamt", "RGB"}:
            result["rgb"] = {
                "channel": self.rgb_channel.currentText(),
                "mode": self.rgb_mode.currentText(),
                "color1": self.color1_hex,
                "color2": self.color2_hex,
                "speed": self.rgb_speed.currentText(),
                "direction": self.rgb_direction.currentText(),
            }
        if category in {"Gesamt", "Design"}:
            result["design"] = {
                "theme": self.theme_mode,
                "accent": self.accent_hex,
                "background_enabled": self.background_enabled,
                "background_theme": self.background_theme,
                "background_fps": self.background_fps,
                "background_intensity": self.background_intensity,
                "background_pause_inactive": self.background_pause_inactive,
                "display_auto": self.display_auto,
                "ui_scale": self.ui_scale_percent,
                "display_layout": self.display_layout,
                "window_width": self.width(),
                "window_height": self.height(),
                "window_maximized": self.isMaximized(),
            }
        return result

    def create_profile_from_current(self) -> None:
        name = self.profile_name_input.text().strip()
        if not name:
            self.show_error("Bitte einen Profilnamen eingeben.")
            return
        category = self.profile_category_combo.currentText()
        profile_id = f"user-{int(time.time() * 1000)}"
        self.user_profiles.append({
            "id": profile_id,
            "name": name,
            "category": category,
            "description": self.profile_description_input.text().strip(),
            "builtin": False,
            "payload": self.capture_profile_payload(category),
        })
        self.current_profile_id = profile_id
        self.save_profiles()
        self.refresh_profiles_table()
        self.footer_status.setText(f"Profil „{name}“ gespeichert")

    def update_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            self.show_error("Bitte zuerst ein eigenes Profil auswählen.")
            return
        if profile.get("builtin"):
            self.show_error("Standardprofile können nicht überschrieben werden. Bitte duplizieren.")
            return
        profile["name"] = self.profile_name_input.text().strip() or str(profile.get("name"))
        profile["category"] = self.profile_category_combo.currentText()
        profile["description"] = self.profile_description_input.text().strip()
        profile["payload"] = self.capture_profile_payload(str(profile["category"]))
        self.save_profiles()
        self.refresh_profiles_table()
        self.footer_status.setText(f"Profil „{profile['name']}“ aktualisiert")

    def duplicate_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            return
        copy_profile = json.loads(json.dumps(profile))
        copy_profile["id"] = f"user-{int(time.time() * 1000)}"
        copy_profile["name"] = f"{profile.get('name', 'Profil')} – Kopie"
        copy_profile["builtin"] = False
        self.user_profiles.append(copy_profile)
        self.current_profile_id = str(copy_profile["id"])
        self.save_profiles()
        self.refresh_profiles_table()

    def rename_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None or profile.get("builtin"):
            self.show_error("Nur eigene Profile können umbenannt werden.")
            return
        name, ok = QInputDialog.getText(self, "Profil umbenennen", "Neuer Name", text=str(profile.get("name", "")))
        if ok and name.strip():
            profile["name"] = name.strip()
            self.save_profiles()
            self.refresh_profiles_table()

    def delete_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None or profile.get("builtin"):
            self.show_error("Standardprofile können nicht gelöscht werden.")
            return
        answer = QMessageBox.question(self, "Profil löschen", f"Profil „{profile.get('name')}“ wirklich löschen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        profile_id = str(profile.get("id"))
        self.user_profiles = [item for item in self.user_profiles if str(item.get("id")) != profile_id]
        if self.current_profile_id == profile_id:
            self.current_profile_id = ""
        self.save_profiles()
        self.refresh_profiles_table()

    def export_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            self.show_error("Bitte ein Profil auswählen.")
            return
        default_name = re.sub(r"[^A-Za-z0-9._-]+", "_", str(profile.get("name", "profil"))).strip("_") or "profil"
        filename, _ = QFileDialog.getSaveFileName(self, "Profil exportieren", str(Path.home() / f"{default_name}.kraken-profile.json"), "Kraken-Profile (*.json)")
        if not filename:
            return
        export_data = {"schema": PROFILE_SCHEMA_VERSION, "profile": profile}
        Path(filename).write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.footer_status.setText("Profil exportiert")

    def import_profiles(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Profil importieren", str(Path.home()), "Kraken-Profile (*.json)")
        if not filename:
            return
        try:
            data = json.loads(Path(filename).read_text(encoding="utf-8"))
            candidates = []
            if isinstance(data, dict) and isinstance(data.get("profile"), dict):
                candidates = [data["profile"]]
            elif isinstance(data, dict) and isinstance(data.get("profiles"), list):
                candidates = data["profiles"]
            for source in candidates:
                imported = json.loads(json.dumps(source))
                imported["id"] = f"user-{int(time.time() * 1000)}-{len(self.user_profiles)}"
                imported["builtin"] = False
                imported["name"] = str(imported.get("name", "Importiertes Profil"))
                self.user_profiles.append(imported)
            if not candidates:
                raise ValueError("Keine Profile gefunden")
            self.save_profiles()
            self.refresh_profiles_table()
            self.footer_status.setText(f"{len(candidates)} Profil(e) importiert")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.show_error(f"Profil konnte nicht importiert werden:\n{exc}")

    def apply_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile is None:
            self.show_error("Bitte ein Profil auswählen.")
            return
        self.current_profile_id = str(profile.get("id", ""))
        payload = profile.get("payload", {})
        if not isinstance(payload, dict):
            self.show_error("Das Profil enthält keine gültigen Einstellungen.")
            return
        self.apply_profile_payload(payload, str(profile.get("name", "Profil")))

    def apply_profile_payload(self, payload: dict[str, object], name: str) -> None:
        design = payload.get("design")
        if isinstance(design, dict):
            self.theme_mode = str(design.get("theme", self.theme_mode))
            self.accent_hex = self.normalize_accent_hex(str(design.get("accent", self.accent_hex))) or self.accent_hex
            self.background_enabled = bool(design.get("background_enabled", self.background_enabled))
            self.background_theme = str(design.get("background_theme", self.background_theme))
            self.background_fps = int(design.get("background_fps", self.background_fps))
            self.background_intensity = int(design.get("background_intensity", self.background_intensity))
            self.background_pause_inactive = bool(design.get("background_pause_inactive", self.background_pause_inactive))
            self.display_auto = bool(design.get("display_auto", self.display_auto))
            self.ui_scale_percent = int(design.get("ui_scale", self.ui_scale_percent))
            self.display_layout = str(design.get("display_layout", self.display_layout))
            target_width = max(920, int(design.get("window_width", self.width())))
            target_height = max(680, int(design.get("window_height", self.height())))
            if bool(design.get("window_maximized", False)):
                self.showMaximized()
            else:
                self.showNormal()
                self.resize(target_width, target_height)
            self.sync_design_controls()
            self.apply_theme()

        rgb = payload.get("rgb")
        if isinstance(rgb, dict):
            self.rgb_channel.setCurrentText(str(rgb.get("channel", self.rgb_channel.currentText())))
            self.rgb_mode.setCurrentText(str(rgb.get("mode", self.rgb_mode.currentText())))
            self.color1_hex = str(rgb.get("color1", self.color1_hex))
            self.color2_hex = str(rgb.get("color2", self.color2_hex))
            self.color1_button.setText(f"Farbe 1 · #{self.color1_hex}")
            self.color2_button.setText(f"Farbe 2 · #{self.color2_hex}")
            self.rgb_speed.setCurrentText(str(rgb.get("speed", self.rgb_speed.currentText())))
            self.rgb_direction.setCurrentText(str(rgb.get("direction", self.rgb_direction.currentText())))
            if self.devices_ready:
                self.apply_rgb()

        lcd = payload.get("lcd")
        if isinstance(lcd, dict):
            self.lcd_brightness.setValue(int(lcd.get("brightness", self.lcd_brightness.value())))
            self.lcd_orientation.setCurrentText(str(lcd.get("orientation", self.lcd_orientation.currentText())))
            self.lcd_interval.setValue(int(lcd.get("interval", self.lcd_interval.value())))
            self.clock_format.setCurrentIndex(0 if str(lcd.get("clock_format", "24")) == "24" else 1)
            self.clock_show_date.setChecked(bool(lcd.get("clock_show_date", self.clock_show_date.isChecked())))
            self.clock_font_size.setValue(int(lcd.get("clock_font_size", self.clock_font_size.value())))
            self.clock_text_hex = str(lcd.get("clock_text_color", self.clock_text_hex))
            self.clock_background_hex = str(lcd.get("clock_background_color", self.clock_background_hex))
            self.clock_auto_resend.setChecked(bool(lcd.get("clock_auto_resend", self.clock_auto_resend.isChecked())))
            self.clock_resend_interval.setValue(int(lcd.get("clock_resend_interval", self.clock_resend_interval.value())))
            file_value = str(lcd.get("file", ""))
            if file_value and Path(file_value).exists():
                self.load_lcd_file(Path(file_value), quiet=True)
            if bool(lcd.get("clock_active", False)):
                QTimer.singleShot(1200, self.start_clock_mode)
            elif self.prepared_lcd_file and bool(lcd.get("keepalive", False)):
                QTimer.singleShot(1200, lambda: self.keep_lcd_checkbox.setChecked(True))

        cooling = payload.get("cooling")
        if isinstance(cooling, dict):
            self.load_profile_cooling_controls(cooling)
            if self.devices_ready:
                self.transmit_profile_cooling(cooling, name)
        self.save_settings()
        self.profile_status_label.setText(f"Aktiv: {name}")
        self.footer_status.setText(f"Profil „{name}“ angewendet")

    def load_profile_cooling_controls(self, cooling: dict[str, object]) -> None:
        self.pump_slider.setValue(int(cooling.get("pump", self.pump_slider.value())))
        self.fan_slider.setValue(int(cooling.get("fan", self.fan_slider.value())))
        pump_curve = [(int(a), int(b)) for a, b in cooling.get("pump_curve", self.pump_curve_table[2].points())]
        fan_curve = [(int(a), int(b)) for a, b in cooling.get("fan_curve", self.fan_curve_table[2].points())]
        self.pump_curve_table[2].set_points(pump_curve)
        self.update_curve_table(self.pump_curve_table[1], pump_curve)
        self.fan_curve_table[2].set_points(fan_curve)
        self.update_curve_table(self.fan_curve_table[1], fan_curve)
        self.expert_mode_checkbox.setChecked(bool(cooling.get("expert", self.expert_mode_checkbox.isChecked())))
        self.warning_temp.setValue(int(cooling.get("warning", self.warning_temp.value())))
        self.critical_temp.setValue(int(cooling.get("critical", self.critical_temp.value())))
        self.auto_max_checkbox.setChecked(bool(cooling.get("auto_max", self.auto_max_checkbox.isChecked())))
        cpu_model = str(cooling.get("cpu_profile", ""))
        cpu_index = self.cpu_profile_combo.findData(cpu_model)
        if cpu_index >= 0:
            self.cpu_profile_combo.setCurrentIndex(cpu_index)
        self.cpu_assist_checkbox.setChecked(bool(cooling.get("cpu_assist", self.cpu_assist_checkbox.isChecked())))

    def transmit_profile_cooling(self, cooling: dict[str, object], name: str) -> None:
        if self.kraken_write_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        commands: list[tuple[str, list[str], str, str]] = []
        for channel, label in (("pump", "Pumpe"), ("fan", "Radiatorlüfter")):
            mode = str(cooling.get(f"{channel}_mode", "fixed"))
            if mode == "curve" or "kurve" in mode.lower():
                raw_points = cooling.get(f"{channel}_curve", [])
                points = [(int(a), int(b)) for a, b in raw_points]
                args = Backend.kraken_direct_args() + ["set", channel, "speed"]
                for temp, duty in points:
                    args.extend([str(temp), str(duty)])
                detail = f"Temperaturkurve · {len(points)} Punkte · Direct Access"
                commands.append((channel, args, "Temperaturkurve", detail))
            else:
                duty = int(cooling.get(channel, 55))
                args = Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)]
                commands.append((channel, args, "Feste Drehzahl", f"{duty} %"))
        self.kraken_write_busy = True

        def run_index(index: int) -> None:
            if index >= len(commands):
                self.kraken_write_busy = False
                self.footer_status.setText(f"Kühlung aus Profil „{name}“ aktiv")
                QTimer.singleShot(700, self.refresh_status)
                return
            channel, args, mode, detail = commands[index]

            def done(result: CommandResult) -> None:
                if not result.ok:
                    self.kraken_write_busy = False
                    self.show_error(result.combined or f"Profil konnte {channel} nicht einstellen")
                    return
                self.set_cooling_mode(channel, mode, detail)
                run_index(index + 1)

            self.backend.run_async(args, callback=done, timeout=30)

        run_index(0)

    def screen_summary(self) -> str:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is None:
            return "Kein Monitor erkannt."
        geometry = screen.geometry()
        dpr = float(screen.devicePixelRatio())
        physical_width = round(geometry.width() * dpr)
        physical_height = round(geometry.height() * dpr)
        ratio = physical_width / max(1, physical_height)
        ratio_name = self.classify_aspect_ratio(ratio)
        return (
            f"{screen.name()} · ca. {physical_width}×{physical_height} physische Pixel · "
            f"Skalierungsfaktor {dpr:.2f} · logisch {screen.logicalDotsPerInch():.0f} DPI · {ratio_name}"
        )

    @staticmethod
    def classify_aspect_ratio(ratio: float) -> str:
        candidates = [(16 / 10, "16:10"), (16 / 9, "16:9"), (21 / 9, "21:9"), (32 / 9, "32:9")]
        return min(candidates, key=lambda item: abs(item[0] - ratio))[1]

    def refresh_display_info(self) -> None:
        if hasattr(self, "display_info_label"):
            self.display_info_label.setText(self.screen_summary())
        if self.display_auto:
            screen = self.screen() or QApplication.primaryScreen()
            if screen is not None:
                ratio = screen.geometry().width() / max(1, screen.geometry().height())
                self.display_layout = self.classify_aspect_ratio(ratio)
                if hasattr(self, "display_layout_combo"):
                    index = self.display_layout_combo.findData(self.display_layout)
                    if index >= 0:
                        self.display_layout_combo.setCurrentIndex(index)
        self.adapt_dashboard_layout()

    def apply_display_settings(self) -> None:
        self.display_auto = self.display_auto_checkbox.isChecked()
        self.ui_scale_percent = self.ui_scale_spin.value()
        self.display_layout = str(self.display_layout_combo.currentData() or "auto")
        if self.display_auto:
            screen = self.screen() or QApplication.primaryScreen()
            if screen is not None:
                ratio = screen.geometry().width() / max(1, screen.geometry().height())
                self.display_layout = self.classify_aspect_ratio(ratio)
        self.apply_theme()
        self.refresh_display_info()
        self.save_settings()
        self.footer_status.setText("Anzeigeeinstellungen angewendet")
        self.log_message(
            f"ANZEIGE: automatische Anpassung={'ein' if self.display_auto else 'aus'} · "
            f"Layout={self.display_layout} · App-Skalierung={self.ui_scale_percent} % · {self.screen_summary()}"
        )

    def adapt_dashboard_layout(self) -> None:
        if not hasattr(self, "dashboard_cards_layout"):
            return
        layout_mode = self.display_layout
        if layout_mode == "auto":
            width = self.width()
            columns = 5 if width >= 1750 else 3 if width >= 1180 else 2
        else:
            columns = {"16:10": 2, "16:9": 3, "21:9": 4, "32:9": 5}.get(layout_mode, 3)
        while self.dashboard_cards_layout.count():
            self.dashboard_cards_layout.takeAt(0)
        for index, card in enumerate(self.dashboard_cards):
            self.dashboard_cards_layout.addWidget(card, index // columns, index % columns)

    def resizeEvent(self, event) -> None:  # noqa: ANN001
        super().resizeEvent(event)
        self.ensure_background_layer_order()
        if self.display_auto:
            self.adapt_dashboard_layout()

    def _restorable_background_theme(self) -> str:
        """Return a real animation theme that can be restored after disabling."""
        current = self.background_theme_combo.currentText() if hasattr(self, "background_theme_combo") else self.background_theme
        if current in AnimatedBackgroundWidget.THEMES and current != "Aus":
            return current
        if self.background_last_theme in AnimatedBackgroundWidget.THEMES and self.background_last_theme != "Aus":
            return self.background_last_theme
        return DEFAULT_BACKGROUND_THEME

    def on_background_enabled_toggled(self, enabled: bool) -> None:
        """Immediately toggle animation while preserving the selected theme."""
        if enabled:
            theme = self._restorable_background_theme()
            if self.background_theme_combo.currentText() == "Aus":
                self.background_theme_combo.blockSignals(True)
                self.background_theme_combo.setCurrentText(theme)
                self.background_theme_combo.blockSignals(False)
            self.background_theme = theme
            self.background_last_theme = theme
        else:
            current = self.background_theme_combo.currentText()
            if current != "Aus" and current in AnimatedBackgroundWidget.THEMES:
                self.background_last_theme = current
                self.background_theme = current
        self.background_enabled = bool(enabled)
        self.background_fps = int(self.background_fps_combo.currentData() or 30)
        self.background_intensity = self.background_intensity_slider.value()
        self.background_pause_inactive = self.background_pause_checkbox.isChecked()
        self.background_widget.configure(
            enabled=self.background_enabled,
            theme=self.background_theme,
            fps=self.background_fps,
            intensity=self.background_intensity,
            pause_inactive=self.background_pause_inactive,
        )
        self.ensure_background_layer_order()
        self.save_settings()
        self.log_user_action(
            "HINTERGRUND",
            f"Animation {'aktiviert' if self.background_enabled else 'deaktiviert'} · Thema '{self.background_theme}' bleibt gespeichert",
        )
        self.footer_status.setText("Animation aktiviert" if self.background_enabled else "Animation ausgeschaltet")

    def apply_background_settings(self) -> None:
        selected_theme = self.background_theme_combo.currentText()
        requested_enabled = self.background_enabled_checkbox.isChecked()
        if selected_theme == "Aus":
            requested_enabled = False
            self.background_enabled_checkbox.blockSignals(True)
            self.background_enabled_checkbox.setChecked(False)
            self.background_enabled_checkbox.blockSignals(False)
        else:
            self.background_last_theme = selected_theme
        self.background_enabled = requested_enabled
        self.background_theme = selected_theme if selected_theme != "Aus" else self.background_last_theme
        self.background_fps = int(self.background_fps_combo.currentData() or 30)
        self.background_intensity = self.background_intensity_slider.value()
        self.background_pause_inactive = self.background_pause_checkbox.isChecked()
        self.background_widget.configure(
            enabled=self.background_enabled,
            theme=self.background_theme,
            fps=self.background_fps,
            intensity=self.background_intensity,
            pause_inactive=self.background_pause_inactive,
        )
        self.ensure_background_layer_order()
        self.save_settings()
        self.log_user_action(
            "HINTERGRUND",
            f"Thema '{self.background_theme}', {self.background_fps} FPS, Intensität {self.background_intensity} %, "
            f"CPU-Offscreen-Renderer {'aktiv' if self.background_enabled else 'aus'}",
        )
        self.footer_status.setText("Animierter Hintergrund aktualisiert")

    def disable_background(self) -> None:
        # Disabling must not overwrite the selected theme with 'Aus'.
        current = self.background_theme_combo.currentText()
        if current != "Aus" and current in AnimatedBackgroundWidget.THEMES:
            self.background_last_theme = current
            self.background_theme = current
        if self.background_enabled_checkbox.isChecked():
            self.background_enabled_checkbox.setChecked(False)
        else:
            self.on_background_enabled_toggled(False)

    def sync_design_controls(self) -> None:
        if hasattr(self, "theme_mode_combo"):
            index = self.theme_mode_combo.findData(self.theme_mode)
            self.theme_mode_combo.setCurrentIndex(max(0, index))
            self.accent_hex_input.setText(self.accent_hex)
            self.ui_scale_spin.setValue(self.ui_scale_percent)
            self.display_auto_checkbox.setChecked(self.display_auto)
            index = self.display_layout_combo.findData(self.display_layout)
            self.display_layout_combo.setCurrentIndex(max(0, index))
            self.background_enabled_checkbox.blockSignals(True)
            self.background_enabled_checkbox.setChecked(self.background_enabled)
            self.background_enabled_checkbox.blockSignals(False)
            self.background_theme_combo.setCurrentText(self.background_theme)
            index = self.background_fps_combo.findData(self.background_fps)
            self.background_fps_combo.setCurrentIndex(max(0, index))
            self.background_intensity_slider.setValue(self.background_intensity)
            self.background_pause_checkbox.setChecked(self.background_pause_inactive)

    def maybe_show_setup_wizard(self, force: bool = False) -> None:
        if not force and self.settings.value("setup/completed", False, type=bool):
            return
        wizard = SetupWizard(self)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        values = wizard.selected_values()
        self.theme_mode = str(values["theme"])
        self.accent_hex = self.normalize_accent_hex(str(values["accent"])) or "#00aaff"
        self.background_theme = str(values["background"])
        self.background_enabled = self.background_theme != "Aus"
        self.display_auto = bool(values["auto_scale"])
        self.ui_scale_percent = int(values["scale"])
        self.display_layout = str(values["layout"])
        self.pending_setup_profile = str(values["cooling"])
        self.settings.setValue("setup/completed", True)
        self.settings.setValue("setup/pending_profile", self.pending_setup_profile)
        self.sync_design_controls()
        self.apply_theme()
        self.save_settings()
        if self.devices_ready:
            self.apply_pending_setup_profile()

    def apply_pending_setup_profile(self) -> None:
        profile = self.pending_setup_profile or str(self.settings.value("setup/pending_profile", ""))
        profiles = {
            "quiet": ("Leise", 45, 35),
            "balanced": ("Ausgeglichen", 55, 50),
            "performance": ("Leistung", 75, 75),
            "safe": ("Sicher", 65, 65),
        }
        if not profile or profile not in profiles or not self.devices_ready or self.kraken_write_busy:
            return
        name, pump, fan = profiles[profile]
        self.pending_setup_profile = ""
        self.settings.setValue("setup/pending_profile", "")
        self.apply_quick_profile(name, pump, fan)

    # ---------- lifecycle/settings ----------
    def setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        icon = QIcon.fromTheme("preferences-system-cooling")
        if icon.isNull():
            icon = self.windowIcon()
        self.tray.setIcon(icon)
        self.tray.setToolTip(DISPLAY_NAME)
        menu = self.tray.contextMenu()
        if menu is None:
            from PySide6.QtWidgets import QMenu

            menu = QMenu()
            self.tray.setContextMenu(menu)
        show_action = QAction("Öffnen", self)
        show_action.triggered.connect(self.show_from_tray)
        liquid_action = QAction("Flüssigkeitstemperatur anzeigen", self)
        liquid_action.triggered.connect(self.show_liquid_screen)
        quit_action = QAction("Beenden", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(show_action)
        menu.addAction(liquid_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.activated.connect(
            lambda reason: self.show_from_tray()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def restore_settings(self) -> None:
        geometry = self.settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        if not self.settings.value("migration/v292_settings_layout", False, type=bool):
            screen = QApplication.primaryScreen()
            target_width, target_height = 1280, 880
            if screen is not None:
                available = screen.availableGeometry()
                target_width = max(800, min(target_width, available.width() - 80))
                target_height = max(580, min(target_height, available.height() - 80))
            self.resize(target_width, target_height)
            self.settings.setValue("migration/v292_settings_layout", True)
            self.log_message(
                f"LAYOUT: Hauptfenster für 2.9.2 auf {target_width}×{target_height} angepasst; Einstellungen sind scrollbar."
            )
        self.ui_scale_percent = max(80, min(180, int(self.settings.value("display/ui_scale", self.ui_scale_percent))))
        self.display_auto = self.settings.value("display/auto", self.display_auto, type=bool)
        self.display_layout = str(self.settings.value("display/layout", self.display_layout))
        self.background_enabled = self.settings.value("background/enabled", self.background_enabled, type=bool)
        self.background_theme = str(self.settings.value("background/theme", self.background_theme))
        self.background_last_theme = str(self.settings.value("background/last_theme", self.background_last_theme))
        if self.background_last_theme not in AnimatedBackgroundWidget.THEMES or self.background_last_theme == "Aus":
            self.background_last_theme = DEFAULT_BACKGROUND_THEME
        if self.background_enabled and self.background_theme == "Aus":
            self.background_theme = self.background_last_theme
        self.background_fps = int(self.settings.value("background/fps", self.background_fps))
        self.background_intensity = int(self.settings.value("background/intensity", self.background_intensity))
        self.background_pause_inactive = self.settings.value("background/pause_inactive", self.background_pause_inactive, type=bool)
        if hasattr(self, "ui_scale_spin"):
            self.ui_scale_spin.setValue(self.ui_scale_percent)
            self.display_auto_checkbox.setChecked(self.display_auto)
            index = self.display_layout_combo.findData(self.display_layout)
            self.display_layout_combo.setCurrentIndex(max(0, index))
            self.background_enabled_checkbox.blockSignals(True)
            self.background_enabled_checkbox.setChecked(self.background_enabled)
            self.background_enabled_checkbox.blockSignals(False)
            self.background_theme_combo.setCurrentText(self.background_theme)
            fps_index = self.background_fps_combo.findData(self.background_fps)
            self.background_fps_combo.setCurrentIndex(max(0, fps_index))
            self.background_intensity_slider.setValue(self.background_intensity)
            self.background_pause_checkbox.setChecked(self.background_pause_inactive)
        self.pump_slider.setValue(int(self.settings.value("cooling/pump", 52)))
        self.fan_slider.setValue(int(self.settings.value("cooling/fan", 52)))
        if hasattr(self, "theme_mode_combo"):
            theme_index = self.theme_mode_combo.findData(self.theme_mode)
            self.theme_mode_combo.blockSignals(True)
            self.theme_mode_combo.setCurrentIndex(max(0, theme_index))
            self.theme_mode_combo.blockSignals(False)
            self.accent_hex_input.setText(self.accent_hex)
            self.apply_theme()
        pump_points = self.deserialize_curve(
            str(self.settings.value("cooling/pump_curve", "")),
            list(DEFAULT_PUMP_CURVE),
        )
        fan_points = self.deserialize_curve(
            str(self.settings.value("cooling/fan_curve", "")),
            list(DEFAULT_FAN_CURVE),
        )
        self.pump_curve_table[2].set_points(pump_points)
        self.update_curve_table(self.pump_curve_table[1], pump_points)
        self.fan_curve_table[2].set_points(fan_points)
        self.update_curve_table(self.fan_curve_table[1], fan_points)
        self.expert_mode_checkbox.blockSignals(True)
        self.expert_mode_checkbox.setChecked(self.expert_mode_enabled)
        self.expert_mode_checkbox.blockSignals(False)
        self.configure_expert_mode_controls(self.expert_mode_enabled)
        saved_warning = int(self.settings.value("safety/warning", 42))
        saved_critical = int(self.settings.value("safety/critical", 50))
        if not self.expert_mode_enabled:
            saved_warning = max(35, min(48, saved_warning))
            saved_critical = max(40, min(55, saved_critical))
            if saved_critical <= saved_warning:
                saved_critical = min(55, saved_warning + 1)
        else:
            saved_warning = max(-20, min(120, saved_warning))
            saved_critical = max(-20, min(120, saved_critical))
        self.warning_temp.blockSignals(True)
        self.critical_temp.blockSignals(True)
        self.warning_temp.setValue(saved_warning)
        self.critical_temp.setValue(saved_critical)
        self.warning_temp.blockSignals(False)
        self.critical_temp.blockSignals(False)
        for channel, label in (("pump", "Pumpe"), ("fan", "Radiatorlüfter")):
            mode = str(self.settings.value(f"cooling/{channel}_mode", "unbekannt"))
            detail = str(self.settings.value(f"cooling/{channel}_mode_detail", "Noch nicht durch Kraken Control gesetzt"))
            self.cooling_modes[channel] = (mode, detail)
        self.update_cooling_mode_label()
        self.auto_max_checkbox.setChecked(self.settings.value("safety/auto_max", True, type=bool))
        saved_cpu = str(self.settings.value("cpu/profile", ""))
        cpu_index = self.cpu_profile_combo.findData(saved_cpu)
        if cpu_index >= 0:
            self.cpu_profile_combo.setCurrentIndex(cpu_index)
            self.selected_cpu_profile = CPU_PROFILE_BY_MODEL.get(saved_cpu)
        else:
            self.detect_and_select_cpu(silent=True)
        self.cpu_assist_checkbox.setChecked(self.settings.value("cpu/assist", False, type=bool))
        self.update_cpu_profile_preview()
        self.lcd_interval.setValue(int(self.settings.value("lcd/interval", DEFAULT_LCD_INTERVAL)))
        security_migrated = self.settings.value("security/migrated_231", False, type=bool)
        previous_keepalive = self.settings.value("lcd/keepalive", False, type=bool)
        previous_clock = self.settings.value("clock/active", False, type=bool)
        saved_keepalive = previous_keepalive if security_migrated else False
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(saved_keepalive)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(saved_keepalive)
        self.restore_lcd_checkbox.setChecked(self.settings.value("lcd/restore", False, type=bool))
        self.clock_format.setCurrentIndex(0 if self.settings.value("clock/format", "24") == "24" else 1)
        self.clock_show_date.setChecked(self.settings.value("clock/show_date", True, type=bool))
        self.clock_font_size.setValue(int(self.settings.value("clock/font_size", 64)))
        self.clock_auto_resend.blockSignals(True)
        self.clock_auto_resend.setChecked(self.settings.value("clock/auto_resend", True, type=bool))
        self.clock_auto_resend.blockSignals(False)
        self.clock_resend_interval.setValue(int(self.settings.value("clock/resend_interval", DEFAULT_LCD_INTERVAL)))
        self.update_clock_keepalive_controls(self.clock_auto_resend.isChecked())
        self.clock_text_hex = str(self.settings.value("clock/text_color", "ffffff"))
        self.clock_background_hex = str(self.settings.value("clock/background_color", "10141c"))
        self.clock_text_button.setText(f"Text · #{self.clock_text_hex}")
        self.clock_background_button.setText(f"Hintergrund · #{self.clock_background_hex}")
        self.clock_active = previous_clock if security_migrated else False
        if not security_migrated:
            self.settings.setValue("lcd/keepalive", False)
            self.settings.setValue("clock/active", False)
            self.settings.setValue("security/migrated_231", True)
            if previous_keepalive or previous_clock:
                self.log_message("Sicherheitsupdate 2.3.1: Wiederholte LCD-Uploads wurden vorsorglich deaktiviert.")
        self.tray_checkbox.setChecked(self.settings.value("app/tray", True, type=bool))
        self.refresh_interval.setValue(int(self.settings.value("app/refresh", 3)))
        self.autostart_checkbox.blockSignals(True)
        self.autostart_checkbox.setChecked(self.autostart_file().exists())
        self.autostart_checkbox.blockSignals(False)
        last_file = self.settings.value("lcd/file", "")
        if last_file and Path(last_file).exists():
            self.load_lcd_file(Path(last_file), quiet=True)

    def save_settings(self) -> None:
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.settings.setValue("cooling/pump", self.pump_slider.value())
        self.settings.setValue("cooling/fan", self.fan_slider.value())
        self.settings.setValue("cooling/pump_curve", self.serialize_curve(self.pump_curve_table[2].points()))
        self.settings.setValue("cooling/fan_curve", self.serialize_curve(self.fan_curve_table[2].points()))
        self.settings.setValue("design/theme", self.theme_mode)
        self.settings.setValue("design/accent", self.accent_hex)
        self.settings.setValue("display/ui_scale", self.ui_scale_percent)
        self.settings.setValue("display/auto", self.display_auto)
        self.settings.setValue("display/layout", self.display_layout)
        self.settings.setValue("background/enabled", self.background_enabled)
        self.settings.setValue("background/theme", self.background_theme)
        self.settings.setValue("background/fps", self.background_fps)
        self.settings.setValue("background/intensity", self.background_intensity)
        self.settings.setValue("background/pause_inactive", self.background_pause_inactive)
        self.settings.setValue("profiles/current", self.current_profile_id)
        self.settings.setValue("safety/expert_mode", self.expert_mode_checkbox.isChecked())
        self.settings.setValue("safety/warning", self.warning_temp.value())
        self.settings.setValue("safety/critical", self.critical_temp.value())
        for channel in ("pump", "fan"):
            mode, detail = self.cooling_modes[channel]
            self.settings.setValue(f"cooling/{channel}_mode", mode)
            self.settings.setValue(f"cooling/{channel}_mode_detail", detail)
        self.settings.setValue("safety/auto_max", self.auto_max_checkbox.isChecked())
        self.settings.setValue("cpu/profile", self.cpu_profile_combo.currentData() or "")
        self.settings.setValue("cpu/assist", self.cpu_assist_checkbox.isChecked())
        self.settings.setValue("lcd/interval", self.lcd_interval.value())
        self.settings.setValue("lcd/keepalive", self.keep_lcd_checkbox.isChecked())
        self.settings.setValue("lcd/restore", self.restore_lcd_checkbox.isChecked())
        self.settings.setValue("lcd/file", str(self.selected_lcd_file or ""))
        self.settings.setValue("clock/format", self.clock_format.currentData())
        self.settings.setValue("clock/show_date", self.clock_show_date.isChecked())
        self.settings.setValue("clock/font_size", self.clock_font_size.value())
        self.settings.setValue("clock/auto_resend", self.clock_auto_resend.isChecked())
        self.settings.setValue("clock/resend_interval", self.clock_resend_interval.value())
        self.settings.setValue("clock/text_color", self.clock_text_hex)
        self.settings.setValue("clock/background_color", self.clock_background_hex)
        self.settings.setValue("clock/active", self.clock_active)
        self.settings.setValue("app/tray", self.tray_checkbox.isChecked())
        self.settings.setValue("app/refresh", self.refresh_interval.value())

    def closeEvent(self, event: QCloseEvent) -> None:
        self.save_settings()
        if self.tray_checkbox.isChecked() and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage(DISPLAY_NAME, "Die Steuerung läuft im Infobereich weiter.")
        else:
            if self.cpu_assist_level != "curve":
                self.restore_curves_sync_on_quit()
            self.backend.shutdown()
            event.accept()

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self.save_settings()
        self.status_timer.stop()
        self.lcd_keepalive_timer.stop()
        self.clock_timer.stop()
        self.clock_keepalive_timer.stop()
        if self.cpu_assist_level != "curve":
            self.restore_curves_sync_on_quit()
        self.backend.shutdown()
        QApplication.quit()

    # ---------- dependency/device ----------
    @staticmethod
    def missing_dependency_packages() -> list[str]:
        missing: list[str] = []
        if shutil.which("liquidctl") is None:
            missing.append("liquidctl")
        try:
            import PySide6  # noqa: F401
        except ImportError:
            missing.append("python3-pyside6")
        if Image is None:
            missing.append("python3-pillow")
        return missing

    def refresh_dependency_status(self) -> list[str]:
        missing = self.missing_dependency_packages()
        if not hasattr(self, "dependency_status"):
            return missing
        if missing:
            self.dependency_status.setText(
                "⚠ Fehlende Pakete: " + ", ".join(missing) +
                ". Die Installation ist nur für Nobara/Fedora mit DNF automatisiert."
            )
        else:
            self.dependency_status.setText(
                "✅ Alle benötigten Pakete sind installiert: liquidctl, PySide6 und Pillow."
            )
        return missing

    def check_dependencies(self) -> list[str]:
        missing = self.refresh_dependency_status()
        if not missing:
            return []
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Fehlende Abhängigkeiten")
        box.setText("Kraken Control benötigt zusätzliche Systempakete.")
        box.setInformativeText(
            "Fehlend: " + ", ".join(missing) +
            "\n\nDie App kann diese Pakete auf Nobara/Fedora über DNF installieren. "
            "Es werden nur fest vorgegebene offizielle Paketnamen verwendet und keine Paketquellen hinzugefügt."
        )
        install_button = box.addButton("Jetzt installieren", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Später", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is install_button:
            self.install_missing_dependencies()
        return missing

    def install_missing_dependencies(self) -> None:
        missing = self.refresh_dependency_status()
        if not missing:
            QMessageBox.information(self, DISPLAY_NAME, "Alle benötigten Abhängigkeiten sind bereits installiert.")
            return
        script = Path(__file__).with_name("install-dependencies.sh")
        if not script.exists():
            self.show_error(
                "Das Abhängigkeits-Skript fehlt. Installiere auf Nobara/Fedora manuell:\n\n"
                "sudo dnf install " + " ".join(missing)
            )
            return
        if shutil.which("dnf") is None:
            self.show_error(
                "Die automatische Installation unterstützt derzeit Nobara/Fedora mit DNF. "
                "Auf diesem System müssen die fehlenden Pakete manuell installiert werden:\n\n" +
                " ".join(missing)
            )
            return
        answer = QMessageBox.question(
            self,
            "Abhängigkeiten installieren",
            "Folgende Pakete werden aus den konfigurierten DNF-Paketquellen installiert:\n\n• " +
            "\n• ".join(missing) +
            "\n\nDanach ist möglicherweise ein Neustart von Kraken Control nötig. Fortfahren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.footer_status.setText("Administratorfreigabe für Paketinstallation wird angefordert …")

        def done(result: CommandResult) -> None:
            current_missing = self.refresh_dependency_status()
            if result.ok and not current_missing:
                QMessageBox.information(
                    self,
                    "Abhängigkeiten installiert",
                    "Die fehlenden Pakete wurden installiert. Starte Kraken Control neu, damit alle Komponenten geladen werden."
                )
                self.footer_status.setText("Abhängigkeiten installiert – Neustart empfohlen")
                QTimer.singleShot(300, self.initialize_devices)
            elif result.ok:
                QMessageBox.warning(
                    self,
                    "Neustart erforderlich",
                    "Die Paketinstallation wurde abgeschlossen. Einige Komponenten werden erst nach einem Neustart "
                    "der Anwendung erkannt."
                )
                self.footer_status.setText("Paketinstallation abgeschlossen")
            else:
                self.show_error(result.combined or "Die Abhängigkeiten konnten nicht installiert werden.")

        self.backend.run_async([str(script), "--install"], callback=done, timeout=900)

    def initialize_devices(self) -> None:
        self.refresh_button.setEnabled(False)
        self.connection_label.setText("● Initialisiere …")
        self.connection_label.setObjectName("connectionPending")
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        self.footer_status.setText("Geräte werden initialisiert …")
        self.backend.run_async(
            [LIQUIDCTL, "initialize", "all"],
            callback=self.on_initialized,
            error_callback=self.on_command_error,
            timeout=45,
        )

    def on_initialized(self, result: CommandResult) -> None:
        self.refresh_button.setEnabled(True)
        if not result.ok:
            self.set_disconnected(result.combined or "Initialisierung fehlgeschlagen")
            return
        has_kraken = "NZXT Kraken 2023" in result.stdout
        has_rgb = "NZXT 2023 RGB Controller" in result.stdout
        self.devices_ready = has_kraken
        firmware = self.extract_value(result.stdout, "Firmware version", occurrence=-1)
        brightness = self.extract_number(result.stdout, "LCD Brightness")
        orientation = self.extract_number(result.stdout, "LCD Orientation")
        if firmware:
            self.firmware_card.set_value(firmware, "Kraken 2023 · LCD 240 × 240")
        if brightness is not None:
            self.lcd_brightness.setValue(int(brightness))
        if orientation is not None:
            self.lcd_orientation.setCurrentText(str(int(orientation)))
        if has_kraken:
            text = "● Verbunden"
            if not has_rgb:
                text += " · RGB-Controller fehlt"
            self.connection_label.setText(text)
            self.connection_label.setObjectName("connectionOk")
            self.connection_label.style().unpolish(self.connection_label)
            self.connection_label.style().polish(self.connection_label)
            self.footer_status.setText("Kraken verbunden")
            self.status_timer.start(self.refresh_interval.value() * 1000)
            self.refresh_status()
            self.test_access()
            QTimer.singleShot(900, self.apply_pending_setup_profile)
            QTimer.singleShot(1700, self.apply_startup_profile)
            if self.clock_active:
                QTimer.singleShot(1500, self.start_clock_mode)
            elif self.restore_lcd_checkbox.isChecked() and self.prepared_lcd_file:
                if self.keep_lcd_checkbox.isChecked():
                    QTimer.singleShot(1500, lambda: self.toggle_lcd_keepalive(True))
                else:
                    QTimer.singleShot(1500, self.send_lcd_now)
        else:
            self.set_disconnected("NZXT Kraken 2023 wurde nicht gefunden")

    def set_disconnected(self, message: str) -> None:
        self.devices_ready = False
        self.connection_label.setText("● Nicht verbunden")
        self.connection_label.setObjectName("connectionBad")
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        self.footer_status.setText(message)
        self.health_label.setText(message)
        self.health_label.setObjectName("healthCritical")

    def on_command_error(self, message: str) -> None:
        self.refresh_button.setEnabled(True)
        self.footer_status.setText("Fehler")
        self.show_error(message)

    @staticmethod
    def matching_hidraw_nodes(product_id: str = "300e") -> list[tuple[Path, bool]]:
        matches: list[tuple[Path, bool]] = []
        for sys_node in sorted(Path("/sys/class/hidraw").glob("hidraw*")):
            try:
                device = (sys_node / "device").resolve()
                vendor = product = None
                for parent in (device, *device.parents):
                    vendor_file = parent / "idVendor"
                    product_file = parent / "idProduct"
                    if vendor_file.exists() and product_file.exists():
                        vendor = vendor_file.read_text(encoding="ascii").strip().lower()
                        product = product_file.read_text(encoding="ascii").strip().lower()
                        break
                if vendor == "1e71" and product == product_id.lower():
                    dev_node = Path("/dev") / sys_node.name
                    writable = os.access(dev_node, os.R_OK | os.W_OK)
                    matches.append((dev_node, writable))
            except OSError:
                continue
        return matches

    def has_kraken_write_access(self) -> bool | None:
        nodes = self.matching_hidraw_nodes("300e")
        if not nodes:
            return None
        return any(writable for _node, writable in nodes)

    def test_access(self) -> None:
        nodes = self.matching_hidraw_nodes("300e")
        node_text = ", ".join(f"{node} ({'lesen/schreiben' if writable else 'nicht schreibbar'})" for node, writable in nodes)

        def done(result: CommandResult) -> None:
            write_ok = any(writable for _node, writable in nodes) if nodes else None
            if result.ok and write_ok is not False:
                details = f"\n{node_text}" if node_text else ""
                self.access_status.setText("✅ Lesezugriff funktioniert; HID-Schreibzugriff ist verfügbar." + details)
            elif result.ok:
                self.access_status.setText(
                    "⚠ Status kann gelesen werden, aber /dev/hidraw ist nicht schreibbar. "
                    "Darum schlagen Lüfter- und Kurvenänderungen fehl.\n" + node_text
                )
            else:
                self.access_status.setText("❌ Kein ausreichender Zugriff ohne sudo:\n" + (result.combined or "Unbekannter Fehler"))

        self.backend.run_async(
            Backend.kraken_args() + ["status"],
            callback=done,
            timeout=15,
            log_command=False,
            log_output=False,
        )

    def repair_permissions(self) -> None:
        script = Path(__file__).with_name("install-udev-rule.sh")
        if not script.exists():
            self.show_error(
                "Das Reparaturskript fehlt. Starte im entpackten Installationsordner: ./install-udev-rule.sh"
            )
            return
        pkexec = shutil.which("pkexec")
        if pkexec is None:
            self.show_error(
                f"pkexec wurde nicht gefunden. Starte im Terminal:\n\n{script}\n\n"
                "Danach die Kraken kurz ab- und wieder anstecken oder den Rechner neu starten."
            )
            return
        self.footer_status.setText("Administratorfreigabe für udev-Regel wird angefordert …")

        def done(result: CommandResult) -> None:
            if result.ok:
                QMessageBox.information(
                    self,
                    "Berechtigungen aktualisiert",
                    "Die udev-Regel wurde installiert und neu ausgelöst. Teste die Kurve erneut. "
                    "Falls der Zugriff weiterhin fehlt, die Kraken kurz neu verbinden oder den Rechner neu starten."
                )
                QTimer.singleShot(1000, self.test_access)
            else:
                self.show_error(result.combined or "Die udev-Regel konnte nicht installiert werden.")

        self.backend.run_async([pkexec, str(script)], callback=done, timeout=180)

    def show_permission_error(self, technical_message: str) -> None:
        self.log_message("BERECHTIGUNG: " + technical_message)
        self.permission_retry_after = max(self.permission_retry_after, time.monotonic() + 60.0)
        self.footer_status.setText("Kraken-Schreibzugriff fehlt · automatische Schreibversuche kurz pausiert")

        # Hintergrundbetrieb darf niemals Spiele oder andere Anwendungen mit
        # einem modalen Dialog unterbrechen. Ein Hinweis im Tray reicht.
        foreground = self.isVisible() and self.isActiveWindow()
        if not foreground:
            now = time.monotonic()
            if now - self.permission_notice_last >= 300.0:
                self.permission_notice_last = now
                if hasattr(self, "tray") and self.tray.isVisible():
                    self.tray.showMessage(
                        DISPLAY_NAME,
                        "Kraken-Schreibzugriff fehlt. Automatische Kühlungswrites wurden vorübergehend pausiert. "
                        "Öffne Kraken Control später, um den Gerätezugriff zu prüfen.",
                    )
            return

        if self.permission_dialog_open:
            return
        self.permission_dialog_open = True
        try:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Schreibzugriff auf die Kraken fehlt")
            box.setText(
                "Die Kraken kann gelesen werden, aber liquidctl darf die Lüfter-/Pumpenwerte nicht schreiben."
            )
            box.setInformativeText(
                "Kraken Control verwendet für Kühlungsänderungen bereits Direct Access. "
                "Wenn auch dieser Zugriff fehlschlägt, prüfe bitte die HID-/udev-Berechtigung.\n\n"
                "Mit „Berechtigungen reparieren“ wird die mitgelieferte Regel über die normale Administratorabfrage installiert. "
                "Danach kann ein Neuverbinden der Kraken oder ein Neustart nötig sein.\n\nTechnische Meldung:\n"
                + technical_message
            )
            repair = box.addButton("Berechtigungen reparieren", QMessageBox.ButtonRole.ActionRole)
            box.addButton(QMessageBox.StandardButton.Close)
            box.exec()
            if box.clickedButton() is repair:
                self.repair_permissions()
        finally:
            self.permission_dialog_open = False

    @staticmethod
    def read_cpu_model() -> str:
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lower().startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass
        return ""

    @staticmethod
    def read_amd_cpu_temperature() -> tuple[float | None, str]:
        for hwmon in sorted(Path("/sys/class/hwmon").glob("hwmon*")):
            try:
                if (hwmon / "name").read_text(encoding="ascii").strip() != "k10temp":
                    continue
                candidates: list[tuple[int, Path, str]] = []
                for input_file in hwmon.glob("temp*_input"):
                    label_file = input_file.with_name(input_file.name.replace("_input", "_label"))
                    label = label_file.read_text(encoding="utf-8").strip() if label_file.exists() else input_file.stem
                    priority = 0 if label == "Tctl" else 1 if label == "Tdie" else 2
                    candidates.append((priority, input_file, label))
                for _priority, input_file, label in sorted(candidates):
                    value = float(input_file.read_text(encoding="ascii").strip()) / 1000.0
                    if 0.0 < value < 125.0:
                        return value, label
            except (OSError, ValueError):
                continue
        return None, "k10temp nicht gefunden"

    def detect_and_select_cpu(self, _checked: bool = False, silent: bool = False) -> None:
        model = self.read_cpu_model()
        match = next((profile for profile in AM5_CPU_PROFILES if profile.model in model), None)
        if match is None:
            if not silent:
                QMessageBox.information(
                    self,
                    "CPU nicht in der Profilliste",
                    f"Erkannt: {model or 'unbekannt'}\n\nFür dieses Modell ist noch kein geprüftes AM5-Profil hinterlegt."
                )
            return
        index = self.cpu_profile_combo.findData(match.model)
        if index >= 0:
            self.cpu_profile_combo.setCurrentIndex(index)
            self.selected_cpu_profile = match
            self.update_cpu_profile_preview()
            self.log_message(f"CPU: {match.model} automatisch erkannt · Familie {match.family} · Tjmax {match.tjmax} °C")
            if not silent:
                self.footer_status.setText(f"CPU erkannt: {match.model}")

    def update_cpu_profile_preview(self) -> None:
        model = self.cpu_profile_combo.currentData()
        profile = CPU_PROFILE_BY_MODEL.get(model)
        self.selected_cpu_profile = profile
        if profile is None:
            self.cpu_profile_info.setText(
                "Bitte einen AM5-Prozessor auswählen. CPU-Tjmax und Kraken-Wassertemperatur sind getrennte Größen."
            )
            return
        self.cpu_profile_info.setText(
            f"{profile.model} · {profile.family} · AMD Tjmax {profile.tjmax} °C · "
            f"verstärkte Kühlung ab {profile.boost_temp} °C · 100 % ab {profile.critical_temp} °C. "
            "Die Kraken-Wassergrenzen bleiben 42/50 °C."
        )

    def apply_selected_cpu_profile(self) -> None:
        profile = self.selected_cpu_profile
        if profile is None:
            self.show_error("Bitte zuerst einen AMD-AM5-Prozessor auswählen.")
            return
        pump_points = list(profile.pump_curve)
        fan_points = list(profile.fan_curve)
        self.pump_curve_table[2].set_points(pump_points)
        self.update_curve_table(self.pump_curve_table[1], pump_points)
        self.fan_curve_table[2].set_points(fan_points)
        self.update_curve_table(self.fan_curve_table[1], fan_points)
        self.cpu_assist_checkbox.setChecked(True)
        self.settings.setValue("cpu/profile", profile.model)
        self.footer_status.setText(f"AM5-Profil geladen: {profile.model}")
        self.log_message(
            f"CPU-PROFIL: {profile.model} geladen · Boost ab {profile.boost_temp} °C · 100 % ab {profile.critical_temp} °C · "
            f"Pumpenkurve {len(pump_points)} Punkte · Lüfterkurve {len(fan_points)} Punkte · CPU-Assistenz ein"
        )
        QMessageBox.information(
            self,
            "AM5-Profil geladen",
            f"Das Profil für {profile.model} wurde geladen.\n\n"
            f"CPU: verstärkte Kraken-Kühlung ab {profile.boost_temp} °C, 100 % ab {profile.critical_temp} °C, "
            f"AMD Tjmax {profile.tjmax} °C.\n"
            "Kraken-Flüssigkeit: eigene Kurven mit 100 % spätestens bei 45 °C; kritische Wassergrenze 50 °C."
        )

    def on_cpu_assist_toggled(self, enabled: bool) -> None:
        if enabled and self.selected_cpu_profile is None:
            self.cpu_assist_checkbox.blockSignals(True)
            self.cpu_assist_checkbox.setChecked(False)
            self.cpu_assist_checkbox.blockSignals(False)
            self.show_error("Bitte zuerst ein CPU-Profil auswählen.")
            return
        if enabled and self.has_kraken_write_access() is False:
            self.cpu_assist_checkbox.blockSignals(True)
            self.cpu_assist_checkbox.setChecked(False)
            self.cpu_assist_checkbox.blockSignals(False)
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return
        if not enabled and self.cpu_assist_level != "curve":
            self.restore_water_curves_after_cpu_assist()

    # ---------- status ----------
    def refresh_status(self) -> None:
        if not self.devices_ready or self.status_busy or self.kraken_write_busy or self.lcd_busy:
            return
        self.status_busy = True

        def done(result: CommandResult) -> None:
            self.status_busy = False
            if not result.ok:
                self.last_status_ok = False
                self.footer_status.setText("Status konnte nicht gelesen werden")
                return
            self.last_status_ok = True
            values = self.parse_status(result.stdout)
            temp = values.get("Liquid temperature")
            pump_speed = values.get("Pump speed")
            pump_duty = values.get("Pump duty")
            fan_speed = values.get("Fan speed")
            fan_duty = values.get("Fan duty")
            if temp is not None:
                self.temp_card.set_value(f"{temp:.1f} °C", self.temperature_hint(temp))
                self.pump_curve_table[2].set_current_temperature(temp)
                self.fan_curve_table[2].set_current_temperature(temp)
                self.update_health(temp, pump_speed, fan_speed)
                self.enforce_temperature_safety(temp)
            cpu_temp, sensor_label = self.read_amd_cpu_temperature()
            self.current_cpu_temp = cpu_temp
            self.cpu_sensor_label = sensor_label
            if cpu_temp is not None:
                profile_hint = self.selected_cpu_profile.model if self.selected_cpu_profile else "kein Profil"
                self.cpu_temp_card.set_value(f"{cpu_temp:.1f} °C", f"{sensor_label} · {profile_hint}")
                self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label} · aktuell {cpu_temp:.1f} °C")
                self.update_cpu_temperature_assist(cpu_temp)
            else:
                self.cpu_temp_card.set_value("— °C", sensor_label)
                self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label}")
            if pump_speed is not None:
                self.pump_card.set_value(f"{int(pump_speed)} rpm", f"{pump_duty:.0f} % Leistung" if pump_duty is not None else "")
            if fan_speed is not None:
                self.fan_card.set_value(f"{int(fan_speed)} rpm", f"{fan_duty:.0f} % Leistung" if fan_duty is not None else "")
            if pump_duty is not None:
                self.pump_slider.setValue(int(round(pump_duty)))
            if fan_duty is not None:
                self.fan_slider.setValue(int(round(fan_duty)))
            self.footer_status.setText("Status aktuell")

        self.backend.run_async(
            Backend.kraken_args() + ["status"],
            callback=done,
            timeout=12,
            log_command=False,
            log_output=False,
        )

    @staticmethod
    def parse_status(text: str) -> dict[str, float]:
        values: dict[str, float] = {}
        for key in ("Liquid temperature", "Pump speed", "Pump duty", "Fan speed", "Fan duty"):
            match = re.search(rf"{re.escape(key)}\s+([0-9]+(?:\.[0-9]+)?)", text)
            if match:
                values[key] = float(match.group(1))
        return values

    @staticmethod
    def extract_value(text: str, label: str, occurrence: int = 0) -> str | None:
        matches = re.findall(rf"{re.escape(label)}\s+([^\n]+?)\s*$", text, flags=re.MULTILINE)
        if not matches:
            return None
        return matches[occurrence].strip()

    @staticmethod
    def extract_number(text: str, label: str) -> float | None:
        match = re.search(rf"{re.escape(label)}\s+([0-9]+(?:\.[0-9]+)?)", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def temperature_hint(temp: float) -> str:
        if temp < 35:
            return "Sehr guter Bereich"
        if temp < 42:
            return "Normal unter Last"
        if temp < 50:
            return "Erhöht – Kurve prüfen"
        return "Kritisch – Kühlung prüfen"

    def update_health(self, temp: float, pump_speed: float | None, fan_speed: float | None) -> None:
        warning = self.warning_temp.value()
        critical = self.critical_temp.value()
        if pump_speed is not None and pump_speed < 500:
            text, obj = "⚠ Pumpendrehzahl ungewöhnlich niedrig.", "healthCritical"
        elif temp >= critical:
            text, obj = f"⚠ Kritische Wassertemperatur: {temp:.1f} °C", "healthCritical"
        elif temp >= warning:
            text, obj = f"⚠ Erhöhte Wassertemperatur: {temp:.1f} °C", "healthWarn"
        elif fan_speed is not None and fan_speed < 100 and temp > 38:
            text, obj = "⚠ Lüfter stehen trotz erhöhter Temperatur.", "healthWarn"
        else:
            text, obj = "✅ Kühlung arbeitet normal.", "healthGood"
        self.health_label.setText(text)
        self.health_label.setObjectName(obj)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)

    def enforce_temperature_safety(self, temp: float) -> None:
        if not self.auto_max_checkbox.isChecked() or temp < self.critical_temp.value():
            return
        last = self.settings.value("safety/last_auto_max", 0.0, type=float)
        now = time.time()
        if now - last < 60:
            return
        self.settings.setValue("safety/last_auto_max", now)
        self.log_message(f"Sicherheitsaktion: {temp:.1f} °C – Pumpe und Lüfter auf 100 %.")
        self.apply_quick_profile("Sicherheit", 100, 100, notify=False)

    def update_cpu_temperature_assist(self, cpu_temp: float) -> None:
        if time.monotonic() < self.permission_retry_after:
            return
        profile = self.selected_cpu_profile
        if profile is None or not self.cpu_assist_checkbox.isChecked():
            return
        if cpu_temp >= profile.critical_temp:
            target_level, pump, fan = "critical", 100, 100
        elif cpu_temp >= profile.boost_temp:
            target_level, pump, fan = "boost", profile.boost_pump, profile.boost_fan
        elif cpu_temp <= profile.boost_temp - 5:
            if self.cpu_assist_level != "curve":
                self.restore_water_curves_after_cpu_assist()
            return
        else:
            return
        if target_level == self.cpu_assist_level or self.kraken_write_busy:
            return
        self.apply_cpu_assist_fixed(target_level, pump, fan, cpu_temp)

    def apply_cpu_assist_fixed(self, level: str, pump: int, fan: int, cpu_temp: float) -> None:
        if self.kraken_write_busy:
            return
        self.kraken_write_busy = True

        def fan_done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if result.ok:
                self.permission_retry_after = 0.0
                self.cpu_assist_level = level
                self.set_cooling_mode("pump", "CPU-Assistenz", f"{pump} % bei {cpu_temp:.1f} °C")
                self.set_cooling_mode("fan", "CPU-Assistenz", f"{fan} % bei {cpu_temp:.1f} °C")
                label = "kritisch" if level == "critical" else "verstärkt"
                self.footer_status.setText(f"CPU-Assistenz {label}: {cpu_temp:.1f} °C · Pumpe {pump} % · Lüfter {fan} %")
                self.log_message(self.footer_status.text())
            else:
                self.show_error(result.combined or "CPU-Temperatur-Assistenz konnte den Lüfter nicht einstellen.")

        def pump_done(result: CommandResult) -> None:
            if not result.ok:
                self.kraken_write_busy = False
                self.show_error(result.combined or "CPU-Temperatur-Assistenz konnte die Pumpe nicht einstellen.")
                return
            self.backend.run_async(
                Backend.kraken_direct_args() + ["set", "fan", "speed", str(fan)],
                callback=fan_done,
                timeout=20,
            )

        self.backend.run_async(
            Backend.kraken_direct_args() + ["set", "pump", "speed", str(pump)],
            callback=pump_done,
            timeout=20,
        )

    @staticmethod
    def curve_args(channel: str, points: list[tuple[int, int]]) -> list[str]:
        args = Backend.kraken_direct_args() + ["set", channel, "speed"]
        for temp, duty in points:
            args.extend([str(int(temp)), str(int(duty))])
        return args

    def restore_water_curves_after_cpu_assist(self) -> None:
        if self.kraken_write_busy or self.cpu_restore_pending:
            return
        self.cpu_restore_pending = True
        self.kraken_write_busy = True
        pump_points = self.pump_curve_table[2].points()
        fan_points = self.fan_curve_table[2].points()

        def fan_done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            self.cpu_restore_pending = False
            if result.ok:
                self.cpu_assist_level = "curve"
                self.set_cooling_mode("pump", "Temperaturkurve", "Nach CPU-Assistenz wiederhergestellt")
                self.set_cooling_mode("fan", "Temperaturkurve", "Nach CPU-Assistenz wiederhergestellt")
                self.footer_status.setText("CPU-Assistenz: Kraken-Wasserkurven wieder aktiv")
            else:
                self.show_error(result.combined or "Lüfterkurve konnte nach CPU-Assistenz nicht wiederhergestellt werden.")

        def pump_done(result: CommandResult) -> None:
            if not result.ok:
                self.kraken_write_busy = False
                self.cpu_restore_pending = False
                self.show_error(result.combined or "Pumpenkurve konnte nach CPU-Assistenz nicht wiederhergestellt werden.")
                return
            self.backend.run_async(self.curve_args("fan", fan_points), callback=fan_done, timeout=25)

        self.backend.run_async(self.curve_args("pump", pump_points), callback=pump_done, timeout=25)

    def restore_curves_sync_on_quit(self) -> None:
        for channel, points in (("pump", self.pump_curve_table[2].points()), ("fan", self.fan_curve_table[2].points())):
            try:
                subprocess.run(self.curve_args(channel, points), capture_output=True, timeout=8, check=False)
            except (OSError, subprocess.SubprocessError):
                pass
        self.cpu_assist_level = "curve"

    # ---------- cooling ----------
    def configure_expert_mode_controls(self, enabled: bool) -> None:
        if enabled:
            self.warning_temp.setRange(-20, 120)
            self.critical_temp.setRange(-20, 120)
            self.safety_note.setText(
                "EXPERTENMODUS: Die App begrenzt oder sortiert Warn- und Kritisch-Grenze nicht. "
                "Ungeeignete Werte können Warnungen und die automatische 100-%-Umschaltung unwirksam machen. "
                "CPU-Tjmax und Kraken-Wassertemperatur bleiben unterschiedliche Messgrößen."
            )
        else:
            warning = max(35, min(48, self.warning_temp.value()))
            critical = max(40, min(55, self.critical_temp.value()))
            if critical <= warning:
                warning, critical = 42, 50
            self.warning_temp.setRange(35, 48)
            self.critical_temp.setRange(40, 55)
            self.warning_temp.setValue(warning)
            self.critical_temp.setValue(critical)
            self.safety_note.setText(
                "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. "
                "Eine CPU-Tjmax von 89 oder 95 °C darf niemals als Wassergrenze übernommen werden. "
                "Im normalen Modus bleiben vorsichtige Einstellbereiche aktiv."
            )

    def toggle_expert_mode(self, enabled: bool) -> None:
        if enabled:
            answer = QMessageBox.warning(
                self,
                "Expertenmodus aktivieren",
                "Im Expertenmodus können Warn- und Kritisch-Grenzen ohne die vorsichtigen App-Begrenzungen "
                "eingestellt werden. Falsche Werte können Warnungen oder die automatische Notkühlung verhindern.\n\n"
                "Der Modus verändert keine physikalische Hardwaregrenze und erfolgt auf eigene Verantwortung. Aktivieren?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.expert_mode_checkbox.blockSignals(True)
                self.expert_mode_checkbox.setChecked(False)
                self.expert_mode_checkbox.blockSignals(False)
                return
        self.expert_mode_enabled = enabled
        self.configure_expert_mode_controls(enabled)
        self.settings.setValue("safety/expert_mode", enabled)
        self.footer_status.setText("Expertenmodus aktiv" if enabled else "Sichere Standardbegrenzungen aktiv")

    def set_cooling_mode(self, channel: str, mode: str, detail: str) -> None:
        self.cooling_modes[channel] = (mode, detail)
        self.settings.setValue(f"cooling/{channel}_mode", mode)
        self.settings.setValue(f"cooling/{channel}_mode_detail", detail)
        self.update_cooling_mode_label()

    def update_cooling_mode_label(self) -> None:
        if not hasattr(self, "cooling_mode_label"):
            return
        pump_mode, pump_detail = self.cooling_modes["pump"]
        fan_mode, fan_detail = self.cooling_modes["fan"]
        self.cooling_mode_label.setText(
            f"Pumpe: {pump_mode} · {pump_detail}\nRadiatorlüfter: {fan_mode} · {fan_detail}"
        )

    def sync_safety_thresholds(self) -> None:
        if self.expert_mode_checkbox.isChecked():
            return
        sender = self.sender()
        if sender is self.warning_temp and self.critical_temp.value() <= self.warning_temp.value():
            self.critical_temp.setValue(min(55, self.warning_temp.value() + 1))
        elif sender is self.critical_temp and self.warning_temp.value() >= self.critical_temp.value():
            self.warning_temp.setValue(max(35, self.critical_temp.value() - 1))

    def confirm_low_cooling_value(self, label: str, duty: int, recommended: int) -> bool:
        answer = QMessageBox.warning(
            self,
            "Niedriger Kühlwert",
            f"{label} soll auf nur {duty} % gesetzt werden. Unter {recommended} % kann die Kühlreserve deutlich sinken.\n\n"
            "Die automatische Sicherheitsumschaltung ist kein Ersatz für eine sichere Hardwarekurve. Trotzdem anwenden?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def apply_safe_profile(self) -> None:
        self.auto_max_checkbox.setChecked(True)
        self.apply_quick_profile("Sicheres Standardprofil", SAFE_PROFILE_PUMP, SAFE_PROFILE_FAN)

    def set_fixed_speed(self, channel: str, duty: int) -> None:
        access = self.has_kraken_write_access()
        if access is False:
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return
        minimum = 20 if channel == "pump" else 0
        if not minimum <= duty <= 100:
            self.show_error(f"Ungültiger Wert für {channel}: {duty} %")
            return
        label = "Pumpe" if channel == "pump" else "Lüfter"
        warning_limit = LOW_PUMP_WARNING if channel == "pump" else LOW_FAN_WARNING
        if duty < warning_limit and not self.confirm_low_cooling_value(label, duty, warning_limit):
            return

        if self.kraken_write_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        self.kraken_write_busy = True

        def done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if result.ok:
                self.permission_retry_after = 0.0
                self.footer_status.setText(f"{label} auf {duty} % gesetzt")
                self.set_cooling_mode(channel, "Feste Drehzahl", f"{duty} %")
                QTimer.singleShot(700, self.refresh_status)
            else:
                self.show_error(result.combined or f"{label} konnte nicht eingestellt werden")

        self.backend.run_async(
            Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)],
            callback=done,
            timeout=20,
        )

    def apply_quick_profile(self, name: str, pump: int, fan: int, notify: bool = True) -> None:
        if self.has_kraken_write_access() is False:
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return
        if self.kraken_write_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        self.kraken_write_busy = True
        self.pump_slider.setValue(pump)
        self.fan_slider.setValue(fan)

        def fan_done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if not result.ok:
                self.show_error(result.combined or f"Profil {name}: Lüfter fehlgeschlagen")
                return
            self.footer_status.setText(f"Profil „{name}“ aktiv")
            self.set_cooling_mode("pump", "Feste Drehzahl", f"{pump} % · Profil {name}")
            self.set_cooling_mode("fan", "Feste Drehzahl", f"{fan} % · Profil {name}")
            if notify:
                self.tray.showMessage(APP_NAME, f"Profil „{name}“ wurde angewendet.")
            QTimer.singleShot(700, self.refresh_status)

        def pump_done(result: CommandResult) -> None:
            if not result.ok:
                self.kraken_write_busy = False
                self.show_error(result.combined or f"Profil {name}: Pumpe fehlgeschlagen")
                return
            self.backend.run_async(
                Backend.kraken_direct_args() + ["set", "fan", "speed", str(fan)],
                callback=fan_done,
                timeout=20,
            )

        self.backend.run_async(
            Backend.kraken_direct_args() + ["set", "pump", "speed", str(pump)],
            callback=pump_done,
            timeout=20,
        )

    def apply_curve(self, channel: str, table: QTableWidget) -> None:
        access = self.has_kraken_write_access()
        if access is False:
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return
        points: list[tuple[int, int]] = []
        try:
            for row in range(table.rowCount()):
                temp = int(table.item(row, 0).text())
                duty = int(table.item(row, 1).text())
                if temp < 0 or temp > 60 or duty < (20 if channel == "pump" else 0) or duty > 100:
                    raise ValueError
                points.append((temp, duty))
        except (AttributeError, ValueError):
            self.show_error("Die Kurve enthält einen ungültigen Temperatur- oder Prozentwert.")
            return
        temperatures = [temp for temp, _ in points]
        duties = [duty for _, duty in points]
        if any(next_temp <= temp for temp, next_temp in zip(temperatures, temperatures[1:])):
            self.show_error("Die Temperaturen müssen strikt von oben nach unten ansteigen.")
            return
        if any(next_duty < duty for duty, next_duty in zip(duties, duties[1:])):
            self.show_error("Die Leistung darf bei steigender Temperatur nicht sinken.")
            return
        if points[-1][0] > 50 or points[-1][1] != 100:
            self.show_error("Eine sichere Kurve muss spätestens bei 50 °C einen Endpunkt mit 100 % besitzen.")
            return
        low_limit = LOW_PUMP_WARNING if channel == "pump" else LOW_FAN_WARNING
        low_points = [(temp, duty) for temp, duty in points if duty < low_limit]
        if low_points:
            low_text = ", ".join(f"{temp} °C/{duty} %" for temp, duty in low_points)
            label = "Pumpenkurve" if channel == "pump" else "Lüfterkurve"
            answer = QMessageBox.warning(
                self,
                "Niedrige Kurvenwerte",
                f"Die {label} enthält sehr niedrige Werte: {low_text}.\n\nTrotzdem anwenden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        args = self.curve_args(channel, points)

        if self.kraken_write_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        self.kraken_write_busy = True

        def done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if result.ok:
                label = "Pumpenkurve" if channel == "pump" else "Lüfterkurve"
                self.footer_status.setText(f"{label} angewendet")
                self.set_cooling_mode(channel, "Temperaturkurve", f"{len(points)} Punkte · Direct Access")
                QTimer.singleShot(700, self.refresh_status)
            else:
                message = result.combined or "Kurve konnte nicht angewendet werden"
                if "insufficient permissions" in message.lower():
                    message += (
                        "\n\nDer Kurvenbefehl wurde bereits mit --direct-access gesendet. "
                        "Bitte prüfe den Schreibzugriff auf das Kraken-hidraw-Gerät oder starte die Sitzung nach der udev-Reparatur neu."
                    )
                self.show_error(message)

        self.backend.run_async(args, callback=done, timeout=25)

    # ---------- RGB ----------
    def update_rgb_controls(self) -> None:
        _, count = self.rgb_modes[self.rgb_mode.currentText()]
        self.color1_button.setEnabled(count >= 1)
        self.color2_button.setEnabled(count >= 2)
        mode = self.rgb_modes[self.rgb_mode.currentText()][0]
        animated = mode not in ("off", "fixed")
        directional_modes = {
            "spectrum-wave", "marquee-4", "moving-alternating-4",
            "rainbow-flow", "super-rainbow", "rainbow-pulse"
        }
        self.rgb_speed.setEnabled(animated)
        self.rgb_direction.setEnabled(mode in directional_modes)

    def pick_color(self, which: int) -> None:
        current = QColor("#" + (self.color1_hex if which == 1 else self.color2_hex))
        color = QColorDialog.getColor(current, self, f"Farbe {which}")
        if not color.isValid():
            return
        value = color.name().lstrip("#")
        if which == 1:
            self.color1_hex = value
            self.color1_button.setText(f"Farbe 1 · #{value}")
        else:
            self.color2_hex = value
            self.color2_button.setText(f"Farbe 2 · #{value}")

    def apply_quick_color(self, color: str) -> None:
        self.rgb_channel.setCurrentText("sync")
        self.rgb_mode.setCurrentText("Statisch")
        self.color1_hex = color
        self.color1_button.setText(f"Farbe 1 · #{color}")
        self.apply_rgb()

    def apply_rgb(self) -> None:
        mode, color_count = self.rgb_modes[self.rgb_mode.currentText()]
        args = Backend.rgb_args() + ["set", self.rgb_channel.currentText(), "color", mode]
        if color_count >= 1:
            args.append(self.color1_hex)
        if color_count >= 2:
            args.append(self.color2_hex)
        if mode not in ("off", "fixed"):
            args.extend(["--speed", self.rgb_speed.currentText()])
        directional_modes = {
            "spectrum-wave", "marquee-4", "moving-alternating-4",
            "rainbow-flow", "super-rainbow", "rainbow-pulse"
        }
        if mode in directional_modes:
            args.extend(["--direction", self.rgb_direction.currentText()])

        def done(result: CommandResult) -> None:
            if result.ok:
                self.footer_status.setText("RGB-Effekt angewendet")
            else:
                self.show_error(result.combined or "RGB konnte nicht eingestellt werden")

        self.backend.run_async(args, callback=done, timeout=20)

    # ---------- LCD ----------
    def choose_lcd_file(self) -> None:
        start = str(self.selected_lcd_file.parent if self.selected_lcd_file else Path.home() / "Bilder")
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Bild für das Kraken-LCD auswählen",
            start,
            "Bilder (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;Alle Dateien (*)",
        )
        if filename:
            self.load_lcd_file(Path(filename))

    def load_lcd_file(self, path: Path, quiet: bool = False) -> None:
        if not path.exists():
            if not quiet:
                self.show_error("Die ausgewählte Datei existiert nicht mehr.")
            return
        self.selected_lcd_file = path
        try:
            prepared = self.prepare_lcd_image(path)
        except Exception as exc:  # noqa: BLE001
            if not quiet:
                self.show_error(f"Das Bild konnte nicht vorbereitet werden:\n{exc}")
            return
        self.prepared_lcd_file = prepared
        self.show_round_preview(prepared)
        self.file_name_label.setText(path.name + (" · erstes GIF-Bild" if path.suffix.lower() == ".gif" else ""))
        self.settings.setValue("lcd/file", str(path))

    def prepare_lcd_image(self, path: Path) -> Path:
        if Image is None:
            raise RuntimeError("Pillow fehlt. Installiere python3-pillow.")
        output = self.temp_dir / "lcd-prepared.png"
        with Image.open(path) as image:
            if getattr(image, "is_animated", False):
                image.seek(0)
            image = image.convert("RGB")
            # Fit/crop to a square before liquidctl performs its own final conversion.
            width, height = image.size
            size = min(width, height)
            left = (width - size) // 2
            top = (height - size) // 2
            image = image.crop((left, top, left + size, top + size))
            image = image.resize((240, 240), Image.Resampling.LANCZOS)
            image.save(output, format="PNG", optimize=True)
        return output

    def apply_lcd_display_settings(self) -> None:
        if self.kraken_write_busy or self.lcd_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        self.kraken_write_busy = True

        def orientation_done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if not result.ok:
                self.show_error(result.combined or "LCD-Ausrichtung konnte nicht gesetzt werden")
                return
            self.footer_status.setText("LCD-Einstellungen angewendet")
            if self.keep_lcd_checkbox.isChecked() and self.prepared_lcd_file:
                QTimer.singleShot(500, self.send_lcd_now)

        def brightness_done(result: CommandResult) -> None:
            if not result.ok:
                self.kraken_write_busy = False
                self.show_error(result.combined or "LCD-Helligkeit konnte nicht gesetzt werden")
                return
            self.backend.run_async(
                Backend.kraken_args()
                + ["set", "lcd", "screen", "orientation", self.lcd_orientation.currentText()],
                callback=orientation_done,
                timeout=20,
            )

        self.backend.run_async(
            Backend.kraken_args()
            + ["set", "lcd", "screen", "brightness", str(self.lcd_brightness.value())],
            callback=brightness_done,
            timeout=20,
        )

    def send_lcd_now(self) -> None:
        self.stop_clock_mode(update_status=False)
        if not self.prepared_lcd_file or not self.prepared_lcd_file.exists():
            self.show_error("Bitte zuerst ein Bild auswählen.")
            return

        def uploaded(result: CommandResult) -> None:
            if result.ok and not self.keep_lcd_checkbox.isChecked():
                self.lcd_mode_label.setText(
                    "LCD-Modus: statisches Bild · einmal übertragen. "
                    "Bei Firmware 2.0.0 kann es ohne Fallback dauerhaft sichtbar bleiben."
                )

        self.send_static_lcd(self.prepared_lcd_file, quiet=False, completion=uploaded)

    def send_lcd_keepalive(self) -> None:
        if self.keep_lcd_checkbox.isChecked() and self.prepared_lcd_file and not self.lcd_busy:
            self.send_static_lcd(self.prepared_lcd_file, quiet=True)

    def send_static_lcd(
        self,
        path: Path,
        quiet: bool,
        completion: Callable[[CommandResult], None] | None = None,
    ) -> None:
        if self.lcd_busy or self.kraken_write_busy:
            return
        self.lcd_busy = True
        self.kraken_write_busy = True
        self.footer_status.setText("LCD-Bild wird übertragen …")

        def done(result: CommandResult) -> None:
            self.lcd_busy = False
            self.kraken_write_busy = False
            if result.ok:
                self.footer_status.setText("LCD-Bild angezeigt")
                if not quiet:
                    self.log_message("LCD-Upload erfolgreich.")
            elif not quiet:
                self.show_error(result.combined or "LCD-Bild konnte nicht übertragen werden")
            else:
                self.footer_status.setText("LCD-Fallback fehlgeschlagen")
                self.log_message(result.combined or "LCD-Fallback fehlgeschlagen")
            if completion is not None:
                completion(result)

        self.backend.run_async(
            Backend.kraken_args() + ["set", "lcd", "screen", "static", str(path)],
            callback=done,
            timeout=60,
            log_command=not quiet,
            log_output=not quiet,
        )

    def show_liquid_screen(self) -> None:
        self.stop_clock_mode(update_status=False)
        self.lcd_keepalive_timer.stop()
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(False)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(False)
        self.settings.setValue("lcd/keepalive", False)
        if self.kraken_write_busy or self.lcd_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        self.kraken_write_busy = True

        def done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if result.ok:
                self.footer_status.setText("Flüssigkeitstemperatur wird angezeigt")
                self.lcd_mode_label.setText("LCD-Modus: Flüssigkeitstemperatur")
            else:
                self.show_error(result.combined or "LCD-Modus konnte nicht umgestellt werden")

        self.backend.run_async(
            Backend.kraken_args() + ["set", "lcd", "screen", "liquid"],
            callback=done,
            timeout=20,
        )

    def toggle_lcd_keepalive(self, enabled: bool) -> None:
        if enabled and not self.keepalive_warning_acknowledged:
            answer = QMessageBox.warning(
                self,
                "Experimenteller LCD-Fallback",
                "Der Fallback überträgt das Bild regelmäßig erneut. Die langfristige Wirkung häufiger Uploads auf den "
                "Displayspeicher ist nicht ausreichend bekannt. Nur fortfahren, wenn das Bild tatsächlich zurückspringt.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.keep_lcd_checkbox.blockSignals(True)
                self.keep_lcd_checkbox.setChecked(False)
                self.keep_lcd_checkbox.blockSignals(False)
                self.set_keepalive_controls(False)
                self.settings.setValue("lcd/keepalive", False)
                return
            self.keepalive_warning_acknowledged = True
        if enabled:
            self.stop_clock_mode(update_status=False)
        self.update_keepalive_interval()
        self.set_keepalive_controls(enabled)
        if enabled:
            if self.lcd_busy or self.kraken_write_busy:
                self.keep_lcd_checkbox.blockSignals(True)
                self.keep_lcd_checkbox.setChecked(False)
                self.keep_lcd_checkbox.blockSignals(False)
                self.set_keepalive_controls(False)
                self.settings.setValue("lcd/keepalive", False)
                self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
                return
            if not self.prepared_lcd_file:
                self.keep_lcd_checkbox.blockSignals(True)
                self.keep_lcd_checkbox.setChecked(False)
                self.keep_lcd_checkbox.blockSignals(False)
                self.set_keepalive_controls(False)
                self.settings.setValue("lcd/keepalive", False)
                self.show_error("Bitte zuerst ein Bild auswählen.")
                return

            def uploaded(result: CommandResult) -> None:
                if result.ok and self.keep_lcd_checkbox.isChecked():
                    self.lcd_keepalive_timer.start()
                    self.footer_status.setText("LCD-Fallback aktiv")
                    self.lcd_mode_label.setText(
                        f"LCD-Modus: statisches Bild · Fallback alle {self.lcd_interval.value()} Sekunden"
                    )
                elif not result.ok:
                    self.keep_lcd_checkbox.blockSignals(True)
                    self.keep_lcd_checkbox.setChecked(False)
                    self.keep_lcd_checkbox.blockSignals(False)
                    self.set_keepalive_controls(False)
                    self.settings.setValue("lcd/keepalive", False)

            # Erst nach einem erfolgreichen Upload startet der Wiederholungs-Timer.
            self.send_static_lcd(self.prepared_lcd_file, quiet=False, completion=uploaded)
        else:
            self.lcd_keepalive_timer.stop()
            self.footer_status.setText("LCD-Fallback ausgeschaltet")
            self.lcd_mode_label.setText(
                "LCD-Modus: Fallback aus · das aktuell übertragene Bild kann auf der Kraken sichtbar bleiben. "
                "Mit „Zur Flüssigkeitstemperatur zurück“ wechselst du bewusst zurück."
            )
        self.settings.setValue("lcd/keepalive", enabled)

    def set_keepalive_controls(self, enabled: bool) -> None:
        self.keepalive_interval_label.setEnabled(enabled)
        self.lcd_interval.setEnabled(enabled)

    def update_keepalive_interval(self) -> None:
        self.lcd_keepalive_timer.setInterval(self.lcd_interval.value() * 1000)
        if self.lcd_keepalive_timer.isActive():
            self.lcd_keepalive_timer.start()
            self.lcd_mode_label.setText(
                f"LCD-Modus: statisches Bild · Fallback alle {self.lcd_interval.value()} Sekunden"
            )

    def show_round_preview(self, path: Path) -> None:
        source = QPixmap(str(path))
        if source.isNull():
            self.preview.clear()
            self.preview.setText("Vorschau nicht verfügbar")
            return
        size = 270
        canvas = QPixmap(size, size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        clip = QPainterPath()
        clip.addEllipse(2, 2, size - 4, size - 4)
        painter.setClipPath(clip)
        scaled = source.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.setClipping(False)
        painter.setPen(QPen(QColor("#35c4ff"), 4))
        painter.drawEllipse(2, 2, size - 4, size - 4)
        painter.end()
        self.preview.setPixmap(canvas)

    @staticmethod
    def _clock_font(size: int, bold: bool = True):
        if ImageFont is None:
            return None
        candidates = [
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
            "/usr/share/fonts/google-noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/google-noto/NotoSans-Regular.ttf",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size)
        return ImageFont.load_default()

    def pick_clock_color(self, target: str) -> None:
        current_hex = self.clock_text_hex if target == "text" else self.clock_background_hex
        color = QColorDialog.getColor(QColor("#" + current_hex), self, "Uhrfarbe auswählen")
        if not color.isValid():
            return
        value = color.name().lstrip("#")
        if target == "text":
            self.clock_text_hex = value
            self.clock_text_button.setText(f"Text · #{value}")
        else:
            self.clock_background_hex = value
            self.clock_background_button.setText(f"Hintergrund · #{value}")
        if self.clock_active:
            self.update_clock_lcd()

    def render_clock_image(self) -> Path:
        if Image is None or ImageDraw is None or ImageFont is None:
            raise RuntimeError("Pillow fehlt. Installiere python3-pillow.")
        now = time.localtime()
        self.clock_render_key = time.strftime("%Y%m%d%H%M", now)
        if self.clock_format.currentData() == "12":
            clock_text = time.strftime("%I:%M %p", now).lstrip("0")
        else:
            clock_text = time.strftime("%H:%M", now)
        date_text = time.strftime("%d.%m.%Y", now)

        image = Image.new("RGB", (240, 240), "#" + self.clock_background_hex)
        draw = ImageDraw.Draw(image)
        # Subtiler Ring verbessert die Lesbarkeit auf dem runden Pumpendisplay.
        ring = tuple(int(self.clock_text_hex[i:i+2], 16) for i in (0, 2, 4))
        ring_color = tuple(max(0, min(255, int(c * 0.35))) for c in ring)
        draw.ellipse((8, 8, 232, 232), outline=ring_color, width=3)

        requested_size = self.clock_font_size.value()
        main_font = self._clock_font(requested_size, bold=True)
        date_font = self._clock_font(22, bold=False)
        fill = "#" + self.clock_text_hex
        bbox = draw.textbbox((0, 0), clock_text, font=main_font)
        while bbox[2] - bbox[0] > 208 and requested_size > 32:
            requested_size -= 2
            main_font = self._clock_font(requested_size, bold=True)
            bbox = draw.textbbox((0, 0), clock_text, font=main_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        y = 92 - th / 2 if self.clock_show_date.isChecked() else 120 - th / 2
        draw.text(((240 - tw) / 2, y), clock_text, font=main_font, fill=fill)
        if self.clock_show_date.isChecked():
            db = draw.textbbox((0, 0), date_text, font=date_font)
            dw = db[2] - db[0]
            draw.text(((240 - dw) / 2, 154), date_text, font=date_font, fill=fill)
        image.save(self.clock_image_file, format="PNG", optimize=True)
        self.show_round_preview(self.clock_image_file)
        self.file_name_label.setText("Live-Uhr · Aktualisierung zum Minutenwechsel")
        return self.clock_image_file

    def preview_clock_image(self) -> None:
        try:
            self.render_clock_image()
            self.clock_status_label.setText("Uhrvorschau aktualisiert · noch nicht auf das LCD übertragen.")
        except Exception as exc:  # noqa: BLE001
            self.show_error(f"Die Uhrvorschau konnte nicht erzeugt werden:\n{exc}")

    def start_clock_mode(self) -> None:
        if not self.devices_ready:
            self.show_error("Die Kraken ist noch nicht verbunden.")
            return
        if not self.clock_warning_acknowledged:
            answer = QMessageBox.warning(
                self,
                "Experimentelle LCD-Uhr",
                "Die Uhr überträgt ungefähr einmal pro Minute ein neues statisches Bild. Die langfristige Wirkung dieser "
                "Upload-Häufigkeit auf den Displayspeicher ist nicht ausreichend bekannt. Uhr trotzdem starten?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.clock_warning_acknowledged = True
        self.lcd_keepalive_timer.stop()
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(False)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(False)
        self.clock_active = True
        self.settings.setValue("clock/active", True)
        self.settings.setValue("lcd/keepalive", False)
        fmt = "24h" if str(self.clock_format.currentData()) == "24" else "12h AM/PM"
        resend = f"alle {self.clock_resend_interval.value()} s" if self.clock_auto_resend.isChecked() else "aus"
        self.log_message(f"LCD-UHR: gestartet · Format {fmt} · Datum={'ein' if self.clock_show_date.isChecked() else 'aus'} · automatisches Senden {resend}")
        self.update_clock_lcd()

    def stop_clock_mode(self, update_status: bool = True) -> None:
        self.clock_active = False
        self.clock_timer.stop()
        self.clock_keepalive_timer.stop()
        self.settings.setValue("clock/active", False)
        if update_status:
            self.clock_status_label.setText(
                "Uhr angehalten. Das zuletzt übertragene Bild kann auf dem Display sichtbar bleiben."
            )
            self.footer_status.setText("LCD-Uhr angehalten")

    def schedule_next_clock_update(self) -> None:
        if not self.clock_active:
            return
        now = time.time()
        delay_ms = max(1000, int((60 - (now % 60)) * 1000) + 150)
        self.clock_timer.start(delay_ms)
        seconds = max(1, delay_ms // 1000)
        resend = (
            f" · automatisches erneutes Senden alle {self.clock_resend_interval.value()} Sekunden"
            if self.clock_auto_resend.isChecked() else " · kein zusätzliches erneutes Senden"
        )
        self.clock_status_label.setText(
            f"Uhr aktiv · nächste Minutenaktualisierung in etwa {seconds} Sekunden{resend}."
        )

    def update_clock_lcd(self) -> None:
        if not self.clock_active:
            return
        if self.lcd_busy or self.kraken_write_busy:
            self.clock_timer.start(2000)
            return
        try:
            image_path = self.render_clock_image()
        except Exception as exc:  # noqa: BLE001
            self.stop_clock_mode(update_status=False)
            self.show_error(f"Die Uhr konnte nicht erzeugt werden:\n{exc}")
            return

        def uploaded(result: CommandResult) -> None:
            if result.ok and self.clock_active:
                current = time.strftime("%H:%M")
                self.lcd_mode_label.setText(f"LCD-Modus: Uhr · zuletzt aktualisiert um {current}")
                self.footer_status.setText("LCD-Uhr aktiv")
                self.log_message(f"LCD-UHR: Bild erfolgreich übertragen · {current}")
                if self.clock_auto_resend.isChecked():
                    self.update_clock_keepalive_interval()
                    self.clock_keepalive_timer.start()
                else:
                    self.clock_keepalive_timer.stop()
                # Falls der Upload genau über den Minutenwechsel lief, sofort das neue Minutenbild erzeugen.
                if time.strftime("%Y%m%d%H%M") != self.clock_render_key:
                    QTimer.singleShot(100, self.update_clock_lcd)
                else:
                    self.schedule_next_clock_update()
            elif not result.ok:
                self.log_message("LCD-UHR: Übertragung fehlgeschlagen · " + (result.combined or "unbekannter Fehler"))
                self.stop_clock_mode(update_status=False)
                self.clock_status_label.setText("Uhr wegen eines Übertragungsfehlers angehalten.")

        self.send_static_lcd(image_path, quiet=True, completion=uploaded)

    def update_clock_keepalive_controls(self, enabled: bool) -> None:
        self.clock_resend_interval.setEnabled(enabled)
        if not enabled:
            self.clock_keepalive_timer.stop()
        elif self.clock_active and self.clock_image_file.exists():
            self.update_clock_keepalive_interval()
            self.clock_keepalive_timer.start()
        self.settings.setValue("clock/auto_resend", enabled)

    def update_clock_keepalive_interval(self) -> None:
        self.clock_keepalive_timer.setInterval(self.clock_resend_interval.value() * 1000)
        if self.clock_keepalive_timer.isActive():
            self.clock_keepalive_timer.start()
        self.settings.setValue("clock/resend_interval", self.clock_resend_interval.value())

    def send_clock_keepalive(self) -> None:
        if not self.clock_active or not self.clock_auto_resend.isChecked():
            self.clock_keepalive_timer.stop()
            return
        if not self.clock_image_file.exists() or self.lcd_busy or self.kraken_write_busy:
            return

        def resent(result: CommandResult) -> None:
            if not result.ok:
                self.clock_status_label.setText(
                    "Uhr bleibt aktiv, aber das automatische erneute Senden ist fehlgeschlagen. Details stehen im Log."
                )

        # Das vorhandene Minutenbild wird erneut gesendet; neu gerendert wird erst zum Minutenwechsel.
        self.send_static_lcd(self.clock_image_file, quiet=True, completion=resent)

    # ---------- app settings ----------
    def update_status_interval(self) -> None:
        self.status_timer.setInterval(self.refresh_interval.value() * 1000)

    @staticmethod
    def autostart_file() -> Path:
        return Path.home() / ".config" / "autostart" / "kraken-control.desktop"

    def set_autostart(self, enabled: bool) -> None:
        path = self.autostart_file()
        try:
            if enabled:
                path.parent.mkdir(parents=True, exist_ok=True)
                executable = shutil.which("kraken-control") or str(Path(__file__).resolve())
                exec_line = executable if executable.endswith("kraken-control") else f"python3 {executable}"
                icon_line = str(Path(__file__).with_name("kraken-control.svg"))
                path.write_text(
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    f"Name={DISPLAY_NAME}\n"
                    f"Exec={exec_line}\n"
                    f"Icon={icon_line}\n"
                    "Terminal=false\n"
                    "X-GNOME-Autostart-enabled=true\n",
                    encoding="utf-8",
                )
            elif path.exists():
                path.unlink()
        except OSError as exc:
            self.show_error(f"Autostart konnte nicht geändert werden:\n{exc}")
            self.autostart_checkbox.blockSignals(True)
            self.autostart_checkbox.setChecked(not enabled)
            self.autostart_checkbox.blockSignals(False)

    # ---------- interaction and audit log ----------
    def enable_interaction_logging(self) -> None:
        app = QApplication.instance()
        self._interaction_audit = InteractionAuditLogger(self)
        if app is not None:
            app.installEventFilter(self._interaction_audit)

        for combo in self.findChildren(QComboBox):
            combo.activated.connect(
                lambda _index, widget=combo: self.log_user_action(
                    "ÄNDERUNG", f"Auswahl '{self.control_name(widget)}' = '{widget.currentText()}'"
                )
            )
        for slider in self.findChildren(QSlider):
            slider.sliderReleased.connect(
                lambda widget=slider: self.log_user_action(
                    "ÄNDERUNG", f"Regler '{self.control_name(widget)}' = {widget.value()}"
                )
            )
        for spin in self.findChildren(QSpinBox):
            spin.editingFinished.connect(
                lambda widget=spin: self.log_user_action(
                    "ÄNDERUNG", f"Zahlenfeld '{self.control_name(widget)}' = {widget.value()}"
                )
            )
        for line_edit in self.findChildren(QLineEdit):
            line_edit.editingFinished.connect(
                lambda widget=line_edit: self.log_user_action(
                    "ÄNDERUNG", f"Textfeld '{self.control_name(widget)}' = '{self.safe_control_value(widget.text())}'"
                )
            )
        for checkbox in self.findChildren(QCheckBox):
            checkbox.clicked.connect(
                lambda checked, widget=checkbox: self.log_user_action(
                    "ÄNDERUNG", f"Kontrollkästchen '{self.control_name(widget)}' = {'ein' if checked else 'aus'}"
                )
            )
        for table in self.findChildren(QTableWidget):
            table.cellChanged.connect(
                lambda row, column, widget=table: self.log_table_change(widget, row, column)
            )
        self.tabs.currentChanged.connect(
            lambda index: self.log_user_action("NAVIGATION", f"Bereich '{self.tabs.tabText(index)}' geöffnet")
        )
        for action in self.findChildren(QAction):
            action.triggered.connect(
                lambda _checked=False, item=action: self.log_user_action(
                    "MENÜ", re.sub(r"\s+", " ", item.text().replace("&", " ")).strip() or "Aktion"
                )
            )

    @staticmethod
    def safe_control_value(value: str) -> str:
        cleaned = redact_private_text(value.strip())
        if len(cleaned) > 80:
            return cleaned[:77] + "..."
        return cleaned

    @staticmethod
    def control_name(widget: QWidget) -> str:
        try:
            accessible = widget.accessibleName().strip()
            if accessible:
                return accessible
        except RuntimeError:
            pass
        current = widget
        for _depth in range(4):
            parent = current.parentWidget()
            if parent is None:
                break
            layout = parent.layout()
            if isinstance(layout, QFormLayout):
                label_widget = layout.labelForField(current)
                if isinstance(label_widget, QLabel):
                    label_text = re.sub(r"\s+", " ", label_widget.text().replace("&", " ")).strip()
                    if label_text:
                        return label_text
            current = parent
        if isinstance(widget, QAbstractButton):
            label = widget.text().replace("&", " ").strip()
            if label:
                return re.sub(r"\s+", " ", label)
        object_name = widget.objectName().strip()
        return object_name or widget.__class__.__name__

    def log_user_action(self, category: str, detail: str) -> None:
        self.log_message(f"{category}: {detail}")

    def log_table_change(self, table: QTableWidget, row: int, column: int) -> None:
        if not table.hasFocus():
            return
        item = table.item(row, column)
        value = item.text() if item is not None else ""
        self.log_user_action(
            "ÄNDERUNG",
            f"{self.control_name(table)} · Zeile {row + 1}, Spalte {column + 1} = '{self.safe_control_value(value)}'",
        )

    def clear_application_log(self) -> None:
        self.log_view.clear()
        self._trim_log_to_character_limit()
        self.log_message("LOG: Protokoll wurde geleert")

    def copy_application_log(self) -> None:
        QApplication.clipboard().setText(self.log_view.toPlainText())
        self.log_message("LOG: Protokoll wurde in die Zwischenablage kopiert")

    def save_application_log(self) -> None:
        default_name = Path.home() / f"kraken-control-{time.strftime('%Y%m%d-%H%M%S')}.log"
        filename, _ = QFileDialog.getSaveFileName(self, "Kraken-Control-Log speichern", str(default_name), "Logdateien (*.log *.txt)")
        if not filename:
            self.log_message("LOG: Speichern abgebrochen")
            return
        try:
            Path(filename).write_text(self.log_view.toPlainText() + "\n", encoding="utf-8")
            self.log_message(f"LOG: Protokoll gespeichert als {Path(filename).name}")
        except OSError as exc:
            self.show_error(f"Log konnte nicht gespeichert werden:\n{exc}")

    # ---------- helpers ----------
    def _trim_log_to_character_limit(self) -> None:
        if not hasattr(self, "log_view"):
            return
        limit = int(getattr(self, "log_char_limit", 10000))
        text = self.log_view.toPlainText()
        if len(text) > limit:
            lines = text.splitlines()
            while lines and len("\n".join(lines)) > limit:
                lines.pop(0)
            self.log_view.setPlainText("\n".join(lines))
            cursor = self.log_view.textCursor()
            cursor.setPosition(len(self.log_view.toPlainText()))
            self.log_view.setTextCursor(cursor)
        if hasattr(self, "log_counter_label"):
            count = len(self.log_view.toPlainText())
            self.log_counter_label.setText(f"Log: {count:,} / {limit:,} Zeichen".replace(",", "."))

    def log_message(self, message: str) -> None:
        if not message:
            return
        stamp = time.strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{stamp}] {redact_private_text(message).rstrip()}")
        self._trim_log_to_character_limit()

    def show_error(self, message: str) -> None:
        if re.search(r"insufficient permissions|permission denied|could not open.*permissions", message, re.IGNORECASE):
            self.show_permission_error(message)
            return
        self.log_message("FEHLER: " + message)
        QMessageBox.critical(self, APP_NAME, message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(True)
    window = KrakenControl()
    app.aboutToQuit.connect(window.backend.shutdown)
    window.show()
    sys.exit(app.exec())

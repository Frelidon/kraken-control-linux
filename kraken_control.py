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
import signal
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
from PySide6.QtCore import QEvent, QObject, QPointF, QProcess, QRectF, QSettings, QSize, Qt, QTimer, Signal, QStandardPaths, QUrl, qVersion
from PySide6.QtGui import QAction, QBrush, QColor, QCloseEvent, QDesktopServices, QFont, QIcon, QImage, QImageReader, QKeyEvent, QKeySequence, QLinearGradient, QMouseEvent, QMovie, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRadialGradient
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
    QMenu,
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
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWizard,
    QWizardPage,
    QWidget,
    QPlainTextEdit,
)

from kraken_lcd_designs import (
    COLOR_PRESETS,
    DEFAULT_ACCENT,
    DEFAULT_LABEL_COLOR,
    DEFAULT_VALUE_COLOR,
    DESIGNS,
    normalize_hex_color,
    render_hardware_animation,
    render_hardware_design,
)
from kraken_sensors import read_amd_cpu_temperature, read_amd_gpu_temperature
from openlinkhub_mouse_visuals import mouse_schema, visual_button_rows

APP_NAME = "Open Hardware Control"
DISPLAY_NAME = "Open Hardware Control by Frelidon"
APP_VERSION = "3.0.9"
ORG_NAME = "FloriLinuxTools"
LEGACY_SETTINGS_APP_NAME = "Kraken Control"
LIQUIDCTL = shutil.which("liquidctl") or "liquidctl"
KRAKEN_MATCH = "NZXT Kraken 2023"
RGB_MATCH = "NZXT 2023 RGB Controller"
DEFAULT_LCD_INTERVAL = 7
LOW_PUMP_WARNING = 30
LOW_FAN_WARNING = 20
SAFE_PROFILE_PUMP = 65
SAFE_PROFILE_FAN = 65
DEPENDENCY_PACKAGES = ("liquidctl", "python3-pyside6", "python3-pillow", "qt6-qtsvg")
PROFILE_SCHEMA_VERSION = 1
DEFAULT_UI_SCALE = 100
DEFAULT_BACKGROUND_THEME = "Sternenfeld"
LCD_FAILURE_LIMIT = 3
GIF_STREAM_START_WAIT_SECONDS = 15.0
GIF_STREAM_WATCHDOG_SECONDS = 12.0
GIF_HELPER_NAME = "kraken_cam_streamer.py"
AUTOSTART_LCD_DELAY_MS = 5000
SUPPORTED_UI_LANGUAGES = {"de": "Deutsch", "en": "English", "es": "Español", "fr": "Français"}


def normalize_temperature_unit(value: object) -> str:
    return "f" if str(value).strip().casefold() in {"f", "fahrenheit", "°f"} else "c"


def celsius_to_display(value: float, unit: str) -> float:
    return value * 9.0 / 5.0 + 32.0 if normalize_temperature_unit(unit) == "f" else value


def display_to_celsius(value: float, unit: str) -> float:
    return (value - 32.0) * 5.0 / 9.0 if normalize_temperature_unit(unit) == "f" else value


def temperature_symbol(unit: str) -> str:
    return "°F" if normalize_temperature_unit(unit) == "f" else "°C"

# Official project, dependency and hardware pages shown in the About tab.
# Public project repository; internal test builds are not pushed unless explicitly released.
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
PROJECT_GITHUB_URL = "https://github.com/Frelidon/kraken-control-linux"
OPENLINKHUB_URL = "https://github.com/jurkovic-nikola/OpenLinkHub"
OPENLINKHUB_API_DOCS_URL = "https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/api/README.md"
OPENLINKHUB_USER_INSTALL_URL = "https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/install-user-space.sh"
OPENLINKHUB_LICENSE_URL = "https://github.com/jurkovic-nikola/OpenLinkHub/blob/main/LICENSE"
OPENLINKHUB_API_URL = "http://127.0.0.1:27003"
AMD_PROCESSOR_SPECS_URL = "https://www.amd.com/en/products/specifications/processors.html"
K10TEMP_DOCS_URL = "https://docs.kernel.org/hwmon/k10temp.html"
LIQUIDCTL_UDEV_URL = "https://github.com/liquidctl/liquidctl/blob/main/extra/linux/71-liquidctl.rules"

# Visible cooling curves are software-controlled CPU-temperature curves.  The
# Kraken firmware itself only knows its liquid sensor, so the application
# evaluates these curves and writes the resulting fixed duty.  Conservative
# liquid curves remain private fallbacks for a clean application shutdown.
DEFAULT_PUMP_CURVE = ((30, 40), (45, 45), (60, 55), (75, 72), (90, 100))
DEFAULT_FAN_CURVE = ((30, 20), (45, 25), (60, 40), (75, 68), (90, 100))
AM5_95_PUMP_CURVE = ((30, 42), (50, 48), (65, 60), (80, 80), (90, 100))
AM5_95_FAN_CURVE = ((30, 22), (50, 30), (65, 48), (80, 78), (90, 100))
AM5_X3D_89_PUMP_CURVE = ((30, 45), (45, 50), (60, 65), (75, 85), (85, 100))
AM5_X3D_89_FAN_CURVE = ((30, 25), (45, 32), (60, 52), (75, 82), (85, 100))
SAFE_HARDWARE_PUMP_CURVE = ((25, 45), (30, 55), (35, 70), (40, 85), (45, 100))
SAFE_HARDWARE_FAN_CURVE = ((25, 30), (30, 40), (35, 60), (40, 82), (45, 100))
CPU_CURVE_SAMPLE_MS = 1000
CPU_CURVE_RISE_INTERVAL = 3.0
CPU_CURVE_FALL_INTERVAL = 12.0
CPU_CURVE_RISE_DELTA = 3
CPU_CURVE_FALL_DELTA = 5
CPU_CURVE_DUTY_QUANTUM = 2
CPU_CURVE_SENSOR_FAILURE_LIMIT = 5

# First localization stage carried forward in the internal 2.9.8 build.  German remains the
# canonical source language so existing profiles/settings and hardware strings
# do not need a migration.  Static UI strings can be switched live; dynamic
# hardware/log messages deliberately keep their original technical wording for
# now so diagnostics remain unambiguous during the internal test phase.
UI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "Übersicht": "Overview", "Kühlung": "Cooling", "Einstellungen": "Settings", "Profile": "Profiles", "Über": "About",
        "&Datei": "&File", "&Gerät": "&Device", "&Ansicht": "&View", "&Profile": "&Profiles", "&Hilfe": "&Help",
        "&Beenden": "&Quit", "Geräte &aktualisieren": "&Refresh devices", "&Sicheres Profil anwenden": "Apply &safe profile",
        "&Berechtigungen reparieren": "&Repair permissions", "Profile verwalten": "Manage profiles", "&Tastaturbedienung": "&Keyboard controls",
        "Zum Bereich &Über": "Open &About", "Bereit": "Ready", "Systemzustand": "System status", "Gerät wird geprüft …": "Checking device …",
        "Geräte initialisieren": "Initialize devices", "Schnellprofile": "Quick profiles", "Anwenden": "Apply", "Leise": "Quiet",
        "Ausgeglichen": "Balanced", "Leistung": "Performance", "Maximum": "Maximum", "Manuelle Steuerung": "Manual control",
        "Pumpe": "Pump", "Radiatorlüfter": "Radiator fans", "&Pumpe anwenden": "Apply &pump", "&Lüfter anwenden": "Apply &fans",
        "Aktiver Kühlmodus": "Active cooling mode", "Pumpenkurve nach Wassertemperatur": "Pump curve by liquid temperature",
        "Lüfterkurve nach Wassertemperatur": "Fan curve by liquid temperature", "&Standardwerte": "&Defaults", "Kurve &anwenden": "Apply &curve",
        "AMD-AM5-Prozessorprofil und CPU-Temperatur-Assistenz": "AMD AM5 CPU profile and CPU temperature assist",
        "Bitte Prozessor auswählen": "Select processor", "CPU &automatisch erkennen": "&Detect CPU automatically",
        "Profil und empfohlene Kraken-Kurven &laden": "&Load profile and recommended Kraken curves",
        "Prozessor": "Processor", "Kraken-Wassertemperatur – Sicherheitsgrenzen": "Kraken liquid temperature – safety limits",
        "Warnung ab": "Warning at", "Kritisch ab": "Critical at", "Bei kritischer Wassertemperatur automatisch 100 % setzen": "Set 100% automatically at critical liquid temperature",
        "Sicheres Standardprofil anwenden · 65 % / 65 %": "Apply safe default profile · 65% / 65%", "Beleuchtung": "Lighting",
        "Kanal": "Channel", "Effekt": "Effect", "Geschwindigkeit": "Speed", "Richtung": "Direction", "Farben": "Colors", "RGB anwenden": "Apply RGB",
        "Eigenes Bild": "Custom image", "PNG, JPG oder GIF auswählen": "Select PNG, JPG or GIF", "Kein Bild ausgewählt": "No image selected",
        "Bild einmal übertragen": "Upload image once", "Automatisch erneut senden (Fallback)": "Automatically resend (fallback)",
        "Helligkeit": "Brightness", "Ausrichtung": "Orientation", "Helligkeit und Ausrichtung anwenden": "Apply brightness and orientation",
        "Zur Flüssigkeitstemperatur zurück": "Return to liquid temperature", "Uhr auf dem LCD": "Clock on LCD", "Zeitformat": "Time format",
        "Datum unter der Uhrzeit anzeigen": "Show date below time", "Schriftgröße": "Font size", "Uhr automatisch erneut senden": "Automatically resend clock",
        "Erneut senden alle": "Resend every", "Vorschau": "Preview", "Uhr starten": "Start clock", "Uhr anhalten": "Stop clock",
        "Automatisches Wiederherstellen": "Automatic restore", "Gewähltes Bild beim Programmstart wieder anzeigen": "Restore selected image at application startup",
        "Design": "Design", "Darstellung": "Appearance", "Systemmodus": "System mode", "Hell": "Light", "Dunkel": "Dark",
        "Eigene Akzentfarbe": "Custom accent color", "Farbe auswählen": "Choose color", "Voreinstellungen": "Presets", "Design anwenden": "Apply design",
        "Anzeige und DPI": "Display and DPI", "Monitor wird erkannt …": "Detecting monitor …", "Automatisch an Monitor und Seitenverhältnis anpassen": "Automatically adapt to monitor and aspect ratio",
        "App-Skalierung": "App scaling", "Layoutvorgabe": "Layout preset", "Automatisch": "Automatic", "Kompakt · 16:10": "Compact · 16:10",
        "Standard · 16:9": "Standard · 16:9", "Ultrawide · 21:9": "Ultrawide · 21:9", "Super-Ultrawide · 32:9": "Super ultrawide · 32:9",
        "Monitor neu erkennen": "Detect monitor again", "Anzeige anwenden": "Apply display settings", "Animierter Hintergrund": "Animated background",
        "Animation aktivieren": "Enable animation", "Pausieren, wenn die App nicht aktiv ist": "Pause when app is inactive", "Hintergrund anwenden": "Apply background",
        "Animation ausschalten": "Disable animation", "Thema": "Theme", "Bildrate": "Frame rate", "Intensität": "Intensity",
        "Programm": "Application", "Mit dem Desktop starten": "Start with desktop", "Beim Schließen im Infobereich weiterlaufen": "Keep running in system tray when closing",
        "Status-Aktualisierung": "Status refresh", "Einrichtungsassistent erneut starten": "Run setup wizard again", "Abhängigkeiten": "Dependencies",
        "Wird geprüft …": "Checking …", "Abhängigkeiten &prüfen": "&Check dependencies", "Fehlende Pakete &installieren": "&Install missing packages",
        "Gerätezugriff": "Device access", "Zugriff ohne sudo &testen": "&Test access without sudo", "Berechtigungen mit Administratorabfrage &reparieren": "&Repair permissions with administrator prompt",
        "Hinweis": "Notice", "Profil beim Start": "Profile at startup", "Automatisch laden": "Load automatically", "Kein automatisches Profil": "No automatic profile",
        "Zuletzt verwendetes Profil": "Last used profile", "Profil erstellen oder aktualisieren": "Create or update profile", "Name": "Name", "Kategorie": "Category",
        "Beschreibung": "Description", "Als neues Profil speichern": "Save as new profile", "Ausgewähltes Profil aktualisieren": "Update selected profile",
        "Profil anwenden": "Apply profile", "Duplizieren": "Duplicate", "Umbenennen": "Rename", "Löschen": "Delete", "Importieren": "Import", "Exportieren": "Export",
        "Noch kein Profil ausgewählt.": "No profile selected yet.", "Kraken Control by Frelidon": "Kraken Control by Frelidon",
        "Komponenten- und Laufzeitversionen": "Component and runtime versions", "Unterstützte Geräte und offizielle Herstellerseiten": "Supported devices and official manufacturer pages",
        "Verwendete Software – Website, Quellcode und Lizenz": "Software used – website, source code and license", "Entwicklung und KI-Unterstützung": "Development and AI assistance",
        "Lizenz von Kraken Control": "Kraken Control license", "Projektumfang – bewusst auf die Kraken begrenzt": "Project scope – intentionally limited to Kraken",
        "Log leeren": "Clear log", "Alles kopieren": "Copy all", "Log speichern": "Save log", "Sprache": "Language", "Sprache der Oberfläche": "Interface language",
        "Experimentalhinweise und LCD-Sicherheit": "Experimental notices and LCD safety", "Experimentalhinweise zurücksetzen": "Reset experimental notices",
        "Hinweise bestätigt": "Notices acknowledged", "Hinweise werden wieder angezeigt": "Notices will be shown again",
    },
    "es": {
        "Übersicht": "Resumen", "Kühlung": "Refrigeración", "Einstellungen": "Ajustes", "Profile": "Perfiles", "Über": "Acerca de",
        "&Datei": "&Archivo", "&Gerät": "&Dispositivo", "&Ansicht": "&Vista", "&Profile": "&Perfiles", "&Hilfe": "A&yuda",
        "&Beenden": "&Salir", "Geräte &aktualisieren": "&Actualizar dispositivos", "Bereit": "Listo", "Systemzustand": "Estado del sistema",
        "Gerät wird geprüft …": "Comprobando dispositivo …", "Geräte initialisieren": "Inicializar dispositivos", "Schnellprofile": "Perfiles rápidos",
        "Anwenden": "Aplicar", "Leise": "Silencioso", "Ausgeglichen": "Equilibrado", "Leistung": "Rendimiento", "Maximum": "Máximo",
        "Manuelle Steuerung": "Control manual", "Pumpe": "Bomba", "Radiatorlüfter": "Ventiladores del radiador", "&Pumpe anwenden": "Aplicar &bomba",
        "&Lüfter anwenden": "Aplicar &ventiladores", "Aktiver Kühlmodus": "Modo de refrigeración activo", "Pumpenkurve nach Wassertemperatur": "Curva de bomba por temperatura del líquido",
        "Lüfterkurve nach Wassertemperatur": "Curva de ventiladores por temperatura del líquido", "&Standardwerte": "Valores &predeterminados", "Kurve &anwenden": "&Aplicar curva",
        "AMD-AM5-Prozessorprofil und CPU-Temperatur-Assistenz": "Perfil de CPU AMD AM5 y asistencia por temperatura de CPU", "Bitte Prozessor auswählen": "Seleccionar procesador",
        "CPU &automatisch erkennen": "Detectar CPU &automáticamente", "Profil und empfohlene Kraken-Kurven &laden": "&Cargar perfil y curvas Kraken recomendadas", "Prozessor": "Procesador",
        "Kraken-Wassertemperatur – Sicherheitsgrenzen": "Temperatura del líquido Kraken – límites de seguridad", "Warnung ab": "Aviso desde", "Kritisch ab": "Crítico desde",
        "Bei kritischer Wassertemperatur automatisch 100 % setzen": "Establecer 100% automáticamente con temperatura crítica del líquido",
        "Sicheres Standardprofil anwenden · 65 % / 65 %": "Aplicar perfil seguro predeterminado · 65% / 65%", "Beleuchtung": "Iluminación", "Kanal": "Canal",
        "Effekt": "Efecto", "Geschwindigkeit": "Velocidad", "Richtung": "Dirección", "Farben": "Colores", "RGB anwenden": "Aplicar RGB", "Eigenes Bild": "Imagen personalizada",
        "PNG, JPG oder GIF auswählen": "Seleccionar PNG, JPG o GIF", "Kein Bild ausgewählt": "Ninguna imagen seleccionada", "Bild einmal übertragen": "Enviar imagen una vez",
        "Automatisch erneut senden (Fallback)": "Reenviar automáticamente (respaldo)", "Helligkeit": "Brillo", "Ausrichtung": "Orientación",
        "Helligkeit und Ausrichtung anwenden": "Aplicar brillo y orientación", "Zur Flüssigkeitstemperatur zurück": "Volver a temperatura del líquido", "Uhr auf dem LCD": "Reloj en LCD",
        "Zeitformat": "Formato de hora", "Datum unter der Uhrzeit anzeigen": "Mostrar fecha debajo de la hora", "Schriftgröße": "Tamaño de fuente",
        "Uhr automatisch erneut senden": "Reenviar reloj automáticamente", "Erneut senden alle": "Reenviar cada", "Vorschau": "Vista previa", "Uhr starten": "Iniciar reloj", "Uhr anhalten": "Detener reloj",
        "Automatisches Wiederherstellen": "Restauración automática", "Gewähltes Bild beim Programmstart wieder anzeigen": "Restaurar imagen seleccionada al iniciar la aplicación",
        "Design": "Diseño", "Darstellung": "Apariencia", "Systemmodus": "Modo del sistema", "Hell": "Claro", "Dunkel": "Oscuro", "Eigene Akzentfarbe": "Color de acento personalizado",
        "Farbe auswählen": "Elegir color", "Voreinstellungen": "Preajustes", "Design anwenden": "Aplicar diseño", "Anzeige und DPI": "Pantalla y DPI", "Monitor wird erkannt …": "Detectando monitor …",
        "Automatisch an Monitor und Seitenverhältnis anpassen": "Adaptar automáticamente al monitor y relación de aspecto", "App-Skalierung": "Escala de la aplicación", "Layoutvorgabe": "Preajuste de diseño",
        "Automatisch": "Automático", "Monitor neu erkennen": "Detectar monitor de nuevo", "Anzeige anwenden": "Aplicar pantalla", "Animierter Hintergrund": "Fondo animado",
        "Animation aktivieren": "Activar animación", "Pausieren, wenn die App nicht aktiv ist": "Pausar cuando la aplicación esté inactiva", "Hintergrund anwenden": "Aplicar fondo",
        "Animation ausschalten": "Desactivar animación", "Thema": "Tema", "Bildrate": "Fotogramas", "Intensität": "Intensidad", "Programm": "Programa",
        "Mit dem Desktop starten": "Iniciar con el escritorio", "Beim Schließen im Infobereich weiterlaufen": "Seguir ejecutándose en la bandeja al cerrar", "Status-Aktualisierung": "Actualización de estado",
        "Einrichtungsassistent erneut starten": "Ejecutar de nuevo el asistente", "Abhängigkeiten": "Dependencias", "Wird geprüft …": "Comprobando …", "Abhängigkeiten &prüfen": "&Comprobar dependencias",
        "Fehlende Pakete &installieren": "&Instalar paquetes faltantes", "Gerätezugriff": "Acceso al dispositivo", "Zugriff ohne sudo &testen": "&Probar acceso sin sudo",
        "Berechtigungen mit Administratorabfrage &reparieren": "&Reparar permisos con autorización de administrador", "Hinweis": "Aviso", "Profil beim Start": "Perfil al iniciar",
        "Automatisch laden": "Cargar automáticamente", "Kein automatisches Profil": "Sin perfil automático", "Zuletzt verwendetes Profil": "Último perfil usado",
        "Profil erstellen oder aktualisieren": "Crear o actualizar perfil", "Name": "Nombre", "Kategorie": "Categoría", "Beschreibung": "Descripción", "Als neues Profil speichern": "Guardar como perfil nuevo",
        "Ausgewähltes Profil aktualisieren": "Actualizar perfil seleccionado", "Profil anwenden": "Aplicar perfil", "Duplizieren": "Duplicar", "Umbenennen": "Renombrar", "Löschen": "Eliminar",
        "Importieren": "Importar", "Exportieren": "Exportar", "Noch kein Profil ausgewählt.": "Aún no hay perfil seleccionado.", "Log leeren": "Vaciar registro", "Alles kopieren": "Copiar todo", "Log speichern": "Guardar registro",
        "Sprache": "Idioma", "Sprache der Oberfläche": "Idioma de la interfaz", "Experimentalhinweise und LCD-Sicherheit": "Avisos experimentales y seguridad LCD",
        "Experimentalhinweise zurücksetzen": "Restablecer avisos experimentales", "Hinweise bestätigt": "Avisos confirmados", "Hinweise werden wieder angezeigt": "Los avisos se mostrarán de nuevo",
    },
    "fr": {
        "Übersicht": "Vue d’ensemble", "Kühlung": "Refroidissement", "Einstellungen": "Paramètres", "Profile": "Profils", "Über": "À propos",
        "&Datei": "&Fichier", "&Gerät": "&Appareil", "&Ansicht": "&Affichage", "&Profile": "&Profils", "&Hilfe": "&Aide",
        "&Beenden": "&Quitter", "Geräte &aktualisieren": "&Actualiser les appareils", "Bereit": "Prêt", "Systemzustand": "État du système",
        "Gerät wird geprüft …": "Vérification de l’appareil …", "Geräte initialisieren": "Initialiser les appareils", "Schnellprofile": "Profils rapides",
        "Anwenden": "Appliquer", "Leise": "Silencieux", "Ausgeglichen": "Équilibré", "Leistung": "Performance", "Maximum": "Maximum",
        "Manuelle Steuerung": "Contrôle manuel", "Pumpe": "Pompe", "Radiatorlüfter": "Ventilateurs du radiateur", "&Pumpe anwenden": "Appliquer la &pompe",
        "&Lüfter anwenden": "Appliquer les &ventilateurs", "Aktiver Kühlmodus": "Mode de refroidissement actif", "Pumpenkurve nach Wassertemperatur": "Courbe de pompe selon la température du liquide",
        "Lüfterkurve nach Wassertemperatur": "Courbe des ventilateurs selon la température du liquide", "&Standardwerte": "Valeurs par &défaut", "Kurve &anwenden": "&Appliquer la courbe",
        "AMD-AM5-Prozessorprofil und CPU-Temperatur-Assistenz": "Profil CPU AMD AM5 et assistance selon la température CPU", "Bitte Prozessor auswählen": "Sélectionner le processeur",
        "CPU &automatisch erkennen": "Détecter le CPU &automatiquement", "Profil und empfohlene Kraken-Kurven &laden": "&Charger le profil et les courbes Kraken recommandées", "Prozessor": "Processeur",
        "Kraken-Wassertemperatur – Sicherheitsgrenzen": "Température du liquide Kraken – limites de sécurité", "Warnung ab": "Alerte à", "Kritisch ab": "Critique à",
        "Bei kritischer Wassertemperatur automatisch 100 % setzen": "Passer automatiquement à 100 % à température critique du liquide",
        "Sicheres Standardprofil anwenden · 65 % / 65 %": "Appliquer le profil sûr par défaut · 65 % / 65 %", "Beleuchtung": "Éclairage", "Kanal": "Canal",
        "Effekt": "Effet", "Geschwindigkeit": "Vitesse", "Richtung": "Direction", "Farben": "Couleurs", "RGB anwenden": "Appliquer RGB", "Eigenes Bild": "Image personnalisée",
        "PNG, JPG oder GIF auswählen": "Sélectionner PNG, JPG ou GIF", "Kein Bild ausgewählt": "Aucune image sélectionnée", "Bild einmal übertragen": "Envoyer l’image une fois",
        "Automatisch erneut senden (Fallback)": "Renvoyer automatiquement (secours)", "Helligkeit": "Luminosité", "Ausrichtung": "Orientation",
        "Helligkeit und Ausrichtung anwenden": "Appliquer luminosité et orientation", "Zur Flüssigkeitstemperatur zurück": "Revenir à la température du liquide", "Uhr auf dem LCD": "Horloge sur l’écran LCD",
        "Zeitformat": "Format de l’heure", "Datum unter der Uhrzeit anzeigen": "Afficher la date sous l’heure", "Schriftgröße": "Taille de police",
        "Uhr automatisch erneut senden": "Renvoyer automatiquement l’horloge", "Erneut senden alle": "Renvoyer toutes les", "Vorschau": "Aperçu", "Uhr starten": "Démarrer l’horloge", "Uhr anhalten": "Arrêter l’horloge",
        "Automatisches Wiederherstellen": "Restauration automatique", "Gewähltes Bild beim Programmstart wieder anzeigen": "Restaurer l’image sélectionnée au démarrage",
        "Design": "Design", "Darstellung": "Apparence", "Systemmodus": "Mode système", "Hell": "Clair", "Dunkel": "Sombre", "Eigene Akzentfarbe": "Couleur d’accent personnalisée",
        "Farbe auswählen": "Choisir la couleur", "Voreinstellungen": "Préréglages", "Design anwenden": "Appliquer le design", "Anzeige und DPI": "Affichage et DPI", "Monitor wird erkannt …": "Détection de l’écran …",
        "Automatisch an Monitor und Seitenverhältnis anpassen": "Adapter automatiquement à l’écran et au format", "App-Skalierung": "Mise à l’échelle de l’application", "Layoutvorgabe": "Préréglage de mise en page",
        "Automatisch": "Automatique", "Monitor neu erkennen": "Redétecter l’écran", "Anzeige anwenden": "Appliquer l’affichage", "Animierter Hintergrund": "Arrière-plan animé",
        "Animation aktivieren": "Activer l’animation", "Pausieren, wenn die App nicht aktiv ist": "Mettre en pause lorsque l’application est inactive", "Hintergrund anwenden": "Appliquer l’arrière-plan",
        "Animation ausschalten": "Désactiver l’animation", "Thema": "Thème", "Bildrate": "Fréquence d’images", "Intensität": "Intensité", "Programm": "Programme",
        "Mit dem Desktop starten": "Démarrer avec le bureau", "Beim Schließen im Infobereich weiterlaufen": "Continuer dans la zone de notification à la fermeture", "Status-Aktualisierung": "Actualisation de l’état",
        "Einrichtungsassistent erneut starten": "Relancer l’assistant de configuration", "Abhängigkeiten": "Dépendances", "Wird geprüft …": "Vérification …", "Abhängigkeiten &prüfen": "&Vérifier les dépendances",
        "Fehlende Pakete &installieren": "&Installer les paquets manquants", "Gerätezugriff": "Accès à l’appareil", "Zugriff ohne sudo &testen": "&Tester l’accès sans sudo",
        "Berechtigungen mit Administratorabfrage &reparieren": "&Réparer les permissions avec autorisation administrateur", "Hinweis": "Remarque", "Profil beim Start": "Profil au démarrage",
        "Automatisch laden": "Charger automatiquement", "Kein automatisches Profil": "Aucun profil automatique", "Zuletzt verwendetes Profil": "Dernier profil utilisé",
        "Profil erstellen oder aktualisieren": "Créer ou mettre à jour un profil", "Name": "Nom", "Kategorie": "Catégorie", "Beschreibung": "Description", "Als neues Profil speichern": "Enregistrer comme nouveau profil",
        "Ausgewähltes Profil aktualisieren": "Mettre à jour le profil sélectionné", "Profil anwenden": "Appliquer le profil", "Duplizieren": "Dupliquer", "Umbenennen": "Renommer", "Löschen": "Supprimer",
        "Importieren": "Importer", "Exportieren": "Exporter", "Noch kein Profil ausgewählt.": "Aucun profil sélectionné.", "Log leeren": "Effacer le journal", "Alles kopieren": "Tout copier", "Log speichern": "Enregistrer le journal",
        "Sprache": "Langue", "Sprache der Oberfläche": "Langue de l’interface", "Experimentalhinweise und LCD-Sicherheit": "Avertissements expérimentaux et sécurité LCD",
        "Experimentalhinweise zurücksetzen": "Réinitialiser les avertissements expérimentaux", "Hinweise bestätigt": "Avertissements confirmés", "Hinweise werden wieder angezeigt": "Les avertissements seront de nouveau affichés",
    },
}

UI_TRANSLATIONS["en"].update({
    "Unabhängige Open-Source-Steuerung · NZXT Kraken 2023 · liquidctl": "Independent open-source control · NZXT Kraken 2023 · liquidctl",
    "● Suche Geräte …": "● Searching for devices …", "↻ &Aktualisieren": "↻ &Refresh",
    "Kraken-Wassertemperatur": "Kraken liquid temperature", "CPU-Temperatur": "CPU temperature", "Firmware": "Firmware",
    "Sensor in der Pumpeneinheit": "Sensor in pump unit", "Wasser °C": "Liquid °C", "Leistung %": "Power %", "Typ": "Type",
    "24 Stunden · 13:30": "24 hour · 13:30", "12 Stunden · 1:30 PM": "12 hour · 1:30 PM",
    "Runde LCD-Vorschau · 240 × 240": "Round LCD preview · 240 × 240", "LCD-Modus: bereit": "LCD mode: ready",
})
UI_TRANSLATIONS["es"].update({
    "Unabhängige Open-Source-Steuerung · NZXT Kraken 2023 · liquidctl": "Control independiente de código abierto · NZXT Kraken 2023 · liquidctl",
    "● Suche Geräte …": "● Buscando dispositivos …", "↻ &Aktualisieren": "↻ &Actualizar",
    "Kraken-Wassertemperatur": "Temperatura del líquido Kraken", "CPU-Temperatur": "Temperatura de CPU", "Firmware": "Firmware",
    "Sensor in der Pumpeneinheit": "Sensor en la unidad de bomba", "Wasser °C": "Líquido °C", "Leistung %": "Potencia %", "Typ": "Tipo",
    "24 Stunden · 13:30": "24 horas · 13:30", "12 Stunden · 1:30 PM": "12 horas · 1:30 PM",
    "Runde LCD-Vorschau · 240 × 240": "Vista previa LCD circular · 240 × 240", "LCD-Modus: bereit": "Modo LCD: listo",
})
UI_TRANSLATIONS["fr"].update({
    "Unabhängige Open-Source-Steuerung · NZXT Kraken 2023 · liquidctl": "Contrôle open source indépendant · NZXT Kraken 2023 · liquidctl",
    "● Suche Geräte …": "● Recherche des appareils …", "↻ &Aktualisieren": "↻ &Actualiser",
    "Kraken-Wassertemperatur": "Température du liquide Kraken", "CPU-Temperatur": "Température CPU", "Firmware": "Firmware",
    "Sensor in der Pumpeneinheit": "Capteur dans l’unité de pompe", "Wasser °C": "Liquide °C", "Leistung %": "Puissance %", "Typ": "Type",
    "24 Stunden · 13:30": "24 heures · 13:30", "12 Stunden · 1:30 PM": "12 heures · 1:30 PM",
    "Runde LCD-Vorschau · 240 × 240": "Aperçu LCD circulaire · 240 × 240", "LCD-Modus: bereit": "Mode LCD : prêt",
})


# 2.9.20: simplified CAM-near GIF controls with diagnostics kept under Advanced.
UI_TRANSLATIONS["en"].update({
    "Beim Systemstart minimiert/im Tray starten": "Start minimized/in the system tray at system login",
    "GIF-Animation · Firmware 2.x · Experimentell": "GIF animation · Firmware 2.x · Experimental",
    "GIF-Bildrate": "GIF frame rate",
    "CAM-nah · automatisch · empfohlen · max. 25 FPS": "CAM-near · automatic · recommended · max. 25 FPS",
    "Erweiterte GIF-Optionen anzeigen": "Show advanced GIF options",
    "Bewegungsglättung (Motion-Interpolation)": "Motion smoothing (motion interpolation)",
    "GIF-Animation starten · Experimentell": "Start GIF animation · Experimental",
    "Animation stoppen": "Stop animation",
    "GIF-Stream: bereit": "GIF stream: ready",
})
UI_TRANSLATIONS["es"].update({
    "Beim Systemstart minimiert/im Tray starten": "Iniciar minimizado/en la bandeja al iniciar el sistema",
    "GIF-Animation · Firmware 2.x · Experimentell": "Animación GIF · Firmware 2.x · Experimental",
    "GIF-Bildrate": "Frecuencia del GIF",
    "CAM-nah · automatisch · empfohlen · max. 25 FPS": "Similar a CAM · automático · recomendado · máx. 25 FPS",
    "Erweiterte GIF-Optionen anzeigen": "Mostrar opciones GIF avanzadas",
    "Bewegungsglättung (Motion-Interpolation)": "Suavizado de movimiento (interpolación de movimiento)",
    "GIF-Animation starten · Experimentell": "Iniciar animación GIF · Experimental",
    "Animation stoppen": "Detener animación",
    "GIF-Stream: bereit": "Flujo GIF: listo",
})
UI_TRANSLATIONS["fr"].update({
    "Beim Systemstart minimiert/im Tray starten": "Démarrer minimisé/dans la zone de notification au démarrage du système",
    "GIF-Animation · Firmware 2.x · Experimentell": "Animation GIF · Firmware 2.x · Expérimental",
    "GIF-Bildrate": "Fréquence du GIF",
    "CAM-nah · automatisch · empfohlen · max. 25 FPS": "Proche de CAM · automatique · recommandé · max. 25 FPS",
    "Erweiterte GIF-Optionen anzeigen": "Afficher les options GIF avancées",
    "Bewegungsglättung (Motion-Interpolation)": "Lissage du mouvement (interpolation de mouvement)",
    "GIF-Animation starten · Experimentell": "Démarrer l’animation GIF · Expérimental",
    "Animation stoppen": "Arrêter l’animation",
    "GIF-Stream: bereit": "Flux GIF : prêt",
})

# 2.9.20: CAM/raw transport-mode labels.
UI_TRANSLATIONS["en"].update({
    'LCD-Transport': 'LCD transport',
    '25,6 Hz · Sicher · bewährt': '25.6 Hz · Safe · proven',
    'CAM-Takt · 26,667 Hz · phasenstabil · Standard': 'CAM cadence · 26.667 Hz · phase-stable · Standard',
})
UI_TRANSLATIONS["es"].update({
    'LCD-Transport': 'Transporte LCD',
    '25,6 Hz · Sicher · bewährt': '25,6 Hz · Seguro · probado',
    'CAM-Takt · 26,667 Hz · phasenstabil · Standard': 'Ritmo CAM · 26,667 Hz · fase estable · Estándar',
})
UI_TRANSLATIONS["fr"].update({
    'LCD-Transport': 'Transport LCD',
    '25,6 Hz · Sicher · bewährt': '25,6 Hz · Sûr · éprouvé',
    'CAM-Takt · 26,667 Hz · phasenstabil · Standard': 'Cadence CAM · 26,667 Hz · phase stable · Standard',
})

# 2.9.21: complete menu/control switching and rounded live hardware dashboards.
UI_TRANSLATIONS["en"].update({
    "Sicher": "Safe", "Beenden": "Quit", "Displayeinstellungen": "Display settings", "Schnellfarben": "Quick colors",
    "Kraken-Wassertemperatur": "Kraken liquid temperature", "CPU-Temperatur": "CPU temperature", "GPU-Temperatur": "GPU temperature",
    "Sensor in der Pumpeneinheit": "Sensor in pump unit", "AMD amdgpu · dedizierte GPU bevorzugt": "AMD amdgpu · dedicated GPU preferred",
    "Runde LCD-Vorschau · 240 × 240": "Round LCD preview · 240 × 240", "Vorschau nicht verfügbar": "Preview unavailable",
    "Hardwaredaten-Designs · Live": "Hardware data designs · Live", "Layout": "Layout", "Farbvoreinstellung": "Color preset",
    "Hex-Farbwert": "Hex color value", "Aktualisierung": "Refresh", "Designvorschau": "Design preview",
    "Live-Design starten": "Start live design", "Live-Design anhalten": "Stop live design", "Eigener Farbwert": "Custom color value",
    "Wasser · Halo": "Liquid · Halo", "CPU · Orbit": "CPU · Orbit", "GPU · Arc": "GPU · Arc",
    "CPU + GPU · Dual": "CPU + GPU · Dual", "Wasser + CPU + GPU · Trio": "Liquid + CPU + GPU · Trio",
    "Eisblau": "Ice blue", "Neongrün": "Neon green", "Weiß": "White", "Rot": "Red", "Gold": "Gold", "Grün": "Green", "Lila": "Purple", "Orange": "Orange", "Blau": "Blue",
    "Live-Hardwaredesign: bereit · Eisblau ist die Standardfarbe.": "Live hardware design: ready · Ice blue is the default color.",
    "Live-Hardwaredesign": "Live hardware design", "Live-Hardwaredesign aktiv": "Live hardware design active",
    "Live-Hardwaredesign angehalten": "Live hardware design stopped", "Live aktiv": "Live active", "Aktualisierung alle": "Refresh every", "Sekunden": "seconds",
    "Designvorschau aktualisiert · noch nicht auf das LCD übertragen.": "Design preview updated · not uploaded to the LCD yet.",
    "Die Designvorschau konnte nicht erzeugt werden:": "The design preview could not be created:",
    "LCD-Akzentfarbe auswählen": "Choose LCD accent color", "Experimentelles Live-Hardwaredesign": "Experimental live hardware design",
    "Bitte einen gültigen Hex-Farbwert im Format #RRGGBB eingeben.": "Enter a valid hex color in #RRGGBB format.",
    "Die Kraken ist noch nicht verbunden.": "The Kraken is not connected yet.",
    "Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.": "LCD safety mode is still waiting to restore the liquid-temperature screen.",
    "Text": "Text", "Hintergrund": "Background", "Farbe 1": "Color 1", "Farbe 2": "Color 2",
    "Gesamt": "All", "Statisch": "Static", "Aus": "Off", "Überblenden": "Fading", "Pulsieren": "Pulse", "Atmen": "Breathing",
    "Kerze": "Candle", "Sternennacht": "Starry night", "Spektrum-Welle": "Spectrum wave", "Regenbogenfluss": "Rainbow flow",
    "Super-Regenbogen": "Super rainbow", "Regenbogen-Puls": "Rainbow pulse", "Abwechselnd": "Alternating", "Bewegend abwechselnd": "Moving alternating", "Flügel": "Wings",
    "Am langsamsten": "Slowest", "Langsamer": "Slower", "Normal": "Normal", "Schneller": "Faster", "Am schnellsten": "Fastest", "Vorwärts": "Forward", "Rückwärts": "Backward",
    "24 FPS Inhalt": "24 FPS content", "25 FPS Inhalt · empfohlen": "25 FPS content · recommended", "Status aktuell": "Status current",
})
UI_TRANSLATIONS["es"].update({
    "&Sicheres Profil anwenden": "Aplicar perfil &seguro", "&Berechtigungen reparieren": "&Reparar permisos", "Profile verwalten": "Gestionar perfiles",
    "&Tastaturbedienung": "&Control por teclado", "Zum Bereich &Über": "Abrir &Acerca de", "Sicher": "Seguro", "Beenden": "Salir",
    "Displayeinstellungen": "Ajustes de pantalla", "Schnellfarben": "Colores rápidos", "Kraken-Wassertemperatur": "Temperatura del líquido Kraken",
    "CPU-Temperatur": "Temperatura de CPU", "GPU-Temperatur": "Temperatura de GPU", "Sensor in der Pumpeneinheit": "Sensor en la unidad de bomba",
    "AMD amdgpu · dedizierte GPU bevorzugt": "AMD amdgpu · GPU dedicada preferida", "Runde LCD-Vorschau · 240 × 240": "Vista previa LCD redonda · 240 × 240",
    "Vorschau nicht verfügbar": "Vista previa no disponible", "Hardwaredaten-Designs · Live": "Diseños de datos de hardware · En vivo", "Layout": "Diseño",
    "Farbvoreinstellung": "Color predefinido", "Hex-Farbwert": "Valor de color hexadecimal", "Aktualisierung": "Actualización", "Designvorschau": "Vista previa del diseño",
    "Live-Design starten": "Iniciar diseño en vivo", "Live-Design anhalten": "Detener diseño en vivo", "Eigener Farbwert": "Color personalizado",
    "Wasser · Halo": "Líquido · Halo", "CPU · Orbit": "CPU · Órbita", "GPU · Arc": "GPU · Arco", "CPU + GPU · Dual": "CPU + GPU · Dual",
    "Wasser + CPU + GPU · Trio": "Líquido + CPU + GPU · Trío", "Eisblau": "Azul hielo", "Neongrün": "Verde neón", "Weiß": "Blanco", "Rot": "Rojo", "Gold": "Dorado", "Grün": "Verde", "Lila": "Morado", "Orange": "Naranja", "Blau": "Azul",
    "Live-Hardwaredesign: bereit · Eisblau ist die Standardfarbe.": "Diseño de hardware en vivo: listo · Azul hielo es el color predeterminado.",
    "Live-Hardwaredesign": "Diseño de hardware en vivo", "Live-Hardwaredesign aktiv": "Diseño de hardware en vivo activo", "Live-Hardwaredesign angehalten": "Diseño de hardware en vivo detenido",
    "Live aktiv": "En vivo activo", "Aktualisierung alle": "Actualizar cada", "Sekunden": "segundos", "Designvorschau aktualisiert · noch nicht auf das LCD übertragen.": "Vista previa actualizada · aún no enviada al LCD.",
    "Die Designvorschau konnte nicht erzeugt werden:": "No se pudo crear la vista previa del diseño:", "LCD-Akzentfarbe auswählen": "Elegir color de acento del LCD",
    "Experimentelles Live-Hardwaredesign": "Diseño de hardware en vivo experimental", "Bitte einen gültigen Hex-Farbwert im Format #RRGGBB eingeben.": "Introduce un color hexadecimal válido en formato #RRGGBB.",
    "Die Kraken ist noch nicht verbunden.": "La Kraken aún no está conectada.", "Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.": "El modo de seguridad LCD aún espera restaurar la pantalla de temperatura del líquido.",
    "Text": "Texto", "Hintergrund": "Fondo", "Farbe 1": "Color 1", "Farbe 2": "Color 2", "Gesamt": "Todo", "Statisch": "Estático", "Aus": "Apagado",
    "Überblenden": "Fundido", "Pulsieren": "Pulso", "Atmen": "Respiración", "Kerze": "Vela", "Sternennacht": "Noche estrellada", "Spektrum-Welle": "Onda de espectro",
    "Regenbogenfluss": "Flujo arcoíris", "Super-Regenbogen": "Súper arcoíris", "Regenbogen-Puls": "Pulso arcoíris", "Abwechselnd": "Alternado", "Bewegend abwechselnd": "Alternado móvil", "Flügel": "Alas",
    "Am langsamsten": "Más lento", "Langsamer": "Lento", "Normal": "Normal", "Schneller": "Rápido", "Am schnellsten": "Más rápido", "Vorwärts": "Adelante", "Rückwärts": "Atrás",
    "24 FPS Inhalt": "Contenido a 24 FPS", "25 FPS Inhalt · empfohlen": "Contenido a 25 FPS · recomendado", "Status aktuell": "Estado actualizado",
})
UI_TRANSLATIONS["fr"].update({
    "&Sicheres Profil anwenden": "Appliquer le profil &sûr", "&Berechtigungen reparieren": "&Réparer les autorisations", "Profile verwalten": "Gérer les profils",
    "&Tastaturbedienung": "&Commandes au clavier", "Zum Bereich &Über": "Ouvrir À &propos", "Sicher": "Sûr", "Beenden": "Quitter",
    "Displayeinstellungen": "Paramètres d’affichage", "Schnellfarben": "Couleurs rapides", "Kraken-Wassertemperatur": "Température du liquide Kraken",
    "CPU-Temperatur": "Température CPU", "GPU-Temperatur": "Température GPU", "Sensor in der Pumpeneinheit": "Capteur dans l’unité de pompe",
    "AMD amdgpu · dedizierte GPU bevorzugt": "AMD amdgpu · GPU dédiée privilégiée", "Runde LCD-Vorschau · 240 × 240": "Aperçu LCD rond · 240 × 240",
    "Vorschau nicht verfügbar": "Aperçu indisponible", "Hardwaredaten-Designs · Live": "Designs de données matérielles · En direct", "Layout": "Disposition",
    "Farbvoreinstellung": "Préréglage couleur", "Hex-Farbwert": "Valeur couleur hexadécimale", "Aktualisierung": "Actualisation", "Designvorschau": "Aperçu du design",
    "Live-Design starten": "Démarrer le design en direct", "Live-Design anhalten": "Arrêter le design en direct", "Eigener Farbwert": "Couleur personnalisée",
    "Wasser · Halo": "Liquide · Halo", "CPU · Orbit": "CPU · Orbite", "GPU · Arc": "GPU · Arc", "CPU + GPU · Dual": "CPU + GPU · Double",
    "Wasser + CPU + GPU · Trio": "Liquide + CPU + GPU · Trio", "Eisblau": "Bleu glacier", "Neongrün": "Vert néon", "Weiß": "Blanc", "Rot": "Rouge", "Gold": "Or", "Grün": "Vert", "Lila": "Violet", "Orange": "Orange", "Blau": "Bleu",
    "Live-Hardwaredesign: bereit · Eisblau ist die Standardfarbe.": "Design matériel en direct : prêt · Le bleu glacier est la couleur par défaut.",
    "Live-Hardwaredesign": "Design matériel en direct", "Live-Hardwaredesign aktiv": "Design matériel en direct actif", "Live-Hardwaredesign angehalten": "Design matériel en direct arrêté",
    "Live aktiv": "Direct actif", "Aktualisierung alle": "Actualisation toutes les", "Sekunden": "secondes", "Designvorschau aktualisiert · noch nicht auf das LCD übertragen.": "Aperçu actualisé · pas encore envoyé au LCD.",
    "Die Designvorschau konnte nicht erzeugt werden:": "Impossible de créer l’aperçu du design :", "LCD-Akzentfarbe auswählen": "Choisir la couleur d’accent du LCD",
    "Experimentelles Live-Hardwaredesign": "Design matériel en direct expérimental", "Bitte einen gültigen Hex-Farbwert im Format #RRGGBB eingeben.": "Saisissez une couleur hexadécimale valide au format #RRGGBB.",
    "Die Kraken ist noch nicht verbunden.": "Le Kraken n’est pas encore connecté.", "Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.": "Le mode de sécurité LCD attend encore la restauration de l’écran de température du liquide.",
    "Text": "Texte", "Hintergrund": "Arrière-plan", "Farbe 1": "Couleur 1", "Farbe 2": "Couleur 2", "Gesamt": "Tout", "Statisch": "Fixe", "Aus": "Désactivé",
    "Überblenden": "Fondu", "Pulsieren": "Pulsation", "Atmen": "Respiration", "Kerze": "Bougie", "Sternennacht": "Nuit étoilée", "Spektrum-Welle": "Onde spectrale",
    "Regenbogenfluss": "Flux arc-en-ciel", "Super-Regenbogen": "Super arc-en-ciel", "Regenbogen-Puls": "Pulsation arc-en-ciel", "Abwechselnd": "Alterné", "Bewegend abwechselnd": "Alterné mobile", "Flügel": "Ailes",
    "Am langsamsten": "Très lent", "Langsamer": "Lent", "Normal": "Normal", "Schneller": "Rapide", "Am schnellsten": "Très rapide", "Vorwärts": "Avant", "Rückwärts": "Arrière",
    "24 FPS Inhalt": "Contenu 24 FPS", "25 FPS Inhalt · empfohlen": "Contenu 25 FPS · recommandé", "Status aktuell": "État à jour",
})

UI_TRANSLATIONS["en"].update({
    "Zuletzt durch Kraken Control gesetzt: Pumpe unbekannt · Radiatorlüfter unbekannt": "Last set by Kraken Control: pump unknown · radiator fans unknown",
    "Ein fester Prozentwert oder ein Schnellprofil ersetzt die jeweilige Kurve in der Kraken-Firmware.": "A fixed percentage or quick profile replaces the respective curve in the Kraken firmware.",
    "Bei hoher CPU-Temperatur Kraken automatisch verstärken (mit 5 °C Hysterese)": "Automatically boost Kraken at high CPU temperature (with 5 °C hysteresis)",
    "Die CPU-Tjmax ist nicht die Wassertemperatur. Für die Kraken-Flüssigkeit gelten die separaten Grenzen unten.": "CPU Tjmax is not the liquid temperature. The separate limits below apply to Kraken liquid.",
    "CPU-Sensor: wird gesucht …": "CPU sensor: searching …", "Expertenmodus: Sicherheitsgrenzen frei einstellen": "Expert mode: freely adjust safety limits",
    "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. Eine CPU-Tjmax von 89 oder 95 °C darf niemals als Wassergrenze übernommen werden. Im normalen Modus bleiben vorsichtige Einstellbereiche aktiv.": "These values apply only to Kraken liquid, not the CPU. A CPU Tjmax of 89 or 95 °C must never be used as a liquid limit. Conservative ranges remain active in normal mode.",
    "Die drei F140/F120-RGB-Core-Lüfter werden über den separaten NZXT 2023 RGB Controller gesteuert.": "The three F140/F120 RGB Core fans are controlled through the separate NZXT 2023 RGB Controller.",
    "Die Hardware nimmt ein quadratisches 240×240-Bild an. Die Vorschau zeigt den tatsächlich sichtbaren runden Bereich.": "The hardware accepts a square 240×240 image. The preview shows the round area that is actually visible.",
    "Sicherheitshinweis: Der Fallback sendet das Bild wiederholt an die Kraken. Langzeitwirkungen auf den Displayspeicher sind nicht ausreichend bekannt. Nur aktivieren, wenn das Display wirklich zurückspringt; standardmäßig bleibt diese Funktion ausgeschaltet.": "Safety notice: fallback repeatedly sends the image to the Kraken. Long-term effects on display memory are not sufficiently known. Enable only if the display actually reverts; this feature is off by default.",
    "Einmalige GIF-Übertragung verwendet weiterhin nur das erste Bild. Der experimentelle Stream darunter emuliert Animation auf Firmware 2.x durch vorbereitete statische Frames über den liquidctl-Treiber.": "A one-time GIF upload still uses only the first frame. The experimental stream below emulates animation on firmware 2.x using prepared static frames through the liquidctl driver.",
    "Experimentell: Das Live-Design rendert Wasser-, CPU- und GPU-Sensordaten als statisches 240×240-Bild und überträgt es im gewählten Intervall. Die Mindestzeit beträgt 5 Sekunden; Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt.": "Experimental: the live design renders liquid, CPU and GPU sensor data as a static 240×240 image and uploads it at the selected interval. The minimum is 5 seconds; long-term effects of frequent LCD uploads are not sufficiently known.",
    "Experimentell: Die Uhr überträgt einmal pro Minute ein neues statisches Bild. Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt; Sekunden werden bewusst nicht übertragen.": "Experimental: the clock uploads a new static image once per minute. Long-term effects of frequent LCD uploads are not sufficiently known; seconds are intentionally omitted.",
    "Akzentvorschau · Schaltflächen, Tabs, Regler und Kurven": "Accent preview · buttons, tabs, sliders and curves",
    "Die App ändert nicht die Linux-Bildschirmauflösung. Qt arbeitet mit geräteunabhängigen Pixeln; hier werden App-Skalierung und responsives Layout angepasst.": "The app does not change the Linux screen resolution. Qt uses device-independent pixels; app scaling and the responsive layout are adjusted here.",
    "Bestätigte LCD-Hinweise werden dauerhaft gespeichert. Nach einem verdächtigen Absturz oder wiederholten LCD-Fehlern stoppt Kraken Control experimentelle LCD-Funktionen und versucht automatisch die Standardanzeige der Flüssigkeitstemperatur wiederherzustellen.": "Acknowledged LCD notices are stored permanently. After a suspicious crash or repeated LCD errors, Kraken Control stops experimental LCD features and automatically attempts to restore the default liquid-temperature screen.",
    "Open Hardware Control erkennt DNF, APT, Pacman und Zypper und installiert nach Bestätigung nur die fest zugeordneten Pakete aus bereits eingerichteten Quellen. Es werden keine fremden Paketquellen hinzugefügt.": "Open Hardware Control detects DNF, APT, Pacman and Zypper and, after confirmation, installs only fixed packages from already configured repositories. No third-party repositories are added.",
    "Schreibzugriff auf /dev/hidraw ist für Pumpen-, Lüfter- und Kurvenänderungen erforderlich. Nach einer neuen udev-Regel kann Ab- und Anstecken oder ein Neustart nötig sein.": "Write access to /dev/hidraw is required for pump, fan and curve changes. Reconnecting the device or restarting may be required after a new udev rule.",
    "Experimentelle Open-Source-Beta: Nutzung auf eigenes Risiko. Die Anwendung nutzt ausschließlich liquidctl. Die automatische Temperatursicherung wirkt nur, solange Programm, USB-Verbindung und Statusabfrage funktionieren. Wiederholte LCD-Uploads sind standardmäßig deaktiviert.": "Experimental open-source beta: use at your own risk. The application uses liquidctl exclusively. Automatic temperature protection works only while the program, USB connection and status polling are functioning. Repeated LCD uploads are disabled by default.",
    "Profile speichern Einstellungen kategorisiert. Gesamtprofile können Kühlung, LCD, RGB, Design, Hintergrund und Anzeige gemeinsam wiederherstellen.": "Profiles store settings by category. Full profiles can restore cooling, LCD, RGB, design, background and display together.",
    "Kühlungsprofile werden erst nach erfolgreicher Kraken-Erkennung übertragen.": "Cooling profiles are uploaded only after successful Kraken detection.",
    "z. B. Gaming, Leise Nacht oder Sommer": "e.g. Gaming, Quiet night or Summer", "Kurze Beschreibung": "Short description",
    "Öffentliches Projekt-Repository und Downloads: https://github.com/Frelidon/kraken-control-linux": "Public project repository and downloads: https://github.com/Frelidon/kraken-control-linux",
    "<b>Enthalten:</b> Wassertemperatur, Kraken-Pumpe, von der Kraken gemeldete beziehungsweise gesteuerte Radiatorlüfter, LCD sowie der separate NZXT 2023 RGB Controller.": "<b>Included:</b> liquid temperature, Kraken pump, radiator fans reported or controlled by the Kraken, LCD, and the separate NZXT 2023 RGB Controller.",
    "<b>Nicht enthalten:</b> Mainboard-Lüfteranschlüsse, zusätzliche Gehäuselüfter, GPU-Lüfter, AMD-Grafiksteuerung sowie allgemeines System-Tuning. Solche Funktionen sollen in eigenständigen Werkzeugen entstehen und können später über eine gemeinsame Oberfläche verbunden werden.": "<b>Not included:</b> motherboard fan headers, additional case fans, GPU fans, AMD graphics controls, or general system tuning. Such features should be developed as separate tools and can later be connected through a shared interface.",
    "Projektleitung und Veröffentlichung: Frelidon. Mit Unterstützung von ChatGPT (GPT-5.6 Thinking) von OpenAI bei Programmierung, Dokumentation und Tests. ChatGPT ist kein Laufzeitbestandteil der App. Die Nennung stellt keine offizielle Unterstützung oder Partnerschaft durch OpenAI dar.": "Project lead and publication: Frelidon. With support from OpenAI's ChatGPT (GPT-5.6 Thinking) for programming, documentation and testing. ChatGPT is not a runtime component of the app. This mention does not imply official OpenAI support or partnership.",
    "AMD-AM5-Temperaturprofile": "AMD AM5 temperature profiles",
    "Die auswählbaren CPU-Profile nutzen die von AMD veröffentlichte maximale Betriebstemperatur (Tjmax). Ryzen 9000, Ryzen 8000G und normale Ryzen-7000-Modelle sind in den aufgenommenen Profilen mit 95 °C hinterlegt; Ryzen 7000 X3D mit 89 °C. Die Kraken-Wassergrenzen bleiben davon unabhängig.": "The selectable CPU profiles use AMD's published maximum operating temperature (Tjmax). Ryzen 9000, Ryzen 8000G and regular Ryzen 7000 models use 95 °C in the included profiles; Ryzen 7000 X3D uses 89 °C. Kraken liquid limits remain independent.",
    "Kraken Control by Frelidon steht unter GNU General Public License v3.0 oder später (GPL-3.0-or-later). Die vollständige Lizenz liegt dem Paket als LICENSE bei.": "Kraken Control by Frelidon is licensed under GNU General Public License v3.0 or later (GPL-3.0-or-later). The full license is included as LICENSE.",
    "liquidctl-Gerätename: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · Temperatur, Pumpe, Radiatorlüfter und LCD": "liquidctl device name: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · temperature, pump, radiator fans and LCD",
    "USB 1e71:2012 · separate RGB-Steuerung über liquidctl. Der Controller wird auf der offiziellen Kraken-(2023)-Seite als Bestandteil der RGB-Varianten aufgeführt.": "USB 1e71:2012 · separate RGB control through liquidctl. The controller is listed on the official Kraken (2023) page as part of the RGB variants.",
    "Unterstützt werden nur Lüfter, die als Teil der Kraken-Kühlung über das Kraken-Gerät gemeldet und gesteuert werden. Andere im PC eingebaute Lüfter werden von Kraken Control nicht angesprochen.": "Only fans reported and controlled through the Kraken device as part of Kraken cooling are supported. Kraken Control does not access other fans installed in the PC.",
    "Alle Links öffnen sich im Standardbrowser. Das bloße Anzeigen dieser Seite überträgt keine Daten; erst das Anklicken eines Links öffnet die jeweilige externe Internetseite.": "All links open in the default browser. Merely viewing this page sends no data; an external website opens only after clicking a link.",
    "Dieses Protokoll erfasst Hardwarebefehle, Fehler, Schaltflächenklicks, Tastaturaktionen und vom Benutzer geänderte Einstellungen. Private Pfade und Kennungen werden weiterhin bereinigt.": "This log records hardware commands, errors, button clicks, keyboard actions and user-changed settings. Private paths and identifiers continue to be redacted.",
    "Das Live-Design überträgt im gewählten Intervall ein neues statisches Bild mit aktuellen Sensordaten. Die langfristige Wirkung häufiger Uploads auf den Displayspeicher ist nicht ausreichend bekannt. Live-Design trotzdem starten?": "The live design uploads a new static image with current sensor data at the selected interval. The long-term effect of frequent uploads on display memory is not sufficiently known. Start the live design anyway?",
})
UI_TRANSLATIONS["es"].update({
    "Kompakt · 16:10": "Compacto · 16:10", "Standard · 16:9": "Estándar · 16:9", "Ultrawide · 21:9": "Ultraancho · 21:9", "Super-Ultrawide · 32:9": "Súper ultraancho · 32:9",
    "Zuletzt durch Kraken Control gesetzt: Pumpe unbekannt · Radiatorlüfter unbekannt": "Último ajuste de Kraken Control: bomba desconocida · ventiladores desconocidos",
    "Ein fester Prozentwert oder ein Schnellprofil ersetzt die jeweilige Kurve in der Kraken-Firmware.": "Un porcentaje fijo o perfil rápido sustituye la curva correspondiente en el firmware de Kraken.",
    "Bei hoher CPU-Temperatur Kraken automatisch verstärken (mit 5 °C Hysterese)": "Reforzar Kraken automáticamente con temperatura alta de CPU (histéresis de 5 °C)",
    "Die CPU-Tjmax ist nicht die Wassertemperatur. Für die Kraken-Flüssigkeit gelten die separaten Grenzen unten.": "La Tjmax de CPU no es la temperatura del líquido. Se aplican los límites separados de abajo.",
    "CPU-Sensor: wird gesucht …": "Sensor de CPU: buscando …", "Expertenmodus: Sicherheitsgrenzen frei einstellen": "Modo experto: ajustar libremente los límites de seguridad",
    "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. Eine CPU-Tjmax von 89 oder 95 °C darf niemals als Wassergrenze übernommen werden. Im normalen Modus bleiben vorsichtige Einstellbereiche aktiv.": "Estos valores se aplican solo al líquido Kraken, no a la CPU. Una Tjmax de 89 o 95 °C nunca debe usarse como límite del líquido. En modo normal siguen activos rangos prudentes.",
    "Die drei F140/F120-RGB-Core-Lüfter werden über den separaten NZXT 2023 RGB Controller gesteuert.": "Los tres ventiladores F140/F120 RGB Core se controlan mediante el NZXT 2023 RGB Controller separado.",
    "Die Hardware nimmt ein quadratisches 240×240-Bild an. Die Vorschau zeigt den tatsächlich sichtbaren runden Bereich.": "El hardware acepta una imagen cuadrada de 240×240. La vista previa muestra el área redonda realmente visible.",
    "Sicherheitshinweis: Der Fallback sendet das Bild wiederholt an die Kraken. Langzeitwirkungen auf den Displayspeicher sind nicht ausreichend bekannt. Nur aktivieren, wenn das Display wirklich zurückspringt; standardmäßig bleibt diese Funktion ausgeschaltet.": "Aviso de seguridad: el respaldo envía la imagen repetidamente a Kraken. No se conocen suficientemente los efectos a largo plazo. Actívalo solo si la pantalla realmente vuelve atrás; está desactivado de forma predeterminada.",
    "Einmalige GIF-Übertragung verwendet weiterhin nur das erste Bild. Der experimentelle Stream darunter emuliert Animation auf Firmware 2.x durch vorbereitete statische Frames über den liquidctl-Treiber.": "La carga única de GIF sigue usando solo el primer fotograma. El flujo experimental emula la animación en firmware 2.x con fotogramas estáticos preparados mediante liquidctl.",
    "Experimentell: Das Live-Design rendert Wasser-, CPU- und GPU-Sensordaten als statisches 240×240-Bild und überträgt es im gewählten Intervall. Die Mindestzeit beträgt 5 Sekunden; Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt.": "Experimental: el diseño en vivo renderiza los sensores de líquido, CPU y GPU como imagen estática de 240×240 y la envía en el intervalo elegido. El mínimo es 5 segundos; no se conocen suficientemente los efectos de cargas frecuentes.",
    "Experimentell: Die Uhr überträgt einmal pro Minute ein neues statisches Bild. Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt; Sekunden werden bewusst nicht übertragen.": "Experimental: el reloj envía una imagen estática nueva una vez por minuto. No se conocen suficientemente los efectos a largo plazo; los segundos se omiten intencionadamente.",
    "Akzentvorschau · Schaltflächen, Tabs, Regler und Kurven": "Vista del acento · botones, pestañas, controles y curvas",
    "Die App ändert nicht die Linux-Bildschirmauflösung. Qt arbeitet mit geräteunabhängigen Pixeln; hier werden App-Skalierung und responsives Layout angepasst.": "La aplicación no cambia la resolución de Linux. Qt usa píxeles independientes del dispositivo; aquí se ajustan la escala y el diseño adaptable.",
    "Bestätigte LCD-Hinweise werden dauerhaft gespeichert. Nach einem verdächtigen Absturz oder wiederholten LCD-Fehlern stoppt Kraken Control experimentelle LCD-Funktionen und versucht automatisch die Standardanzeige der Flüssigkeitstemperatur wiederherzustellen.": "Los avisos LCD confirmados se guardan permanentemente. Tras un cierre sospechoso o errores repetidos, Kraken Control detiene las funciones experimentales e intenta restaurar la pantalla estándar del líquido.",
    "Open Hardware Control erkennt DNF, APT, Pacman und Zypper und installiert nach Bestätigung nur die fest zugeordneten Pakete aus bereits eingerichteten Quellen. Es werden keine fremden Paketquellen hinzugefügt.": "Open Hardware Control detecta DNF, APT, Pacman y Zypper e instala, tras confirmación, solo paquetes fijos de repositorios ya configurados. No se añaden repositorios externos.",
    "Schreibzugriff auf /dev/hidraw ist für Pumpen-, Lüfter- und Kurvenänderungen erforderlich. Nach einer neuen udev-Regel kann Ab- und Anstecken oder ein Neustart nötig sein.": "Se requiere escritura en /dev/hidraw para cambiar bomba, ventiladores y curvas. Tras una nueva regla udev puede ser necesario reconectar o reiniciar.",
    "Experimentelle Open-Source-Beta: Nutzung auf eigenes Risiko. Die Anwendung nutzt ausschließlich liquidctl. Die automatische Temperatursicherung wirkt nur, solange Programm, USB-Verbindung und Statusabfrage funktionieren. Wiederholte LCD-Uploads sind standardmäßig deaktiviert.": "Beta experimental de código abierto: uso bajo tu responsabilidad. La aplicación usa solo liquidctl. La protección automática funciona únicamente mientras programa, USB y consulta de estado funcionen. Las cargas LCD repetidas están desactivadas por defecto.",
    "Profile speichern Einstellungen kategorisiert. Gesamtprofile können Kühlung, LCD, RGB, Design, Hintergrund und Anzeige gemeinsam wiederherstellen.": "Los perfiles guardan ajustes por categoría. Los perfiles completos restauran refrigeración, LCD, RGB, diseño, fondo y pantalla juntos.",
    "Kühlungsprofile werden erst nach erfolgreicher Kraken-Erkennung übertragen.": "Los perfiles de refrigeración se envían solo tras detectar Kraken correctamente.",
    "z. B. Gaming, Leise Nacht oder Sommer": "p. ej., Juegos, Noche silenciosa o Verano", "Kurze Beschreibung": "Descripción breve",
    "Kraken Control by Frelidon": "Kraken Control by Frelidon", "Projektumfang – bewusst auf die Kraken begrenzt": "Alcance del proyecto: limitado deliberadamente a Kraken",
    "Entwicklung und KI-Unterstützung": "Desarrollo y asistencia de IA", "Verwendete Software – Website, Quellcode und Lizenz": "Software utilizada: web, código fuente y licencia",
    "Komponenten- und Laufzeitversionen": "Versiones de componentes y ejecución", "AMD-AM5-Temperaturprofile": "Perfiles de temperatura AMD AM5",
    "Lizenz von Kraken Control": "Licencia de Kraken Control", "Unterstützte Geräte und offizielle Herstellerseiten": "Dispositivos compatibles y páginas oficiales",
    "Öffentliches Projekt-Repository und Downloads: https://github.com/Frelidon/kraken-control-linux": "Repositorio público y descargas: https://github.com/Frelidon/kraken-control-linux",
    "<b>Enthalten:</b> Wassertemperatur, Kraken-Pumpe, von der Kraken gemeldete beziehungsweise gesteuerte Radiatorlüfter, LCD sowie der separate NZXT 2023 RGB Controller.": "<b>Incluye:</b> temperatura del líquido, bomba Kraken, ventiladores informados o controlados por Kraken, LCD y NZXT 2023 RGB Controller separado.",
    "<b>Nicht enthalten:</b> Mainboard-Lüfteranschlüsse, zusätzliche Gehäuselüfter, GPU-Lüfter, AMD-Grafiksteuerung sowie allgemeines System-Tuning. Solche Funktionen sollen in eigenständigen Werkzeugen entstehen und können später über eine gemeinsame Oberfläche verbunden werden.": "<b>No incluye:</b> conectores de ventilador de placa, ventiladores de caja, ventiladores GPU, controles gráficos AMD ni ajuste general. Esas funciones se desarrollarán como herramientas separadas.",
    "Projektleitung und Veröffentlichung: Frelidon. Mit Unterstützung von ChatGPT (GPT-5.6 Thinking) von OpenAI bei Programmierung, Dokumentation und Tests. ChatGPT ist kein Laufzeitbestandteil der App. Die Nennung stellt keine offizielle Unterstützung oder Partnerschaft durch OpenAI dar.": "Dirección y publicación: Frelidon. Con ayuda de ChatGPT (GPT-5.6 Thinking) de OpenAI en programación, documentación y pruebas. ChatGPT no forma parte de la ejecución ni implica soporte oficial de OpenAI.",
    "Die auswählbaren CPU-Profile nutzen die von AMD veröffentlichte maximale Betriebstemperatur (Tjmax). Ryzen 9000, Ryzen 8000G und normale Ryzen-7000-Modelle sind in den aufgenommenen Profilen mit 95 °C hinterlegt; Ryzen 7000 X3D mit 89 °C. Die Kraken-Wassergrenzen bleiben davon unabhängig.": "Los perfiles usan la temperatura máxima publicada por AMD (Tjmax). Ryzen 9000, 8000G y Ryzen 7000 normales usan 95 °C; Ryzen 7000 X3D usa 89 °C. Los límites del líquido Kraken son independientes.",
    "Kraken Control by Frelidon steht unter GNU General Public License v3.0 oder später (GPL-3.0-or-later). Die vollständige Lizenz liegt dem Paket als LICENSE bei.": "Kraken Control by Frelidon usa GNU GPL v3.0 o posterior. La licencia completa se incluye como LICENSE.",
    "liquidctl-Gerätename: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · Temperatur, Pumpe, Radiatorlüfter und LCD": "Dispositivo liquidctl: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · temperatura, bomba, ventiladores y LCD",
    "USB 1e71:2012 · separate RGB-Steuerung über liquidctl. Der Controller wird auf der offiziellen Kraken-(2023)-Seite als Bestandteil der RGB-Varianten aufgeführt.": "USB 1e71:2012 · control RGB separado mediante liquidctl. El controlador figura en la página oficial Kraken (2023) como parte de las variantes RGB.",
    "Unterstützt werden nur Lüfter, die als Teil der Kraken-Kühlung über das Kraken-Gerät gemeldet und gesteuert werden. Andere im PC eingebaute Lüfter werden von Kraken Control nicht angesprochen.": "Solo se admiten ventiladores informados y controlados por el dispositivo Kraken. Kraken Control no accede a otros ventiladores del PC.",
    "Alle Links öffnen sich im Standardbrowser. Das bloße Anzeigen dieser Seite überträgt keine Daten; erst das Anklicken eines Links öffnet die jeweilige externe Internetseite.": "Los enlaces se abren en el navegador predeterminado. Ver esta página no transmite datos; solo un clic abre el sitio externo.",
    "Dieses Protokoll erfasst Hardwarebefehle, Fehler, Schaltflächenklicks, Tastaturaktionen und vom Benutzer geänderte Einstellungen. Private Pfade und Kennungen werden weiterhin bereinigt.": "Este registro guarda comandos, errores, clics, teclado y ajustes cambiados. Las rutas e identificadores privados se ocultan.",
    "Das Live-Design überträgt im gewählten Intervall ein neues statisches Bild mit aktuellen Sensordaten. Die langfristige Wirkung häufiger Uploads auf den Displayspeicher ist nicht ausreichend bekannt. Live-Design trotzdem starten?": "El diseño en vivo envía una nueva imagen con sensores actuales en el intervalo elegido. No se conoce suficientemente el efecto de cargas frecuentes. ¿Iniciarlo de todos modos?",
})
UI_TRANSLATIONS["fr"].update({
    "Kompakt · 16:10": "Compact · 16:10", "Standard · 16:9": "Standard · 16:9", "Ultrawide · 21:9": "Ultra-large · 21:9", "Super-Ultrawide · 32:9": "Super ultra-large · 32:9",
    "Zuletzt durch Kraken Control gesetzt: Pumpe unbekannt · Radiatorlüfter unbekannt": "Dernier réglage par Kraken Control : pompe inconnue · ventilateurs inconnus",
    "Ein fester Prozentwert oder ein Schnellprofil ersetzt die jeweilige Kurve in der Kraken-Firmware.": "Un pourcentage fixe ou un profil rapide remplace la courbe correspondante dans le micrologiciel Kraken.",
    "Bei hoher CPU-Temperatur Kraken automatisch verstärken (mit 5 °C Hysterese)": "Renforcer automatiquement Kraken à haute température CPU (hystérésis de 5 °C)",
    "Die CPU-Tjmax ist nicht die Wassertemperatur. Für die Kraken-Flüssigkeit gelten die separaten Grenzen unten.": "La Tjmax du CPU n’est pas la température du liquide. Les limites séparées ci-dessous s’appliquent.",
    "CPU-Sensor: wird gesucht …": "Capteur CPU : recherche …", "Expertenmodus: Sicherheitsgrenzen frei einstellen": "Mode expert : régler librement les limites de sécurité",
    "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. Eine CPU-Tjmax von 89 oder 95 °C darf niemals als Wassergrenze übernommen werden. Im normalen Modus bleiben vorsichtige Einstellbereiche aktiv.": "Ces valeurs concernent uniquement le liquide Kraken, pas le CPU. Une Tjmax de 89 ou 95 °C ne doit jamais servir de limite du liquide. Les plages prudentes restent actives en mode normal.",
    "Die drei F140/F120-RGB-Core-Lüfter werden über den separaten NZXT 2023 RGB Controller gesteuert.": "Les trois ventilateurs F140/F120 RGB Core sont pilotés par le NZXT 2023 RGB Controller séparé.",
    "Die Hardware nimmt ein quadratisches 240×240-Bild an. Die Vorschau zeigt den tatsächlich sichtbaren runden Bereich.": "Le matériel accepte une image carrée de 240×240. L’aperçu montre la zone ronde réellement visible.",
    "Sicherheitshinweis: Der Fallback sendet das Bild wiederholt an die Kraken. Langzeitwirkungen auf den Displayspeicher sind nicht ausreichend bekannt. Nur aktivieren, wenn das Display wirklich zurückspringt; standardmäßig bleibt diese Funktion ausgeschaltet.": "Avis de sécurité : le secours renvoie l’image régulièrement. Les effets à long terme sont insuffisamment connus. Activez-le seulement si l’écran revient réellement ; il est désactivé par défaut.",
    "Einmalige GIF-Übertragung verwendet weiterhin nur das erste Bild. Der experimentelle Stream darunter emuliert Animation auf Firmware 2.x durch vorbereitete statische Frames über den liquidctl-Treiber.": "L’envoi unique d’un GIF utilise toujours sa première image. Le flux expérimental émule l’animation sur le micrologiciel 2.x avec des images statiques via liquidctl.",
    "Experimentell: Das Live-Design rendert Wasser-, CPU- und GPU-Sensordaten als statisches 240×240-Bild und überträgt es im gewählten Intervall. Die Mindestzeit beträgt 5 Sekunden; Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt.": "Expérimental : le design en direct rend les capteurs liquide, CPU et GPU en image statique 240×240 et l’envoie à l’intervalle choisi. Le minimum est 5 secondes ; les effets d’envois fréquents sont insuffisamment connus.",
    "Experimentell: Die Uhr überträgt einmal pro Minute ein neues statisches Bild. Langzeitwirkungen häufiger LCD-Uploads sind nicht ausreichend bekannt; Sekunden werden bewusst nicht übertragen.": "Expérimental : l’horloge envoie une nouvelle image statique une fois par minute. Les effets à long terme sont insuffisamment connus ; les secondes sont volontairement omises.",
    "Akzentvorschau · Schaltflächen, Tabs, Regler und Kurven": "Aperçu de l’accent · boutons, onglets, curseurs et courbes",
    "Die App ändert nicht die Linux-Bildschirmauflösung. Qt arbeitet mit geräteunabhängigen Pixeln; hier werden App-Skalierung und responsives Layout angepasst.": "L’application ne modifie pas la résolution Linux. Qt utilise des pixels indépendants ; l’échelle et la disposition adaptative se règlent ici.",
    "Bestätigte LCD-Hinweise werden dauerhaft gespeichert. Nach einem verdächtigen Absturz oder wiederholten LCD-Fehlern stoppt Kraken Control experimentelle LCD-Funktionen und versucht automatisch die Standardanzeige der Flüssigkeitstemperatur wiederherzustellen.": "Les avis LCD confirmés sont conservés. Après un arrêt suspect ou des erreurs répétées, Kraken Control arrête les fonctions expérimentales et tente de restaurer l’écran standard du liquide.",
    "Open Hardware Control erkennt DNF, APT, Pacman und Zypper und installiert nach Bestätigung nur die fest zugeordneten Pakete aus bereits eingerichteten Quellen. Es werden keine fremden Paketquellen hinzugefügt.": "Open Hardware Control détecte DNF, APT, Pacman et Zypper et, après confirmation, installe uniquement les paquets définis depuis les dépôts déjà configurés. Aucun dépôt tiers n’est ajouté.",
    "Schreibzugriff auf /dev/hidraw ist für Pumpen-, Lüfter- und Kurvenänderungen erforderlich. Nach einer neuen udev-Regel kann Ab- und Anstecken oder ein Neustart nötig sein.": "L’écriture sur /dev/hidraw est requise pour la pompe, les ventilateurs et les courbes. Une reconnexion ou un redémarrage peut être nécessaire après une règle udev.",
    "Experimentelle Open-Source-Beta: Nutzung auf eigenes Risiko. Die Anwendung nutzt ausschließlich liquidctl. Die automatische Temperatursicherung wirkt nur, solange Programm, USB-Verbindung und Statusabfrage funktionieren. Wiederholte LCD-Uploads sind standardmäßig deaktiviert.": "Bêta open source expérimentale : utilisation à vos risques. L’application utilise uniquement liquidctl. La protection automatique fonctionne tant que le programme, l’USB et l’état fonctionnent. Les envois LCD répétés sont désactivés par défaut.",
    "Profile speichern Einstellungen kategorisiert. Gesamtprofile können Kühlung, LCD, RGB, Design, Hintergrund und Anzeige gemeinsam wiederherstellen.": "Les profils enregistrent les réglages par catégorie. Les profils complets restaurent ensemble refroidissement, LCD, RGB, design, fond et affichage.",
    "Kühlungsprofile werden erst nach erfolgreicher Kraken-Erkennung übertragen.": "Les profils de refroidissement sont envoyés après détection réussie de Kraken.",
    "z. B. Gaming, Leise Nacht oder Sommer": "p. ex. Jeu, Nuit calme ou Été", "Kurze Beschreibung": "Description courte",
    "Kraken Control by Frelidon": "Kraken Control by Frelidon", "Projektumfang – bewusst auf die Kraken begrenzt": "Portée du projet : volontairement limitée à Kraken",
    "Entwicklung und KI-Unterstützung": "Développement et assistance IA", "Verwendete Software – Website, Quellcode und Lizenz": "Logiciels utilisés : site, source et licence",
    "Komponenten- und Laufzeitversionen": "Versions des composants et d’exécution", "AMD-AM5-Temperaturprofile": "Profils de température AMD AM5",
    "Lizenz von Kraken Control": "Licence de Kraken Control", "Unterstützte Geräte und offizielle Herstellerseiten": "Appareils compatibles et pages officielles",
    "Öffentliches Projekt-Repository und Downloads: https://github.com/Frelidon/kraken-control-linux": "Dépôt public et téléchargements : https://github.com/Frelidon/kraken-control-linux",
    "<b>Enthalten:</b> Wassertemperatur, Kraken-Pumpe, von der Kraken gemeldete beziehungsweise gesteuerte Radiatorlüfter, LCD sowie der separate NZXT 2023 RGB Controller.": "<b>Inclus :</b> température du liquide, pompe Kraken, ventilateurs signalés ou contrôlés par Kraken, LCD et NZXT 2023 RGB Controller séparé.",
    "<b>Nicht enthalten:</b> Mainboard-Lüfteranschlüsse, zusätzliche Gehäuselüfter, GPU-Lüfter, AMD-Grafiksteuerung sowie allgemeines System-Tuning. Solche Funktionen sollen in eigenständigen Werkzeugen entstehen und können später über eine gemeinsame Oberfläche verbunden werden.": "<b>Non inclus :</b> ventilateurs de carte mère ou boîtier, ventilateurs GPU, commandes graphiques AMD et réglage général. Ces fonctions seront des outils séparés.",
    "Projektleitung und Veröffentlichung: Frelidon. Mit Unterstützung von ChatGPT (GPT-5.6 Thinking) von OpenAI bei Programmierung, Dokumentation und Tests. ChatGPT ist kein Laufzeitbestandteil der App. Die Nennung stellt keine offizielle Unterstützung oder Partnerschaft durch OpenAI dar.": "Direction et publication : Frelidon. Avec l’aide de ChatGPT (GPT-5.6 Thinking) d’OpenAI pour le code, la documentation et les tests. ChatGPT ne fait pas partie de l’exécution et n’implique aucun soutien officiel d’OpenAI.",
    "Die auswählbaren CPU-Profile nutzen die von AMD veröffentlichte maximale Betriebstemperatur (Tjmax). Ryzen 9000, Ryzen 8000G und normale Ryzen-7000-Modelle sind in den aufgenommenen Profilen mit 95 °C hinterlegt; Ryzen 7000 X3D mit 89 °C. Die Kraken-Wassergrenzen bleiben davon unabhängig.": "Les profils utilisent la température maximale publiée par AMD (Tjmax). Ryzen 9000, 8000G et Ryzen 7000 standard utilisent 95 °C ; Ryzen 7000 X3D utilise 89 °C. Les limites du liquide Kraken sont indépendantes.",
    "Kraken Control by Frelidon steht unter GNU General Public License v3.0 oder später (GPL-3.0-or-later). Die vollständige Lizenz liegt dem Paket als LICENSE bei.": "Kraken Control by Frelidon est sous GNU GPL v3.0 ou ultérieure. La licence complète est incluse dans LICENSE.",
    "liquidctl-Gerätename: NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · Temperatur, Pumpe, Radiatorlüfter und LCD": "Appareil liquidctl : NZXT Kraken 2023 · USB 1e71:300e · LCD 240×240 · température, pompe, ventilateurs et LCD",
    "USB 1e71:2012 · separate RGB-Steuerung über liquidctl. Der Controller wird auf der offiziellen Kraken-(2023)-Seite als Bestandteil der RGB-Varianten aufgeführt.": "USB 1e71:2012 · commande RGB séparée via liquidctl. Le contrôleur figure sur la page officielle Kraken (2023) avec les variantes RGB.",
    "Unterstützt werden nur Lüfter, die als Teil der Kraken-Kühlung über das Kraken-Gerät gemeldet und gesteuert werden. Andere im PC eingebaute Lüfter werden von Kraken Control nicht angesprochen.": "Seuls les ventilateurs signalés et contrôlés par l’appareil Kraken sont pris en charge. Kraken Control n’accède pas aux autres ventilateurs du PC.",
    "Alle Links öffnen sich im Standardbrowser. Das bloße Anzeigen dieser Seite überträgt keine Daten; erst das Anklicken eines Links öffnet die jeweilige externe Internetseite.": "Les liens s’ouvrent dans le navigateur par défaut. Afficher cette page n’envoie aucune donnée ; seul un clic ouvre le site externe.",
    "Dieses Protokoll erfasst Hardwarebefehle, Fehler, Schaltflächenklicks, Tastaturaktionen und vom Benutzer geänderte Einstellungen. Private Pfade und Kennungen werden weiterhin bereinigt.": "Ce journal enregistre commandes, erreurs, clics, clavier et réglages modifiés. Les chemins et identifiants privés restent masqués.",
    "Das Live-Design überträgt im gewählten Intervall ein neues statisches Bild mit aktuellen Sensordaten. Die langfristige Wirkung häufiger Uploads auf den Displayspeicher ist nicht ausreichend bekannt. Live-Design trotzdem starten?": "Le design en direct envoie une nouvelle image avec les capteurs à l’intervalle choisi. L’effet d’envois fréquents est insuffisamment connu. Démarrer quand même ?",
})
UI_TRANSLATIONS["en"].update({
    "Hell (Standard)": "Light (default)", "Akzentfarbe": "Accent color", "Leise · 45 % / 35 %": "Quiet · 45% / 35%",
    "Ausgeglichen · 55 % / 50 %": "Balanced · 55% / 50%", "Leistung · 75 % / 75 %": "Performance · 75% / 75%",
    "Sicher · 65 % / 65 %": "Safe · 65% / 65%", "Kühlprofil": "Cooling profile", "Öffnen": "Open",
    "Flüssigkeitstemperatur anzeigen": "Show liquid temperature", "Farbe 1 · #00aaff": "Color 1 · #00aaff",
    "Farbe 2 · #ffffff": "Color 2 · #ffffff", "Text · #ffffff": "Text · #ffffff", "Hintergrund · #10141c": "Background · #10141c",
    "Eisblau · #00c8ff": "Ice blue · #00c8ff", "Neongrün · #39ff88": "Neon green · #39ff88", "Orange · #ff9a32": "Orange · #ff9a32",
    "Rot · #ff4058": "Red · #ff4058", "Gold · #ffd54a": "Gold · #ffd54a", "Weiß · #f4f7ff": "White · #f4f7ff", "Lila · #a855f7": "Purple · #a855f7",
})
UI_TRANSLATIONS["es"].update({
    "Hell (Standard)": "Claro (predeterminado)", "Akzentfarbe": "Color de acento", "Leise · 45 % / 35 %": "Silencioso · 45% / 35%",
    "Ausgeglichen · 55 % / 50 %": "Equilibrado · 55% / 50%", "Leistung · 75 % / 75 %": "Rendimiento · 75% / 75%",
    "Sicher · 65 % / 65 %": "Seguro · 65% / 65%", "Kühlprofil": "Perfil de refrigeración", "Öffnen": "Abrir",
    "Flüssigkeitstemperatur anzeigen": "Mostrar temperatura del líquido", "Farbe 1 · #00aaff": "Color 1 · #00aaff",
    "Farbe 2 · #ffffff": "Color 2 · #ffffff", "Text · #ffffff": "Texto · #ffffff", "Hintergrund · #10141c": "Fondo · #10141c",
    "Eisblau · #00c8ff": "Azul hielo · #00c8ff", "Neongrün · #39ff88": "Verde neón · #39ff88", "Orange · #ff9a32": "Naranja · #ff9a32",
    "Rot · #ff4058": "Rojo · #ff4058", "Gold · #ffd54a": "Dorado · #ffd54a", "Weiß · #f4f7ff": "Blanco · #f4f7ff", "Lila · #a855f7": "Morado · #a855f7",
})
UI_TRANSLATIONS["fr"].update({
    "Hell (Standard)": "Clair (par défaut)", "Akzentfarbe": "Couleur d’accent", "Leise · 45 % / 35 %": "Silencieux · 45% / 35%",
    "Ausgeglichen · 55 % / 50 %": "Équilibré · 55% / 50%", "Leistung · 75 % / 75 %": "Performance · 75% / 75%",
    "Sicher · 65 % / 65 %": "Sûr · 65% / 65%", "Kühlprofil": "Profil de refroidissement", "Öffnen": "Ouvrir",
    "Flüssigkeitstemperatur anzeigen": "Afficher la température du liquide", "Farbe 1 · #00aaff": "Couleur 1 · #00aaff",
    "Farbe 2 · #ffffff": "Couleur 2 · #ffffff", "Text · #ffffff": "Texte · #ffffff", "Hintergrund · #10141c": "Arrière-plan · #10141c",
    "Eisblau · #00c8ff": "Bleu glacier · #00c8ff", "Neongrün · #39ff88": "Vert néon · #39ff88", "Orange · #ff9a32": "Orange · #ff9a32",
    "Rot · #ff4058": "Rouge · #ff4058", "Gold · #ffd54a": "Or · #ffd54a", "Weiß · #f4f7ff": "Blanc · #f4f7ff", "Lila · #a855f7": "Violet · #a855f7",
})
UI_TRANSLATIONS["en"].update({
    "Sehr guter Bereich": "Excellent range", "Normal unter Last": "Normal under load", "Erhöht – Kurve prüfen": "Elevated – check curve", "Kritisch – Kühlung prüfen": "Critical – check cooling",
    "⚠ Pumpendrehzahl ungewöhnlich niedrig.": "⚠ Pump speed unusually low.", "⚠ Kritische Wassertemperatur": "⚠ Critical liquid temperature", "⚠ Erhöhte Wassertemperatur": "⚠ Elevated liquid temperature",
    "⚠ Lüfter stehen trotz erhöhter Temperatur.": "⚠ Fans are stopped despite elevated temperature.", "✅ Kühlung arbeitet normal.": "✅ Cooling is operating normally.",
    "LCD-Uhr-Hinweis": "LCD clock notice", "LCD-Fallback-Hinweis": "LCD fallback notice", "GIF-Streamer-Hinweis": "GIF streamer notice", "Live-Hardwaredesign-Hinweis": "Live hardware design notice", "LCD-Sicherheitswiederherstellung vorgemerkt": "LCD safety recovery pending",
})
UI_TRANSLATIONS["es"].update({
    "Sehr guter Bereich": "Rango excelente", "Normal unter Last": "Normal bajo carga", "Erhöht – Kurve prüfen": "Elevado – comprobar curva", "Kritisch – Kühlung prüfen": "Crítico – comprobar refrigeración",
    "⚠ Pumpendrehzahl ungewöhnlich niedrig.": "⚠ Velocidad de bomba inusualmente baja.", "⚠ Kritische Wassertemperatur": "⚠ Temperatura crítica del líquido", "⚠ Erhöhte Wassertemperatur": "⚠ Temperatura elevada del líquido",
    "⚠ Lüfter stehen trotz erhöhter Temperatur.": "⚠ Los ventiladores están parados con temperatura elevada.", "✅ Kühlung arbeitet normal.": "✅ La refrigeración funciona normalmente.",
    "LCD-Uhr-Hinweis": "Aviso del reloj LCD", "LCD-Fallback-Hinweis": "Aviso de respaldo LCD", "GIF-Streamer-Hinweis": "Aviso del flujo GIF", "Live-Hardwaredesign-Hinweis": "Aviso del diseño en vivo", "LCD-Sicherheitswiederherstellung vorgemerkt": "Recuperación segura del LCD pendiente",
})
UI_TRANSLATIONS["fr"].update({
    "Sehr guter Bereich": "Excellente plage", "Normal unter Last": "Normal en charge", "Erhöht – Kurve prüfen": "Élevé – vérifier la courbe", "Kritisch – Kühlung prüfen": "Critique – vérifier le refroidissement",
    "⚠ Pumpendrehzahl ungewöhnlich niedrig.": "⚠ Vitesse de pompe anormalement basse.", "⚠ Kritische Wassertemperatur": "⚠ Température critique du liquide", "⚠ Erhöhte Wassertemperatur": "⚠ Température élevée du liquide",
    "⚠ Lüfter stehen trotz erhöhter Temperatur.": "⚠ Les ventilateurs sont arrêtés malgré une température élevée.", "✅ Kühlung arbeitet normal.": "✅ Le refroidissement fonctionne normalement.",
    "LCD-Uhr-Hinweis": "Avis de l’horloge LCD", "LCD-Fallback-Hinweis": "Avis de secours LCD", "GIF-Streamer-Hinweis": "Avis du flux GIF", "Live-Hardwaredesign-Hinweis": "Avis du design matériel en direct", "LCD-Sicherheitswiederherstellung vorgemerkt": "Récupération de sécurité LCD en attente",
})

_GIF_SAFETY_TEXT = (
    "Kein nativer Firmware-2.x-GIF-Modus: Version 3.0.9 verwendet im NZXT-Modul einen exklusiven CAM-nahen Roh-Framepfad. "
    "Jeder Frame verwendet explizit Start → ACK → 20-Byte-Header → 115.200 Byte RGB565 → "
    "Ende → ACK. Standard ist eine phasenstabile 26,667-Hz-Folge ohne Frame-Sprünge; 25,6 Hz bleibt als sicherer Rückfallmodus. Die Bewegungsglättung arbeitet "
    "bewegungskompensiert statt mit reinem Crossfade. Transfers werden nie überlappt und Catch-up-Bursts bleiben verboten. "
    "Kraken-Statusabfragen pausieren während des Streams. Die CPU-Kurvenregelung liest Linux-hwmon weiter und verwendet nur bei "
    "einer relevanten Drehzahländerung die koordinierte Kurzpause: USB freigeben → Kühlbefehl übertragen → denselben Stream fortsetzen. "
    "Bei falschen ACKs oder ausbleibenden Lebenszeichen folgt der sichere Fallback auf die Flüssigkeitstemperatur."
)
_ABOUT_SUMMARY_TEXT = (
    "Gemeinsame, quelloffene Linux-Hardwarezentrale. Version 3.0.9 ergänzt das Corsair-/OpenLinkHub-Modul um "
    "direkte Maustastenbelegung und eine begrenzte fensterlokale Makroaufnahme. LCD-Hardwaredesigns besitzen "
    "getrennte Farben und Größen für Beschriftung und Zahl sowie globale Celsius-/Fahrenheit-Anzeige. "
    "CPU-Kurven, GIF-USB-Koordination und validierte Geräteeinstellungen "
    "bleiben erhalten. Open Radeon Control Center bleibt ein eigenständiges Projekt. Experimentelle Beta, "
    "Nutzung auf eigenes Risiko; unabhängiges Projekt ohne offizielle Verbindung zu den genannten Herstellern."
)
UI_TRANSLATIONS["en"].update({
    "Menüs, Tabs, Schaltflächen, Gruppen und Auswahlfelder wechseln vollständig mit der gewählten Sprache. Rein technische Diagnosezeilen im Log bleiben für vergleichbare Hardwaretests teilweise Deutsch.": "Menus, tabs, buttons, groups and choices switch completely with the selected language. Purely technical log diagnostics remain partly in German for comparable hardware tests.",
    "Diese Version enthält fünf runde Live-Hardwaredesigns für Wasser, CPU und GPU, Eisblau als Standardakzent, Farbvorlagen und freie Hex-Farben. Die sichtbare Grundoberfläche unterstützt Deutsch, Englisch, Spanisch und Französisch. Der exklusive CAM-nahe Firmware-2.x-LCD-Streamer, passende ACK-Prüfung, ein 12-Sekunden-Watchdog und der gemeinsame LCD-Sicherheitsfallback bleiben enthalten. ": "This version includes five rounded live hardware designs for liquid, CPU and GPU, ice blue as the default accent, color presets and custom hex colors. The visible base interface supports German, English, Spanish and French. The exclusive CAM-near firmware-2.x LCD streamer, matched ACK checks, a 12-second watchdog and the shared LCD safety fallback remain included. ",
    _GIF_SAFETY_TEXT: "No native firmware-2.x GIF mode: version 3.0.9 uses an exclusive CAM-near raw-frame path in the NZXT module. Every frame explicitly uses Start → ACK → 20-byte header → 115,200 bytes RGB565 → End → ACK. Kraken status polling pauses, while CPU-curve sensing through Linux hwmon continues. Relevant duty changes use a coordinated short USB handoff before the same cached stream resumes. Invalid ACKs or missing heartbeats trigger the safe fallback.",
    "Log: 0 / 10.000 Zeichen": "Log: 0 / 10,000 characters",
    _ABOUT_SUMMARY_TEXT: "Shared open-source Linux hardware hub. Version 3.0.9 adds direct OpenLinkHub mouse assignments, a bounded window-local macro recorder, separate LCD label/value styling and global Celsius/Fahrenheit display. CPU curves, coordinated GIF USB handoff and validated controls remain available. Open Radeon Control Center remains separate. Experimental beta, use at your own risk.",
})
UI_TRANSLATIONS["es"].update({
    "Menüs, Tabs, Schaltflächen, Gruppen und Auswahlfelder wechseln vollständig mit der gewählten Sprache. Rein technische Diagnosezeilen im Log bleiben für vergleichbare Hardwaretests teilweise Deutsch.": "Menús, pestañas, botones, grupos y selecciones cambian completamente con el idioma elegido. Algunas líneas técnicas del registro permanecen en alemán para comparar pruebas.",
    "Diese Version enthält fünf runde Live-Hardwaredesigns für Wasser, CPU und GPU, Eisblau als Standardakzent, Farbvorlagen und freie Hex-Farben. Die sichtbare Grundoberfläche unterstützt Deutsch, Englisch, Spanisch und Französisch. Der exklusive CAM-nahe Firmware-2.x-LCD-Streamer, passende ACK-Prüfung, ein 12-Sekunden-Watchdog und der gemeinsame LCD-Sicherheitsfallback bleiben enthalten. ": "Esta versión incluye cinco diseños redondos en vivo para líquido, CPU y GPU, azul hielo predeterminado, colores predefinidos y hexadecimales personalizados. La interfaz visible admite alemán, inglés, español y francés. Se mantienen el flujo LCD exclusivo similar a CAM, las respuestas ACK verificadas, el vigilante de 12 segundos y el respaldo seguro del LCD. ",
    _GIF_SAFETY_TEXT: "No existe modo GIF nativo en firmware 2.x: la versión 3.0.9 usa una ruta exclusiva similar a CAM. Las consultas Kraken se pausan, pero el sensor de las curvas de CPU sigue activo mediante hwmon. Los cambios relevantes usan una entrega USB coordinada y después continúa el mismo flujo.",
    "Log: 0 / 10.000 Zeichen": "Registro: 0 / 10.000 caracteres",
    _ABOUT_SUMMARY_TEXT: "Centro de hardware Linux de código abierto. La versión 3.0.9 añade asignaciones directas de botones OpenLinkHub, grabación local de macros, estilos LCD separados y Celsius/Fahrenheit global.",
})
UI_TRANSLATIONS["fr"].update({
    "Menüs, Tabs, Schaltflächen, Gruppen und Auswahlfelder wechseln vollständig mit der gewählten Sprache. Rein technische Diagnosezeilen im Log bleiben für vergleichbare Hardwaretests teilweise Deutsch.": "Menus, onglets, boutons, groupes et sélections changent entièrement avec la langue choisie. Certaines lignes techniques du journal restent en allemand pour comparer les tests.",
    "Diese Version enthält fünf runde Live-Hardwaredesigns für Wasser, CPU und GPU, Eisblau als Standardakzent, Farbvorlagen und freie Hex-Farben. Die sichtbare Grundoberfläche unterstützt Deutsch, Englisch, Spanisch und Französisch. Der exklusive CAM-nahe Firmware-2.x-LCD-Streamer, passende ACK-Prüfung, ein 12-Sekunden-Watchdog und der gemeinsame LCD-Sicherheitsfallback bleiben enthalten. ": "Cette version contient cinq designs matériels ronds en direct pour liquide, CPU et GPU, le bleu glacier par défaut, des préréglages et des couleurs hexadécimales personnalisées. L’interface visible prend en charge l’allemand, l’anglais, l’espagnol et le français. Le flux LCD exclusif proche de CAM, les ACK vérifiés, le watchdog de 12 secondes et le secours LCD commun restent inclus. ",
    _GIF_SAFETY_TEXT: "Pas de mode GIF natif sur le micrologiciel 2.x : la version 3.0.9 utilise un chemin exclusif proche de CAM. Les états Kraken sont suspendus, mais les courbes CPU continuent de lire hwmon. Les changements utiles emploient une courte remise USB coordonnée puis reprennent le même flux.",
    "Log: 0 / 10.000 Zeichen": "Journal : 0 / 10 000 caractères",
    _ABOUT_SUMMARY_TEXT: "Centre matériel Linux open source. La version 3.0.9 ajoute l’affectation directe des boutons OpenLinkHub, un enregistreur de macro local, des styles LCD séparés et Celsius/Fahrenheit global.",
})

UI_TRANSLATIONS["en"].update({
    "Schrift- und Zahlen-Größe": "Text and number size", "Animierte Hardwaredaten · Ringe und Orbits": "Animated hardware data · Rings and orbits",
    "20 FPS · ruhig": "20 FPS · calm", "25 FPS · flüssig · empfohlen": "25 FPS · smooth · recommended",
    "Animierte Vorschau erzeugen": "Generate animated preview", "Hardwareanimation starten": "Start hardware animation", "Hardwareanimation anhalten": "Stop hardware animation",
    "Animationslayout": "Animation layout", "Animationsrate": "Animation rate", "Animierte Hardwaredaten": "Animated hardware data",
    "Animierte Hardwaredaten: bereit · Farbe und Schriftgröße werden vom Live-Design übernommen.": "Animated hardware data: ready · Color and text size are shared with the live design.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. Die angezeigten Temperaturen sind eine Momentaufnahme beim Start. Während des exklusiven CAM-Raw-Streams bleiben Kraken-Statusabfragen und neue Kühlbefehle wie bisher pausiert; gespeicherte Hardwarekurven laufen weiter.": "The animation creates a seamless GIF loop with rotating rings, light points and orbits. Displayed temperatures are a snapshot taken at start. During the exclusive CAM-raw stream, Kraken status polling and new cooling commands remain paused while stored hardware curves continue.",
    "Animierte Vorschau läuft · noch nicht auf das LCD übertragen.": "Animated preview is running · not uploaded to the LCD yet.", "Die Hardwareanimation konnte nicht erzeugt werden:": "The hardware animation could not be created:",
    "Experimentelle Hardwareanimation": "Experimental hardware animation", "Hardwareanimation wird vorbereitet …": "Preparing hardware animation …",
    "Hardwareanimation vorbereitet": "Hardware animation prepared", "Frames": "frames", "LCD-Modus: animierte Hardwaredaten · experimentell": "LCD mode: animated hardware data · experimental",
    "Hardwareanimation aktiv": "Hardware animation active", "Temperaturen als Start-Momentaufnahme": "temperatures are a start snapshot", "Upload": "upload",
    "Hardwareanimation angehalten · das letzte Bild kann sichtbar bleiben.": "Hardware animation stopped · the last image may remain visible.", "Hardwareanimation angehalten": "Hardware animation stopped",
    "Hardwareanimation: Fehler": "Hardware animation: error", "Hardwareanimation: Start abgebrochen": "Hardware animation: start canceled", "Hardwareanimation: Datei nicht mehr vorhanden": "Hardware animation: file no longer available",
    "Hardwareanimation-Hinweis": "Hardware animation notice",
    "Die Animation verwendet die zuletzt gelesenen Temperaturen als Momentaufnahme. Während des Streams pausieren Kraken-Statusabfragen und neue Kühlbefehle; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "The animation uses the last-read temperatures as a snapshot. Kraken status polling and new cooling commands pause during the stream while curves stored in the Kraken continue. Frequent LCD uploads remain experimental. Start the hardware animation anyway?",
    "LCD-Modus: Live-Hardwaredesign": "LCD mode: live hardware design",
    "Live-Hardwaredesign angehalten · das letzte Bild kann sichtbar bleiben.": "Live hardware design stopped · the last image may remain visible.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben; gespeicherte Hardwarekurven laufen weiter.": "The animation creates a seamless GIF loop with rotating rings, light points and orbits. CPU and GPU temperatures are safely refreshed through Linux hwmon. Liquid temperature remains the last safe Kraken value because Kraken status polling stays paused during the exclusive CAM-raw stream; stored hardware curves continue running.",
    "CPU/GPU live · Wasser letzter sicherer Wert": "CPU/GPU live · liquid last safe value",
    "CPU live": "CPU live", "GPU live": "GPU live", "Wasser letzter sicherer Wert": "liquid last safe value",
    "Livewerte aktualisiert": "Live values updated", "Livewert-Aktualisierung fehlgeschlagen": "Live value refresh failed", "Wasser zuletzt": "liquid last",
    "Die Animation aktualisiert CPU- und GPU-Temperaturen sicher über Linux-hwmon. Die Wassertemperatur bleibt während des exklusiven Streams der letzte sichere Kraken-Wert. Kraken-Statusabfragen und neue Kühlbefehle pausieren; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "The animation safely refreshes CPU and GPU temperatures through Linux hwmon. During the exclusive stream, liquid temperature remains the last safe Kraken value. Kraken status polling and new cooling commands pause while curves stored in the Kraken continue. Frequent LCD uploads remain experimental. Start the hardware animation anyway?",
})
UI_TRANSLATIONS["es"].update({
    "Schrift- und Zahlen-Größe": "Tamaño de texto y números", "Animierte Hardwaredaten · Ringe und Orbits": "Datos de hardware animados · Anillos y órbitas",
    "20 FPS · ruhig": "20 FPS · tranquilo", "25 FPS · flüssig · empfohlen": "25 FPS · fluido · recomendado",
    "Animierte Vorschau erzeugen": "Generar vista animada", "Hardwareanimation starten": "Iniciar animación de hardware", "Hardwareanimation anhalten": "Detener animación de hardware",
    "Animationslayout": "Diseño de animación", "Animationsrate": "Velocidad de animación", "Animierte Hardwaredaten": "Datos de hardware animados",
    "Animierte Hardwaredaten: bereit · Farbe und Schriftgröße werden vom Live-Design übernommen.": "Datos de hardware animados: listo · El color y tamaño se comparten con el diseño en vivo.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. Die angezeigten Temperaturen sind eine Momentaufnahme beim Start. Während des exklusiven CAM-Raw-Streams bleiben Kraken-Statusabfragen und neue Kühlbefehle wie bisher pausiert; gespeicherte Hardwarekurven laufen weiter.": "La animación crea un bucle GIF continuo con anillos, puntos luminosos y órbitas. Las temperaturas son una instantánea al iniciar. Durante el flujo CAM exclusivo se pausan el estado y nuevos comandos; las curvas guardadas continúan.",
    "Animierte Vorschau läuft · noch nicht auf das LCD übertragen.": "Vista animada en ejecución · aún no enviada al LCD.", "Die Hardwareanimation konnte nicht erzeugt werden:": "No se pudo crear la animación de hardware:",
    "Experimentelle Hardwareanimation": "Animación de hardware experimental", "Hardwareanimation wird vorbereitet …": "Preparando animación de hardware …", "Hardwareanimation vorbereitet": "Animación preparada", "Frames": "fotogramas",
    "LCD-Modus: animierte Hardwaredaten · experimentell": "Modo LCD: datos de hardware animados · experimental", "Hardwareanimation aktiv": "Animación de hardware activa", "Temperaturen als Start-Momentaufnahme": "temperaturas como instantánea inicial", "Upload": "envío",
    "Hardwareanimation angehalten · das letzte Bild kann sichtbar bleiben.": "Animación detenida · la última imagen puede seguir visible.", "Hardwareanimation angehalten": "Animación de hardware detenida", "Hardwareanimation: Fehler": "Animación de hardware: error",
    "Hardwareanimation: Start abgebrochen": "Animación de hardware: inicio cancelado", "Hardwareanimation: Datei nicht mehr vorhanden": "Animación de hardware: archivo no disponible", "Hardwareanimation-Hinweis": "Aviso de animación de hardware",
    "Die Animation verwendet die zuletzt gelesenen Temperaturen als Momentaufnahme. Während des Streams pausieren Kraken-Statusabfragen und neue Kühlbefehle; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "La animación usa las últimas temperaturas como instantánea. Durante el flujo se pausan el estado y nuevos comandos, mientras continúan las curvas guardadas. Las cargas frecuentes siguen siendo experimentales. ¿Iniciar de todos modos?",
    "LCD-Modus: Live-Hardwaredesign": "Modo LCD: diseño de hardware en vivo",
    "Live-Hardwaredesign angehalten · das letzte Bild kann sichtbar bleiben.": "Diseño de hardware en vivo detenido · la última imagen puede seguir visible.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben; gespeicherte Hardwarekurven laufen weiter.": "La animación crea un bucle continuo con anillos, puntos luminosos y órbitas. Las temperaturas de CPU y GPU se actualizan de forma segura mediante hwmon de Linux. La temperatura del líquido conserva el último valor seguro de Kraken porque las consultas quedan pausadas durante el flujo CAM exclusivo; las curvas guardadas continúan.",
    "CPU/GPU live · Wasser letzter sicherer Wert": "CPU/GPU en vivo · líquido: último valor seguro",
    "CPU live": "CPU en vivo", "GPU live": "GPU en vivo", "Wasser letzter sicherer Wert": "líquido: último valor seguro",
    "Livewerte aktualisiert": "Valores en vivo actualizados", "Livewert-Aktualisierung fehlgeschlagen": "Error al actualizar valores en vivo", "Wasser zuletzt": "líquido último",
    "Die Animation aktualisiert CPU- und GPU-Temperaturen sicher über Linux-hwmon. Die Wassertemperatur bleibt während des exklusiven Streams der letzte sichere Kraken-Wert. Kraken-Statusabfragen und neue Kühlbefehle pausieren; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "La animación actualiza de forma segura CPU y GPU mediante hwmon de Linux. Durante el flujo exclusivo, el líquido conserva el último valor seguro de Kraken. Se pausan las consultas y nuevos comandos, mientras continúan las curvas guardadas. Las cargas frecuentes siguen siendo experimentales. ¿Iniciar de todos modos?",
})
UI_TRANSLATIONS["fr"].update({
    "Schrift- und Zahlen-Größe": "Taille du texte et des nombres", "Animierte Hardwaredaten · Ringe und Orbits": "Données matérielles animées · Anneaux et orbites",
    "20 FPS · ruhig": "20 FPS · calme", "25 FPS · flüssig · empfohlen": "25 FPS · fluide · recommandé",
    "Animierte Vorschau erzeugen": "Générer l’aperçu animé", "Hardwareanimation starten": "Démarrer l’animation matérielle", "Hardwareanimation anhalten": "Arrêter l’animation matérielle",
    "Animationslayout": "Disposition de l’animation", "Animationsrate": "Fréquence de l’animation", "Animierte Hardwaredaten": "Données matérielles animées",
    "Animierte Hardwaredaten: bereit · Farbe und Schriftgröße werden vom Live-Design übernommen.": "Données matérielles animées : prêt · La couleur et la taille sont partagées avec le design en direct.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. Die angezeigten Temperaturen sind eine Momentaufnahme beim Start. Während des exklusiven CAM-Raw-Streams bleiben Kraken-Statusabfragen und neue Kühlbefehle wie bisher pausiert; gespeicherte Hardwarekurven laufen weiter.": "L’animation crée une boucle GIF continue avec anneaux, points lumineux et orbites. Les températures sont un instantané au démarrage. Pendant le flux CAM exclusif, les états et nouvelles commandes sont suspendus ; les courbes enregistrées continuent.",
    "Animierte Vorschau läuft · noch nicht auf das LCD übertragen.": "Aperçu animé en cours · pas encore envoyé au LCD.", "Die Hardwareanimation konnte nicht erzeugt werden:": "Impossible de créer l’animation matérielle :",
    "Experimentelle Hardwareanimation": "Animation matérielle expérimentale", "Hardwareanimation wird vorbereitet …": "Préparation de l’animation matérielle …", "Hardwareanimation vorbereitet": "Animation préparée", "Frames": "images",
    "LCD-Modus: animierte Hardwaredaten · experimentell": "Mode LCD : données matérielles animées · expérimental", "Hardwareanimation aktiv": "Animation matérielle active", "Temperaturen als Start-Momentaufnahme": "températures comme instantané initial", "Upload": "envoi",
    "Hardwareanimation angehalten · das letzte Bild kann sichtbar bleiben.": "Animation arrêtée · la dernière image peut rester visible.", "Hardwareanimation angehalten": "Animation matérielle arrêtée", "Hardwareanimation: Fehler": "Animation matérielle : erreur",
    "Hardwareanimation: Start abgebrochen": "Animation matérielle : démarrage annulé", "Hardwareanimation: Datei nicht mehr vorhanden": "Animation matérielle : fichier indisponible", "Hardwareanimation-Hinweis": "Avis d’animation matérielle",
    "Die Animation verwendet die zuletzt gelesenen Temperaturen als Momentaufnahme. Während des Streams pausieren Kraken-Statusabfragen und neue Kühlbefehle; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "L’animation utilise les dernières températures comme instantané. Pendant le flux, les états et nouvelles commandes sont suspendus tandis que les courbes enregistrées continuent. Les envois fréquents restent expérimentaux. Démarrer quand même ?",
    "LCD-Modus: Live-Hardwaredesign": "Mode LCD : design matériel en direct",
    "Live-Hardwaredesign angehalten · das letzte Bild kann sichtbar bleiben.": "Design matériel en direct arrêté · la dernière image peut rester visible.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben; gespeicherte Hardwarekurven laufen weiter.": "L’animation crée une boucle continue avec anneaux, points lumineux et orbites. Les températures CPU et GPU sont actualisées en toute sécurité via hwmon Linux. Le liquide conserve la dernière valeur Kraken sûre car les états restent suspendus pendant le flux CAM exclusif ; les courbes enregistrées continuent.",
    "CPU/GPU live · Wasser letzter sicherer Wert": "CPU/GPU en direct · liquide : dernière valeur sûre",
    "CPU live": "CPU en direct", "GPU live": "GPU en direct", "Wasser letzter sicherer Wert": "liquide : dernière valeur sûre",
    "Livewerte aktualisiert": "Valeurs en direct actualisées", "Livewert-Aktualisierung fehlgeschlagen": "Échec de l’actualisation en direct", "Wasser zuletzt": "liquide dernier",
    "Die Animation aktualisiert CPU- und GPU-Temperaturen sicher über Linux-hwmon. Die Wassertemperatur bleibt während des exklusiven Streams der letzte sichere Kraken-Wert. Kraken-Statusabfragen und neue Kühlbefehle pausieren; die in der Kraken gespeicherten Kurven laufen weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?": "L’animation actualise en toute sécurité le CPU et le GPU via hwmon Linux. Pendant le flux exclusif, le liquide conserve la dernière valeur Kraken sûre. Les états et nouvelles commandes sont suspendus tandis que les courbes enregistrées continuent. Les envois fréquents restent expérimentaux. Démarrer quand même ?",
})
UI_TRANSLATIONS["en"].update({
    "Geräte": "Devices", "Diagnose": "Diagnostics", "Corsair · OpenLinkHub": "Corsair · OpenLinkHub",
    "Nicht erkannte Geräte/Module anzeigen": "Show undetected devices/modules",
    "Gemeinsame Linux-Hardwarezentrale · NZXT Kraken · Corsair/OpenLinkHub": "Shared Linux hardware hub · NZXT Kraken · Corsair/OpenLinkHub",
    "OpenLinkHub-Status": "OpenLinkHub status", "↻ OpenLinkHub aktualisieren": "↻ Refresh OpenLinkHub",
    "Web-Dashboard öffnen": "Open web dashboard", "Benutzerdienst starten": "Start user service",
    "Benutzerdienst stoppen": "Stop user service", "Benutzerdienst neu starten": "Restart user service",
    "Beim Login aktivieren": "Enable at login",
    "Dienstkontext und Hilfe": "Service context and help", "Gerät": "Device", "Kanal": "Channel",
    "Temperatur": "Temperature", "Drehzahl": "Speed", "Firmware": "Firmware",
    "Offizielles OpenLinkHub-Projekt": "Official OpenLinkHub project", "API-Dokumentation": "API documentation",
    "Offizielle Benutzerinstallation": "Official user installation",
    "Migrationshilfe: System → Benutzer": "Migration help: system → user",
})
UI_TRANSLATIONS["es"].update({
    "Geräte": "Dispositivos", "Diagnose": "Diagnóstico", "Corsair · OpenLinkHub": "Corsair · OpenLinkHub",
    "Nicht erkannte Geräte/Module anzeigen": "Mostrar dispositivos/módulos no detectados",
    "Gemeinsame Linux-Hardwarezentrale · NZXT Kraken · Corsair/OpenLinkHub": "Centro de hardware Linux · NZXT Kraken · Corsair/OpenLinkHub",
    "OpenLinkHub-Status": "Estado de OpenLinkHub", "↻ OpenLinkHub aktualisieren": "↻ Actualizar OpenLinkHub",
    "Web-Dashboard öffnen": "Abrir panel web", "Benutzerdienst starten": "Iniciar servicio de usuario",
    "Benutzerdienst stoppen": "Detener servicio de usuario", "Benutzerdienst neu starten": "Reiniciar servicio de usuario",
    "Beim Login aktivieren": "Activar al iniciar sesión",
    "Dienstkontext und Hilfe": "Contexto del servicio y ayuda", "Gerät": "Dispositivo", "Kanal": "Canal",
    "Temperatur": "Temperatura", "Drehzahl": "Velocidad", "Firmware": "Firmware",
    "Offizielles OpenLinkHub-Projekt": "Proyecto oficial OpenLinkHub", "API-Dokumentation": "Documentación API",
    "Offizielle Benutzerinstallation": "Instalación oficial de usuario",
    "Migrationshilfe: System → Benutzer": "Ayuda de migración: sistema → usuario",
})
UI_TRANSLATIONS["fr"].update({
    "Geräte": "Appareils", "Diagnose": "Diagnostic", "Corsair · OpenLinkHub": "Corsair · OpenLinkHub",
    "Nicht erkannte Geräte/Module anzeigen": "Afficher les appareils/modules non détectés",
    "Gemeinsame Linux-Hardwarezentrale · NZXT Kraken · Corsair/OpenLinkHub": "Centre matériel Linux · NZXT Kraken · Corsair/OpenLinkHub",
    "OpenLinkHub-Status": "État OpenLinkHub", "↻ OpenLinkHub aktualisieren": "↻ Actualiser OpenLinkHub",
    "Web-Dashboard öffnen": "Ouvrir le tableau de bord web", "Benutzerdienst starten": "Démarrer le service utilisateur",
    "Benutzerdienst stoppen": "Arrêter le service utilisateur", "Benutzerdienst neu starten": "Redémarrer le service utilisateur",
    "Beim Login aktivieren": "Activer à la connexion",
    "Dienstkontext und Hilfe": "Contexte du service et aide", "Gerät": "Appareil", "Kanal": "Canal",
    "Temperatur": "Température", "Drehzahl": "Vitesse", "Firmware": "Micrologiciel",
    "Offizielles OpenLinkHub-Projekt": "Projet OpenLinkHub officiel", "API-Dokumentation": "Documentation API",
    "Offizielle Benutzerinstallation": "Installation utilisateur officielle",
    "Migrationshilfe: System → Benutzer": "Aide à la migration : système → utilisateur",
})
UI_TRANSLATIONS["en"].update({
    "Direkte Gerätesteuerung": "Direct device control", "Direkte OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren": "Enable direct OpenLinkHub writes for this application session",
    "Kühlung": "Cooling", "RGB und Gerät": "RGB and device", "Maus": "Mouse", "Tastatur": "Keyboard", "Headset": "Headset", "Netzteil": "Power supply",
    "Corsair-Kühlgerät": "Corsair cooling device", "Lüfter-/Pumpenkanal": "Fan/pump channel", "Vorhandenes Temperaturprofil": "Existing temperature profile",
    "Temperaturprofil auf Kanal anwenden": "Apply temperature profile to channel", "Manuelle Leistung": "Manual output", "Manuellen Wert auf Kanal anwenden": "Apply manual value to channel",
    "Vorhandenes RGB-Profil": "Existing RGB profile", "RGB-Profil auf Kanal anwenden": "Apply RGB profile to channel", "Neue Kanalbezeichnung": "New channel label",
    "Kanalbezeichnung speichern": "Save channel label", "Gerätehelligkeit": "Device brightness", "Helligkeit anwenden": "Apply brightness", "LCD-Ausrichtung": "LCD rotation", "LCD-Ausrichtung anwenden": "Apply LCD rotation",
    "Corsair-Maus": "Corsair mouse", "Fünf DPI-Stufen": "Five DPI stages", "DPI-Stufen anwenden": "Apply DPI stages", "USB-Abfragerate": "USB polling rate", "Abfragerate anwenden": "Apply polling rate", "Ruhemodus": "Sleep mode", "Ruhemodus anwenden": "Apply sleep mode",
    "Corsair-Tastatur": "Corsair keyboard", "Benutzerprofil wechseln": "Switch user profile", "Tastaturprofil wechseln": "Switch keyboard profile", "Tastaturbelegung": "Keyboard layout", "Tastaturbelegung anwenden": "Apply keyboard layout",
    "Corsair-Headset": "Corsair headset", "Geräuschmodus": "Noise mode", "Geräuschmodus anwenden": "Apply noise mode", "Sidetone-Lautstärke": "Sidetone volume", "Sidetone-Lautstärke anwenden": "Apply sidetone volume", "Corsair-Netzteil": "Corsair power supply", "Netzteil-Lüftermodus anwenden": "Apply PSU fan mode",
})
UI_TRANSLATIONS["es"].update({
    "Direkte Gerätesteuerung": "Control directo del dispositivo", "Direkte OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren": "Activar escritura directa de OpenLinkHub para esta sesión",
    "Kühlung": "Refrigeración", "RGB und Gerät": "RGB y dispositivo", "Maus": "Ratón", "Tastatur": "Teclado", "Headset": "Auriculares", "Netzteil": "Fuente de alimentación",
    "Corsair-Kühlgerät": "Dispositivo de refrigeración Corsair", "Lüfter-/Pumpenkanal": "Canal de ventilador/bomba", "Vorhandenes Temperaturprofil": "Perfil de temperatura existente",
    "Temperaturprofil auf Kanal anwenden": "Aplicar perfil de temperatura al canal", "Manuelle Leistung": "Potencia manual", "Manuellen Wert auf Kanal anwenden": "Aplicar valor manual al canal",
    "Vorhandenes RGB-Profil": "Perfil RGB existente", "RGB-Profil auf Kanal anwenden": "Aplicar perfil RGB al canal", "Neue Kanalbezeichnung": "Nueva etiqueta de canal", "Kanalbezeichnung speichern": "Guardar etiqueta",
    "Gerätehelligkeit": "Brillo del dispositivo", "Helligkeit anwenden": "Aplicar brillo", "LCD-Ausrichtung": "Rotación LCD", "LCD-Ausrichtung anwenden": "Aplicar rotación LCD",
    "Corsair-Maus": "Ratón Corsair", "Fünf DPI-Stufen": "Cinco niveles DPI", "DPI-Stufen anwenden": "Aplicar niveles DPI", "USB-Abfragerate": "Frecuencia USB", "Ruhemodus": "Modo de reposo",
    "Corsair-Tastatur": "Teclado Corsair", "Benutzerprofil wechseln": "Cambiar perfil de usuario", "Tastaturprofil wechseln": "Cambiar perfil de teclado", "Tastaturbelegung": "Distribución del teclado",
    "Corsair-Headset": "Auriculares Corsair", "Geräuschmodus": "Modo de ruido", "Sidetone-Lautstärke": "Volumen de sidetone", "Corsair-Netzteil": "Fuente Corsair", "Netzteil-Lüftermodus anwenden": "Aplicar modo del ventilador",
})
UI_TRANSLATIONS["fr"].update({
    "Direkte Gerätesteuerung": "Commande directe de l’appareil", "Direkte OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren": "Activer les écritures OpenLinkHub directes pour cette session",
    "Kühlung": "Refroidissement", "RGB und Gerät": "RGB et appareil", "Maus": "Souris", "Tastatur": "Clavier", "Headset": "Casque", "Netzteil": "Alimentation",
    "Corsair-Kühlgerät": "Appareil de refroidissement Corsair", "Lüfter-/Pumpenkanal": "Canal ventilateur/pompe", "Vorhandenes Temperaturprofil": "Profil de température existant",
    "Temperaturprofil auf Kanal anwenden": "Appliquer le profil au canal", "Manuelle Leistung": "Puissance manuelle", "Manuellen Wert auf Kanal anwenden": "Appliquer la valeur manuelle au canal",
    "Vorhandenes RGB-Profil": "Profil RGB existant", "RGB-Profil auf Kanal anwenden": "Appliquer le profil RGB", "Neue Kanalbezeichnung": "Nouveau libellé du canal", "Kanalbezeichnung speichern": "Enregistrer le libellé",
    "Gerätehelligkeit": "Luminosité de l’appareil", "Helligkeit anwenden": "Appliquer la luminosité", "LCD-Ausrichtung": "Rotation LCD", "LCD-Ausrichtung anwenden": "Appliquer la rotation LCD",
    "Corsair-Maus": "Souris Corsair", "Fünf DPI-Stufen": "Cinq niveaux DPI", "DPI-Stufen anwenden": "Appliquer les niveaux DPI", "USB-Abfragerate": "Fréquence USB", "Ruhemodus": "Mode veille",
    "Corsair-Tastatur": "Clavier Corsair", "Benutzerprofil wechseln": "Changer le profil utilisateur", "Tastaturprofil wechseln": "Changer le profil clavier", "Tastaturbelegung": "Disposition du clavier",
    "Corsair-Headset": "Casque Corsair", "Geräuschmodus": "Mode de bruit", "Sidetone-Lautstärke": "Volume du retour micro", "Corsair-Netzteil": "Alimentation Corsair", "Netzteil-Lüftermodus anwenden": "Appliquer le mode ventilateur",
})
_GIF_COOLING_WARNING = (
    "Die Animation aktualisiert CPU- und GPU-Temperaturen sicher über Linux-hwmon. Die Wassertemperatur bleibt während "
    "des exklusiven Streams der letzte sichere Kraken-Wert. Kraken-Statusabfragen pausieren, aber aktive Pumpen- und "
    "Lüfterkurven lesen die CPU weiter. Nur eine relevante Drehzahländerung unterbricht die Animation kurz; anschließend "
    "läuft derselbe Framecache automatisch weiter. Häufige LCD-Uploads bleiben experimentell. Hardwareanimation trotzdem starten?"
)
UI_TRANSLATIONS["en"][_GIF_COOLING_WARNING] = (
    "The animation safely refreshes CPU and GPU temperatures through Linux hwmon. Liquid temperature remains the last "
    "safe Kraken value while status polling is paused, but active pump and fan curves keep reading the CPU. Only a relevant "
    "duty change briefly interrupts the animation before the same cached stream continues. Frequent LCD uploads "
    "remain experimental. Start the hardware animation anyway?"
)
UI_TRANSLATIONS["es"][_GIF_COOLING_WARNING] = (
    "La animación actualiza CPU y GPU mediante hwmon de Linux. El líquido conserva el último valor seguro mientras las "
    "consultas están pausadas, pero las curvas activas siguen leyendo la CPU. Solo un cambio relevante interrumpe brevemente "
    "la animación y después continúa el mismo flujo. ¿Iniciar la animación experimental?"
)
UI_TRANSLATIONS["fr"][_GIF_COOLING_WARNING] = (
    "L’animation actualise le CPU et le GPU via hwmon Linux. Le liquide conserve la dernière valeur sûre pendant la pause "
    "des états, mais les courbes actives continuent de lire le CPU. Seule une variation utile interrompt brièvement "
    "l’animation puis reprend automatiquement le même flux. Démarrer l’animation expérimentale ?"
)

UI_TRANSLATIONS["en"].update({
    "Betriebsart umschalten": "Switch operating mode",
    "Manuell aktivieren": "Activate manual mode",
    "Pumpenkurve aktivieren": "Activate pump curve",
    "Lüfterkurve aktivieren": "Activate fan curve",
    "Der markierte Modus wurde zuletzt erfolgreich auf die Kraken übertragen. Das Bearbeiten eines Reglers oder einer Kurve ändert den aktiven Modus erst beim Anwenden.":
        "The highlighted mode was last applied successfully to the Kraken. Editing a slider or curve does not change the active mode until it is applied.",
})
UI_TRANSLATIONS["es"].update({
    "Betriebsart umschalten": "Cambiar modo de funcionamiento",
    "Manuell aktivieren": "Activar modo manual",
    "Pumpenkurve aktivieren": "Activar curva de bomba",
    "Lüfterkurve aktivieren": "Activar curva de ventiladores",
    "Der markierte Modus wurde zuletzt erfolgreich auf die Kraken übertragen. Das Bearbeiten eines Reglers oder einer Kurve ändert den aktiven Modus erst beim Anwenden.":
        "El modo marcado es el último aplicado correctamente al Kraken. Editar un control o una curva no cambia el modo activo hasta aplicarlo.",
})
UI_TRANSLATIONS["fr"].update({
    "Betriebsart umschalten": "Changer de mode de fonctionnement",
    "Manuell aktivieren": "Activer le mode manuel",
    "Pumpenkurve aktivieren": "Activer la courbe de pompe",
    "Lüfterkurve aktivieren": "Activer la courbe des ventilateurs",
    "Der markierte Modus wurde zuletzt erfolgreich auf die Kraken übertragen. Das Bearbeiten eines Reglers oder einer Kurve ändert den aktiven Modus erst beim Anwenden.":
        "Le mode marqué est le dernier appliqué avec succès au Kraken. Modifier un réglage ou une courbe ne change le mode actif qu’après application.",
})

# 3.0.5: visible NZXT curves are evaluated from the CPU sensor.  Liquid
# temperature remains a separate emergency safeguard.
UI_TRANSLATIONS["en"].update({
    "Pumpenkurve nach CPU-Temperatur": "Pump curve by CPU temperature",
    "Lüfterkurve nach CPU-Temperatur": "Fan curve by CPU temperature",
    "AMD-AM5-Prozessorprofil für CPU-Kurven": "AMD AM5 processor profile for CPU curves",
    "CPU-Kurven werden von Open Hardware Control laufend berechnet. Ein manueller Wert oder ein Schnellprofil deaktiviert die CPU-Kurve des jeweiligen Kanals.": "Open Hardware Control continuously evaluates CPU curves. A manual value or quick profile disables the CPU curve for that channel.",
    "Die Profile setzen beide sichtbaren Kurven passend zur CPU-Temperatur. Die Wassertemperatur bleibt unabhängig davon als zusätzliche Sicherheitsüberwachung aktiv.": "Profiles configure both visible curves for CPU temperature. Liquid temperature remains active independently as an additional safety monitor.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben. Aktive Pumpen- und Lüfterkurven lesen die CPU trotzdem weiter. Eine relevante Drehzahländerung verwendet die koordinierte Kurzpause und setzt danach denselben Framecache fort.": "The animation creates a seamless GIF loop with rotating rings, light points and orbits. CPU and GPU temperatures are refreshed safely through Linux hwmon. Liquid remains the last safe Kraken value while status polling is paused. Active pump and fan curves keep reading the CPU; a relevant duty change uses the coordinated short handoff and then resumes the same frame cache.",
})
UI_TRANSLATIONS["es"].update({
    "Pumpenkurve nach CPU-Temperatur": "Curva de bomba según la temperatura de CPU",
    "Lüfterkurve nach CPU-Temperatur": "Curva de ventiladores según la temperatura de CPU",
    "AMD-AM5-Prozessorprofil für CPU-Kurven": "Perfil de procesador AMD AM5 para curvas de CPU",
    "CPU-Kurven werden von Open Hardware Control laufend berechnet. Ein manueller Wert oder ein Schnellprofil deaktiviert die CPU-Kurve des jeweiligen Kanals.": "Open Hardware Control calcula continuamente las curvas de CPU. Un valor manual o perfil rápido desactiva la curva de CPU de ese canal.",
    "Die Profile setzen beide sichtbaren Kurven passend zur CPU-Temperatur. Die Wassertemperatur bleibt unabhängig davon als zusätzliche Sicherheitsüberwachung aktiv.": "Los perfiles configuran ambas curvas visibles según la temperatura de CPU. La temperatura del líquido sigue activa como vigilancia de seguridad adicional.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben. Aktive Pumpen- und Lüfterkurven lesen die CPU trotzdem weiter. Eine relevante Drehzahländerung verwendet die koordinierte Kurzpause und setzt danach denselben Framecache fort.": "La animación crea un bucle continuo con anillos, puntos luminosos y órbitas. CPU y GPU se actualizan mediante hwmon. El líquido conserva el último valor seguro mientras las consultas Kraken están pausadas. Las curvas activas siguen leyendo la CPU; un cambio relevante usa la entrega breve coordinada y reanuda el mismo caché.",
})
UI_TRANSLATIONS["fr"].update({
    "Pumpenkurve nach CPU-Temperatur": "Courbe de pompe selon la température CPU",
    "Lüfterkurve nach CPU-Temperatur": "Courbe des ventilateurs selon la température CPU",
    "AMD-AM5-Prozessorprofil für CPU-Kurven": "Profil processeur AMD AM5 pour les courbes CPU",
    "CPU-Kurven werden von Open Hardware Control laufend berechnet. Ein manueller Wert oder ein Schnellprofil deaktiviert die CPU-Kurve des jeweiligen Kanals.": "Open Hardware Control calcule continuellement les courbes CPU. Une valeur manuelle ou un profil rapide désactive la courbe CPU du canal concerné.",
    "Die Profile setzen beide sichtbaren Kurven passend zur CPU-Temperatur. Die Wassertemperatur bleibt unabhängig davon als zusätzliche Sicherheitsüberwachung aktiv.": "Les profils configurent les deux courbes visibles selon la température CPU. La température du liquide reste active comme surveillance de sécurité supplémentaire.",
    "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams pausiert bleiben. Aktive Pumpen- und Lüfterkurven lesen die CPU trotzdem weiter. Eine relevante Drehzahländerung verwendet die koordinierte Kurzpause und setzt danach denselben Framecache fort.": "L’animation crée une boucle continue avec anneaux, points lumineux et orbites. CPU et GPU sont actualisés via hwmon. Le liquide conserve la dernière valeur sûre pendant la pause des états Kraken. Les courbes actives continuent de lire le CPU ; un changement utile emploie la remise brève coordonnée puis reprend le même cache.",
})


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

    def is_idle(self) -> bool:
        """Return whether no liquidctl command is running or queued."""
        return self._process is None and self._current is None and not self._queue

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


class MouseSchematicWidget(QWidget):
    """Interactive overlay for the project's own copyright-safe mouse SVGs."""

    buttonSelected = Signal(str)

    def __init__(self):
        super().__init__()
        self._product = "Corsair-Maus"
        self._schema = mouse_schema(self._product)
        self._rows = visual_button_rows(self._product, [])
        self._selected_id = ""
        self._pixmap = QPixmap()
        self.setMinimumSize(430, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAccessibleName("Grafische Corsair-Maustastenansicht")
        self.setAccessibleDescription(
            "Eigene schematische Vektorgrafik. Eine markierte Taste kann angeklickt oder mit den Pfeiltasten ausgewählt werden."
        )
        self._load_asset()

    def set_mouse(self, product: str, assignments: object) -> list[dict[str, object]]:
        self._product = str(product or "Corsair-Maus")
        self._schema = mouse_schema(self._product)
        self._rows = visual_button_rows(self._product, assignments)
        self._selected_id = str(self._rows[0]["id"]) if self._rows else ""
        self._load_asset()
        self.update()
        return list(self._rows)

    def select_button(self, button_id: str) -> None:
        if any(str(row.get("id")) == button_id for row in self._rows):
            self._selected_id = button_id
            self.update()

    def _load_asset(self) -> None:
        asset = str(self._schema.get("asset") or "")
        path = Path(__file__).with_name("assets") / asset
        self._pixmap = QPixmap(str(path)) if path.is_file() else QPixmap()

    def _canvas_rect(self) -> QRectF:
        margin = 12.0
        available_w = max(1.0, self.width() - margin * 2)
        available_h = max(1.0, self.height() - margin * 2)
        ratio = 600.0 / 360.0
        width = min(available_w, available_h * ratio)
        height = width / ratio
        left = (self.width() - width) / 2.0
        top = (self.height() - height) / 2.0
        return QRectF(left, top, width, height)

    def _hotspot_rect(self, row: dict[str, object]) -> QRectF:
        x, y, width, height = row.get("rect", (0, 0, 1, 1))
        canvas = self._canvas_rect()
        return QRectF(
            canvas.left() + float(x) / 600.0 * canvas.width(),
            canvas.top() + float(y) / 360.0 * canvas.height(),
            float(width) / 600.0 * canvas.width(),
            float(height) / 360.0 * canvas.height(),
        )

    def _row_at(self, point: QPointF) -> dict[str, object] | None:
        for row in reversed(self._rows):
            if row.get("reported_only"):
                continue
            if self._hotspot_rect(row).adjusted(-4, -4, 4, 4).contains(point):
                return row
        return None

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        canvas = self._canvas_rect()
        base = self.palette().color(QPalette.ColorRole.Base)
        border = self.palette().color(QPalette.ColorRole.Midlight)
        painter.setPen(QPen(border, 1))
        painter.setBrush(base)
        painter.drawRoundedRect(canvas, 14, 14)
        if not self._pixmap.isNull():
            painter.drawPixmap(canvas.toRect(), self._pixmap)
        else:
            painter.setPen(QPen(QColor("#73899d"), 3))
            painter.setBrush(QColor("#17232d"))
            painter.drawEllipse(QRectF(canvas.center().x() - 75, canvas.top() + 18, 150, canvas.height() - 36))

        for row in self._rows:
            if row.get("reported_only"):
                continue
            hotspot = self._hotspot_rect(row)
            selected = str(row.get("id")) == self._selected_id
            reported = bool(row.get("reported"))
            color = QColor("#48c6ff" if reported else "#a9bccb")
            if selected:
                color = QColor("#ffb52e")
            fill = QColor(color)
            fill.setAlpha(95 if selected else 55)
            painter.setPen(QPen(color, 3 if selected else 2))
            painter.setBrush(fill)
            painter.drawRoundedRect(hotspot, 6, 6)
            badge = QRectF(hotspot.center().x() - 12, hotspot.center().y() - 12, 24, 24)
            painter.setBrush(color)
            painter.setPen(QPen(QColor("#071119"), 1))
            painter.drawEllipse(badge)
            painter.setPen(QColor("#071119"))
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(row.get("number") or "?"))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            row = self._row_at(event.position())
            if row is not None:
                self._selected_id = str(row.get("id") or "")
                self.setFocus(Qt.FocusReason.MouseFocusReason)
                self.update()
                self.buttonSelected.emit(self._selected_id)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        row = self._row_at(event.position())
        if row is None:
            self.setToolTip("Taste anklicken, um ihre aktuelle Funktion in der Liste zu markieren.")
        else:
            self.setToolTip(f"{row.get('label', 'Taste')} · {row.get('function', 'Nicht belegt')}")
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._rows:
            return super().keyPressEvent(event)
        ids = [str(row.get("id") or "") for row in self._rows]
        current = ids.index(self._selected_id) if self._selected_id in ids else 0
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
            current = (current - 1) % len(ids)
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
            current = (current + 1) % len(ids)
        elif event.key() not in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            return super().keyPressEvent(event)
        self._selected_id = ids[current]
        self.update()
        self.buttonSelected.emit(self._selected_id)


class MacroRecorderDialog(QDialog):
    """Focus-local keyboard macro recorder backed by OLH's input catalog."""

    def __init__(self, catalog: list[dict[str, object]], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("OpenLinkHub-Makro aufnehmen")
        self.setModal(True)
        self.resize(620, 460)
        self._catalog = [item for item in catalog if isinstance(item, dict)]
        self._steps: list[dict[str, object]] = []
        self._recording = False
        self._last_key_time = 0.0

        layout = QVBoxLayout(self)
        note = QLabel(
            "Die Aufnahme erfasst einzelne Tastendrücke nur solange dieses Fenster aktiv ist. "
            "Sie ist bewusst nicht systemweit und zeichnet keine Passwörter, Mausbewegungen oder "
            "Tastenkombinationen mit gehaltenen Modifikatortasten auf. Escape beendet die Aufnahme."
        )
        note.setWordWrap(True)
        note.setObjectName("warningText")
        layout.addWidget(note)

        self.status = QLabel("Bereit · Aufnahme starten und danach die gewünschten Einzeltasten drücken.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Pause", "Taste", "OpenLinkHub-Wert"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        recording_buttons = QHBoxLayout()
        self.start_button = QPushButton("Aufnahme starten")
        self.stop_button = QPushButton("Aufnahme stoppen")
        self.stop_button.setEnabled(False)
        clear_button = QPushButton("Leeren")
        self.start_button.clicked.connect(self.start_recording)
        self.stop_button.clicked.connect(self.stop_recording)
        clear_button.clicked.connect(self.clear_steps)
        recording_buttons.addWidget(self.start_button)
        recording_buttons.addWidget(self.stop_button)
        recording_buttons.addWidget(clear_button)
        recording_buttons.addStretch()
        layout.addLayout(recording_buttons)

        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        cancel_button = QPushButton("Abbrechen")
        self.save_button = QPushButton("Aufnahme übernehmen")
        self.save_button.setEnabled(False)
        cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self.accept)
        dialog_buttons.addWidget(cancel_button)
        dialog_buttons.addWidget(self.save_button)
        layout.addLayout(dialog_buttons)

    @property
    def steps(self) -> list[dict[str, int]]:
        return [
            {"key": int(item["key"]), "delay": int(item["delay"])}
            for item in self._steps
        ]

    @staticmethod
    def _token(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())

    def _event_tokens(self, event: QKeyEvent) -> set[str]:
        tokens = {
            self._token(event.text()),
            self._token(QKeySequence(event.key()).toString()),
        }
        special = {
            Qt.Key.Key_Return: {"enter", "return"},
            Qt.Key.Key_Enter: {"enter", "return", "numpadenter"},
            Qt.Key.Key_Space: {"space", "spacebar"},
            Qt.Key.Key_Backspace: {"backspace"},
            Qt.Key.Key_Delete: {"delete", "del"},
            Qt.Key.Key_Tab: {"tab"},
            Qt.Key.Key_Left: {"left", "arrowleft"},
            Qt.Key.Key_Right: {"right", "arrowright"},
            Qt.Key.Key_Up: {"up", "arrowup"},
            Qt.Key.Key_Down: {"down", "arrowdown"},
            Qt.Key.Key_Home: {"home"},
            Qt.Key.Key_End: {"end"},
            Qt.Key.Key_PageUp: {"pageup", "pgup"},
            Qt.Key.Key_PageDown: {"pagedown", "pgdown"},
        }
        tokens.update(special.get(event.key(), set()))
        tokens.discard("")
        return tokens

    def _catalog_match(self, event: QKeyEvent) -> dict[str, object] | None:
        tokens = self._event_tokens(event)
        if not tokens:
            return None
        exact: list[dict[str, object]] = []
        fuzzy: list[dict[str, object]] = []
        for item in self._catalog:
            name = self._token(item.get("name"))
            if name in tokens:
                exact.append(item)
            elif any(name in {f"key{token}", f"keyboard{token}"} or name.endswith(token) for token in tokens):
                fuzzy.append(item)
        matches = exact or fuzzy
        return matches[0] if len(matches) == 1 else None

    def start_recording(self) -> None:
        if not self._catalog:
            self.status.setText("Der OpenLinkHub-Tastaturkatalog ist nicht verfügbar.")
            return
        self._recording = True
        self._last_key_time = time.monotonic()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_button.setEnabled(False)
        self.status.setText("Aufnahme läuft · Einzeltasten drücken · Escape beendet.")
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def stop_recording(self) -> None:
        if self._recording:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        self._recording = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.save_button.setEnabled(bool(self._steps))
        self.status.setText(f"Aufnahme gestoppt · {len(self._steps)} Tastenschritt(e).")

    def clear_steps(self) -> None:
        self._steps.clear()
        self.table.setRowCount(0)
        self.save_button.setEnabled(False)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if not self._recording or event.type() != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return super().eventFilter(watched, event)
        if event.isAutoRepeat():
            return True
        if event.key() == Qt.Key.Key_Escape:
            self.stop_recording()
            return True
        if event.key() in {Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta}:
            self.status.setText("Modifikatortasten werden allein nicht aufgenommen; bitte Einzeltasten verwenden.")
            return True
        matched = self._catalog_match(event)
        if matched is None:
            shown = QKeySequence(event.key()).toString() or event.text() or str(event.key())
            self.status.setText(f"„{shown}“ konnte im OpenLinkHub-Katalog nicht eindeutig zugeordnet werden.")
            return True
        now = time.monotonic()
        delay = 0 if not self._steps else min(5000, max(0, round((now - self._last_key_time) * 1000)))
        self._last_key_time = now
        step = {"key": int(matched.get("id", 0)), "delay": delay, "name": str(matched.get("name", "Taste"))}
        self._steps.append(step)
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"{delay} ms"))
        self.table.setItem(row, 1, QTableWidgetItem(str(step["name"])))
        self.table.setItem(row, 2, QTableWidgetItem(str(step["key"])))
        self.status.setText(f"Aufnahme läuft · {len(self._steps)} Tastenschritt(e).")
        return True

    def done(self, result: int) -> None:
        self.stop_recording()
        super().done(result)


class CurveEditor(QWidget):
    """Interactive, safety-aware CPU-temperature curve editor.

    Points can be dragged with the mouse or adjusted with the arrow keys. The
    editor keeps temperatures strictly increasing and duties non-decreasing.
    The final point remains fixed at 100 percent and cannot move beyond 100 °C.
    """

    pointsChanged = Signal(object)

    def __init__(self, points: list[tuple[int, int]], minimum_duty: int, channel_label: str):
        super().__init__()
        self._points = [(int(temp), int(duty)) for temp, duty in points]
        self._minimum_duty = int(minimum_duty)
        self._channel_label = channel_label
        self._temperature_min = 20
        self._temperature_max = 100
        self._accent = QColor("#00aaff")
        self._current_temperature: float | None = None
        self._temperature_unit = "c"
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

    def set_temperature_unit(self, unit: str) -> None:
        self._temperature_unit = normalize_temperature_unit(unit)
        self.update()

    def _temperature_text(self, value: float, decimals: int = 0) -> str:
        displayed = celsius_to_display(value, self._temperature_unit)
        return f"{displayed:.{decimals}f}{temperature_symbol(self._temperature_unit)}"

    def _plot_rect(self) -> QRectF:
        return QRectF(54.0, 18.0, max(120.0, self.width() - 78.0), max(100.0, self.height() - 70.0))

    def _to_canvas(self, temp: float, duty: float) -> QPointF:
        rect = self._plot_rect()
        span = float(self._temperature_max - self._temperature_min)
        x = rect.left() + ((temp - self._temperature_min) / span) * rect.width()
        y = rect.bottom() - (duty / 100.0) * rect.height()
        return QPointF(x, y)

    def _from_canvas(self, point: QPointF) -> tuple[int, int]:
        rect = self._plot_rect()
        span = float(self._temperature_max - self._temperature_min)
        temp = self._temperature_min + ((point.x() - rect.left()) / max(1.0, rect.width())) * span
        duty = ((rect.bottom() - point.y()) / max(1.0, rect.height())) * 100.0
        return int(round(temp)), int(round(duty))

    def _move_selected(self, delta_temp: int, delta_duty: int) -> None:
        if not self._points:
            return
        index = self._selected_index
        temp, duty = self._points[index]
        self._set_point(index, temp + delta_temp, duty + delta_duty)

    def _set_point(self, index: int, temp: int, duty: int) -> None:
        previous_temp = self._points[index - 1][0] + 1 if index > 0 else self._temperature_min
        next_temp = self._points[index + 1][0] - 1 if index < len(self._points) - 1 else self._temperature_max
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
            p1 = self._to_canvas(self._temperature_min, duty)
            p2 = self._to_canvas(self._temperature_max, duty)
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(p1, p2)
            painter.setPen(muted)
            painter.drawText(QRectF(2, p1.y() - 10, 46, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{duty}%")
        for temp in range(self._temperature_min, self._temperature_max + 1, 10):
            p1 = self._to_canvas(temp, 0)
            p2 = self._to_canvas(temp, 100)
            painter.setPen(QPen(grid, 1, Qt.PenStyle.DotLine))
            painter.drawLine(p1, p2)
            painter.setPen(muted)
            painter.drawText(QRectF(p1.x() - 24, rect.bottom() + 7, 48, 20), Qt.AlignmentFlag.AlignHCenter, self._temperature_text(temp))

        # Current CPU temperature marker.
        if self._current_temperature is not None:
            current = max(float(self._temperature_min), min(float(self._temperature_max), float(self._current_temperature)))
            x = self._to_canvas(current, 0).x()
            warning = QColor("#d49b21")
            painter.setPen(QPen(warning, 2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.setPen(warning)
            painter.drawText(QRectF(x - 55, rect.top() + 3, 110, 20), Qt.AlignmentFlag.AlignHCenter, f"Aktuell {self._temperature_text(self._current_temperature, 1)}")

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
            painter.drawText(label_rect.adjusted(-10, 0, 10, 0), Qt.AlignmentFlag.AlignHCenter, f"{self._temperature_text(temp)} / {duty}%")

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
        if not self.settings.allKeys():
            legacy_settings = QSettings(ORG_NAME, LEGACY_SETTINGS_APP_NAME)
            for key in legacy_settings.allKeys():
                self.settings.setValue(key, legacy_settings.value(key))
            self.settings.sync()
        self.launched_from_autostart = "--autostart" in sys.argv
        self.autostart_launch_monotonic = time.monotonic()
        self.session_shutdown_requested = False
        self.ui_language = str(self.settings.value("ui/language", "de"))
        if self.ui_language not in SUPPORTED_UI_LANGUAGES:
            self.ui_language = "de"
        self.temperature_unit = normalize_temperature_unit(
            self.settings.value("display/temperature_unit", "c")
        )
        self._i18n_widget_sources: dict[object, dict[str, object]] = {}
        self.previous_experimental_lcd_session = self.settings.value("lcd/experimental_session_active", False, type=bool)
        self.experimental_autostart_blocked = self.previous_experimental_lcd_session
        self.lcd_recovery_required = self.settings.value("lcd/recovery_required", False, type=bool) or self.previous_experimental_lcd_session
        if self.previous_experimental_lcd_session:
            self.settings.setValue("lcd/recovery_required", True)
            self.settings.setValue("lcd/experimental_session_active", False)
            self.settings.sync()
        self.lcd_failure_count = 0
        self.lcd_safety_reason = ""
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
        self.current_liquid_temp: float | None = None
        self.current_cpu_temp: float | None = None
        self.cpu_sensor_label = "Nicht erkannt"
        self.current_gpu_temp: float | None = None
        self.gpu_sensor_label = "Nicht erkannt"
        self.cpu_curve_filtered_temp: float | None = None
        self.cpu_curve_last_write = 0.0
        self.cpu_curve_last_duties: dict[str, int | None] = {"pump": None, "fan": None}
        self.cpu_curve_sensor_failures = 0
        self.cpu_curve_fallback_active = False
        self.cpu_curve_force_update = True
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
        self.openlinkhub_detected = False
        self.openlinkhub_status_busy = False
        self.openlinkhub_write_busy = False
        self.openlinkhub_last_status: dict[str, object] = {}
        self.show_undetected_modules = self.settings.value("navigation/show_undetected_modules", False, type=bool)
        self.last_status_ok = False
        self.selected_lcd_file: Path | None = None
        self.prepared_lcd_file: Path | None = None
        self.temp_dir = Path(tempfile.gettempdir()) / "open-hardware-control"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle(f"{DISPLAY_NAME} {APP_VERSION} — Linux")
        self.resize(1280, 880)
        self.setMinimumSize(920, 620)
        icon_path = Path(__file__).with_name("kraken-control.svg")
        app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon.fromTheme("preferences-system-cooling")
        self.setWindowIcon(app_icon)

        self.build_ui()
        self.build_menu_bar()
        self.update_navigation_visibility()
        self.configure_accessibility()
        self.apply_theme()

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(3000)
        self.status_timer.timeout.connect(self.refresh_status)

        # CPU curves are evaluated independently from Kraken status polling.
        # This timer deliberately keeps running during the exclusive LCD-GIF
        # stream because reading Linux hwmon does not touch the Kraken USB
        # device.  Actual duty writes use the coordinated short USB handoff.
        self.cpu_curve_timer = QTimer(self)
        self.cpu_curve_timer.setInterval(CPU_CURVE_SAMPLE_MS)
        self.cpu_curve_timer.timeout.connect(self.update_cpu_curve_control)

        self.lcd_keepalive_timer = QTimer(self)
        self.lcd_keepalive_timer.timeout.connect(self.send_lcd_keepalive)

        self.clock_timer = QTimer(self)
        self.clock_timer.setSingleShot(True)
        self.clock_timer.timeout.connect(self.update_clock_lcd)

        self.clock_keepalive_timer = QTimer(self)
        self.clock_keepalive_timer.timeout.connect(self.send_clock_keepalive)

        self.hardware_lcd_timer = QTimer(self)
        self.hardware_lcd_timer.timeout.connect(self.update_hardware_lcd)
        self.hardware_lcd_active = False
        self.hardware_lcd_image_file = self.temp_dir / "lcd-hardware.png"
        self.hardware_animation_file = self.temp_dir / "lcd-hardware-animation.gif"
        self.hardware_animation_spec_file = self.temp_dir / "lcd-hardware-animation.json"
        self.hardware_animation_movie: QMovie | None = None
        self.hardware_animation_warning_acknowledged = self.settings.value("hardware_animation/experimental_warning_ack", False, type=bool)

        # GIF streaming runs in its own long-lived QProcess so the GUI remains
        # responsive and only one liquidctl device connection is used for all
        # frames.  No Python worker threads are introduced.
        self.gif_process = QProcess(self)
        self.gif_process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.gif_process.readyReadStandardOutput.connect(self.on_gif_stream_stdout)
        self.gif_process.readyReadStandardError.connect(self.on_gif_stream_stderr)
        self.gif_process.finished.connect(self.on_gif_stream_finished)
        self.gif_force_stop_timer = QTimer(self)
        self.gif_force_stop_timer.setSingleShot(True)
        self.gif_force_stop_timer.timeout.connect(self.force_stop_gif_stream_if_needed)
        self.gif_stream_active = False
        self.gif_stream_source_file: Path | None = None
        self.gif_stream_fps_override: int | None = None
        self.gif_stream_interpolate_override: bool | None = None
        self.gif_generated_hardware_mode = False
        self.gif_start_pending = False
        self.gif_start_wait_deadline = 0.0
        self.gif_kraken_io_paused = False
        self.gif_last_heartbeat = 0.0
        self.gif_user_stop_requested = False
        self.gif_safety_stop = False
        self.gif_stop_callbacks: list[Callable[[], None]] = []
        self.gif_cooling_transaction_active = False
        self.gif_cooling_window_open = False
        self.gif_cooling_waiting_resume = False
        self.gif_cooling_deadline = 0.0
        self.gif_cooling_action = ""
        self.gif_cooling_callback: Callable[[], None] | None = None
        self.gif_stdout_buffer = ""
        self.gif_watchdog_timer = QTimer(self)
        self.gif_watchdog_timer.setInterval(1000)
        self.gif_watchdog_timer.timeout.connect(self.check_gif_stream_watchdog)
        self.clock_active = False
        self.clock_text_hex = "ffffff"
        self.clock_background_hex = "10141c"
        self.clock_image_file = self.temp_dir / "lcd-clock.png"
        self.clock_render_key = ""
        self.clock_last_minute_upload_key = ""
        # 2.9.13 carries forward persistent one-time experimental notices across normal restarts.
        if not self.settings.contains("clock/experimental_warning_ack") and self.settings.value("clock/active", False, type=bool):
            self.settings.setValue("clock/experimental_warning_ack", True)
        if not self.settings.contains("lcd/keepalive_warning_ack") and self.settings.value("lcd/keepalive", False, type=bool):
            self.settings.setValue("lcd/keepalive_warning_ack", True)
        self.keepalive_warning_acknowledged = self.settings.value("lcd/keepalive_warning_ack", False, type=bool)
        self.clock_warning_acknowledged = self.settings.value("clock/experimental_warning_ack", False, type=bool)
        self.gif_warning_acknowledged = self.settings.value("gif/experimental_warning_ack", False, type=bool)
        self.hardware_lcd_warning_acknowledged = self.settings.value("hardware_lcd/experimental_warning_ack", False, type=bool)

        self.restore_settings()
        # Settings restoration repopulates controls and updates dynamic button
        # captions.  Capture the canonical German sources only after that work,
        # otherwise those late updates overwrite the selected language.
        self.capture_translation_sources()
        self.apply_ui_language(self.ui_language, persist=False, log_change=False)
        self.refresh_dynamic_translations()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.mark_clean_shutdown)
        self.setup_tray()
        self.enable_interaction_logging()
        self.log_message(f"START: Open Hardware Control {APP_VERSION} gestartet · NZXT-Kraken-Modul vollständig geladen")
        missing_dependencies = self.check_dependencies()
        if not missing_dependencies:
            self.initialize_devices()
        else:
            self.connection_label.setText("● Abhängigkeiten fehlen")
            self.connection_label.setObjectName("connectionPending")
            self.footer_status.setText("Bitte fehlende Abhängigkeiten installieren")
        QTimer.singleShot(0, self.refresh_display_info)
        QTimer.singleShot(0, self.refresh_openlinkhub_status)
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
        refresh_action.triggered.connect(self.refresh_all_devices)
        device_menu.addAction(refresh_action)
        safe_action = QAction("&Sicheres Profil anwenden", self)
        safe_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        safe_action.triggered.connect(self.apply_safe_profile)
        device_menu.addAction(safe_action)
        repair_action = QAction("&Berechtigungen reparieren", self)
        repair_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        repair_action.triggered.connect(self.repair_permissions)
        device_menu.addAction(repair_action)
        self.kraken_menu_actions = [safe_action, repair_action]

        view_menu = self.menuBar().addMenu("&Ansicht")
        tab_names = ("Übersicht", "Kühlung", "RGB", "LCD", "Einstellungen", "Profile", "Über", "Log", "OpenLinkHub")
        self.module_view_actions: dict[int, QAction] = {}
        for index, tab_name in enumerate(tab_names):
            action = QAction(tab_name, self)
            action.setShortcut(QKeySequence(f"Alt+{index + 1}"))
            action.triggered.connect(lambda _checked=False, i=index: self.tabs.setCurrentIndex(i))
            view_menu.addAction(action)
            if index in {1, 2, 3, 8}:
                self.module_view_actions[index] = action

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

    def capture_translation_sources(self) -> None:
        """Capture canonical German static UI texts so language switching is reversible."""
        self._i18n_widget_sources.clear()
        for label in self.findChildren(QLabel):
            self._i18n_widget_sources[label] = {"text": label.text()}
        for button in self.findChildren(QAbstractButton):
            self._i18n_widget_sources[button] = {"text": button.text()}
        for group in self.findChildren(QGroupBox):
            self._i18n_widget_sources[group] = {"title": group.title()}
        for line_edit in self.findChildren(QLineEdit):
            self._i18n_widget_sources[line_edit] = {"placeholder": line_edit.placeholderText()}
        for combo in self.findChildren(QComboBox):
            # Only translate combo boxes that carry stable item data. Several
            # legacy controls (e.g. profile categories and RGB modes) still use
            # currentText() as an internal identifier and must keep their German
            # canonical values until they are migrated to data-backed IDs.
            has_stable_data = any(combo.itemData(i) is not None for i in range(combo.count()))
            self._i18n_widget_sources[combo] = {
                "items": [combo.itemText(i) for i in range(combo.count())],
                "translate_items": has_stable_data,
            }
        for action in self.findChildren(QAction):
            self._i18n_widget_sources[action] = {"text": action.text()}
        for menu in self.findChildren(QMenu):
            self._i18n_widget_sources[menu] = {"title": menu.title()}
        if hasattr(self, "tabs"):
            self._i18n_widget_sources[self.tabs] = {"tabs": [self.tabs.tabText(i) for i in range(self.tabs.count())]}
        self._navigation_item_sources: list[tuple[QTreeWidgetItem, str]] = []
        if hasattr(self, "navigation"):
            nav_root = self.navigation.invisibleRootItem()
            pending = [nav_root.child(i) for i in range(nav_root.childCount())]
            while pending:
                item = pending.pop(0)
                self._navigation_item_sources.append((item, item.text(0)))
                pending.extend(item.child(i) for i in range(item.childCount()))
        for table in self.findChildren(QTableWidget):
            headers: list[str] = []
            for col in range(table.columnCount()):
                item = table.horizontalHeaderItem(col)
                headers.append(item.text() if item else "")
            if headers:
                self._i18n_widget_sources[table] = {"headers": headers}

    def tr_static(self, source: str) -> str:
        if self.ui_language == "de":
            return source
        return UI_TRANSLATIONS.get(self.ui_language, {}).get(source, source)

    def apply_ui_language(self, language: str, *, persist: bool = True, log_change: bool = True) -> None:
        if language not in SUPPORTED_UI_LANGUAGES:
            language = "de"
        self.ui_language = language
        translations = UI_TRANSLATIONS.get(language, {})
        for obj, source in list(self._i18n_widget_sources.items()):
            try:
                if isinstance(obj, QLabel) and "text" in source:
                    obj.setText(translations.get(str(source["text"]), str(source["text"])))
                elif isinstance(obj, QAbstractButton) and "text" in source:
                    obj.setText(translations.get(str(source["text"]), str(source["text"])))
                elif isinstance(obj, QGroupBox) and "title" in source:
                    obj.setTitle(translations.get(str(source["title"]), str(source["title"])))
                elif isinstance(obj, QLineEdit) and "placeholder" in source:
                    raw = str(source["placeholder"])
                    obj.setPlaceholderText(translations.get(raw, raw))
                elif isinstance(obj, QComboBox) and "items" in source and bool(source.get("translate_items", False)):
                    current_data = obj.currentData()
                    current_index = obj.currentIndex()
                    obj.blockSignals(True)
                    for i, raw in enumerate(source["items"]):
                        if i < obj.count():
                            obj.setItemText(i, translations.get(str(raw), str(raw)))
                    data_index = obj.findData(current_data)
                    obj.setCurrentIndex(data_index if data_index >= 0 else current_index)
                    obj.blockSignals(False)
                elif isinstance(obj, QAction) and "text" in source:
                    raw = str(source["text"])
                    obj.setText(translations.get(raw, raw))
                elif isinstance(obj, QMenu) and "title" in source:
                    raw = str(source["title"])
                    obj.setTitle(translations.get(raw, raw))
                elif obj is getattr(self, "tabs", None) and "tabs" in source:
                    for i, raw in enumerate(source["tabs"]):
                        if i < self.tabs.count():
                            self.tabs.setTabText(i, translations.get(str(raw), str(raw)))
                elif isinstance(obj, QTableWidget) and "headers" in source:
                    for col, raw in enumerate(source["headers"]):
                        item = obj.horizontalHeaderItem(col)
                        if item is not None:
                            item.setText(translations.get(str(raw), str(raw)))
            except RuntimeError:
                continue
        for item, raw in getattr(self, "_navigation_item_sources", []):
            try:
                item.setText(0, translations.get(raw, raw))
            except RuntimeError:
                continue
        if hasattr(self, "language_combo"):
            idx = self.language_combo.findData(language)
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(max(0, idx))
            self.language_combo.blockSignals(False)
        if persist:
            self.settings.setValue("ui/language", language)
            self.settings.sync()
        if log_change and hasattr(self, "log_view"):
            self.log_message(f"SPRACHE: Oberfläche = {SUPPORTED_UI_LANGUAGES[language]} ({language})")

    def on_language_changed(self, _index: int = -1) -> None:
        if not hasattr(self, "language_combo"):
            return
        language = str(self.language_combo.currentData() or "de")
        self.apply_ui_language(language)
        self.refresh_dynamic_translations()
        self.footer_status.setText(self.tr_static("Bereit"))

    def format_temperature(self, value_c: float | None, decimals: int = 1) -> str:
        symbol = temperature_symbol(self.temperature_unit)
        if value_c is None:
            return f"— {symbol}"
        return f"{celsius_to_display(float(value_c), self.temperature_unit):.{decimals}f} {symbol}"

    def safety_limits_explanation(self) -> str:
        return (
            "Diese Werte gelten ausschließlich für die Kraken-Flüssigkeit, nicht für die CPU. "
            f"Eine CPU-Tjmax von {self.format_temperature(89, 0)} oder {self.format_temperature(95, 0)} "
            "darf niemals als Wassergrenze übernommen werden. Im normalen Modus bleiben vorsichtige "
            "Einstellbereiche aktiv."
        )

    def cpu_profile_temperature_explanation(self) -> str:
        return (
            "Die auswählbaren CPU-Profile nutzen die von AMD veröffentlichte maximale Betriebstemperatur "
            f"(Tjmax). Ryzen 9000, Ryzen 8000G und normale Ryzen-7000-Modelle sind mit "
            f"{self.format_temperature(95, 0)} hinterlegt; Ryzen 7000 X3D mit "
            f"{self.format_temperature(89, 0)}. Die Kraken-Wassergrenzen bleiben davon unabhängig."
        )

    def display_temperature_int(self, value_c: float) -> int:
        return int(round(celsius_to_display(float(value_c), self.temperature_unit)))

    def temperature_c_from_display(self, value: float) -> int:
        return int(round(display_to_celsius(float(value), self.temperature_unit)))

    def safety_temperature_c(self, spin: QSpinBox) -> int:
        return self.temperature_c_from_display(spin.value())

    def set_safety_temperature_values_c(self, warning_c: int, critical_c: int) -> None:
        self.warning_temp.blockSignals(True)
        self.critical_temp.blockSignals(True)
        self.warning_temp.setValue(self.display_temperature_int(warning_c))
        self.critical_temp.setValue(self.display_temperature_int(critical_c))
        self.warning_temp.blockSignals(False)
        self.critical_temp.blockSignals(False)

    def on_temperature_unit_changed(self, _index: int = -1) -> None:
        if not hasattr(self, "temperature_unit_combo"):
            return
        new_unit = normalize_temperature_unit(self.temperature_unit_combo.currentData() or "c")
        old_unit = self.temperature_unit
        if new_unit == old_unit:
            return
        warning_c = display_to_celsius(self.warning_temp.value(), old_unit) if hasattr(self, "warning_temp") else 42.0
        critical_c = display_to_celsius(self.critical_temp.value(), old_unit) if hasattr(self, "critical_temp") else 50.0
        self.temperature_unit = new_unit
        self.apply_temperature_unit_to_controls(warning_c=warning_c, critical_c=critical_c)
        self.settings.setValue("display/temperature_unit", self.temperature_unit)
        self.settings.sync()
        self.log_message(f"TEMPERATUREINHEIT: Anzeige auf {temperature_symbol(self.temperature_unit)} umgestellt")
        if self.hardware_lcd_active:
            QTimer.singleShot(0, lambda: self.update_hardware_lcd(force=True))
        if self.gif_generated_hardware_mode:
            self.hardware_animation_status_label.setText("Temperatureinheit geändert · Hardwareanimation wird neu erzeugt …")
            self.stop_gif_stream(self.start_hardware_animation)
        else:
            self.refresh_status()

    def apply_temperature_unit_to_controls(
        self,
        *,
        warning_c: float | None = None,
        critical_c: float | None = None,
    ) -> None:
        if hasattr(self, "pump_curve_table"):
            for _group, table, editor in (self.pump_curve_table, self.fan_curve_table):
                editor.set_temperature_unit(self.temperature_unit)
                header = table.horizontalHeaderItem(0)
                if header is not None:
                    header.setText(f"CPU {temperature_symbol(self.temperature_unit)}")
                self.update_curve_table(table, editor.points())
        if hasattr(self, "warning_temp"):
            if warning_c is None:
                warning_c = 42.0
            if critical_c is None:
                critical_c = 50.0
            self.configure_expert_mode_controls(self.expert_mode_checkbox.isChecked())
            self.set_safety_temperature_values_c(round(warning_c), round(critical_c))
            suffix = f" {temperature_symbol(self.temperature_unit)}"
            self.warning_temp.setSuffix(suffix)
            self.critical_temp.setSuffix(suffix)
        if hasattr(self, "temp_card"):
            self.temp_card.set_value(self.format_temperature(self.current_liquid_temp))
            self.cpu_temp_card.set_value(self.format_temperature(self.current_cpu_temp))
            self.gpu_temp_card.set_value(self.format_temperature(self.current_gpu_temp))
        if hasattr(self, "cpu_profile_info"):
            self.update_cpu_profile_preview()
        if hasattr(self, "cpu_sources_text"):
            self.cpu_sources_text.setText(self.cpu_profile_temperature_explanation())

    def animated_hardware_live_summary(self, design_id: str | None = None) -> str:
        if design_id is None and hasattr(self, "hardware_animation_design_combo"):
            design_id = str(self.hardware_animation_design_combo.currentData() or "water_halo")
        parts: list[str] = []
        if design_id in {"cpu_orbit", "cpu_gpu_dual", "system_trio"}:
            parts.append(self.tr_static("CPU live"))
        if design_id in {"gpu_arc", "cpu_gpu_dual", "system_trio"}:
            parts.append(self.tr_static("GPU live"))
        if design_id in {"water_halo", "system_trio"}:
            parts.append(self.tr_static("Wasser letzter sicherer Wert"))
        return " · ".join(parts)

    def refresh_dynamic_translations(self) -> None:
        """Refresh captions whose values are assembled at runtime."""
        if hasattr(self, "pump_curve_table"):
            self.apply_temperature_unit_to_controls(
                warning_c=self.safety_temperature_c(self.warning_temp),
                critical_c=self.safety_temperature_c(self.critical_temp),
            )
        if hasattr(self, "clock_text_button"):
            self.clock_text_button.setText(f"{self.tr_static('Text')} · #{self.clock_text_hex}")
            self.clock_background_button.setText(f"{self.tr_static('Hintergrund')} · #{self.clock_background_hex}")
        if hasattr(self, "color1_button"):
            self.color1_button.setText(f"{self.tr_static('Farbe 1')} · #{self.color1_hex}")
            self.color2_button.setText(f"{self.tr_static('Farbe 2')} · #{self.color2_hex}")
        self.update_experimental_notice_status()
        if getattr(self, "hardware_lcd_active", False):
            QTimer.singleShot(0, lambda: self.update_hardware_lcd(force=True))
        if getattr(self, "gif_generated_hardware_mode", False):
            self.hardware_animation_status_label.setText(
                f"{self.tr_static('Hardwareanimation aktiv')} · {self.animated_hardware_live_summary()}"
            )

    def configure_accessibility(self) -> None:
        self.tabs.setAccessibleName("Seiten von Open Hardware Control")
        self.refresh_button.setAccessibleName("Alle unterstützten Geräte aktualisieren")
        self.pump_slider.setAccessibleName("Manuelle Pumpenleistung in Prozent")
        self.fan_slider.setAccessibleName("Manuelle Radiatorlüfterleistung in Prozent")
        self.warning_temp.setAccessibleName("Warnschwelle der Kraken-Wassertemperatur")
        self.critical_temp.setAccessibleName("Kritische Schwelle der Kraken-Wassertemperatur")
        self.cpu_profile_combo.setAccessibleName("AMD-AM5-Prozessorprofil")
        self.pump_curve_table[1].setAccessibleName("Tabelle der Pumpenkurve nach CPU-Temperatur")
        self.fan_curve_table[1].setAccessibleName("Tabelle der Radiatorlüfterkurve nach CPU-Temperatur")

    def show_keyboard_help(self) -> None:
        QMessageBox.information(
            self,
            "Tastaturbedienung",
            "F5: Geräte aktualisieren\n"
            "Alt+1 bis Alt+9: Hauptbereiche öffnen\n"
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
        title = QLabel("◈ Open Hardware Control by Frelidon")
        title.setObjectName("mainTitle")
        subtitle = QLabel("Gemeinsame Linux-Hardwarezentrale · NZXT Kraken · Corsair/OpenLinkHub")
        subtitle.setObjectName("subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        self.connection_label = QLabel("● Suche Geräte …")
        self.connection_label.setObjectName("connectionPending")
        self.refresh_button = QPushButton("↻ &Aktualisieren")
        self.refresh_button.clicked.connect(self.refresh_all_devices)
        header.addWidget(self.connection_label)
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.make_dashboard_tab(), "Übersicht")
        self.tabs.addTab(self.make_cooling_tab(), "Kühlung")
        self.tabs.addTab(self.make_rgb_tab(), "RGB")
        self.tabs.addTab(self.make_lcd_tab(), "LCD")
        self.tabs.addTab(self.make_settings_tab(), "Einstellungen")
        self.tabs.addTab(self.make_profiles_tab(), "Profile")
        self.tabs.addTab(self.make_about_tab(), "Über")
        self.tabs.addTab(self.make_log_tab(), "Log")
        self.tabs.addTab(self.make_openlinkhub_tab(), "OpenLinkHub")
        self.tabs.tabBar().hide()

        workspace = QHBoxLayout()
        workspace.setSpacing(12)
        self.navigation = self.make_navigation_sidebar()
        workspace.addWidget(self.navigation)
        workspace.addWidget(self.tabs, 1)
        root.addLayout(workspace, 1)
        self.update_navigation_visibility()

        footer = QHBoxLayout()
        self.footer_status = QLabel("Bereit")
        self.footer_status.setObjectName("footerStatus")
        footer.addWidget(self.footer_status)
        footer.addStretch()
        self.version_label = QLabel(f"{DISPLAY_NAME} {APP_VERSION}")
        self.version_label.setObjectName("muted")
        footer.addWidget(self.version_label)
        root.addLayout(footer)

    def make_navigation_sidebar(self) -> QTreeWidget:
        navigation = QTreeWidget()
        navigation.setObjectName("hardwareNavigation")
        navigation.setHeaderHidden(True)
        navigation.setMinimumWidth(210)
        navigation.setMaximumWidth(280)
        navigation.setIndentation(18)
        navigation.setAccessibleName("Hardware- und Hauptnavigation")

        def page_item(parent: QTreeWidgetItem | None, text: str, page: int) -> QTreeWidgetItem:
            item = QTreeWidgetItem(parent if parent is not None else navigation, [text])
            item.setData(0, Qt.ItemDataRole.UserRole, page)
            return item

        self.nav_overview = page_item(None, "Übersicht", 0)
        devices = QTreeWidgetItem(navigation, ["Geräte"])
        devices.setFlags(devices.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.nav_nzxt = QTreeWidgetItem(devices, ["NZXT Kraken 2023"])
        self.nav_nzxt.setFlags(self.nav_nzxt.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        page_item(self.nav_nzxt, "Kühlung", 1)
        page_item(self.nav_nzxt, "RGB", 2)
        page_item(self.nav_nzxt, "LCD", 3)
        self.nav_openlinkhub = page_item(devices, "Corsair · OpenLinkHub", 8)
        page_item(None, "Profile", 5)
        page_item(None, "Einstellungen", 4)
        diagnostics = QTreeWidgetItem(navigation, ["Diagnose"])
        diagnostics.setFlags(diagnostics.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        page_item(diagnostics, "Log", 7)
        page_item(diagnostics, "Über", 6)

        devices.setExpanded(True)
        self.nav_nzxt.setExpanded(True)
        diagnostics.setExpanded(False)
        navigation.setCurrentItem(self.nav_overview)
        navigation.currentItemChanged.connect(self.on_navigation_changed)
        self.tabs.currentChanged.connect(self.sync_navigation_to_page)
        return navigation

    def on_navigation_changed(self, current: QTreeWidgetItem | None, _previous: QTreeWidgetItem | None) -> None:
        if current is None:
            return
        page = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(page, int):
            self.tabs.setCurrentIndex(page)

    def sync_navigation_to_page(self, page: int) -> None:
        if not hasattr(self, "navigation"):
            return
        root = self.navigation.invisibleRootItem()
        pending = [root.child(i) for i in range(root.childCount())]
        while pending:
            item = pending.pop(0)
            if item.data(0, Qt.ItemDataRole.UserRole) == page and not item.isHidden():
                self.navigation.blockSignals(True)
                self.navigation.setCurrentItem(item)
                self.navigation.blockSignals(False)
                return
            pending.extend(item.child(i) for i in range(item.childCount()))

    def update_navigation_visibility(self) -> None:
        if not hasattr(self, "nav_nzxt"):
            return
        show_all = bool(self.show_undetected_modules)
        self.nav_nzxt.setHidden(not (show_all or self.devices_ready))
        self.nav_openlinkhub.setHidden(not (show_all or self.openlinkhub_detected))
        for widget in getattr(self, "nzxt_overview_widgets", []):
            widget.setVisible(show_all or self.devices_ready)
        if hasattr(self, "openlinkhub_overview_box"):
            self.openlinkhub_overview_box.setVisible(show_all or self.openlinkhub_detected)
        for page, action in getattr(self, "module_view_actions", {}).items():
            detected = self.devices_ready if page in {1, 2, 3} else self.openlinkhub_detected
            action.setVisible(show_all or detected)
        for action in getattr(self, "kraken_menu_actions", []):
            action.setVisible(show_all or self.devices_ready)
        current = self.navigation.currentItem()
        nzxt_hidden_current = current is not None and (current is self.nav_nzxt or current.parent() is self.nav_nzxt) and self.nav_nzxt.isHidden()
        if current is not None and (current.isHidden() or nzxt_hidden_current):
            self.navigation.setCurrentItem(self.nav_overview)

    def refresh_all_devices(self) -> None:
        self.initialize_devices()
        self.refresh_openlinkhub_status()

    def update_main_connection_summary(self) -> None:
        if not hasattr(self, "connection_label"):
            return
        modules: list[str] = []
        if self.devices_ready:
            modules.append("NZXT")
        if self.openlinkhub_detected:
            modules.append("OpenLinkHub")
        if modules:
            self.connection_label.setText("● Verbunden · " + " + ".join(modules))
            self.connection_label.setObjectName("connectionOk")
        else:
            self.connection_label.setText("● Keine unterstützte Hardware erkannt")
            self.connection_label.setObjectName("connectionBad")
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        if hasattr(self, "module_overview_label"):
            if modules:
                self.module_overview_label.setText("Erkannte Module: " + " · ".join(modules))
            else:
                self.module_overview_label.setText("Noch keine unterstützte Hardware erkannt.")

    def set_show_undetected_modules(self, enabled: bool) -> None:
        self.show_undetected_modules = bool(enabled)
        self.settings.setValue("navigation/show_undetected_modules", self.show_undetected_modules)
        self.settings.sync()
        self.update_navigation_visibility()

    def make_openlinkhub_tab(self) -> QWidget:
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        page.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        intro = QLabel(
            "Corsair-Hardware wird über den lokal laufenden OpenLinkHub-Dienst erkannt. Version 3.0.9 kann "
            "dokumentierte Gerätewerte direkt über die lokale API lesen und ändern. Für Mäuse stehen eigene "
            "anklickbare SVG-Schemata mit einem Belegungsdialog und einer fensterlokalen Makroaufnahme bereit. Es werden ausschließlich fest "
            "freigegebene Befehle an erkannte Geräte und Kanäle übertragen."
        )
        intro.setWordWrap(True)
        intro.setObjectName("infoText")
        layout.addWidget(intro)

        status_box = QGroupBox("OpenLinkHub-Status")
        status_layout = QGridLayout(status_box)
        self.openlinkhub_version_label = QLabel("Installation: wird geprüft …")
        self.openlinkhub_service_label = QLabel("Dienstkontext: wird geprüft …")
        self.openlinkhub_api_label = QLabel("Lokale API: wird geprüft …")
        self.openlinkhub_warning_label = QLabel("")
        self.openlinkhub_warning_label.setWordWrap(True)
        self.openlinkhub_warning_label.setObjectName("warningText")
        status_layout.addWidget(self.openlinkhub_version_label, 0, 0)
        status_layout.addWidget(self.openlinkhub_service_label, 0, 1)
        status_layout.addWidget(self.openlinkhub_api_label, 1, 0, 1, 2)
        status_layout.addWidget(self.openlinkhub_warning_label, 2, 0, 1, 2)
        layout.addWidget(status_box)

        actions = QGridLayout()
        self.openlinkhub_refresh_button = QPushButton("↻ OpenLinkHub aktualisieren")
        self.openlinkhub_refresh_button.clicked.connect(self.refresh_openlinkhub_status)
        dashboard = QPushButton("Web-Dashboard öffnen")
        dashboard.clicked.connect(self.open_openlinkhub_dashboard)
        self.openlinkhub_start_button = QPushButton("Benutzerdienst starten")
        self.openlinkhub_start_button.clicked.connect(lambda: self.run_openlinkhub_user_action("start"))
        self.openlinkhub_stop_button = QPushButton("Benutzerdienst stoppen")
        self.openlinkhub_stop_button.clicked.connect(lambda: self.run_openlinkhub_user_action("stop"))
        self.openlinkhub_restart_button = QPushButton("Benutzerdienst neu starten")
        self.openlinkhub_restart_button.clicked.connect(lambda: self.run_openlinkhub_user_action("restart"))
        self.openlinkhub_enable_button = QPushButton("Beim Login aktivieren")
        self.openlinkhub_enable_button.clicked.connect(lambda: self.run_openlinkhub_user_action("enable"))
        actions.addWidget(self.openlinkhub_refresh_button, 0, 0)
        actions.addWidget(dashboard, 0, 1)
        actions.addWidget(self.openlinkhub_enable_button, 0, 2)
        actions.addWidget(self.openlinkhub_start_button, 1, 0)
        actions.addWidget(self.openlinkhub_stop_button, 1, 1)
        actions.addWidget(self.openlinkhub_restart_button, 1, 2)
        actions.setColumnStretch(3, 1)
        layout.addLayout(actions)

        write_box = QGroupBox("Direkte Gerätesteuerung")
        write_layout = QVBoxLayout(write_box)
        self.openlinkhub_write_checkbox = QCheckBox(
            "Direkte OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren"
        )
        self.openlinkhub_write_checkbox.toggled.connect(self.set_openlinkhub_writes_enabled)
        self.openlinkhub_write_status_label = QLabel(
            "Gesperrt · erst aktivieren, wenn genau eine OpenLinkHub-Instanz läuft."
        )
        self.openlinkhub_write_status_label.setWordWrap(True)
        self.openlinkhub_write_status_label.setObjectName("warningText")
        write_layout.addWidget(self.openlinkhub_write_checkbox)
        write_layout.addWidget(self.openlinkhub_write_status_label)
        layout.addWidget(write_box)

        self.openlinkhub_devices_table = QTableWidget(0, 7)
        self.openlinkhub_devices_table.setHorizontalHeaderLabels(
            ["Gerät", "Kanal", "Temperatur", "Drehzahl", "Profil", "RGB", "Firmware"]
        )
        self.openlinkhub_devices_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.openlinkhub_devices_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.openlinkhub_devices_table.setAccessibleName("Von OpenLinkHub erkannte Corsair-Geräte")
        self.openlinkhub_devices_table.setMinimumHeight(230)
        layout.addWidget(self.openlinkhub_devices_table)

        layout.addWidget(self.make_openlinkhub_control_tabs())

        help_box = QGroupBox("Dienstkontext und Hilfe")
        help_layout = QVBoxLayout(help_box)
        help_text = QLabel(
            "Für Medienwiedergabe und virtuelles Audio muss OpenLinkHub im Benutzerkontext laufen. "
            "Open Hardware Control verändert oder entfernt den systemweiten Dienst nicht automatisch, damit niemals "
            "zwei OpenLinkHub-Instanzen gleichzeitig auf dieselbe Hardware zugreifen. Dasselbe Corsair-Gerät darf "
            "auch nicht gleichzeitig von OpenLinkHub und ckb-next gesteuert werden."
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        migration_help = QPushButton("Migrationshilfe: System → Benutzer")
        migration_help.clicked.connect(self.show_openlinkhub_migration_help)
        help_layout.addWidget(migration_help)
        links = QHBoxLayout()
        links.addWidget(self.make_external_link("Offizielles OpenLinkHub-Projekt", OPENLINKHUB_URL))
        links.addWidget(self.make_external_link("API-Dokumentation", OPENLINKHUB_API_DOCS_URL))
        links.addWidget(self.make_external_link("Offizielle Benutzerinstallation", OPENLINKHUB_USER_INSTALL_URL))
        links.addStretch()
        help_layout.addLayout(links)
        layout.addWidget(help_box)
        layout.addStretch()
        return page

    def make_openlinkhub_control_tabs(self) -> QWidget:
        self.openlinkhub_write_buttons: list[QPushButton] = []
        tabs = QTabWidget()
        tabs.setObjectName("openLinkHubControlTabs")

        cooling = QWidget()
        cooling_form = QFormLayout(cooling)
        self.openlinkhub_cooling_device_combo = QComboBox()
        self.openlinkhub_cooling_channel_combo = QComboBox()
        self.openlinkhub_temperature_profile_combo = QComboBox()
        self.openlinkhub_manual_speed = QSpinBox()
        self.openlinkhub_manual_speed.setRange(0, 100)
        self.openlinkhub_manual_speed.setValue(50)
        self.openlinkhub_manual_speed.setSuffix(" %")
        self.openlinkhub_cooling_device_combo.currentIndexChanged.connect(
            self.update_openlinkhub_cooling_channels
        )
        cooling_form.addRow("Corsair-Kühlgerät", self.openlinkhub_cooling_device_combo)
        cooling_form.addRow("Lüfter-/Pumpenkanal", self.openlinkhub_cooling_channel_combo)
        cooling_form.addRow("Vorhandenes Temperaturprofil", self.openlinkhub_temperature_profile_combo)
        profile_button = QPushButton("Temperaturprofil auf Kanal anwenden")
        profile_button.clicked.connect(self.apply_openlinkhub_speed_profile)
        cooling_form.addRow(profile_button)
        cooling_form.addRow("Manuelle Leistung", self.openlinkhub_manual_speed)
        manual_button = QPushButton("Manuellen Wert auf Kanal anwenden")
        manual_button.clicked.connect(self.apply_openlinkhub_manual_speed)
        cooling_form.addRow(manual_button)
        cooling_note = QLabel(
            "Profile werden von OpenLinkHub gelesen. Werte unter 30 % erfordern eine zusätzliche Bestätigung. "
            "Eine sichere, temperaturabhängige Kühlung bleibt empfohlen."
        )
        cooling_note.setWordWrap(True)
        cooling_note.setObjectName("warningText")
        cooling_form.addRow(cooling_note)
        self.openlinkhub_write_buttons.extend((profile_button, manual_button))
        tabs.addTab(cooling, "Kühlung")

        device = QWidget()
        device_form = QFormLayout(device)
        self.openlinkhub_general_device_combo = QComboBox()
        self.openlinkhub_general_channel_combo = QComboBox()
        self.openlinkhub_rgb_profile_combo = QComboBox()
        self.openlinkhub_channel_label = QLineEdit()
        self.openlinkhub_channel_label.setMaxLength(48)
        self.openlinkhub_channel_label.setPlaceholderText("z. B. Frontlüfter oben")
        self.openlinkhub_brightness = QSpinBox()
        self.openlinkhub_brightness.setRange(0, 100)
        self.openlinkhub_brightness.setValue(100)
        self.openlinkhub_brightness.setSuffix(" %")
        self.openlinkhub_lcd_rotation = QComboBox()
        for text, value in (("0°", 0), ("90°", 1), ("180°", 2), ("270°", 3)):
            self.openlinkhub_lcd_rotation.addItem(text, value)
        self.openlinkhub_general_device_combo.currentIndexChanged.connect(
            self.update_openlinkhub_general_controls
        )
        device_form.addRow("Corsair-Gerät", self.openlinkhub_general_device_combo)
        device_form.addRow("Kanal", self.openlinkhub_general_channel_combo)
        device_form.addRow("Vorhandenes RGB-Profil", self.openlinkhub_rgb_profile_combo)
        rgb_button = QPushButton("RGB-Profil auf Kanal anwenden")
        rgb_button.clicked.connect(self.apply_openlinkhub_rgb_profile)
        device_form.addRow(rgb_button)
        device_form.addRow("Neue Kanalbezeichnung", self.openlinkhub_channel_label)
        label_button = QPushButton("Kanalbezeichnung speichern")
        label_button.clicked.connect(self.apply_openlinkhub_label)
        device_form.addRow(label_button)
        device_form.addRow("Gerätehelligkeit", self.openlinkhub_brightness)
        brightness_button = QPushButton("Helligkeit anwenden")
        brightness_button.clicked.connect(self.apply_openlinkhub_brightness)
        device_form.addRow(brightness_button)
        device_form.addRow("LCD-Ausrichtung", self.openlinkhub_lcd_rotation)
        rotation_button = QPushButton("LCD-Ausrichtung anwenden")
        rotation_button.clicked.connect(self.apply_openlinkhub_lcd_rotation)
        device_form.addRow(rotation_button)
        self.openlinkhub_write_buttons.extend((rgb_button, label_button, brightness_button, rotation_button))
        tabs.addTab(device, "RGB und Gerät")

        mouse = QWidget()
        mouse_form = QFormLayout(mouse)
        self.openlinkhub_mouse_device_combo = QComboBox()
        self.openlinkhub_mouse_device_combo.currentIndexChanged.connect(
            self.update_openlinkhub_mouse_visual
        )
        mouse_form.addRow("Corsair-Maus", self.openlinkhub_mouse_device_combo)

        mouse_visual_group = QGroupBox("Grafische Tastenbelegung")
        mouse_visual_layout = QVBoxLayout(mouse_visual_group)
        mouse_visual_intro = QLabel(
            "Die Darstellung verwendet eigene schematische SVG-Zeichnungen und keine Herstellerfotos. "
            "Eine Taste in der Maus anklicken oder einen Listeneintrag doppelt anklicken, um die Funktion zu ändern."
        )
        mouse_visual_intro.setWordWrap(True)
        mouse_visual_layout.addWidget(mouse_visual_intro)
        mouse_visual_content = QHBoxLayout()
        self.openlinkhub_mouse_diagram = MouseSchematicWidget()
        self.openlinkhub_mouse_diagram.buttonSelected.connect(self.edit_openlinkhub_mouse_button_by_id)
        self.openlinkhub_mouse_assignment_table = QTableWidget(0, 3)
        self.openlinkhub_mouse_assignment_table.setHorizontalHeaderLabels(["Taste", "Position", "Funktion"])
        self.openlinkhub_mouse_assignment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.openlinkhub_mouse_assignment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.openlinkhub_mouse_assignment_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.openlinkhub_mouse_assignment_table.setMinimumWidth(390)
        self.openlinkhub_mouse_assignment_table.setAccessibleName("Aktuelle OpenLinkHub-Maustastenbelegung")
        self.openlinkhub_mouse_assignment_table.itemSelectionChanged.connect(
            self.sync_openlinkhub_mouse_table_selection
        )
        self.openlinkhub_mouse_assignment_table.itemDoubleClicked.connect(
            lambda _item: self.edit_selected_openlinkhub_mouse_button()
        )
        mouse_visual_content.addWidget(self.openlinkhub_mouse_diagram, 6)
        mouse_visual_content.addWidget(self.openlinkhub_mouse_assignment_table, 5)
        mouse_visual_layout.addLayout(mouse_visual_content)
        self.openlinkhub_mouse_assignment_status = QLabel(
            "Maus auswählen und OpenLinkHub aktualisieren, um Belegungen einzulesen."
        )
        self.openlinkhub_mouse_assignment_status.setWordWrap(True)
        self.openlinkhub_mouse_assignment_status.setObjectName("cardHint")
        mouse_visual_layout.addWidget(self.openlinkhub_mouse_assignment_status)
        mouse_assignment_buttons = QHBoxLayout()
        self.openlinkhub_mouse_edit_button = QPushButton("Ausgewählte Taste belegen")
        self.openlinkhub_mouse_edit_button.clicked.connect(self.edit_selected_openlinkhub_mouse_button)
        self.openlinkhub_macro_record_button = QPushButton("Tastaturmakro aufnehmen")
        self.openlinkhub_macro_record_button.clicked.connect(self.record_openlinkhub_keyboard_macro)
        mouse_assignment_buttons.addWidget(self.openlinkhub_mouse_edit_button)
        mouse_assignment_buttons.addWidget(self.openlinkhub_macro_record_button)
        mouse_assignment_buttons.addStretch()
        mouse_visual_layout.addLayout(mouse_assignment_buttons)
        mouse_form.addRow(mouse_visual_group)

        self.openlinkhub_mouse_dpi: list[QSpinBox] = []
        dpi_row = QWidget()
        dpi_layout = QHBoxLayout(dpi_row)
        dpi_layout.setContentsMargins(0, 0, 0, 0)
        for value in (800, 1200, 1600, 2400, 3200):
            field = QSpinBox()
            field.setRange(100, 30000)
            field.setSingleStep(100)
            field.setValue(value)
            field.setSuffix(" DPI")
            self.openlinkhub_mouse_dpi.append(field)
            dpi_layout.addWidget(field)
        self.openlinkhub_mouse_polling = QComboBox()
        for text, value in (("125 Hz", 1), ("250 Hz", 2), ("500 Hz", 3), ("1000 Hz", 4)):
            self.openlinkhub_mouse_polling.addItem(text, value)
        self.openlinkhub_mouse_sleep = QComboBox()
        for minutes in (1, 5, 10, 15, 30, 60):
            label = "1 Stunde" if minutes == 60 else f"{minutes} Minute{'n' if minutes != 1 else ''}"
            self.openlinkhub_mouse_sleep.addItem(label, minutes)
        self.openlinkhub_mouse_angle = QCheckBox("Angle Snapping aktivieren")
        self.openlinkhub_mouse_button_opt = QCheckBox("Tastenoptimierung aktivieren")
        mouse_settings_group = QGroupBox("Mauseinstellungen")
        mouse_settings_form = QFormLayout(mouse_settings_group)
        mouse_settings_form.addRow("Fünf DPI-Stufen", dpi_row)
        dpi_button = QPushButton("DPI-Stufen anwenden")
        dpi_button.clicked.connect(self.apply_openlinkhub_mouse_dpi)
        mouse_settings_form.addRow(dpi_button)
        mouse_settings_form.addRow("USB-Abfragerate", self.openlinkhub_mouse_polling)
        polling_button = QPushButton("Abfragerate anwenden")
        polling_button.clicked.connect(self.apply_openlinkhub_mouse_polling)
        mouse_settings_form.addRow(polling_button)
        mouse_settings_form.addRow("Ruhemodus", self.openlinkhub_mouse_sleep)
        sleep_button = QPushButton("Ruhemodus anwenden")
        sleep_button.clicked.connect(self.apply_openlinkhub_mouse_sleep)
        mouse_settings_form.addRow(sleep_button)
        mouse_settings_form.addRow(self.openlinkhub_mouse_angle)
        angle_button = QPushButton("Angle Snapping anwenden")
        angle_button.clicked.connect(self.apply_openlinkhub_mouse_angle)
        mouse_settings_form.addRow(angle_button)
        mouse_settings_form.addRow(self.openlinkhub_mouse_button_opt)
        button_opt = QPushButton("Tastenoptimierung anwenden")
        button_opt.clicked.connect(self.apply_openlinkhub_mouse_button_optimization)
        mouse_settings_form.addRow(button_opt)
        mouse_form.addRow(mouse_settings_group)
        self.openlinkhub_write_buttons.extend((
            self.openlinkhub_mouse_edit_button,
            self.openlinkhub_macro_record_button,
            dpi_button,
            polling_button,
            sleep_button,
            angle_button,
            button_opt,
        ))
        tabs.addTab(mouse, "Maus")

        keyboard = QWidget()
        keyboard_form = QFormLayout(keyboard)
        self.openlinkhub_keyboard_device_combo = QComboBox()
        self.openlinkhub_keyboard_user_profile = QLineEdit()
        self.openlinkhub_keyboard_user_profile.setMaxLength(48)
        self.openlinkhub_keyboard_user_profile.setPlaceholderText("Vorhandener OpenLinkHub-Profilname")
        self.openlinkhub_keyboard_profile = QLineEdit()
        self.openlinkhub_keyboard_profile.setMaxLength(48)
        self.openlinkhub_keyboard_profile.setPlaceholderText("Vorhandenes Tastaturprofil")
        self.openlinkhub_keyboard_layout = QLineEdit("DE")
        self.openlinkhub_keyboard_layout.setMaxLength(16)
        self.openlinkhub_keyboard_dial = QSpinBox()
        self.openlinkhub_keyboard_dial.setRange(0, 20)
        self.openlinkhub_keyboard_sleep = QSpinBox()
        self.openlinkhub_keyboard_sleep.setRange(0, 60)
        self.openlinkhub_keyboard_sleep.setValue(3)
        self.openlinkhub_keyboard_polling = QSpinBox()
        self.openlinkhub_keyboard_polling.setRange(1, 8)
        keyboard_form.addRow("Corsair-Tastatur", self.openlinkhub_keyboard_device_combo)
        keyboard_form.addRow("OpenLinkHub-Benutzerprofil", self.openlinkhub_keyboard_user_profile)
        user_profile_button = QPushButton("Benutzerprofil wechseln")
        user_profile_button.clicked.connect(self.apply_openlinkhub_keyboard_user_profile)
        keyboard_form.addRow(user_profile_button)
        keyboard_form.addRow("Tastaturprofil", self.openlinkhub_keyboard_profile)
        keyboard_profile_button = QPushButton("Tastaturprofil wechseln")
        keyboard_profile_button.clicked.connect(self.apply_openlinkhub_keyboard_profile)
        keyboard_form.addRow(keyboard_profile_button)
        keyboard_form.addRow("Tastaturbelegung", self.openlinkhub_keyboard_layout)
        layout_button = QPushButton("Tastaturbelegung anwenden")
        layout_button.clicked.connect(self.apply_openlinkhub_keyboard_layout)
        keyboard_form.addRow(layout_button)
        keyboard_form.addRow("Drehregler-Option · Gerätewert", self.openlinkhub_keyboard_dial)
        dial_button = QPushButton("Drehregler-Option anwenden")
        dial_button.clicked.connect(self.apply_openlinkhub_keyboard_dial)
        keyboard_form.addRow(dial_button)
        keyboard_form.addRow("Ruhemodus · Gerätewert", self.openlinkhub_keyboard_sleep)
        keyboard_sleep_button = QPushButton("Tastatur-Ruhemodus anwenden")
        keyboard_sleep_button.clicked.connect(self.apply_openlinkhub_keyboard_sleep)
        keyboard_form.addRow(keyboard_sleep_button)
        keyboard_form.addRow("Abfragerate · Gerätewert", self.openlinkhub_keyboard_polling)
        keyboard_polling_button = QPushButton("Tastatur-Abfragerate anwenden")
        keyboard_polling_button.clicked.connect(self.apply_openlinkhub_keyboard_polling)
        keyboard_form.addRow(keyboard_polling_button)
        keyboard_note = QLabel(
            "Layout-, Drehregler-, Ruhemodus- und Abfrageratenwerte unterscheiden sich je nach Tastatur. "
            "Die Gerätewerte bitte mit der OpenLinkHub-Geräteseite abgleichen."
        )
        keyboard_note.setWordWrap(True)
        keyboard_note.setObjectName("warningText")
        keyboard_form.addRow(keyboard_note)
        self.openlinkhub_write_buttons.extend(
            (user_profile_button, keyboard_profile_button, layout_button, dial_button, keyboard_sleep_button, keyboard_polling_button)
        )
        tabs.addTab(keyboard, "Tastatur")

        headset = QWidget()
        headset_form = QFormLayout(headset)
        self.openlinkhub_headset_device_combo = QComboBox()
        self.openlinkhub_headset_sleep = QSpinBox()
        self.openlinkhub_headset_sleep.setRange(0, 60)
        self.openlinkhub_headset_sleep.setValue(3)
        self.openlinkhub_headset_anc = QComboBox()
        self.openlinkhub_headset_anc.addItem("Aus", 0)
        self.openlinkhub_headset_anc.addItem("Aktive Geräuschunterdrückung", 1)
        self.openlinkhub_headset_anc.addItem("Transparenzmodus", 2)
        self.openlinkhub_headset_mute_indicator = QCheckBox("Mikrofon-Stummschaltanzeige aktivieren")
        self.openlinkhub_headset_sidetone = QCheckBox("Sidetone aktivieren")
        self.openlinkhub_headset_sidetone_value = QSpinBox()
        self.openlinkhub_headset_sidetone_value.setRange(0, 100)
        self.openlinkhub_headset_sidetone_value.setValue(50)
        self.openlinkhub_headset_sidetone_value.setSuffix(" %")
        headset_form.addRow("Corsair-Headset", self.openlinkhub_headset_device_combo)
        headset_form.addRow("Ruhemodus · Gerätewert", self.openlinkhub_headset_sleep)
        headset_sleep_button = QPushButton("Headset-Ruhemodus anwenden")
        headset_sleep_button.clicked.connect(self.apply_openlinkhub_headset_sleep)
        headset_form.addRow(headset_sleep_button)
        headset_form.addRow("Geräuschmodus", self.openlinkhub_headset_anc)
        anc_button = QPushButton("Geräuschmodus anwenden")
        anc_button.clicked.connect(self.apply_openlinkhub_headset_anc)
        headset_form.addRow(anc_button)
        headset_form.addRow(self.openlinkhub_headset_mute_indicator)
        mute_button = QPushButton("Stummschaltanzeige anwenden")
        mute_button.clicked.connect(self.apply_openlinkhub_headset_mute_indicator)
        headset_form.addRow(mute_button)
        headset_form.addRow(self.openlinkhub_headset_sidetone)
        sidetone_button = QPushButton("Sidetone-Modus anwenden")
        sidetone_button.clicked.connect(self.apply_openlinkhub_headset_sidetone)
        headset_form.addRow(sidetone_button)
        headset_form.addRow("Sidetone-Lautstärke", self.openlinkhub_headset_sidetone_value)
        sidetone_value_button = QPushButton("Sidetone-Lautstärke anwenden")
        sidetone_value_button.clicked.connect(self.apply_openlinkhub_headset_sidetone_value)
        headset_form.addRow(sidetone_value_button)
        headset_note = QLabel(
            "OpenLinkHub verlangt: ANC nur bei ausgeschaltetem Sidetone; Sidetone nur bei ausgeschaltetem ANC."
        )
        headset_note.setWordWrap(True)
        headset_note.setObjectName("warningText")
        headset_form.addRow(headset_note)
        self.openlinkhub_write_buttons.extend(
            (headset_sleep_button, anc_button, mute_button, sidetone_button, sidetone_value_button)
        )
        tabs.addTab(headset, "Headset")

        psu = QWidget()
        psu_form = QFormLayout(psu)
        self.openlinkhub_psu_device_combo = QComboBox()
        self.openlinkhub_psu_fan_mode = QSpinBox()
        self.openlinkhub_psu_fan_mode.setRange(0, 10)
        self.openlinkhub_psu_fan_mode.setValue(7)
        psu_form.addRow("Corsair-Netzteil", self.openlinkhub_psu_device_combo)
        psu_form.addRow("Lüftermodus · Gerätewert", self.openlinkhub_psu_fan_mode)
        psu_button = QPushButton("Netzteil-Lüftermodus anwenden")
        psu_button.clicked.connect(self.apply_openlinkhub_psu_speed)
        psu_form.addRow(psu_button)
        psu_note = QLabel(
            "Die Bedeutung des Lüftermodus ist netzteilabhängig. Nur einen in OpenLinkHub für das Modell angebotenen Gerätewert verwenden."
        )
        psu_note.setWordWrap(True)
        psu_note.setObjectName("warningText")
        psu_form.addRow(psu_note)
        self.openlinkhub_write_buttons.append(psu_button)
        tabs.addTab(psu, "Netzteil")
        self.update_openlinkhub_write_state()
        return tabs

    def set_openlinkhub_writes_enabled(self, enabled: bool) -> None:
        if enabled:
            reachable = bool(self.openlinkhub_last_status.get("api_reachable", False))
            context = str(self.openlinkhub_last_status.get("service_context", "absent"))
            if not reachable or context not in {"user", "system"}:
                self.openlinkhub_write_checkbox.blockSignals(True)
                self.openlinkhub_write_checkbox.setChecked(False)
                self.openlinkhub_write_checkbox.blockSignals(False)
                self.show_error(
                    "Direkte OpenLinkHub-Steuerung benötigt eine erreichbare lokale API und genau eine aktive Dienstinstanz."
                )
                self.update_openlinkhub_write_state()
                return
            answer = QMessageBox.warning(
                self,
                "Direkte OpenLinkHub-Steuerung aktivieren",
                "Die folgenden Regler ändern Corsair-Geräte unmittelbar über die lokale OpenLinkHub-API. "
                "Verwende nur Werte, die dein Gerät unterstützt, und lasse niemals zwei OpenLinkHub-Instanzen "
                "gleichzeitig laufen. Die Freigabe gilt nur für diese Programmsitzung.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.openlinkhub_write_checkbox.blockSignals(True)
                self.openlinkhub_write_checkbox.setChecked(False)
                self.openlinkhub_write_checkbox.blockSignals(False)
        self.update_openlinkhub_write_state()

    def update_openlinkhub_write_state(self) -> None:
        if not hasattr(self, "openlinkhub_write_buttons"):
            return
        reachable = bool(self.openlinkhub_last_status.get("api_reachable", False))
        context = str(self.openlinkhub_last_status.get("service_context", "absent"))
        checked = bool(getattr(self, "openlinkhub_write_checkbox", None) and self.openlinkhub_write_checkbox.isChecked())
        service_ok = context in {"user", "system"}
        allowed = reachable and service_ok and checked and not self.openlinkhub_write_busy
        for button in self.openlinkhub_write_buttons:
            button.setEnabled(allowed)
        if self.openlinkhub_write_busy:
            text = "Befehl wird übertragen … weitere Schreibzugriffe sind kurz gesperrt."
        elif context == "conflict":
            text = "Gesperrt · Benutzer- und Systemdienst laufen gleichzeitig."
        elif not service_ok:
            text = "Gesperrt · es läuft keine eindeutig erkannte einzelne OpenLinkHub-Dienstinstanz."
        elif not reachable:
            text = "Gesperrt · lokale OpenLinkHub-API ist nicht erreichbar."
        elif checked:
            text = "Freigegeben · dokumentierte Befehle können an erkannte Geräte übertragen werden."
        else:
            text = "Gesperrt · direkte Schreibzugriffe sind für diese Sitzung nicht aktiviert."
        if hasattr(self, "openlinkhub_write_status_label"):
            self.openlinkhub_write_status_label.setText(text)

    @staticmethod
    def _openlinkhub_combo_data(combo: QComboBox) -> dict[str, object] | None:
        data = combo.currentData()
        return data if isinstance(data, dict) else None

    @staticmethod
    def _openlinkhub_device_label(device: dict[str, object]) -> str:
        product = str(device.get("product") or "Corsair-Gerät")
        suffix = str(device.get("serial_suffix") or "")
        return f"{product} · …{suffix}" if suffix else product

    def populate_openlinkhub_control_widgets(self, devices: list[object]) -> None:
        clean_devices = [device for device in devices if isinstance(device, dict) and device.get("control_id")]
        combos = (
            self.openlinkhub_cooling_device_combo,
            self.openlinkhub_general_device_combo,
            self.openlinkhub_mouse_device_combo,
            self.openlinkhub_keyboard_device_combo,
            self.openlinkhub_headset_device_combo,
            self.openlinkhub_psu_device_combo,
        )
        previous = {
            id(combo): str((self._openlinkhub_combo_data(combo) or {}).get("control_id", ""))
            for combo in combos
        }
        for combo in combos:
            combo.blockSignals(True)
            combo.clear()
        for device in clean_devices:
            label = self._openlinkhub_device_label(device)
            if bool(device.get("has_speed")):
                self.openlinkhub_cooling_device_combo.addItem(label, device)
            self.openlinkhub_general_device_combo.addItem(label, device)
            if device.get("kind") == "mouse":
                self.openlinkhub_mouse_device_combo.addItem(label, device)
            if device.get("kind") == "keyboard":
                self.openlinkhub_keyboard_device_combo.addItem(label, device)
            if device.get("kind") == "headset":
                self.openlinkhub_headset_device_combo.addItem(label, device)
            if device.get("kind") == "psu":
                self.openlinkhub_psu_device_combo.addItem(label, device)
        for combo in combos:
            wanted = previous[id(combo)]
            if wanted:
                for index in range(combo.count()):
                    data = combo.itemData(index)
                    if isinstance(data, dict) and data.get("control_id") == wanted:
                        combo.setCurrentIndex(index)
                        break
            combo.blockSignals(False)

        self.openlinkhub_temperature_profile_combo.clear()
        profiles = self.openlinkhub_last_status.get("temperature_profiles", [])
        if isinstance(profiles, list):
            for profile in profiles:
                if isinstance(profile, str) and profile.strip():
                    self.openlinkhub_temperature_profile_combo.addItem(profile, profile)
        if self.openlinkhub_temperature_profile_combo.count() == 0:
            self.openlinkhub_temperature_profile_combo.addItem("Keine Profile gemeldet", "")
        self.update_openlinkhub_cooling_channels()
        self.update_openlinkhub_general_controls()
        self.update_openlinkhub_mouse_visual()
        self.update_openlinkhub_write_state()

    def update_openlinkhub_cooling_channels(self) -> None:
        combo = self.openlinkhub_cooling_channel_combo
        current = self._openlinkhub_combo_data(combo)
        current_id = int(current.get("channel_id", -999)) if current else -999
        combo.clear()
        device = self._openlinkhub_combo_data(self.openlinkhub_cooling_device_combo)
        channels = device.get("channels", []) if device else []
        if isinstance(channels, list):
            for channel in channels:
                if not isinstance(channel, dict) or not channel.get("has_speed"):
                    continue
                channel_id = int(channel.get("channel_id", 0))
                label = str(channel.get("label") or channel.get("name") or f"Kanal {channel_id}")
                combo.addItem(f"{label} · Kanal {channel_id}", channel)
                if channel_id == current_id:
                    combo.setCurrentIndex(combo.count() - 1)

    def update_openlinkhub_general_controls(self) -> None:
        device = self._openlinkhub_combo_data(self.openlinkhub_general_device_combo)
        combo = self.openlinkhub_general_channel_combo
        current = self._openlinkhub_combo_data(combo)
        current_id = int(current.get("channel_id", -999)) if current else -999
        combo.clear()
        channels = device.get("channels", []) if device else []
        if isinstance(channels, list):
            for channel in channels:
                if not isinstance(channel, dict):
                    continue
                channel_id = int(channel.get("channel_id", 0))
                label = str(channel.get("label") or channel.get("name") or f"Kanal {channel_id}")
                combo.addItem(f"{label} · Kanal {channel_id}", channel)
                if channel_id == current_id:
                    combo.setCurrentIndex(combo.count() - 1)
        self.openlinkhub_rgb_profile_combo.clear()
        profiles_by_device = self.openlinkhub_last_status.get("rgb_profiles", {})
        control_id = str(device.get("control_id", "")) if device else ""
        profiles = profiles_by_device.get(control_id, []) if isinstance(profiles_by_device, dict) else []
        if isinstance(profiles, list):
            for profile in profiles:
                if isinstance(profile, str) and profile.strip():
                    self.openlinkhub_rgb_profile_combo.addItem(profile, profile)
        if self.openlinkhub_rgb_profile_combo.count() == 0:
            self.openlinkhub_rgb_profile_combo.addItem("Keine RGB-Profile gemeldet", "")

    def update_openlinkhub_mouse_visual(self, _index: int | None = None) -> None:
        if not hasattr(self, "openlinkhub_mouse_assignment_table"):
            return
        device = self._openlinkhub_combo_data(self.openlinkhub_mouse_device_combo)
        table = self.openlinkhub_mouse_assignment_table
        table.blockSignals(True)
        table.setRowCount(0)
        if device is None:
            self.openlinkhub_mouse_assignment_status.setText(
                "Keine von OpenLinkHub erkannte Corsair-Maus ausgewählt."
            )
            self.openlinkhub_mouse_diagram.set_mouse("Corsair-Maus", [])
            table.blockSignals(False)
            return

        product = str(device.get("product") or "Corsair-Maus")
        assignments = device.get("mouse_assignments")
        if not isinstance(assignments, list):
            assignments = []
        rows = self.openlinkhub_mouse_diagram.set_mouse(product, assignments)
        self.openlinkhub_mouse_visual_rows = rows
        for row_data in rows:
            row = table.rowCount()
            table.insertRow(row)
            number_item = QTableWidgetItem(str(row_data.get("number") or "?"))
            number_item.setData(Qt.ItemDataRole.UserRole, str(row_data.get("id") or ""))
            number_item.setData(int(Qt.ItemDataRole.UserRole) + 1, row_data)
            position = str(row_data.get("reported_label") or row_data.get("label") or "Taste")
            function = str(row_data.get("function") or "Nicht belegt")
            table.setItem(row, 0, number_item)
            table.setItem(row, 1, QTableWidgetItem(position))
            table.setItem(row, 2, QTableWidgetItem(function))
        table.resizeColumnsToContents()
        if table.rowCount() > 0:
            table.selectRow(0)
        table.blockSignals(False)

        reported = sum(1 for row in rows if row.get("reported"))
        layout_title = str(mouse_schema(product).get("title") or "Gaming-Maus")
        if assignments:
            self.openlinkhub_mouse_assignment_status.setText(
                f"{product} · {layout_title} · {reported} von OpenLinkHub gemeldete Zuordnung(en) eingeblendet. "
                "Gemeldete Tasten lassen sich jetzt direkt anklicken und über die offizielle OpenLinkHub-API neu belegen."
            )
        else:
            self.openlinkhub_mouse_assignment_status.setText(
                f"{product} · {layout_title} · OpenLinkHub meldet in der aktuellen Geräteantwort keine "
                "auslesbaren Tastenbelegungen. Deshalb werden die üblichen Grundfunktionen der schematischen "
                "Tasten gezeigt. Ohne gemeldeten OpenLinkHub-Tastenindex wird keine unsichere Zuordnung geraten."
            )

    def edit_openlinkhub_mouse_button_by_id(self, button_id: str) -> None:
        self.select_openlinkhub_mouse_button(button_id)
        self.edit_selected_openlinkhub_mouse_button()

    def selected_openlinkhub_mouse_row(self) -> dict[str, object] | None:
        table = self.openlinkhub_mouse_assignment_table
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 else None
        data = item.data(int(Qt.ItemDataRole.UserRole) + 1) if item is not None else None
        return data if isinstance(data, dict) else None

    def openlinkhub_assignment_options(self, assignment_type: int) -> list[dict[str, object]]:
        catalogs = self.openlinkhub_last_status.get("input_catalogs", {})
        if not isinstance(catalogs, dict):
            catalogs = {}
        catalog_name = {1: "media", 3: "keyboard", 9: "mouse"}.get(assignment_type)
        if catalog_name:
            values = catalogs.get(catalog_name, [])
            return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
        if assignment_type == 10:
            values = self.openlinkhub_last_status.get("macros", [])
            return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
        return [{"id": 0, "name": "Keine Auswahl erforderlich"}]

    def edit_selected_openlinkhub_mouse_button(self) -> None:
        if not self.openlinkhub_write_checkbox.isChecked():
            self.show_error("Bitte zuerst die direkten OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren.")
            return
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        row = self.selected_openlinkhub_mouse_row()
        if selected is None or row is None:
            self.show_error("Bitte zuerst eine von OpenLinkHub gemeldete Maustaste auswählen.")
            return
        key_index = int(row.get("key_index", -1))
        if not row.get("reported") or key_index < 0:
            self.show_error(
                "OpenLinkHub meldet für diese schematische Taste keinen sicheren Tastenindex. "
                "Die App nimmt deshalb keine Zuordnung auf Verdacht vor."
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Maustaste belegen · {row.get('label', 'Taste')}")
        dialog.setModal(True)
        dialog.resize(540, 360)
        layout = QVBoxLayout(dialog)
        title = QLabel(
            f"<b>{row.get('reported_label') or row.get('label') or 'Taste'}</b> · "
            f"OpenLinkHub-Index {key_index} · aktuell: {row.get('function', 'nicht belegt')}"
        )
        title.setWordWrap(True)
        layout.addWidget(title)
        form = QFormLayout()
        default_box = QCheckBox("Originalfunktion des Geräts verwenden")
        default_box.setChecked(bool(row.get("default", False)))
        assignment_type = QComboBox()
        for text, value in (
            ("Keine Funktion", 0),
            ("Medientaste", 1),
            ("DPI-Funktion", 2),
            ("Tastaturtaste", 3),
            ("Sniper-DPI", 8),
            ("Maustaste", 9),
            ("Vorhandenes Makro", 10),
        ):
            assignment_type.addItem(text, value)
        type_index = assignment_type.findData(int(row.get("assignment_type", 0)))
        assignment_type.setCurrentIndex(max(0, type_index))
        assignment_value = QComboBox()
        press_and_hold = QCheckBox("Funktion beim Gedrückthalten wiederholen")
        press_and_hold.setChecked(bool(row.get("press_and_hold", False)))
        on_release = QCheckBox("Funktion erst beim Loslassen ausführen")
        on_release.setChecked(bool(row.get("on_release", False)))
        press_and_hold.toggled.connect(lambda enabled: on_release.setChecked(False) if enabled else None)
        on_release.toggled.connect(lambda enabled: press_and_hold.setChecked(False) if enabled else None)

        def populate_values() -> None:
            current = int(row.get("assignment_value", 0))
            assignment_value.clear()
            for option in self.openlinkhub_assignment_options(int(assignment_type.currentData() or 0)):
                value = int(option.get("id", 0))
                assignment_value.addItem(str(option.get("name") or f"Wert {value}"), value)
            value_index = assignment_value.findData(current)
            assignment_value.setCurrentIndex(value_index if value_index >= 0 else 0)
            has_values = assignment_value.count() > 0
            assignment_value.setEnabled(has_values and not default_box.isChecked())

        def update_enabled() -> None:
            enabled = not default_box.isChecked()
            assignment_type.setEnabled(enabled)
            assignment_value.setEnabled(enabled and assignment_value.count() > 0)
            press_and_hold.setEnabled(enabled)
            on_release.setEnabled(enabled)

        assignment_type.currentIndexChanged.connect(lambda _index: populate_values())
        default_box.toggled.connect(lambda _enabled: update_enabled())
        populate_values()
        update_enabled()
        form.addRow(default_box)
        form.addRow("Funktionsart", assignment_type)
        form.addRow("Taste oder Funktion", assignment_value)
        form.addRow(press_and_hold)
        form.addRow(on_release)
        layout.addLayout(form)
        note = QLabel(
            "Makros werden separat aufgenommen und erscheinen anschließend unter „Vorhandenes Makro“. "
            "Die linke Haupttaste kann von einzelnen OpenLinkHub-Geräten absichtlich geschützt sein."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Abbrechen")
        save = QPushButton("Belegung speichern")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not default_box.isChecked() and assignment_value.count() == 0:
            self.show_error("OpenLinkHub hat für diese Funktionsart keine auswählbaren Werte gemeldet.")
            return
        _device, payload = selected
        payload.update(
            key_index=key_index,
            default=int(default_box.isChecked()),
            press_and_hold=int(press_and_hold.isChecked()),
            on_release=int(on_release.isChecked()),
            assignment_type=int(assignment_type.currentData() or 0),
            assignment_value=int(assignment_value.currentData() or 0),
        )
        self.run_openlinkhub_write(
            "mouse-key-assignment",
            payload,
            f"Maustaste {row.get('label', key_index)} neu belegen",
        )

    def record_openlinkhub_keyboard_macro(self) -> None:
        if not self.openlinkhub_write_checkbox.isChecked():
            self.show_error("Bitte zuerst die direkten OpenLinkHub-Schreibzugriffe für diese Programmsitzung aktivieren.")
            return
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        catalog = self.openlinkhub_assignment_options(3)
        if not catalog:
            self.show_error("Der OpenLinkHub-Tastaturkatalog ist nicht verfügbar. Bitte OpenLinkHub aktualisieren.")
            return
        name, accepted = QInputDialog.getText(
            self,
            "Neues OpenLinkHub-Makro",
            "Makroname (maximal 48 Zeichen):",
        )
        name = name.strip()
        if not accepted or not name:
            return
        if len(name) < 3:
            self.show_error("Der OpenLinkHub-Makroname benötigt mindestens drei Zeichen.")
            return
        recorder = MacroRecorderDialog(catalog, self)
        if recorder.exec() != QDialog.DialogCode.Accepted or not recorder.steps:
            return
        _device, payload = selected
        payload.update(name=name[:48], steps=recorder.steps)
        self.run_openlinkhub_write(
            "macro-create-recording",
            payload,
            f"Tastaturmakro „{name[:48]}“ anlegen",
        )

    def select_openlinkhub_mouse_button(self, button_id: str) -> None:
        if not hasattr(self, "openlinkhub_mouse_assignment_table"):
            return
        table = self.openlinkhub_mouse_assignment_table
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) == button_id:
                table.selectRow(row)
                table.scrollToItem(item)
                return

    def sync_openlinkhub_mouse_table_selection(self) -> None:
        if not hasattr(self, "openlinkhub_mouse_assignment_table"):
            return
        row = self.openlinkhub_mouse_assignment_table.currentRow()
        item = self.openlinkhub_mouse_assignment_table.item(row, 0) if row >= 0 else None
        if item is not None:
            self.openlinkhub_mouse_diagram.select_button(str(item.data(Qt.ItemDataRole.UserRole) or ""))

    def run_openlinkhub_write(self, action: str, payload: dict[str, object], description: str) -> None:
        if self.openlinkhub_write_busy or not self.openlinkhub_write_checkbox.isChecked():
            self.show_error("Direkte OpenLinkHub-Schreibzugriffe sind derzeit gesperrt.")
            return
        helper = self.openlinkhub_helper_path()
        self.openlinkhub_write_busy = True
        self.update_openlinkhub_write_state()
        self.footer_status.setText(f"OpenLinkHub: {description} …")
        self.log_message(f"OPENLINKHUB-SCHREIBEN: {description} angefordert")

        def done(result: CommandResult) -> None:
            self.openlinkhub_write_busy = False
            try:
                response = json.loads(result.stdout)
            except json.JSONDecodeError:
                response = {"ok": False, "error": result.combined or "Ungültige API-Antwort"}
            if result.ok and isinstance(response, dict) and response.get("ok"):
                self.footer_status.setText(f"OpenLinkHub: {description} erfolgreich")
                self.log_message(f"OPENLINKHUB-SCHREIBEN: {description} erfolgreich bestätigt")
                QTimer.singleShot(400, self.refresh_openlinkhub_status)
            else:
                message = str(response.get("error") or response.get("message") or "OpenLinkHub-Befehl fehlgeschlagen")
                self.log_message(f"OPENLINKHUB-SCHREIBEN-FEHLER: {description} · {message}")
                self.show_error(message)
            self.update_openlinkhub_write_state()

        self.backend.run_async(
            [
                sys.executable, str(helper), "--write-action", action,
                "--payload-json", json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                "--api-url", OPENLINKHUB_API_URL,
            ],
            callback=done,
            timeout=12,
            log_command=False,
            log_output=False,
        )

    def _openlinkhub_device_payload(self, combo: QComboBox) -> tuple[dict[str, object], dict[str, object]] | None:
        device = self._openlinkhub_combo_data(combo)
        if not device or not device.get("control_id"):
            self.show_error("Bitte zuerst ein unterstütztes Corsair-Gerät auswählen.")
            return None
        return device, {"control_id": str(device["control_id"])}

    def apply_openlinkhub_speed_profile(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_cooling_device_combo)
        channel = self._openlinkhub_combo_data(self.openlinkhub_cooling_channel_combo)
        profile = str(self.openlinkhub_temperature_profile_combo.currentData() or "")
        if selected is None or channel is None or not profile:
            self.show_error("Bitte Kühlkanal und vorhandenes Temperaturprofil auswählen.")
            return
        _, payload = selected
        payload.update(channel_id=int(channel.get("channel_id", 0)), profile=profile)
        self.run_openlinkhub_write("speed-profile", payload, f"Temperaturprofil „{profile}“ anwenden")

    def apply_openlinkhub_manual_speed(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_cooling_device_combo)
        channel = self._openlinkhub_combo_data(self.openlinkhub_cooling_channel_combo)
        if selected is None or channel is None:
            self.show_error("Bitte zuerst einen Lüfter- oder Pumpenkanal auswählen.")
            return
        value = self.openlinkhub_manual_speed.value()
        if value < 30:
            answer = QMessageBox.warning(
                self,
                "Niedrige Corsair-Kühlleistung bestätigen",
                f"{value} % können für Pumpe oder Lüfter zu niedrig sein. Wirklich unmittelbar anwenden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        _, payload = selected
        payload.update(channel_id=int(channel.get("channel_id", 0)), value=value)
        self.run_openlinkhub_write("speed-manual", payload, f"manuellen Kühlwert {value} % anwenden")

    def apply_openlinkhub_rgb_profile(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_general_device_combo)
        channel = self._openlinkhub_combo_data(self.openlinkhub_general_channel_combo)
        profile = str(self.openlinkhub_rgb_profile_combo.currentData() or "")
        if selected is None or channel is None or not profile:
            self.show_error("Bitte Gerät, Kanal und vorhandenes RGB-Profil auswählen.")
            return
        _, payload = selected
        payload.update(channel_id=int(channel.get("channel_id", 0)), profile=profile)
        self.run_openlinkhub_write("rgb-profile", payload, f"RGB-Profil „{profile}“ anwenden")

    def apply_openlinkhub_label(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_general_device_combo)
        channel = self._openlinkhub_combo_data(self.openlinkhub_general_channel_combo)
        label = self.openlinkhub_channel_label.text().strip()
        if selected is None or channel is None or not label:
            self.show_error("Bitte Gerät, Kanal und eine neue Kanalbezeichnung angeben.")
            return
        _, payload = selected
        payload.update(
            channel_id=int(channel.get("channel_id", 0)),
            device_type=int(channel.get("device_type", 0)),
            label=label,
        )
        self.run_openlinkhub_write("label", payload, f"Kanal als „{label}“ benennen")

    def apply_openlinkhub_brightness(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_general_device_combo)
        if selected is None:
            return
        _, payload = selected
        value = self.openlinkhub_brightness.value()
        payload["brightness"] = value
        self.run_openlinkhub_write("brightness", payload, f"Gerätehelligkeit {value} % anwenden")

    def apply_openlinkhub_lcd_rotation(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_general_device_combo)
        channel = self._openlinkhub_combo_data(self.openlinkhub_general_channel_combo)
        if selected is None or channel is None:
            self.show_error("Bitte ein Corsair-LCD-Gerät und seinen Kanal auswählen.")
            return
        device, payload = selected
        if not device.get("has_lcd") and not channel.get("lcd_serial_present"):
            self.show_error("OpenLinkHub meldet für diesen Kanal kein LCD.")
            return
        payload.update(
            channel_id=int(channel.get("channel_id", 0)),
            rotation=int(self.openlinkhub_lcd_rotation.currentData() or 0),
        )
        self.run_openlinkhub_write("lcd-rotation", payload, "LCD-Ausrichtung anwenden")

    def apply_openlinkhub_mouse_dpi(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["stages"] = {str(index): field.value() for index, field in enumerate(self.openlinkhub_mouse_dpi)}
        self.run_openlinkhub_write("mouse-dpi", payload, "fünf Maus-DPI-Stufen anwenden")

    def apply_openlinkhub_mouse_polling(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["polling_rate"] = int(self.openlinkhub_mouse_polling.currentData())
        self.run_openlinkhub_write("mouse-polling", payload, "Maus-Abfragerate anwenden")

    def apply_openlinkhub_mouse_sleep(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["sleep_mode"] = int(self.openlinkhub_mouse_sleep.currentData())
        self.run_openlinkhub_write("mouse-sleep", payload, "Maus-Ruhemodus anwenden")

    def apply_openlinkhub_mouse_angle(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["enabled"] = int(self.openlinkhub_mouse_angle.isChecked())
        self.run_openlinkhub_write("mouse-angle-snapping", payload, "Maus-Angle-Snapping anwenden")

    def apply_openlinkhub_mouse_button_optimization(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_mouse_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["enabled"] = int(self.openlinkhub_mouse_button_opt.isChecked())
        self.run_openlinkhub_write("mouse-button-optimization", payload, "Maus-Tastenoptimierung anwenden")

    def apply_openlinkhub_keyboard_user_profile(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        profile = self.openlinkhub_keyboard_user_profile.text().strip()
        if selected is None or not profile:
            self.show_error("Bitte Tastatur und vorhandenes OpenLinkHub-Benutzerprofil angeben.")
            return
        _, payload = selected
        payload["profile"] = profile
        self.run_openlinkhub_write("keyboard-user-profile", payload, f"Benutzerprofil „{profile}“ wechseln")

    def apply_openlinkhub_keyboard_profile(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        profile = self.openlinkhub_keyboard_profile.text().strip()
        if selected is None or not profile:
            self.show_error("Bitte Tastatur und vorhandenes Tastaturprofil angeben.")
            return
        _, payload = selected
        payload["profile"] = profile
        self.run_openlinkhub_write("keyboard-profile", payload, f"Tastaturprofil „{profile}“ wechseln")

    def apply_openlinkhub_keyboard_layout(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        layout = self.openlinkhub_keyboard_layout.text().strip()
        if selected is None or not layout:
            self.show_error("Bitte Tastatur und eine unterstützte Tastaturbelegung angeben.")
            return
        _, payload = selected
        payload["layout"] = layout
        self.run_openlinkhub_write("keyboard-layout", payload, f"Tastaturbelegung „{layout}“ anwenden")

    def apply_openlinkhub_keyboard_dial(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["dial"] = self.openlinkhub_keyboard_dial.value()
        self.run_openlinkhub_write("keyboard-dial", payload, "Tastatur-Drehregler-Option anwenden")

    def apply_openlinkhub_keyboard_sleep(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["sleep_mode"] = self.openlinkhub_keyboard_sleep.value()
        self.run_openlinkhub_write("keyboard-sleep", payload, "Tastatur-Ruhemodus anwenden")

    def apply_openlinkhub_keyboard_polling(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_keyboard_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["polling_rate"] = self.openlinkhub_keyboard_polling.value()
        self.run_openlinkhub_write("keyboard-polling", payload, "Tastatur-Abfragerate anwenden")

    def apply_openlinkhub_headset_sleep(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_headset_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["sleep_mode"] = self.openlinkhub_headset_sleep.value()
        self.run_openlinkhub_write("headset-sleep", payload, "Headset-Ruhemodus anwenden")

    def apply_openlinkhub_headset_anc(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_headset_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["mode"] = int(self.openlinkhub_headset_anc.currentData())
        self.run_openlinkhub_write("headset-anc", payload, "Headset-Geräuschmodus anwenden")

    def apply_openlinkhub_headset_mute_indicator(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_headset_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["enabled"] = int(self.openlinkhub_headset_mute_indicator.isChecked())
        self.run_openlinkhub_write("headset-mute-indicator", payload, "Headset-Stummschaltanzeige anwenden")

    def apply_openlinkhub_headset_sidetone(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_headset_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["enabled"] = int(self.openlinkhub_headset_sidetone.isChecked())
        self.run_openlinkhub_write("headset-sidetone", payload, "Headset-Sidetone-Modus anwenden")

    def apply_openlinkhub_headset_sidetone_value(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_headset_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["value"] = self.openlinkhub_headset_sidetone_value.value()
        self.run_openlinkhub_write("headset-sidetone-value", payload, "Headset-Sidetone-Lautstärke anwenden")

    def apply_openlinkhub_psu_speed(self) -> None:
        selected = self._openlinkhub_device_payload(self.openlinkhub_psu_device_combo)
        if selected is None:
            return
        _, payload = selected
        payload["fan_mode"] = self.openlinkhub_psu_fan_mode.value()
        self.run_openlinkhub_write("psu-speed", payload, "Netzteil-Lüftermodus anwenden")

    @staticmethod
    def openlinkhub_helper_path() -> Path:
        return Path(__file__).with_name("openlinkhub_integration.py")

    def refresh_openlinkhub_status(self) -> None:
        if self.openlinkhub_status_busy or not hasattr(self, "openlinkhub_refresh_button"):
            return
        helper = self.openlinkhub_helper_path()
        if not helper.exists():
            self.openlinkhub_warning_label.setText("OpenLinkHub-Integrationsmodul fehlt.")
            return
        self.openlinkhub_status_busy = True
        self.openlinkhub_refresh_button.setEnabled(False)
        self.openlinkhub_api_label.setText("Lokale API: wird geprüft …")
        self.backend.run_async(
            [sys.executable, str(helper), "--status", "--api-url", OPENLINKHUB_API_URL],
            callback=self.on_openlinkhub_status,
            timeout=12,
            log_output=False,
        )

    def on_openlinkhub_status(self, result: CommandResult) -> None:
        self.openlinkhub_status_busy = False
        self.openlinkhub_refresh_button.setEnabled(True)
        try:
            status = json.loads(result.stdout)
            if not result.ok or not isinstance(status, dict) or status.get("ok") is False:
                raise ValueError(str(status.get("error", result.combined or "Statusabfrage fehlgeschlagen")))
        except (json.JSONDecodeError, ValueError) as exc:
            self.openlinkhub_detected = False
            self.openlinkhub_api_label.setText("Lokale API: nicht erreichbar")
            self.openlinkhub_warning_label.setText(f"OpenLinkHub-Status konnte nicht gelesen werden: {exc}")
            self.openlinkhub_overview_label.setText("Statusabfrage fehlgeschlagen")
            self.update_openlinkhub_write_state()
            self.update_navigation_visibility()
            self.update_main_connection_summary()
            return

        self.openlinkhub_last_status = status
        user = status.get("user_service", {}) if isinstance(status.get("user_service"), dict) else {}
        system = status.get("system_service", {}) if isinstance(status.get("system_service"), dict) else {}
        version = str(status.get("installed_version", "nicht erkannt"))
        context = str(status.get("service_context", "absent"))
        devices = status.get("devices", []) if isinstance(status.get("devices"), list) else []
        reachable = bool(status.get("api_reachable", False))
        self.openlinkhub_detected = (
            version != "nicht erkannt" or bool(user.get("available")) or bool(system.get("available")) or reachable
        )

        context_labels = {
            "user": "Benutzerkontext · aktiv",
            "system": "Systemkontext · aktiv",
            "conflict": "Konflikt · Benutzer- und Systemdienst aktiv",
            "user-stopped": "Benutzerkontext · gestoppt",
            "system-stopped": "Systemkontext · gestoppt",
            "absent": "kein Dienst erkannt",
        }
        self.openlinkhub_version_label.setText(f"Installation: {version}")
        self.openlinkhub_service_label.setText(f"Dienstkontext: {context_labels.get(context, context)}")
        self.openlinkhub_api_label.setText(
            f"Lokale API: {'erreichbar' if reachable else 'nicht erreichbar'} · {len(devices)} Gerät(e)"
        )
        self.openlinkhub_overview_label.setText(
            f"{context_labels.get(context, context)} · API {'online' if reachable else 'offline'} · {len(devices)} Gerät(e)"
        )
        if context == "system":
            warning = (
                "OpenLinkHub läuft im Systemkontext. Virtuelles Audio und Medienwiedergabe benötigen den "
                "Benutzerkontext. Nutze die offizielle Benutzerinstallation und deaktiviere anschließend den "
                "Systemdienst, bevor du den Benutzerdienst startest."
            )
        elif context == "conflict":
            warning = (
                "Beide OpenLinkHub-Dienste sind aktiv. Beende eine Instanz, damit nicht zwei Prozesse gleichzeitig "
                "auf Corsair-Hardware zugreifen."
            )
        elif not reachable and self.openlinkhub_detected:
            error = str(status.get("api_error", "")).strip()
            warning = "Die Installation wurde erkannt, aber die lokale API antwortet nicht."
            if error:
                warning += f" Technischer Hinweis: {error}"
        else:
            warning = ""
        self.openlinkhub_warning_label.setText(warning)
        user_active = user.get("active") == "active"
        user_available = bool(user.get("available"))
        self.openlinkhub_start_button.setEnabled(user_available and not user_active and context != "system")
        self.openlinkhub_stop_button.setEnabled(user_available and user_active)
        self.openlinkhub_restart_button.setEnabled(user_available and user_active)
        self.openlinkhub_enable_button.setEnabled(
            user_available and context not in {"system", "conflict"} and user.get("enabled") != "enabled"
        )
        self.populate_openlinkhub_devices(devices)
        self.populate_openlinkhub_control_widgets(devices)
        self.update_openlinkhub_write_state()
        self.update_navigation_visibility()
        self.update_main_connection_summary()
        self.log_message(
            f"OPENLINKHUB: Kontext={context} · API={'online' if reachable else 'offline'} · Geräte={len(devices)}"
        )

    def populate_openlinkhub_devices(self, devices: list[object]) -> None:
        table = self.openlinkhub_devices_table
        table.setRowCount(0)
        for raw_device in devices:
            if not isinstance(raw_device, dict):
                continue
            product = str(raw_device.get("product", "Corsair-Gerät"))
            serial_suffix = str(raw_device.get("serial_suffix", ""))
            if serial_suffix:
                product += f" · …{serial_suffix}"
            firmware = str(raw_device.get("firmware", "—"))
            channels = raw_device.get("channels") if isinstance(raw_device.get("channels"), list) else []
            rows = channels or [{}]
            for channel in rows:
                if not isinstance(channel, dict):
                    channel = {}
                name = str(channel.get("label") or channel.get("name") or "—")
                temperature = channel.get("temperature")
                rpm = channel.get("rpm")
                values = [
                    product,
                    name,
                    self.format_temperature(float(temperature)) if isinstance(temperature, (int, float)) else "—",
                    f"{rpm} rpm" if isinstance(rpm, (int, float)) else "—",
                    str(channel.get("profile") or "—"),
                    str(channel.get("rgb") or "—"),
                    firmware,
                ]
                row = table.rowCount()
                table.insertRow(row)
                for column, value in enumerate(values):
                    table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def run_openlinkhub_user_action(self, action: str) -> None:
        helper = self.openlinkhub_helper_path()
        self.footer_status.setText(f"OpenLinkHub-Benutzerdienst: {action} …")

        def done(result: CommandResult) -> None:
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError:
                payload = {"ok": False, "message": result.combined}
            if result.ok and payload.get("ok"):
                self.footer_status.setText("OpenLinkHub-Benutzerdienst aktualisiert")
                QTimer.singleShot(500, self.refresh_openlinkhub_status)
            else:
                self.show_error(str(payload.get("message") or payload.get("error") or "Dienstaktion fehlgeschlagen"))

        self.backend.run_async(
            [sys.executable, str(helper), "--user-service-action", action],
            callback=done,
            timeout=20,
            log_output=False,
        )

    def open_openlinkhub_dashboard(self) -> None:
        if not QDesktopServices.openUrl(QUrl(OPENLINKHUB_API_URL)):
            self.show_error("Das OpenLinkHub-Web-Dashboard konnte nicht im Standardbrowser geöffnet werden.")

    def show_openlinkhub_migration_help(self) -> None:
        QMessageBox.information(
            self,
            "OpenLinkHub in den Benutzerkontext migrieren",
            "Die Migration bleibt absichtlich manuell, weil dafür der systemweite Dienst mit Administratorrechten "
            "beendet werden muss.\n\n"
            "1. Falls keine eigenen OpenLinkHub-Profile vorhanden sind, kann die Profilsicherung übersprungen werden.\n"
            "2. Installiere den Benutzerdienst anhand der verlinkten offiziellen OpenLinkHub-Anleitung.\n"
            "3. Beende anschließend den Systemdienst:\n"
            "   sudo systemctl disable --now OpenLinkHub.service\n"
            "4. Aktiviere genau eine Benutzerinstanz:\n"
            "   systemctl --user enable --now OpenLinkHub.service\n"
            "5. Klicke danach in Open Hardware Control auf „OpenLinkHub aktualisieren“.\n\n"
            "Starte Benutzer- und Systemdienst niemals gleichzeitig."
        )

    def make_dashboard_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(14)

        self.module_overview_label = QLabel("Automatische Hardwareerkennung läuft …")
        self.module_overview_label.setWordWrap(True)
        self.module_overview_label.setObjectName("infoText")
        layout.addWidget(self.module_overview_label)

        self.nzxt_overview_box = QGroupBox("NZXT Kraken 2023")
        cards = QGridLayout(self.nzxt_overview_box)
        self.dashboard_cards_layout = cards
        cards.setSpacing(12)
        self.temp_card = ValueCard("Kraken-Wassertemperatur", self.format_temperature(None), "Sensor in der Pumpeneinheit")
        self.cpu_temp_card = ValueCard("CPU-Temperatur", self.format_temperature(None), "AMD k10temp · Tctl/Tdie")
        self.gpu_temp_card = ValueCard("GPU-Temperatur", self.format_temperature(None), "AMD amdgpu · dedizierte GPU bevorzugt")
        self.pump_card = ValueCard("Pumpe", "— rpm", "— % Leistung")
        self.fan_card = ValueCard("Radiatorlüfter", "— rpm", "— % Leistung")
        self.firmware_card = ValueCard("Firmware", "—", "LCD 240 × 240")
        cards.addWidget(self.temp_card, 0, 0)
        cards.addWidget(self.cpu_temp_card, 0, 1)
        cards.addWidget(self.gpu_temp_card, 0, 2)
        cards.addWidget(self.pump_card, 1, 0)
        cards.addWidget(self.fan_card, 1, 1)
        cards.addWidget(self.firmware_card, 1, 2)
        self.dashboard_cards = [self.temp_card, self.cpu_temp_card, self.gpu_temp_card, self.pump_card, self.fan_card, self.firmware_card]
        layout.addWidget(self.nzxt_overview_box)

        self.openlinkhub_overview_box = QGroupBox("Corsair · OpenLinkHub")
        openlinkhub_overview_layout = QHBoxLayout(self.openlinkhub_overview_box)
        self.openlinkhub_overview_label = QLabel("Dienst und lokale API werden geprüft …")
        self.openlinkhub_overview_label.setWordWrap(True)
        openlinkhub_overview_layout.addWidget(self.openlinkhub_overview_label, 1)
        open_openlinkhub = QPushButton("OpenLinkHub öffnen")
        open_openlinkhub.clicked.connect(lambda: self.tabs.setCurrentIndex(8))
        openlinkhub_overview_layout.addWidget(open_openlinkhub)
        layout.addWidget(self.openlinkhub_overview_box)

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
        self.nzxt_overview_widgets = [self.nzxt_overview_box, warning_box, quick]
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

        mode_box = QGroupBox("Aktiver Kühlmodus")
        mode_layout = QVBoxLayout(mode_box)
        self.cooling_mode_label = QLabel(
            "Zuletzt durch Kraken Control gesetzt: Pumpe unbekannt · Radiatorlüfter unbekannt"
        )
        self.cooling_mode_label.setWordWrap(True)
        self.cooling_mode_label.setObjectName("infoText")
        self.cooling_mode_hint = QLabel(
            "CPU-Kurven werden von Open Hardware Control laufend berechnet. Ein manueller Wert oder ein Schnellprofil "
            "deaktiviert die CPU-Kurve des jeweiligen Kanals."
        )
        self.cooling_mode_hint.setWordWrap(True)
        self.cooling_mode_hint.setObjectName("muted")
        mode_layout.addWidget(self.cooling_mode_label)
        mode_layout.addWidget(self.cooling_mode_hint)

        switch_title = QLabel("Betriebsart umschalten")
        switch_title.setObjectName("cardTitle")
        mode_layout.addWidget(switch_title)
        self.cooling_mode_buttons: dict[str, dict[str, QPushButton]] = {}
        for channel, label, curve_text in (
            ("pump", "Pumpe", "Pumpenkurve aktivieren"),
            ("fan", "Radiatorlüfter", "Lüfterkurve aktivieren"),
        ):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_label = QLabel(label)
            row_label.setMinimumWidth(145)
            manual_button = QPushButton("Manuell aktivieren")
            curve_button = QPushButton(curve_text)
            for button in (manual_button, curve_button):
                button.setObjectName("coolingModeButton")
                # A dynamic property is deliberately used instead of Qt's
                # checkable state.  A checkable button changes colour before
                # the asynchronous Kraken write has actually succeeded and can
                # visibly flicker when the confirmed state is restored.
                button.setProperty("coolingState", "inactive")
            manual_button.setToolTip(
                "Überträgt den aktuellen Prozentwert als feste Drehzahl und ersetzt damit die aktive Hardwarekurve dieses Kanals."
            )
            curve_button.setToolTip(
                "Aktiviert die angezeigte CPU-Temperaturkurve. Open Hardware Control liest den Linux-CPU-Sensor und "
                "überträgt nur bei einer relevanten Änderung einen neuen Prozentwert."
            )
            manual_button.clicked.connect(
                lambda _checked=False, ch=channel: self.switch_cooling_mode(ch, "manual")
            )
            curve_button.clicked.connect(
                lambda _checked=False, ch=channel: self.switch_cooling_mode(ch, "curve")
            )
            self.cooling_mode_buttons[channel] = {
                "manual": manual_button,
                "curve": curve_button,
            }
            row_layout.addWidget(row_label)
            row_layout.addWidget(manual_button)
            row_layout.addWidget(curve_button)
            row_layout.addStretch()
            mode_layout.addWidget(row)
        switch_hint = QLabel(
            "Der markierte Modus wurde zuletzt erfolgreich auf die Kraken übertragen. Das Bearbeiten eines Reglers oder "
            "einer Kurve ändert den aktiven Modus erst beim Anwenden."
        )
        switch_hint.setWordWrap(True)
        switch_hint.setObjectName("muted")
        mode_layout.addWidget(switch_hint)
        layout.addWidget(mode_box)
        layout.addWidget(manual)

        curves = QHBoxLayout()
        self.pump_curve_table = self.make_curve_group(
            "Pumpenkurve nach CPU-Temperatur",
            list(DEFAULT_PUMP_CURVE),
            "pump",
        )
        self.fan_curve_table = self.make_curve_group(
            "Lüfterkurve nach CPU-Temperatur",
            list(DEFAULT_FAN_CURVE),
            "fan",
        )
        curves.addWidget(self.pump_curve_table[0])
        curves.addWidget(self.fan_curve_table[0])
        layout.addLayout(curves)

        cpu_box = QGroupBox("AMD-AM5-Prozessorprofil für CPU-Kurven")
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
        self.cpu_profile_info = QLabel(
            "Die Profile setzen beide sichtbaren Kurven passend zur CPU-Temperatur. Die Wassertemperatur bleibt "
            "unabhängig davon als zusätzliche Sicherheitsüberwachung aktiv."
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
        self.safety_note = QLabel(self.safety_limits_explanation())
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
        editor.set_temperature_unit(self.temperature_unit)

        table = QTableWidget(len(defaults), 2)
        table.setHorizontalHeaderLabels([f"CPU {temperature_symbol(self.temperature_unit)}", "Leistung %"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(180)
        for row, (temp, duty) in enumerate(defaults):
            table.setItem(row, 0, QTableWidgetItem(str(self.display_temperature_int(temp))))
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
                table.setItem(row, 0, QTableWidgetItem(str(self.display_temperature_int(temp))))
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
                points.append((self.temperature_c_from_display(int(table.item(row, 0).text())), int(table.item(row, 1).text())))
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
        for channel in ("sync", "led1", "led2", "led3"):
            self.rgb_channel.addItem(channel, channel)
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
        for label in self.rgb_modes:
            self.rgb_mode.addItem(label, label)
        self.rgb_mode.currentIndexChanged.connect(self.update_rgb_controls)

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
        for label, value in (("Am langsamsten", "slowest"), ("Langsamer", "slower"), ("Normal", "normal"), ("Schneller", "faster"), ("Am schnellsten", "fastest")):
            self.rgb_speed.addItem(label, value)
        self.rgb_speed.setCurrentIndex(self.rgb_speed.findData("normal"))
        self.rgb_direction = QComboBox()
        self.rgb_direction.addItem("Vorwärts", "forward")
        self.rgb_direction.addItem("Rückwärts", "backward")

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
            "Einmalige GIF-Übertragung verwendet weiterhin nur das erste Bild. Der experimentelle Stream darunter "
            "emuliert Animation auf Firmware 2.x durch vorbereitete statische Frames über den liquidctl-Treiber."
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

        hardware_box = QGroupBox("Hardwaredaten-Designs · Live")
        hf = QFormLayout(hardware_box)
        self.hardware_design_combo = QComboBox()
        for design_id, label in DESIGNS:
            self.hardware_design_combo.addItem(label, design_id)

        self.hardware_color_preset_combo = QComboBox()
        for label, color in COLOR_PRESETS:
            self.hardware_color_preset_combo.addItem(f"{label} · {color}", color)
        self.hardware_color_preset_combo.addItem("Eigener Farbwert", "custom")
        self.hardware_color_preset_combo.currentIndexChanged.connect(self.apply_hardware_color_preset)

        hardware_color_row = QWidget()
        hcr = QHBoxLayout(hardware_color_row)
        hcr.setContentsMargins(0, 0, 0, 0)
        self.hardware_color_input = QLineEdit(DEFAULT_ACCENT)
        self.hardware_color_input.setMaxLength(7)
        self.hardware_color_input.setPlaceholderText("#00c8ff")
        self.hardware_color_input.setAccessibleName("LCD-Akzentfarbe als Hex-Code")
        self.hardware_color_input.editingFinished.connect(self.validate_hardware_color_input)
        self.hardware_color_button = QPushButton("Farbe auswählen")
        self.hardware_color_button.clicked.connect(self.pick_hardware_color)
        hcr.addWidget(self.hardware_color_input)
        hcr.addWidget(self.hardware_color_button)

        hardware_label_color_row = QWidget()
        hlcr = QHBoxLayout(hardware_label_color_row)
        hlcr.setContentsMargins(0, 0, 0, 0)
        self.hardware_label_color_input = QLineEdit(DEFAULT_LABEL_COLOR)
        self.hardware_label_color_input.setMaxLength(7)
        self.hardware_label_color_input.setPlaceholderText(DEFAULT_LABEL_COLOR)
        self.hardware_label_color_input.setAccessibleName("LCD-Farbe der Beschriftung als Hex-Code")
        self.hardware_label_color_input.editingFinished.connect(self.validate_hardware_text_colors)
        self.hardware_label_color_button = QPushButton("Farbe auswählen")
        self.hardware_label_color_button.clicked.connect(
            lambda: self.pick_hardware_text_color(self.hardware_label_color_input, "LCD-Beschriftungsfarbe auswählen")
        )
        hlcr.addWidget(self.hardware_label_color_input)
        hlcr.addWidget(self.hardware_label_color_button)

        hardware_value_color_row = QWidget()
        hvcr = QHBoxLayout(hardware_value_color_row)
        hvcr.setContentsMargins(0, 0, 0, 0)
        self.hardware_value_color_input = QLineEdit(DEFAULT_VALUE_COLOR)
        self.hardware_value_color_input.setMaxLength(7)
        self.hardware_value_color_input.setPlaceholderText(DEFAULT_VALUE_COLOR)
        self.hardware_value_color_input.setAccessibleName("LCD-Farbe der Temperaturzahl als Hex-Code")
        self.hardware_value_color_input.editingFinished.connect(self.validate_hardware_text_colors)
        self.hardware_value_color_button = QPushButton("Farbe auswählen")
        self.hardware_value_color_button.clicked.connect(
            lambda: self.pick_hardware_text_color(self.hardware_value_color_input, "LCD-Zahlenfarbe auswählen")
        )
        hvcr.addWidget(self.hardware_value_color_input)
        hvcr.addWidget(self.hardware_value_color_button)

        self.hardware_update_interval = QSpinBox()
        self.hardware_update_interval.setRange(5, 60)
        self.hardware_update_interval.setValue(7)
        self.hardware_update_interval.setSuffix(" s")
        self.hardware_update_interval.valueChanged.connect(self.update_hardware_lcd_interval)

        def hardware_scale_control(value: int) -> tuple[QWidget, QSlider, QLabel]:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(60, 200)
            slider.setValue(value)
            slider.setTickInterval(10)
            slider.setSingleStep(5)
            label = QLabel(f"{value} %")
            row_layout.addWidget(slider, 1)
            row_layout.addWidget(label)
            return row, slider, label

        hardware_label_scale_row, self.hardware_label_scale, self.hardware_label_scale_label = hardware_scale_control(125)
        hardware_value_scale_row, self.hardware_value_scale, self.hardware_value_scale_label = hardware_scale_control(125)
        self.hardware_label_scale.valueChanged.connect(self.update_hardware_text_scales)
        self.hardware_value_scale.valueChanged.connect(self.update_hardware_text_scales)

        hardware_buttons = QWidget()
        hb = QHBoxLayout(hardware_buttons)
        hb.setContentsMargins(0, 0, 0, 0)
        self.hardware_preview_button = QPushButton("Designvorschau")
        self.hardware_start_button = QPushButton("Live-Design starten")
        self.hardware_stop_button = QPushButton("Live-Design anhalten")
        self.hardware_stop_button.setEnabled(False)
        self.hardware_preview_button.clicked.connect(self.preview_hardware_lcd)
        self.hardware_start_button.clicked.connect(self.start_hardware_lcd_mode)
        self.hardware_stop_button.clicked.connect(self.stop_hardware_lcd_mode)
        hb.addWidget(self.hardware_preview_button)
        hb.addWidget(self.hardware_start_button)
        hb.addWidget(self.hardware_stop_button)

        self.hardware_lcd_status_label = QLabel(
            "Live-Hardwaredesign: bereit · Eisblau ist die Standardfarbe."
        )
        self.hardware_lcd_status_label.setWordWrap(True)
        self.hardware_lcd_status_label.setObjectName("infoText")
        hardware_safety_note = QLabel(
            "Experimentell: Das Live-Design rendert Wasser-, CPU- und GPU-Sensordaten als statisches 240×240-Bild "
            "und überträgt es im gewählten Intervall. Die Mindestzeit beträgt 5 Sekunden; Langzeitwirkungen häufiger "
            "LCD-Uploads sind nicht ausreichend bekannt."
        )
        hardware_safety_note.setWordWrap(True)
        hardware_safety_note.setObjectName("warningText")
        hf.addRow("Layout", self.hardware_design_combo)
        hf.addRow("Farbvoreinstellung", self.hardware_color_preset_combo)
        hf.addRow("Akzentfarbe für Ringe", hardware_color_row)
        hf.addRow("Farbe der Beschriftung", hardware_label_color_row)
        hf.addRow("Farbe der Temperaturzahl", hardware_value_color_row)
        hf.addRow("Größe der Beschriftung", hardware_label_scale_row)
        hf.addRow("Größe der Temperaturzahl", hardware_value_scale_row)
        hf.addRow("Aktualisierung", self.hardware_update_interval)
        hf.addRow(hardware_buttons)
        hf.addRow(self.hardware_lcd_status_label)
        hf.addRow(hardware_safety_note)
        controls.addWidget(hardware_box)

        animation_box = QGroupBox("Animierte Hardwaredaten · Ringe und Orbits")
        af = QFormLayout(animation_box)
        self.hardware_animation_design_combo = QComboBox()
        for design_id, label in DESIGNS:
            self.hardware_animation_design_combo.addItem(label, design_id)
        self.hardware_animation_fps_combo = QComboBox()
        self.hardware_animation_fps_combo.addItem("20 FPS · ruhig", 20)
        self.hardware_animation_fps_combo.addItem("25 FPS · flüssig · empfohlen", 25)
        self.hardware_animation_fps_combo.setCurrentIndex(1)

        animation_buttons = QWidget()
        ab = QHBoxLayout(animation_buttons)
        ab.setContentsMargins(0, 0, 0, 0)
        self.hardware_animation_preview_button = QPushButton("Animierte Vorschau erzeugen")
        self.hardware_animation_start_button = QPushButton("Hardwareanimation starten")
        self.hardware_animation_stop_button = QPushButton("Hardwareanimation anhalten")
        self.hardware_animation_stop_button.setEnabled(False)
        self.hardware_animation_preview_button.clicked.connect(self.preview_hardware_animation)
        self.hardware_animation_start_button.clicked.connect(self.start_hardware_animation)
        self.hardware_animation_stop_button.clicked.connect(self.stop_hardware_animation)
        ab.addWidget(self.hardware_animation_preview_button)
        ab.addWidget(self.hardware_animation_start_button)
        ab.addWidget(self.hardware_animation_stop_button)

        self.hardware_animation_status_label = QLabel(
            "Animierte Hardwaredaten: bereit · Farbe und Schriftgröße werden vom Live-Design übernommen."
        )
        self.hardware_animation_status_label.setWordWrap(True)
        self.hardware_animation_status_label.setObjectName("infoText")
        animation_note = QLabel(
            "Die Animation erzeugt einen nahtlosen GIF-Loop mit rotierenden Ringen, Lichtpunkten und Orbits. "
            "CPU- und GPU-Temperaturen werden währenddessen sicher über Linux-hwmon aktualisiert. Die Wassertemperatur "
            "bleibt der letzte sichere Kraken-Wert, weil Kraken-Statusabfragen während des exklusiven CAM-Raw-Streams "
            "pausiert bleiben. Aktive Pumpen- und Lüfterkurven lesen die CPU trotzdem weiter. Eine relevante "
            "Drehzahländerung verwendet die koordinierte Kurzpause und setzt danach denselben Framecache fort."
        )
        animation_note.setWordWrap(True)
        animation_note.setObjectName("warningText")
        af.addRow("Animationslayout", self.hardware_animation_design_combo)
        af.addRow("Animationsrate", self.hardware_animation_fps_combo)
        af.addRow(animation_buttons)
        af.addRow(self.hardware_animation_status_label)
        af.addRow(animation_note)
        controls.addWidget(animation_box)

        gif_box = QGroupBox("GIF-Animation · Firmware 2.x · Experimentell")
        gf = QFormLayout(gif_box)
        self.gif_fps_combo = QComboBox()
        self.populate_gif_fps_options(False)
        self.gif_advanced_checkbox = QCheckBox("Erweiterte GIF-Optionen anzeigen")
        self.gif_transport_combo = QComboBox()
        self.gif_transport_combo.addItem("CAM-Takt · 26,667 Hz · phasenstabil · Standard", "cam")
        self.gif_transport_combo.addItem("25,6 Hz · Sicher · bewährt", "safe")
        self.gif_transport_combo.setCurrentIndex(0)
        self.gif_transport_combo.setToolTip(
            "3.0.9 überträgt die vorbereiteten LCD-Phasen im NZXT-Modul streng in Reihenfolge mit CAM-nahem 26,667-Hz-Zieltakt. "
            "25,6 Hz bleibt als tearing-armer Diagnose- und Rückfallmodus erhalten."
        )
        self.gif_interpolate_checkbox = QCheckBox("Bewegungsglättung (Motion-Interpolation)")
        self.gif_interpolate_checkbox.setChecked(True)
        self.gif_interpolate_checkbox.setToolTip(
            "Schätzt die Bewegung zwischen benachbarten GIF-Frames und verschiebt die Bilder vor dem Überblenden. "
            "Anders als die alte Crossfade-Interpolation entstehen dadurch bei Scroll-/Balkenbewegungen echte Zwischenpositionen."
        )
        self.gif_start_button = QPushButton("GIF-Animation starten · Experimentell")
        self.gif_stop_button = QPushButton("Animation stoppen")
        self.gif_stop_button.setEnabled(False)
        self.gif_start_button.clicked.connect(self.start_gif_stream)
        self.gif_stop_button.clicked.connect(lambda: self.stop_gif_stream())
        gif_buttons = QWidget()
        gif_buttons_layout = QHBoxLayout(gif_buttons)
        gif_buttons_layout.setContentsMargins(0, 0, 0, 0)
        gif_buttons_layout.addWidget(self.gif_start_button)
        gif_buttons_layout.addWidget(self.gif_stop_button)
        self.gif_status_label = QLabel("GIF-Stream: bereit")
        self.gif_status_label.setWordWrap(True)
        self.gif_status_label.setObjectName("infoText")
        self.gif_loop_warning_label = QLabel()
        self.gif_loop_warning_label.setWordWrap(True)
        self.gif_loop_warning_label.setObjectName("warningText")
        self.gif_loop_warning_label.hide()
        gif_safety_note = QLabel(_GIF_SAFETY_TEXT)
        gif_safety_note.setWordWrap(True)
        gif_safety_note.setObjectName("warningText")
        gf.addRow("GIF-Bildrate", self.gif_fps_combo)
        gf.addRow(self.gif_advanced_checkbox)
        gf.addRow("LCD-Transport", self.gif_transport_combo)
        self.gif_transport_label = gf.labelForField(self.gif_transport_combo)
        gf.addRow(self.gif_interpolate_checkbox)
        gf.addRow(gif_buttons)
        gf.addRow(self.gif_status_label)
        gf.addRow(self.gif_loop_warning_label)
        gf.addRow(gif_safety_note)
        self.gif_advanced_checkbox.toggled.connect(self.set_gif_advanced_options_visible)
        self.set_gif_advanced_options_visible(False)
        controls.addWidget(gif_box)

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

        language_box = QGroupBox("Sprache")
        language_form = QFormLayout(language_box)
        self.language_combo = QComboBox()
        for code, label in SUPPORTED_UI_LANGUAGES.items():
            self.language_combo.addItem(label, code)
        language_index = self.language_combo.findData(self.ui_language)
        self.language_combo.setCurrentIndex(max(0, language_index))
        language_note = QLabel(
            "Menüs, Tabs, Schaltflächen, Gruppen und Auswahlfelder wechseln vollständig mit der gewählten Sprache. "
            "Rein technische Diagnosezeilen im Log bleiben für vergleichbare Hardwaretests teilweise Deutsch."
        )
        language_note.setWordWrap(True)
        language_note.setObjectName("muted")
        language_form.addRow("Sprache der Oberfläche", self.language_combo)
        language_form.addRow(language_note)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        layout.addWidget(language_box)

        temperature_box = QGroupBox("Temperatureinheit")
        temperature_form = QFormLayout(temperature_box)
        self.temperature_unit_combo = QComboBox()
        self.temperature_unit_combo.addItem("Celsius · °C", "c")
        self.temperature_unit_combo.addItem("Fahrenheit · °F", "f")
        temperature_index = self.temperature_unit_combo.findData(self.temperature_unit)
        self.temperature_unit_combo.setCurrentIndex(max(0, temperature_index))
        temperature_note = QLabel(
            "Die Einheit gilt für Dashboard, Statusmeldungen, Kurventabellen, Diagramme, Profile und die "
            "erzeugten LCD-Hardwaredesigns. Intern bleiben Kühlregeln und Schutzgrenzen unverändert in Celsius."
        )
        temperature_note.setWordWrap(True)
        temperature_note.setObjectName("muted")
        temperature_form.addRow("Temperaturen anzeigen in", self.temperature_unit_combo)
        temperature_form.addRow(temperature_note)
        self.temperature_unit_combo.currentIndexChanged.connect(self.on_temperature_unit_changed)
        layout.addWidget(temperature_box)

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
            f"Alle vierzehn Animationen werden prozedural aus dem GPL-Quellcode erzeugt. Version {APP_VERSION} rendert sie "
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
        self.autostart_minimized_checkbox = QCheckBox("Beim Systemstart minimiert/im Tray starten")
        self.autostart_minimized_checkbox.setChecked(True)
        self.autostart_minimized_checkbox.toggled.connect(
            lambda enabled: self.settings.setValue("app/autostart_minimized", enabled)
        )
        self.tray_checkbox = QCheckBox("Beim Schließen im Infobereich weiterlaufen")
        self.tray_checkbox.setChecked(True)
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 30)
        self.refresh_interval.setValue(3)
        self.refresh_interval.setSuffix(" s")
        self.refresh_interval.valueChanged.connect(self.update_status_interval)
        form.addRow(self.autostart_checkbox)
        form.addRow(self.autostart_minimized_checkbox)
        form.addRow(self.tray_checkbox)
        form.addRow("Status-Aktualisierung", self.refresh_interval)
        self.show_undetected_checkbox = QCheckBox("Nicht erkannte Geräte/Module anzeigen")
        self.show_undetected_checkbox.setChecked(self.show_undetected_modules)
        self.show_undetected_checkbox.toggled.connect(self.set_show_undetected_modules)
        form.addRow(self.show_undetected_checkbox)
        rerun_setup = QPushButton("Einrichtungsassistent erneut starten")
        rerun_setup.clicked.connect(lambda: self.maybe_show_setup_wizard(force=True))
        form.addRow(rerun_setup)
        layout.addWidget(app_box)

        experimental_box = QGroupBox("Experimentalhinweise und LCD-Sicherheit")
        experimental_layout = QVBoxLayout(experimental_box)
        self.experimental_notice_status = QLabel()
        self.experimental_notice_status.setWordWrap(True)
        self.experimental_notice_status.setObjectName("muted")
        reset_experimental = QPushButton("Experimentalhinweise zurücksetzen")
        reset_experimental.clicked.connect(self.reset_experimental_warnings)
        experimental_note = QLabel(
            "Bestätigte LCD-Hinweise werden dauerhaft gespeichert. Nach einem verdächtigen Absturz oder wiederholten "
            "LCD-Fehlern stoppt Kraken Control experimentelle LCD-Funktionen und versucht automatisch die Standardanzeige "
            "der Flüssigkeitstemperatur wiederherzustellen."
        )
        experimental_note.setWordWrap(True)
        experimental_note.setObjectName("warningText")
        experimental_layout.addWidget(self.experimental_notice_status)
        experimental_layout.addWidget(reset_experimental)
        experimental_layout.addWidget(experimental_note)
        layout.addWidget(experimental_box)
        self.update_experimental_notice_status()

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
            "Open Hardware Control erkennt DNF, APT, Pacman und Zypper und installiert nach Bestätigung nur "
            "die fest zugeordneten Pakete aus bereits eingerichteten Quellen. Es werden keine fremden "
            "Paketquellen hinzugefügt."
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
        for category in ("Gesamt", "Kühlung", "LCD", "RGB", "Design"):
            self.profile_category_combo.addItem(category, category)
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
            ("Open Hardware Control", APP_VERSION),
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

        project = QGroupBox("Open Hardware Control by Frelidon")
        pl = QVBoxLayout(project)
        title = QLabel(f"Open Hardware Control by Frelidon · Version {APP_VERSION}")
        title.setObjectName("mainTitle")
        description = QLabel(_ABOUT_SUMMARY_TEXT)
        description.setWordWrap(True)
        repo_notice = QLabel(
            "Diese interne Open-Hardware-Control-Version wird nicht automatisch veröffentlicht. Das bisherige "
            "öffentliche Kraken-Repository bleibt als Herkunft und Modulhistorie verlinkt: "
            "https://github.com/Frelidon/kraken-control-linux"
        )
        repo_notice.setWordWrap(True)
        repo_notice.setObjectName("muted")
        pl.addWidget(title)
        pl.addWidget(description)
        pl.addWidget(repo_notice)
        layout.addWidget(project)

        scope_box = QGroupBox("Projektumfang – gemeinsame Hardwarezentrale")
        scope_layout = QVBoxLayout(scope_box)
        scope_included = QLabel(
            "<b>Enthalten:</b> vollständiges NZXT-Kraken-Modul mit Kühlung, RGB und LCD sowie ein "
            "Corsair-/OpenLinkHub-Modul für Dienstkontext, lokale API, Geräte und Telemetrie."
        )
        scope_included.setWordWrap(True)
        scope_excluded = QLabel(
            "<b>Nicht enthalten:</b> Firmwareaktualisierungen, ungetestete Rohzugriffe sowie die AMD-Grafiksteuerung. "
            "Open Radeon Control Center bleibt bewusst eigenständig und wird nicht in dieses Projekt verschmolzen."
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
                "OpenLinkHub",
                "Lokaler Dienst und API für unterstützte Corsair-Hardware",
                ("API-Dokumentation", OPENLINKHUB_API_DOCS_URL),
                ("GitHub", OPENLINKHUB_URL),
                ("GPL-3.0", OPENLINKHUB_LICENSE_URL),
            ),
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
        self.cpu_sources_text = QLabel(self.cpu_profile_temperature_explanation())
        self.cpu_sources_text.setWordWrap(True)
        cpu_sources_layout.addWidget(self.cpu_sources_text)
        cpu_sources_layout.addWidget(self.make_external_link("AMD Prozessorspezifikationen", AMD_PROCESSOR_SPECS_URL))
        cpu_sources_layout.addWidget(self.make_external_link("Linux-k10temp-Dokumentation", K10TEMP_DOCS_URL))
        layout.addWidget(cpu_sources)

        license_box = QGroupBox("Lizenz von Open Hardware Control")
        ll = QHBoxLayout(license_box)
        license_text = QLabel(
            "Open Hardware Control by Frelidon steht unter GNU General Public License v3.0 oder später "
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
        self.settings.setValue("display/temperature_unit", self.temperature_unit)
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
            QPushButton#coolingModeButton[coolingState="active"] {{
                border: 2px solid #2fbf71;
                background: #238b55;
                color: #ffffff;
                font-weight: 750;
            }}
            QPushButton#coolingModeButton[coolingState="active"]:hover {{
                border-color: #59d992;
                background: #238b55;
                color: #ffffff;
            }}
            QPushButton#coolingModeButton[coolingState="active"]:pressed {{
                border-color: #8aefb7;
                background: #1b6f44;
                color: #ffffff;
            }}
            QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTableWidget:focus {{
                border: 2px solid {accent.name()};
            }}
            QTabWidget::pane {{ border: 1px solid palette(midlight); border-radius: 8px; background: {surface_rgba}; }}
            QScrollArea#settingsScrollArea {{ border: none; background: transparent; }}
            QScrollArea#settingsScrollArea > QWidget > QWidget {{ background: transparent; }}
            QWidget#settingsContent {{ background: transparent; }}
            QTabBar::tab {{ padding: 9px 16px; border-bottom: 2px solid transparent; }}
            QTabBar::tab:selected {{ font-weight: 700; color: {accent.name()}; border-bottom-color: {accent.name()}; }}
            QTreeWidget#hardwareNavigation {{
                border: 1px solid palette(midlight);
                border-radius: 10px;
                background: {surface_rgba};
                padding: 7px;
            }}
            QTreeWidget#hardwareNavigation::item {{ min-height: 30px; padding: 3px 7px; border-radius: 6px; }}
            QTreeWidget#hardwareNavigation::item:selected {{ background: {accent.name()}; color: white; font-weight: 700; }}
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
                and all(20 <= temp <= 100 for temp in temperatures)
                and all(0 <= duty <= 100 for duty in duties)
                and all(b > a for a, b in zip(temperatures, temperatures[1:]))
                and all(b >= a for a, b in zip(duties, duties[1:]))
                and points[-1][0] <= 100
                and points[-1][1] == 100
            )
            return points if valid else list(fallback)
        except (TypeError, ValueError):
            return list(fallback)

    @staticmethod
    def normalize_profile_cpu_curve(
        raw_points: object,
        fallback: list[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """Validate profile points and migrate old 20–50 °C liquid curves."""
        try:
            points = [(int(item[0]), int(item[1])) for item in raw_points]  # type: ignore[index, union-attr]
        except (TypeError, ValueError, IndexError):
            return list(fallback)
        temperatures = [temp for temp, _ in points]
        duties = [duty for _, duty in points]
        valid = (
            len(points) >= 2
            and all(20 <= temp <= 100 for temp in temperatures)
            and all(0 <= duty <= 100 for duty in duties)
            and all(b > a for a, b in zip(temperatures, temperatures[1:]))
            and all(b >= a for a, b in zip(duties, duties[1:]))
            and points[-1][1] == 100
        )
        # Profiles from 3.0.4 and older stored liquid curves ending near
        # 45–50 °C.  They must never be interpreted as CPU curves.
        if not valid or max(temperatures, default=0) <= 60:
            return list(fallback)
        return points

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

    def apply_profile_by_id(self, profile_id: str, *, startup: bool = False) -> None:
        profile = next((item for item in self.all_profiles() if str(item.get("id")) == profile_id), None)
        if profile is not None:
            self.current_profile_id = profile_id
            payload = profile.get("payload", {})
            if isinstance(payload, dict):
                self.apply_profile_payload(payload, str(profile.get("name", "Profil")), startup=startup)

    def profile_startup_changed(self) -> None:
        if hasattr(self, "profile_startup_combo"):
            self.settings.setValue("profiles/startup", self.profile_startup_combo.currentData() or "none")

    def apply_startup_profile(self) -> None:
        startup = str(self.settings.value("profiles/startup", "none"))
        if startup == "none" or self.pending_setup_profile:
            return
        profile_id = self.current_profile_id if startup == "last" else startup
        if profile_id:
            self.apply_profile_by_id(profile_id, startup=True)

    def startup_profile_has_lcd_payload(self) -> bool:
        startup = str(self.settings.value("profiles/startup", "none"))
        if startup == "none" or self.pending_setup_profile:
            return False
        profile_id = self.current_profile_id if startup == "last" else startup
        profile = next((item for item in self.all_profiles() if str(item.get("id")) == profile_id), None)
        if not isinstance(profile, dict):
            return False
        payload = profile.get("payload")
        return isinstance(payload, dict) and isinstance(payload.get("lcd"), dict)

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
        category_index = self.profile_category_combo.findData(str(profile.get("category", "Gesamt")))
        self.profile_category_combo.setCurrentIndex(max(0, category_index))
        profile_type = "Standardprofil" if profile.get("builtin") else "eigenes Profil"
        self.profile_status_label.setText(f"Ausgewählt: {profile.get('name')} · {profile_type}")

    def current_lcd_profile_mode(self) -> str:
        """Return the LCD mode that a newly saved profile must restore."""
        gif_active = self.gif_start_pending or self.is_gif_stream_running()
        if gif_active and self.gif_generated_hardware_mode:
            return "hardware_animation"
        if gif_active:
            return "gif"
        if self.hardware_lcd_active:
            return "hardware"
        if self.clock_active:
            return "clock"
        if self.keep_lcd_checkbox.isChecked() and self.prepared_lcd_file:
            return "image_keepalive"
        if self.prepared_lcd_file:
            return "image"
        return "unchanged"

    @staticmethod
    def resolve_profile_lcd_mode(lcd: dict[str, object]) -> str:
        """Normalize new and legacy profile LCD payloads.

        Profiles written by 3.0.5 did not store an explicit active GIF flag.
        A selected GIF in such an LCD profile is therefore migrated to the GIF
        mode; static files are migrated to a one-time image upload.
        """
        allowed = {
            "unchanged",
            "liquid",
            "image",
            "image_keepalive",
            "clock",
            "hardware",
            "hardware_animation",
            "gif",
        }
        explicit = str(lcd.get("mode", "")).strip().lower()
        if explicit in allowed:
            return explicit
        if bool(lcd.get("hardware_animation_active", False)):
            return "hardware_animation"
        if bool(lcd.get("hardware_active", False)):
            return "hardware"
        if bool(lcd.get("clock_active", False)):
            return "clock"
        if bool(lcd.get("keepalive", False)):
            return "image_keepalive"
        file_value = str(lcd.get("file", "")).strip()
        if file_value.lower().endswith(".gif"):
            return "gif"
        if file_value:
            return "image"
        return "unchanged"

    def startup_lcd_delay_ms(self, minimum_delay_ms: int = 0) -> int:
        """Delay LCD restoration until five seconds after desktop autostart."""
        minimum = max(0, int(minimum_delay_ms))
        if not self.launched_from_autostart:
            return minimum
        elapsed_ms = round((time.monotonic() - self.autostart_launch_monotonic) * 1000)
        return max(minimum, AUTOSTART_LCD_DELAY_MS - elapsed_ms)

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
                "warning": self.safety_temperature_c(self.warning_temp),
                "critical": self.safety_temperature_c(self.critical_temp),
                "expert": self.expert_mode_checkbox.isChecked(),
                "auto_max": self.auto_max_checkbox.isChecked(),
                "cpu_profile": self.cpu_profile_combo.currentData() or "",
                "curve_source": "cpu",
            }
        if category in {"Gesamt", "LCD"}:
            result["lcd"] = {
                "file": str(self.selected_lcd_file or ""),
                "mode": self.current_lcd_profile_mode(),
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
                "hardware_active": self.hardware_lcd_active,
                "hardware_design": self.hardware_design_combo.currentData(),
                "hardware_color": normalize_hex_color(self.hardware_color_input.text()) or DEFAULT_ACCENT,
                "hardware_interval": self.hardware_update_interval.value(),
                "hardware_label_color": normalize_hex_color(self.hardware_label_color_input.text()) or DEFAULT_LABEL_COLOR,
                "hardware_value_color": normalize_hex_color(self.hardware_value_color_input.text()) or DEFAULT_VALUE_COLOR,
                "hardware_label_scale": self.hardware_label_scale.value(),
                "hardware_value_scale": self.hardware_value_scale.value(),
                "temperature_unit": self.temperature_unit,
                "hardware_animation_design": self.hardware_animation_design_combo.currentData(),
                "hardware_animation_fps": self.hardware_animation_fps_combo.currentData(),
            }
        if category in {"Gesamt", "RGB"}:
            result["rgb"] = {
                "channel": self.rgb_channel.currentData(),
                "mode": self.rgb_mode.currentData(),
                "color1": self.color1_hex,
                "color2": self.color2_hex,
                "speed": self.rgb_speed.currentData(),
                "direction": self.rgb_direction.currentData(),
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
                "temperature_unit": self.temperature_unit,
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
        category = str(self.profile_category_combo.currentData() or "Gesamt")
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
        profile["category"] = str(self.profile_category_combo.currentData() or "Gesamt")
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

    def apply_profile_payload(self, payload: dict[str, object], name: str, *, startup: bool = False) -> None:
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
            requested_unit = normalize_temperature_unit(design.get("temperature_unit", self.temperature_unit))
            target_width = max(920, int(design.get("window_width", self.width())))
            target_height = max(680, int(design.get("window_height", self.height())))
            # A full profile also contains the former window state.  During a
            # desktop autostart this must never make the deliberately hidden
            # tray window visible or maximized again.
            if not (startup and self.should_start_minimized_from_autostart()):
                if bool(design.get("window_maximized", False)):
                    self.showMaximized()
                else:
                    self.showNormal()
                    self.resize(target_width, target_height)
            else:
                self.log_message(
                    "AUTOSTART: gespeicherter Fensterzustand des Startprofils übersprungen · "
                    "Hauptfenster bleibt im Tray."
                )
            self.sync_design_controls()
            self.apply_theme()
            if hasattr(self, "temperature_unit_combo"):
                unit_index = self.temperature_unit_combo.findData(requested_unit)
                self.temperature_unit_combo.setCurrentIndex(max(0, unit_index))

        rgb = payload.get("rgb")
        if isinstance(rgb, dict):
            channel_index = self.rgb_channel.findData(str(rgb.get("channel", self.rgb_channel.currentData())))
            self.rgb_channel.setCurrentIndex(max(0, channel_index))
            mode_index = self.rgb_mode.findData(str(rgb.get("mode", self.rgb_mode.currentData())))
            self.rgb_mode.setCurrentIndex(max(0, mode_index))
            self.color1_hex = str(rgb.get("color1", self.color1_hex))
            self.color2_hex = str(rgb.get("color2", self.color2_hex))
            self.color1_button.setText(f"Farbe 1 · #{self.color1_hex}")
            self.color2_button.setText(f"Farbe 2 · #{self.color2_hex}")
            speed_index = self.rgb_speed.findData(str(rgb.get("speed", self.rgb_speed.currentData())))
            self.rgb_speed.setCurrentIndex(max(0, speed_index))
            direction_index = self.rgb_direction.findData(str(rgb.get("direction", self.rgb_direction.currentData())))
            self.rgb_direction.setCurrentIndex(max(0, direction_index))
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
            hardware_design_index = self.hardware_design_combo.findData(str(lcd.get("hardware_design", self.hardware_design_combo.currentData())))
            self.hardware_design_combo.setCurrentIndex(max(0, hardware_design_index))
            self.hardware_color_input.setText(normalize_hex_color(str(lcd.get("hardware_color", self.hardware_color_input.text()))) or DEFAULT_ACCENT)
            self.validate_hardware_color_input(show_message=False)
            self.hardware_update_interval.setValue(int(lcd.get("hardware_interval", self.hardware_update_interval.value())))
            legacy_scale = int(lcd.get("hardware_text_scale", 125))
            self.hardware_label_color_input.setText(normalize_hex_color(str(lcd.get("hardware_label_color", self.hardware_label_color_input.text()))) or DEFAULT_LABEL_COLOR)
            self.hardware_value_color_input.setText(normalize_hex_color(str(lcd.get("hardware_value_color", self.hardware_value_color_input.text()))) or DEFAULT_VALUE_COLOR)
            self.hardware_label_scale.setValue(int(lcd.get("hardware_label_scale", legacy_scale)))
            self.hardware_value_scale.setValue(int(lcd.get("hardware_value_scale", legacy_scale)))
            profile_unit = normalize_temperature_unit(lcd.get("temperature_unit", self.temperature_unit))
            unit_index = self.temperature_unit_combo.findData(profile_unit)
            self.temperature_unit_combo.setCurrentIndex(max(0, unit_index))
            self.validate_hardware_text_colors(show_message=False)
            animation_design_index = self.hardware_animation_design_combo.findData(str(lcd.get("hardware_animation_design", self.hardware_animation_design_combo.currentData())))
            self.hardware_animation_design_combo.setCurrentIndex(max(0, animation_design_index))
            animation_fps_index = self.hardware_animation_fps_combo.findData(int(lcd.get("hardware_animation_fps", self.hardware_animation_fps_combo.currentData())))
            self.hardware_animation_fps_combo.setCurrentIndex(max(0, animation_fps_index))
            file_value = str(lcd.get("file", ""))
            if file_value and Path(file_value).exists():
                self.load_lcd_file(Path(file_value), quiet=True)
            requested_mode = self.resolve_profile_lcd_mode(lcd)
            experimental_modes = {"gif", "hardware_animation", "hardware", "clock", "image_keepalive"}
            if self.experimental_autostart_blocked and requested_mode in experimental_modes:
                self.log_message(
                    "SICHERHEIT: Experimenteller LCD-Anteil des Startprofils nach erkanntem Absturz übersprungen. "
                    "Manuelle Aktivierung bleibt nach erfolgreichem Sicherheitsfallback möglich."
                )
            else:
                lcd_action: Callable[[], None] | None = None
                if requested_mode == "hardware_animation":
                    lcd_action = self.start_hardware_animation
                elif requested_mode == "gif" and self.selected_lcd_file and self.selected_lcd_file.suffix.lower() == ".gif":
                    source_path = self.selected_lcd_file
                    lcd_action = lambda path=source_path: self.start_gif_stream(source_path=path)
                elif requested_mode == "hardware":
                    lcd_action = self.start_hardware_lcd_mode
                elif requested_mode == "clock":
                    lcd_action = self.start_clock_mode
                elif requested_mode == "image_keepalive" and self.prepared_lcd_file:
                    lcd_action = lambda: self.keep_lcd_checkbox.setChecked(True)
                elif requested_mode == "image" and self.prepared_lcd_file:
                    lcd_action = self.send_lcd_now
                elif requested_mode == "liquid":
                    lcd_action = self.show_liquid_screen
                if lcd_action is not None:
                    delay_ms = self.startup_lcd_delay_ms(1200) if startup else 1200
                    if startup and self.launched_from_autostart:
                        self.log_message(
                            f"LCD-START: Modus {requested_mode} aus Profil „{name}“ vorgemerkt · "
                            f"Start nach Desktop-Ruhezeit in {delay_ms / 1000:.1f} Sekunden."
                        )
                    QTimer.singleShot(delay_ms, lcd_action)

        cooling = payload.get("cooling")
        if isinstance(cooling, dict):
            self.load_profile_cooling_controls(cooling)
            if self.devices_ready:
                self.transmit_profile_cooling(cooling, name)
        self.save_settings()
        self.profile_status_label.setText(f"Aktiv: {name}")
        self.footer_status.setText(f"Profil „{name}“ angewendet")
        if startup:
            QTimer.singleShot(0, self.apply_initial_window_state)

    def load_profile_cooling_controls(self, cooling: dict[str, object]) -> None:
        self.pump_slider.setValue(int(cooling.get("pump", self.pump_slider.value())))
        self.fan_slider.setValue(int(cooling.get("fan", self.fan_slider.value())))
        pump_curve = self.normalize_profile_cpu_curve(
            cooling.get("pump_curve", self.pump_curve_table[2].points()),
            list(DEFAULT_PUMP_CURVE),
        )
        fan_curve = self.normalize_profile_cpu_curve(
            cooling.get("fan_curve", self.fan_curve_table[2].points()),
            list(DEFAULT_FAN_CURVE),
        )
        self.pump_curve_table[2].set_points(pump_curve)
        self.update_curve_table(self.pump_curve_table[1], pump_curve)
        self.fan_curve_table[2].set_points(fan_curve)
        self.update_curve_table(self.fan_curve_table[1], fan_curve)
        self.expert_mode_checkbox.setChecked(bool(cooling.get("expert", self.expert_mode_checkbox.isChecked())))
        self.set_safety_temperature_values_c(
            int(cooling.get("warning", self.safety_temperature_c(self.warning_temp))),
            int(cooling.get("critical", self.safety_temperature_c(self.critical_temp))),
        )
        self.auto_max_checkbox.setChecked(bool(cooling.get("auto_max", self.auto_max_checkbox.isChecked())))
        cpu_model = str(cooling.get("cpu_profile", ""))
        cpu_index = self.cpu_profile_combo.findData(cpu_model)
        if cpu_index >= 0:
            self.cpu_profile_combo.setCurrentIndex(cpu_index)
        self.cpu_curve_force_update = True

    def transmit_profile_cooling(self, cooling: dict[str, object], name: str) -> None:
        if self.defer_cooling_action_for_gif(
            "Kühlprofil",
            lambda: self.transmit_profile_cooling(cooling, name),
        ):
            return
        if self.kraken_write_busy:
            self.show_error("Die Kraken verarbeitet gerade noch einen anderen Befehl.")
            return
        requested_modes = {
            channel: str(cooling.get(f"{channel}_mode", "fixed"))
            for channel in ("pump", "fan")
        }
        needs_cpu = any(self.cooling_mode_kind(mode) == "curve" for mode in requested_modes.values())
        cpu_temp, sensor_label = self.read_amd_cpu_temperature()
        if needs_cpu and cpu_temp is None:
            self.show_error(
                "Das Profil enthält eine CPU-Temperaturkurve, aber der CPU-Sensor ist nicht verfügbar.\n\n"
                + sensor_label
            )
            return
        commands: list[tuple[str, list[str], str, str, int, bool]] = []
        for channel, label in (("pump", "Pumpe"), ("fan", "Radiatorlüfter")):
            mode = requested_modes[channel]
            if self.cooling_mode_kind(mode) == "curve":
                editor = self.pump_curve_table[2] if channel == "pump" else self.fan_curve_table[2]
                duty = self.quantize_curve_duty(self.interpolate_curve(editor.points(), float(cpu_temp)))
                duty = max(20 if channel == "pump" else 0, duty)
                args = Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)]
                detail = f"{duty} % · CPU {self.format_temperature(float(cpu_temp))} · Software-Regelung"
                commands.append((channel, args, "CPU-Temperaturkurve", detail, duty, True))
            else:
                duty = int(cooling.get(channel, 55))
                args = Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)]
                commands.append((channel, args, "Feste Drehzahl", f"{duty} %", duty, False))
        self.kraken_write_busy = True

        def run_index(index: int) -> None:
            if index >= len(commands):
                self.kraken_write_busy = False
                self.cpu_curve_last_write = time.monotonic()
                self.cpu_curve_force_update = False
                self.footer_status.setText(f"Kühlung aus Profil „{name}“ aktiv")
                QTimer.singleShot(700, self.refresh_status)
                return
            channel, args, mode, detail, duty, curve_controlled = commands[index]

            def done(result: CommandResult) -> None:
                if not result.ok:
                    self.kraken_write_busy = False
                    self.show_error(result.combined or f"Profil konnte {channel} nicht einstellen")
                    return
                self.set_cooling_mode(channel, mode, detail)
                self.cpu_curve_last_duties[channel] = duty if curve_controlled else None
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
        if not self.settings.contains("app/autostart_minimized"):
            self.settings.setValue("app/autostart_minimized", True)
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
        curve_source = str(self.settings.value("cooling/curve_source", "liquid"))
        curves_migrated = curve_source != "cpu"
        if curve_source == "cpu":
            pump_points = self.deserialize_curve(
                str(self.settings.value("cooling/pump_curve", "")),
                list(DEFAULT_PUMP_CURVE),
            )
            fan_points = self.deserialize_curve(
                str(self.settings.value("cooling/fan_curve", "")),
                list(DEFAULT_FAN_CURVE),
            )
        else:
            pump_points = list(DEFAULT_PUMP_CURVE)
            fan_points = list(DEFAULT_FAN_CURVE)
            self.settings.setValue("cooling/curve_source", "cpu")
            self.log_message(
                "KURVEN-MIGRATION 3.0.5: bisherige Wassertemperaturkurven durch sichere CPU-Temperaturkurven ersetzt."
            )
        self.pump_curve_table[2].set_points(pump_points)
        self.update_curve_table(self.pump_curve_table[1], pump_points)
        self.fan_curve_table[2].set_points(fan_points)
        self.update_curve_table(self.fan_curve_table[1], fan_points)
        self.expert_mode_checkbox.blockSignals(True)
        self.expert_mode_checkbox.setChecked(self.expert_mode_enabled)
        self.expert_mode_checkbox.blockSignals(False)
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
        self.configure_expert_mode_controls(
            self.expert_mode_enabled,
            warning_c=saved_warning,
            critical_c=saved_critical,
        )
        for channel, label in (("pump", "Pumpe"), ("fan", "Radiatorlüfter")):
            mode = str(self.settings.value(f"cooling/{channel}_mode", "unbekannt"))
            detail = str(self.settings.value(f"cooling/{channel}_mode_detail", "Noch nicht durch Kraken Control gesetzt"))
            if self.cooling_mode_kind(mode) == "curve":
                mode = "CPU-Temperaturkurve"
                detail = "Nach 3.0.5-Migration · Software-Regelung"
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
        self.update_cpu_profile_preview()
        if curves_migrated and self.selected_cpu_profile is not None:
            pump_points = list(self.selected_cpu_profile.pump_curve)
            fan_points = list(self.selected_cpu_profile.fan_curve)
            self.pump_curve_table[2].set_points(pump_points)
            self.update_curve_table(self.pump_curve_table[1], pump_points)
            self.fan_curve_table[2].set_points(fan_points)
            self.update_curve_table(self.fan_curve_table[1], fan_points)
            self.log_message(
                f"KURVEN-MIGRATION 3.0.5: CPU-Profil {self.selected_cpu_profile.model} auf beide Kurven übernommen."
            )
        self.lcd_interval.setValue(int(self.settings.value("lcd/interval", DEFAULT_LCD_INTERVAL)))
        security_migrated = self.settings.value("security/migrated_231", False, type=bool)
        previous_keepalive = self.settings.value("lcd/keepalive", False, type=bool)
        previous_clock = self.settings.value("clock/active", False, type=bool)
        previous_hardware_lcd = self.settings.value("hardware_lcd/active", False, type=bool)
        saved_keepalive = previous_keepalive if security_migrated else False
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(saved_keepalive)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(saved_keepalive)
        self.restore_lcd_checkbox.setChecked(self.settings.value("lcd/restore", False, type=bool))
        hardware_design = str(self.settings.value("hardware_lcd/design", "water_halo"))
        hardware_design_index = self.hardware_design_combo.findData(hardware_design)
        self.hardware_design_combo.setCurrentIndex(max(0, hardware_design_index))
        hardware_color = normalize_hex_color(str(self.settings.value("hardware_lcd/color", DEFAULT_ACCENT))) or DEFAULT_ACCENT
        self.hardware_color_input.setText(hardware_color)
        hardware_preset_index = self.hardware_color_preset_combo.findData(hardware_color)
        if hardware_preset_index < 0:
            hardware_preset_index = self.hardware_color_preset_combo.findData("custom")
        self.hardware_color_preset_combo.setCurrentIndex(max(0, hardware_preset_index))
        self.hardware_update_interval.setValue(int(self.settings.value("hardware_lcd/interval", 7)))
        legacy_hardware_scale = int(self.settings.value("hardware_lcd/text_scale", 125))
        self.hardware_label_color_input.setText(
            normalize_hex_color(str(self.settings.value("hardware_lcd/label_color", DEFAULT_LABEL_COLOR))) or DEFAULT_LABEL_COLOR
        )
        self.hardware_value_color_input.setText(
            normalize_hex_color(str(self.settings.value("hardware_lcd/value_color", DEFAULT_VALUE_COLOR))) or DEFAULT_VALUE_COLOR
        )
        self.hardware_label_scale.setValue(int(self.settings.value("hardware_lcd/label_scale", legacy_hardware_scale)))
        self.hardware_value_scale.setValue(int(self.settings.value("hardware_lcd/value_scale", legacy_hardware_scale)))
        self.validate_hardware_text_colors(show_message=False)
        self.update_hardware_lcd_interval()
        animation_design = str(self.settings.value("hardware_animation/design", "water_halo"))
        animation_design_index = self.hardware_animation_design_combo.findData(animation_design)
        self.hardware_animation_design_combo.setCurrentIndex(max(0, animation_design_index))
        animation_fps = int(self.settings.value("hardware_animation/fps", 25))
        animation_fps_index = self.hardware_animation_fps_combo.findData(animation_fps)
        self.hardware_animation_fps_combo.setCurrentIndex(max(0, animation_fps_index))
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
        if hasattr(self, "gif_fps_combo"):
            show_advanced = self.settings.value("gif/show_advanced", False, type=bool)
            self.gif_advanced_checkbox.blockSignals(True)
            self.gif_advanced_checkbox.setChecked(show_advanced)
            self.gif_advanced_checkbox.blockSignals(False)
            self.set_gif_advanced_options_visible(show_advanced)
            gif_fps = int(self.settings.value("gif/fps", 0))
            gif_idx = self.gif_fps_combo.findData(gif_fps)
            self.gif_fps_combo.setCurrentIndex(max(0, gif_idx))
            transport_mode = str(self.settings.value("gif/transport_mode", "cam") or "cam")
            if transport_mode not in {"cam", "safe"} or not show_advanced:
                transport_mode = "cam"
            transport_idx = self.gif_transport_combo.findData(transport_mode)
            self.gif_transport_combo.setCurrentIndex(max(0, transport_idx))
            self.gif_interpolate_checkbox.setChecked(
                self.settings.value("gif/interpolate", True, type=bool)
            )
        if self.lcd_recovery_required:
            self.clock_active = False
            self.hardware_lcd_active = False
            self.keep_lcd_checkbox.blockSignals(True)
            self.keep_lcd_checkbox.setChecked(False)
            self.keep_lcd_checkbox.blockSignals(False)
            self.set_keepalive_controls(False)
            self.settings.setValue("clock/active", False)
            self.settings.setValue("hardware_lcd/active", False)
            self.settings.setValue("lcd/keepalive", False)
            self.log_message(
                "SICHERHEIT: Unsauber beendete experimentelle LCD-Sitzung erkannt · "
                "automatischer Start blockiert · Rückkehr zur Flüssigkeitstemperatur vorgemerkt."
            )
        else:
            self.clock_active = previous_clock if security_migrated else False
            self.hardware_lcd_active = previous_hardware_lcd if security_migrated else False
            if self.hardware_lcd_active:
                self.clock_active = False
        if not security_migrated:
            self.settings.setValue("lcd/keepalive", False)
            self.settings.setValue("clock/active", False)
            self.settings.setValue("hardware_lcd/active", False)
            self.settings.setValue("security/migrated_231", True)
            if previous_keepalive or previous_clock or previous_hardware_lcd:
                self.log_message("Sicherheitsupdate 2.3.1: Wiederholte LCD-Uploads wurden vorsorglich deaktiviert.")
        self.tray_checkbox.setChecked(self.settings.value("app/tray", True, type=bool))
        self.refresh_interval.setValue(int(self.settings.value("app/refresh", 3)))
        self.autostart_checkbox.blockSignals(True)
        autostart_path = self.autostart_file()
        legacy_autostart_path = self.legacy_autostart_file()
        self.autostart_checkbox.setChecked(autostart_path.exists() or legacy_autostart_path.exists())
        self.autostart_checkbox.blockSignals(False)
        self.autostart_minimized_checkbox.setChecked(
            self.settings.value("app/autostart_minimized", True, type=bool)
        )
        if legacy_autostart_path.exists() and not autostart_path.exists():
            self.set_autostart(True)
            self.log_message("AUTOSTART: Kraken-Control-Autostart auf Open Hardware Control migriert.")
        if autostart_path.exists():
            try:
                autostart_text = autostart_path.read_text(encoding="utf-8")
            except OSError:
                autostart_text = ""
            if "--autostart" not in autostart_text:
                self.set_autostart(True)
                self.log_message("AUTOSTART: bestehender Desktop-Autostart auf minimierten Startmarker migriert.")
        if hasattr(self, "language_combo"):
            idx = self.language_combo.findData(self.ui_language)
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(max(0, idx))
            self.language_combo.blockSignals(False)
        self.update_experimental_notice_status()
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
        self.settings.setValue("display/temperature_unit", self.temperature_unit)
        self.settings.setValue("background/enabled", self.background_enabled)
        self.settings.setValue("background/theme", self.background_theme)
        self.settings.setValue("background/fps", self.background_fps)
        self.settings.setValue("background/intensity", self.background_intensity)
        self.settings.setValue("background/pause_inactive", self.background_pause_inactive)
        self.settings.setValue("profiles/current", self.current_profile_id)
        self.settings.setValue("safety/expert_mode", self.expert_mode_checkbox.isChecked())
        self.settings.setValue("safety/warning", self.safety_temperature_c(self.warning_temp))
        self.settings.setValue("safety/critical", self.safety_temperature_c(self.critical_temp))
        for channel in ("pump", "fan"):
            mode, detail = self.cooling_modes[channel]
            self.settings.setValue(f"cooling/{channel}_mode", mode)
            self.settings.setValue(f"cooling/{channel}_mode_detail", detail)
        self.settings.setValue("safety/auto_max", self.auto_max_checkbox.isChecked())
        self.settings.setValue("cpu/profile", self.cpu_profile_combo.currentData() or "")
        self.settings.setValue("cooling/curve_source", "cpu")
        self.settings.setValue("lcd/interval", self.lcd_interval.value())
        self.settings.setValue("lcd/keepalive", self.keep_lcd_checkbox.isChecked())
        self.settings.setValue("lcd/restore", self.restore_lcd_checkbox.isChecked())
        self.settings.setValue("lcd/file", str(self.selected_lcd_file or ""))
        self.settings.setValue("hardware_lcd/design", self.hardware_design_combo.currentData() or "water_halo")
        self.settings.setValue("hardware_lcd/color", normalize_hex_color(self.hardware_color_input.text()) or DEFAULT_ACCENT)
        self.settings.setValue("hardware_lcd/interval", self.hardware_update_interval.value())
        self.settings.setValue("hardware_lcd/active", self.hardware_lcd_active)
        self.settings.setValue("hardware_lcd/label_color", normalize_hex_color(self.hardware_label_color_input.text()) or DEFAULT_LABEL_COLOR)
        self.settings.setValue("hardware_lcd/value_color", normalize_hex_color(self.hardware_value_color_input.text()) or DEFAULT_VALUE_COLOR)
        self.settings.setValue("hardware_lcd/label_scale", self.hardware_label_scale.value())
        self.settings.setValue("hardware_lcd/value_scale", self.hardware_value_scale.value())
        self.settings.setValue("hardware_animation/design", self.hardware_animation_design_combo.currentData() or "water_halo")
        self.settings.setValue("hardware_animation/fps", self.hardware_animation_fps_combo.currentData() or 25)
        self.settings.setValue("clock/format", self.clock_format.currentData())
        self.settings.setValue("clock/show_date", self.clock_show_date.isChecked())
        self.settings.setValue("clock/font_size", self.clock_font_size.value())
        self.settings.setValue("clock/auto_resend", self.clock_auto_resend.isChecked())
        self.settings.setValue("clock/resend_interval", self.clock_resend_interval.value())
        self.settings.setValue("clock/text_color", self.clock_text_hex)
        self.settings.setValue("clock/background_color", self.clock_background_hex)
        self.settings.setValue("clock/active", self.clock_active)
        self.settings.setValue("gif/fps", int(self.gif_fps_combo.currentData() or 0))
        self.settings.setValue("gif/transport_mode", str(self.gif_transport_combo.currentData() or "cam"))
        self.settings.setValue("gif/interpolate", self.gif_interpolate_checkbox.isChecked())
        self.settings.setValue("gif/show_advanced", self.gif_advanced_checkbox.isChecked())
        self.settings.setValue("app/tray", self.tray_checkbox.isChecked())
        self.settings.setValue("app/autostart_minimized", self.autostart_minimized_checkbox.isChecked())
        self.settings.setValue("app/refresh", self.refresh_interval.value())
        self.settings.setValue("ui/language", self.ui_language)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.save_settings()
        if self.tray_checkbox.isChecked() and QSystemTrayIcon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
            self.tray.showMessage(DISPLAY_NAME, "Die Steuerung läuft im Infobereich weiter.")
        else:
            self.hardware_lcd_timer.stop()
            self.cpu_curve_timer.stop()
            self.shutdown_gif_stream_sync()
            self.restore_original_lcd_sync_on_quit()
            self.restore_safe_hardware_fallback_sync_on_quit()
            self.mark_clean_shutdown()
            self.backend.shutdown()
            event.accept()

    def show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self.save_settings()
        # Clear the crash marker before potentially blocking USB cleanup.  A
        # desktop logout may terminate the process shortly after SIGTERM.
        self.mark_clean_shutdown()
        self.status_timer.stop()
        self.cpu_curve_timer.stop()
        self.lcd_keepalive_timer.stop()
        self.clock_timer.stop()
        self.clock_keepalive_timer.stop()
        self.hardware_lcd_timer.stop()
        self.shutdown_gif_stream_sync()
        self.restore_original_lcd_sync_on_quit()
        self.restore_safe_hardware_fallback_sync_on_quit()
        self.backend.shutdown()
        QApplication.quit()

    def request_session_shutdown(self) -> None:
        """Handle an orderly desktop logout without leaving a crash marker."""
        if self.session_shutdown_requested:
            return
        self.session_shutdown_requested = True
        self.log_message("SYSTEMENDE: Sitzung wird beendet · LCD-Zustand und Einstellungen werden sauber gesichert.")
        self.quit_app()

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
        else:
            formats = {bytes(item).lower() for item in QImageReader.supportedImageFormats()}
            if b"svg" not in formats:
                missing.append("qt6-qtsvg")
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
                "✅ Alle benötigten Pakete sind installiert: liquidctl, PySide6, Qt SVG und Pillow."
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
        if self.kraken_command_blocked_by_gif("Geräteinitialisierung"):
            return
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
            self.cpu_curve_timer.start(CPU_CURVE_SAMPLE_MS)
            self.refresh_status()
            QTimer.singleShot(250, self.update_cpu_curve_control)
            self.test_access()
            QTimer.singleShot(900, self.apply_pending_setup_profile)
            QTimer.singleShot(1700, self.apply_startup_profile)
            startup_profile_owns_lcd = self.startup_profile_has_lcd_payload()
            startup_lcd_delay = self.startup_lcd_delay_ms(1500)
            if self.lcd_recovery_required:
                QTimer.singleShot(startup_lcd_delay, lambda: self.activate_lcd_safe_mode(
                    "Startwiederherstellung nach unsauberer experimenteller LCD-Sitzung",
                    preserve_recovery=True,
                ))
            elif startup_profile_owns_lcd:
                self.log_message(
                    "LCD-START: automatisches Startprofil aktiv · globale LCD-Wiederherstellung wird übersprungen, "
                    "damit Uhr/Bild/Fallback nicht gleichzeitig um das Display konkurrieren."
                )
            elif self.hardware_lcd_active:
                QTimer.singleShot(startup_lcd_delay, self.start_hardware_lcd_mode)
            elif self.clock_active:
                QTimer.singleShot(startup_lcd_delay, self.start_clock_mode)
            elif self.restore_lcd_checkbox.isChecked() and self.prepared_lcd_file:
                if self.keep_lcd_checkbox.isChecked():
                    QTimer.singleShot(startup_lcd_delay, lambda: self.toggle_lcd_keepalive(True))
                else:
                    QTimer.singleShot(startup_lcd_delay, self.send_lcd_now)
        else:
            self.set_disconnected("NZXT Kraken 2023 wurde nicht gefunden")
        self.update_navigation_visibility()
        self.update_main_connection_summary()

    def set_disconnected(self, message: str) -> None:
        if self.hardware_lcd_active or self.clock_active or self.is_gif_stream_running() or (hasattr(self, "keep_lcd_checkbox") and self.keep_lcd_checkbox.isChecked()):
            self.arm_lcd_recovery("Kraken-Verbindung während experimentellem LCD-Modus verloren")
        self.devices_ready = False
        self.cpu_curve_timer.stop()
        self.connection_label.setText("● Nicht verbunden")
        self.connection_label.setObjectName("connectionBad")
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        self.footer_status.setText(message)
        self.health_label.setText(message)
        self.health_label.setObjectName("healthCritical")
        self.update_navigation_visibility()
        self.update_main_connection_summary()

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
        return read_amd_cpu_temperature()

    @staticmethod
    def read_amd_gpu_temperature(drm_root: Path = Path("/sys/class/drm")) -> tuple[float | None, str]:
        return read_amd_gpu_temperature(drm_root)

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
            self.log_message(f"CPU: {match.model} automatisch erkannt · Familie {match.family} · Tjmax {self.format_temperature(match.tjmax, 0)}")
            if not silent:
                self.footer_status.setText(f"CPU erkannt: {match.model}")

    def update_cpu_profile_preview(self) -> None:
        model = self.cpu_profile_combo.currentData()
        profile = CPU_PROFILE_BY_MODEL.get(model)
        self.selected_cpu_profile = profile
        if profile is None:
            self.cpu_profile_info.setText(
                "Bitte einen AM5-Prozessor auswählen. Ohne Profil gilt die sichere Standard-CPU-Kurve mit "
                f"100 % bei {self.format_temperature(90, 0)}."
            )
            return
        self.cpu_profile_info.setText(
            f"{profile.model} · {profile.family} · AMD Tjmax {self.format_temperature(profile.tjmax, 0)} · "
            f"CPU-Kurven verstärken ab {self.format_temperature(profile.boost_temp, 0)} · "
            f"100 % ab {self.format_temperature(profile.critical_temp, 0)}. "
            f"Wassersicherheit weiterhin separat bei {self.format_temperature(42, 0)}/{self.format_temperature(50, 0)}."
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
        self.cpu_curve_force_update = True
        self.settings.setValue("cpu/profile", profile.model)
        self.settings.setValue("cooling/curve_source", "cpu")
        self.footer_status.setText(f"AM5-Profil geladen: {profile.model}")
        self.log_message(
            f"CPU-PROFIL: {profile.model} geladen · Boost ab {self.format_temperature(profile.boost_temp, 0)} · "
            f"100 % ab {self.format_temperature(profile.critical_temp, 0)} · "
            f"CPU-Pumpenkurve {len(pump_points)} Punkte · CPU-Lüfterkurve {len(fan_points)} Punkte"
        )
        QTimer.singleShot(0, self.update_cpu_curve_control)
        QMessageBox.information(
            self,
            "AM5-Profil geladen",
            f"Das Profil für {profile.model} wurde geladen.\n\n"
            f"Beide Kurven verwenden jetzt die CPU-Temperatur und erreichen bei {self.format_temperature(profile.critical_temp, 0)} 100 %. "
            f"AMD Tjmax: {self.format_temperature(profile.tjmax, 0)}.\n\n"
            "Aktiviere die gewünschte Pumpen- und Lüfterkurve über die beiden Kurven-Schaltflächen. "
            "Die Kraken-Wassertemperatur bleibt unabhängig davon als Sicherheitsüberwachung aktiv."
        )

    # ---------- status ----------
    def refresh_status(self) -> None:
        if (
            self.gif_kraken_io_paused
            or self.gif_start_pending
            or self.is_gif_stream_running()
            or not self.devices_ready
            or self.status_busy
            or self.kraken_write_busy
            or self.lcd_busy
        ):
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
            self.current_liquid_temp = temp
            if temp is not None:
                self.temp_card.set_value(self.format_temperature(temp), self.temperature_hint(temp))
                self.update_health(temp, pump_speed, fan_speed)
                self.enforce_temperature_safety(temp)
            cpu_temp, sensor_label = self.read_amd_cpu_temperature()
            self.current_cpu_temp = cpu_temp
            self.cpu_sensor_label = sensor_label
            if cpu_temp is not None:
                profile_hint = self.selected_cpu_profile.model if self.selected_cpu_profile else "kein Profil"
                self.cpu_temp_card.set_value(self.format_temperature(cpu_temp), f"{sensor_label} · {profile_hint}")
                self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label} · aktuell {self.format_temperature(cpu_temp)}")
                self.pump_curve_table[2].set_current_temperature(cpu_temp)
                self.fan_curve_table[2].set_current_temperature(cpu_temp)
            else:
                self.cpu_temp_card.set_value(self.format_temperature(None), sensor_label)
                self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label}")
            gpu_temp, gpu_sensor_label = self.read_amd_gpu_temperature()
            self.current_gpu_temp = gpu_temp
            self.gpu_sensor_label = gpu_sensor_label
            if gpu_temp is not None:
                self.gpu_temp_card.set_value(self.format_temperature(gpu_temp), gpu_sensor_label)
            else:
                self.gpu_temp_card.set_value(self.format_temperature(None), gpu_sensor_label)
            if pump_speed is not None:
                self.pump_card.set_value(f"{int(pump_speed)} rpm", f"{pump_duty:.0f} % Leistung" if pump_duty is not None else "")
            if fan_speed is not None:
                self.fan_card.set_value(f"{int(fan_speed)} rpm", f"{fan_duty:.0f} % Leistung" if fan_duty is not None else "")
            if pump_duty is not None:
                self.pump_slider.setValue(int(round(pump_duty)))
            if fan_duty is not None:
                self.fan_slider.setValue(int(round(fan_duty)))
            self.footer_status.setText(self.tr_static("Status aktuell"))

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

    def temperature_hint(self, temp: float) -> str:
        if temp < 35:
            return self.tr_static("Sehr guter Bereich")
        if temp < 42:
            return self.tr_static("Normal unter Last")
        if temp < 50:
            return self.tr_static("Erhöht – Kurve prüfen")
        return self.tr_static("Kritisch – Kühlung prüfen")

    def update_health(self, temp: float, pump_speed: float | None, fan_speed: float | None) -> None:
        warning = self.safety_temperature_c(self.warning_temp)
        critical = self.safety_temperature_c(self.critical_temp)
        if pump_speed is not None and pump_speed < 500:
            text, obj = self.tr_static("⚠ Pumpendrehzahl ungewöhnlich niedrig."), "healthCritical"
        elif temp >= critical:
            text, obj = f"{self.tr_static('⚠ Kritische Wassertemperatur')}: {self.format_temperature(temp)}", "healthCritical"
        elif temp >= warning:
            text, obj = f"{self.tr_static('⚠ Erhöhte Wassertemperatur')}: {self.format_temperature(temp)}", "healthWarn"
        elif fan_speed is not None and fan_speed < 100 and temp > 38:
            text, obj = self.tr_static("⚠ Lüfter stehen trotz erhöhter Temperatur."), "healthWarn"
        else:
            text, obj = self.tr_static("✅ Kühlung arbeitet normal."), "healthGood"
        self.health_label.setText(text)
        self.health_label.setObjectName(obj)
        self.health_label.style().unpolish(self.health_label)
        self.health_label.style().polish(self.health_label)

    def enforce_temperature_safety(self, temp: float) -> None:
        if not self.auto_max_checkbox.isChecked() or temp < self.safety_temperature_c(self.critical_temp):
            return
        last = self.settings.value("safety/last_auto_max", 0.0, type=float)
        now = time.time()
        if now - last < 60:
            return
        self.settings.setValue("safety/last_auto_max", now)
        self.log_message(f"Sicherheitsaktion: {self.format_temperature(temp)} – Pumpe und Lüfter auf 100 %.")
        self.apply_quick_profile("Sicherheit", 100, 100, notify=False)

    @staticmethod
    def interpolate_curve(points: list[tuple[int, int]], temperature: float) -> int:
        """Linearly interpolate one monotonic CPU curve."""
        if not points:
            raise ValueError("Leere CPU-Kurve")
        if temperature <= points[0][0]:
            return int(points[0][1])
        if temperature >= points[-1][0]:
            return int(points[-1][1])
        for (left_temp, left_duty), (right_temp, right_duty) in zip(points, points[1:]):
            if temperature <= right_temp:
                span = max(1.0, float(right_temp - left_temp))
                ratio = (float(temperature) - left_temp) / span
                return int(round(left_duty + ratio * (right_duty - left_duty)))
        return int(points[-1][1])

    @staticmethod
    def quantize_curve_duty(duty: int) -> int:
        quantum = max(1, CPU_CURVE_DUTY_QUANTUM)
        return max(0, min(100, int(round(int(duty) / quantum) * quantum)))

    @staticmethod
    def should_update_curve_duty(
        previous: int | None,
        target: int,
        elapsed: float,
        *,
        force: bool = False,
        emergency: bool = False,
    ) -> bool:
        if force or emergency or previous is None:
            return True
        if target >= previous + CPU_CURVE_RISE_DELTA:
            return elapsed >= CPU_CURVE_RISE_INTERVAL
        if target <= previous - CPU_CURVE_FALL_DELTA:
            return elapsed >= CPU_CURVE_FALL_INTERVAL
        return False

    def active_cpu_curve_channels(self) -> list[str]:
        return [
            channel
            for channel in ("pump", "fan")
            if self.cooling_mode_kind(self.cooling_modes.get(channel, ("", ""))[0]) == "curve"
        ]

    def update_cpu_curve_control(self) -> None:
        """Evaluate active CPU curves without touching Kraken status polling."""
        cpu_temp, sensor_label = self.read_amd_cpu_temperature()
        self.cpu_sensor_label = sensor_label
        active_channels = self.active_cpu_curve_channels()
        if cpu_temp is None:
            self.cpu_temp_card.set_value(self.format_temperature(None), sensor_label)
            self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label}")
            self.cpu_curve_sensor_failures += 1
            if (
                active_channels
                and self.devices_ready
                and self.cpu_curve_sensor_failures == CPU_CURVE_SENSOR_FAILURE_LIMIT
            ):
                fallback_targets = {channel: 75 for channel in active_channels}
                self.apply_cpu_curve_targets(
                    fallback_targets,
                    None,
                    action="CPU-Sensor-Fallback",
                    force=True,
                    fallback=True,
                )
            return

        self.cpu_curve_sensor_failures = 0
        self.current_cpu_temp = float(cpu_temp)
        self.cpu_temp_card.set_value(
            self.format_temperature(cpu_temp),
            f"{sensor_label} · {self.selected_cpu_profile.model if self.selected_cpu_profile else 'Standardkurve'}",
        )
        self.cpu_current_label.setText(f"CPU-Sensor: {sensor_label} · aktuell {self.format_temperature(cpu_temp)}")
        self.pump_curve_table[2].set_current_temperature(cpu_temp)
        self.fan_curve_table[2].set_current_temperature(cpu_temp)

        if self.cpu_curve_filtered_temp is None or self.cpu_curve_fallback_active:
            self.cpu_curve_filtered_temp = float(cpu_temp)
        else:
            # Ryzen CPUs can jump by many degrees for milliseconds.  A modest
            # EMA avoids audible hunting while still reacting quickly to load.
            self.cpu_curve_filtered_temp = 0.35 * float(cpu_temp) + 0.65 * self.cpu_curve_filtered_temp
        self.cpu_curve_fallback_active = False

        if not active_channels or not self.devices_ready or time.monotonic() < self.permission_retry_after:
            return

        targets: dict[str, int] = {}
        for channel in active_channels:
            editor = self.pump_curve_table[2] if channel == "pump" else self.fan_curve_table[2]
            target = self.interpolate_curve(editor.points(), self.cpu_curve_filtered_temp)
            if cpu_temp >= editor.points()[-1][0]:
                target = 100
            minimum = 20 if channel == "pump" else 0
            targets[channel] = max(minimum, self.quantize_curve_duty(target))

        now = time.monotonic()
        elapsed = now - self.cpu_curve_last_write
        changed: dict[str, int] = {}
        emergency = any(target >= 100 for target in targets.values())
        for channel, target in targets.items():
            previous = self.cpu_curve_last_duties.get(channel)
            if self.should_update_curve_duty(
                previous,
                target,
                elapsed,
                force=self.cpu_curve_force_update,
                emergency=emergency,
            ):
                changed[channel] = target
        if changed:
            self.apply_cpu_curve_targets(
                changed,
                float(cpu_temp),
                action="CPU-Kurvenregelung",
                force=self.cpu_curve_force_update or emergency,
            )

    def apply_cpu_curve_targets(
        self,
        targets: dict[str, int],
        cpu_temp: float | None,
        *,
        action: str,
        force: bool = False,
        activate_channels: set[str] | None = None,
        fallback: bool = False,
    ) -> None:
        """Write one or both calculated duties in a single coordinated window."""
        ordered_targets = {
            channel: int(targets[channel])
            for channel in ("pump", "fan")
            if channel in targets
        }
        if not ordered_targets:
            return
        if self.defer_cooling_action_for_gif(
            action,
            lambda: self.apply_cpu_curve_targets(
                ordered_targets,
                cpu_temp,
                action=action,
                force=force,
                activate_channels=activate_channels,
                fallback=fallback,
            ),
        ):
            return
        if self.kraken_write_busy:
            return
        if self.has_kraken_write_access() is False:
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return

        commands = list(ordered_targets.items())
        self.kraken_write_busy = True

        def run_index(index: int) -> None:
            if index >= len(commands):
                self.kraken_write_busy = False
                self.permission_retry_after = 0.0
                self.cpu_curve_last_write = time.monotonic()
                for channel, duty in commands:
                    self.cpu_curve_last_duties[channel] = duty
                    temperature_text = "Sensorfehler" if cpu_temp is None else f"CPU {self.format_temperature(cpu_temp)}"
                    detail = f"{duty} % · {temperature_text} · Software-Regelung"
                    if fallback:
                        detail = f"{duty} % · sicherer Sensorfehler-Fallback"
                    self.set_cooling_mode(channel, "CPU-Temperaturkurve", detail)
                self.cpu_curve_force_update = False
                self.cpu_curve_fallback_active = fallback
                values = " · ".join(
                    f"{'Pumpe' if channel == 'pump' else 'Lüfter'} {duty} %"
                    for channel, duty in commands
                )
                temperature_text = "CPU-Sensor nicht verfügbar" if cpu_temp is None else f"CPU {self.format_temperature(cpu_temp)}"
                self.footer_status.setText(f"CPU-Kurve: {temperature_text} · {values}")
                self.log_message(f"CPU-KURVE: {temperature_text} · {values} · geglättet/hysteretisch")
                return

            channel, duty = commands[index]

            def done(result: CommandResult) -> None:
                if not result.ok:
                    self.kraken_write_busy = False
                    self.show_error(result.combined or f"CPU-Kurve konnte {channel} nicht einstellen.")
                    return
                run_index(index + 1)

            self.backend.run_async(
                Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)],
                callback=done,
                timeout=20,
            )

        run_index(0)

    @staticmethod
    def curve_args(channel: str, points: list[tuple[int, int]]) -> list[str]:
        args = Backend.kraken_direct_args() + ["set", channel, "speed"]
        for temp, duty in points:
            args.extend([str(int(temp)), str(int(duty))])
        return args

    def restore_original_lcd_sync_on_quit(self) -> None:
        """Restore the Kraken firmware liquid screen after an orderly exit.

        Window close-to-tray never reaches this method.  It runs only for a
        real application exit or an orderly desktop logout/shutdown, after a
        possible raw GIF streamer has released the Kraken USB interface.
        """
        try:
            result = subprocess.run(
                Backend.kraken_args() + ["set", "lcd", "screen", "liquid"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.log_message(
                "LCD-PROGRAMMENDE: Originalanzeige konnte nicht wiederhergestellt werden · "
                f"{redact_private_text(str(exc))}"
            )
            return
        if result.returncode == 0:
            self.log_message(
                "LCD-PROGRAMMENDE: Kraken-Originalanzeige mit Wassertemperatur wiederhergestellt."
            )
            return
        detail = redact_private_text((result.stderr or result.stdout or "unbekannter Fehler").strip())
        self.log_message(
            "LCD-PROGRAMMENDE: Wiederherstellung der Wassertemperaturanzeige fehlgeschlagen"
            + (f" · {detail}" if detail else "")
        )

    def restore_safe_hardware_fallback_sync_on_quit(self) -> None:
        """Leave autonomous liquid-temperature protection after a real exit."""
        fallbacks = {
            "pump": list(SAFE_HARDWARE_PUMP_CURVE),
            "fan": list(SAFE_HARDWARE_FAN_CURVE),
        }
        for channel in self.active_cpu_curve_channels():
            try:
                subprocess.run(
                    self.curve_args(channel, fallbacks[channel]),
                    capture_output=True,
                    timeout=8,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                pass

    # ---------- cooling ----------
    def configure_expert_mode_controls(
        self,
        enabled: bool,
        *,
        warning_c: float | None = None,
        critical_c: float | None = None,
    ) -> None:
        if warning_c is None:
            warning_c = self.safety_temperature_c(self.warning_temp)
        if critical_c is None:
            critical_c = self.safety_temperature_c(self.critical_temp)
        suffix = f" {temperature_symbol(self.temperature_unit)}"
        self.warning_temp.blockSignals(True)
        self.critical_temp.blockSignals(True)
        if enabled:
            self.warning_temp.setRange(self.display_temperature_int(-20), self.display_temperature_int(120))
            self.critical_temp.setRange(self.display_temperature_int(-20), self.display_temperature_int(120))
            self.safety_note.setText(
                "EXPERTENMODUS: Die App begrenzt oder sortiert Warn- und Kritisch-Grenze nicht. "
                "Ungeeignete Werte können Warnungen und die automatische 100-%-Umschaltung unwirksam machen. "
                "CPU-Tjmax und Kraken-Wassertemperatur bleiben unterschiedliche Messgrößen."
            )
        else:
            warning = max(35, min(48, round(warning_c)))
            critical = max(40, min(55, round(critical_c)))
            if critical <= warning:
                warning, critical = 42, 50
            warning_c, critical_c = warning, critical
            self.warning_temp.setRange(self.display_temperature_int(35), self.display_temperature_int(48))
            self.critical_temp.setRange(self.display_temperature_int(40), self.display_temperature_int(55))
            self.safety_note.setText(self.safety_limits_explanation())
        self.warning_temp.setSuffix(suffix)
        self.critical_temp.setSuffix(suffix)
        self.warning_temp.setValue(self.display_temperature_int(float(warning_c)))
        self.critical_temp.setValue(self.display_temperature_int(float(critical_c)))
        self.warning_temp.blockSignals(False)
        self.critical_temp.blockSignals(False)

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

    @staticmethod
    def cooling_mode_kind(mode: str) -> str | None:
        normalized = str(mode).strip().casefold()
        if "kurve" in normalized or "curve" in normalized or "temperatur" in normalized:
            return "curve"
        if normalized in {"fixed", "manual", "manuell"} or any(
            marker in normalized for marker in ("fest", "drehzahl", "cpu-assistenz")
        ):
            return "manual"
        return None

    def switch_cooling_mode(self, channel: str, target: str) -> None:
        if channel not in {"pump", "fan"} or target not in {"manual", "curve"}:
            self.show_error("Ungültige Kühlungsbetriebsart.")
            return
        # Keep the last confirmed device state visible until the asynchronous
        # Kraken command succeeds and set_cooling_mode records the new mode.
        self.update_cooling_mode_buttons()
        if target == "manual":
            slider = self.pump_slider if channel == "pump" else self.fan_slider
            self.set_fixed_speed(channel, slider.value())
            return
        curve_table = self.pump_curve_table[1] if channel == "pump" else self.fan_curve_table[1]
        self.apply_curve(channel, curve_table)

    def update_cooling_mode_buttons(self) -> None:
        if not hasattr(self, "cooling_mode_buttons"):
            return
        for channel, buttons in self.cooling_mode_buttons.items():
            active = self.cooling_mode_kind(self.cooling_modes.get(channel, ("", ""))[0])
            for kind, button in buttons.items():
                state = "active" if kind == active else "inactive"
                if button.property("coolingState") == state:
                    continue
                button.setProperty("coolingState", state)
                # Qt does not automatically repolish a widget when a dynamic
                # property used by QSS changes.  Reapply only this button so
                # the success colour switches immediately and remains stable.
                button.style().unpolish(button)
                button.style().polish(button)
                button.update()
                button.setAccessibleDescription(
                    "Aktiver, erfolgreich übertragener Kühlmodus" if state == "active"
                    else "Nicht aktiver Kühlmodus"
                )

    def update_cooling_mode_label(self) -> None:
        if not hasattr(self, "cooling_mode_label"):
            return
        pump_mode, pump_detail = self.cooling_modes["pump"]
        fan_mode, fan_detail = self.cooling_modes["fan"]
        self.cooling_mode_label.setText(
            f"Pumpe: {pump_mode} · {pump_detail}\nRadiatorlüfter: {fan_mode} · {fan_detail}"
        )
        self.update_cooling_mode_buttons()

    def sync_safety_thresholds(self) -> None:
        if self.expert_mode_checkbox.isChecked():
            return
        sender = self.sender()
        if sender is self.warning_temp and self.critical_temp.value() <= self.warning_temp.value():
            self.critical_temp.setValue(min(self.critical_temp.maximum(), self.warning_temp.value() + 1))
        elif sender is self.critical_temp and self.warning_temp.value() >= self.critical_temp.value():
            self.warning_temp.setValue(max(self.warning_temp.minimum(), self.critical_temp.value() - 1))

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
        if self.defer_cooling_action_for_gif(
            "Pumpen-/Lüfterbefehl",
            lambda: self.set_fixed_speed(channel, duty),
        ):
            return
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
                self.cpu_curve_last_duties[channel] = None
                QTimer.singleShot(700, self.refresh_status)
            else:
                self.show_error(result.combined or f"{label} konnte nicht eingestellt werden")

        self.backend.run_async(
            Backend.kraken_direct_args() + ["set", channel, "speed", str(duty)],
            callback=done,
            timeout=20,
        )

    def apply_quick_profile(self, name: str, pump: int, fan: int, notify: bool = True) -> None:
        if self.defer_cooling_action_for_gif(
            "Kühlprofil",
            lambda: self.apply_quick_profile(name, pump, fan, notify),
        ):
            return
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
            self.cpu_curve_last_duties = {"pump": None, "fan": None}
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
        if self.defer_cooling_action_for_gif(
            "CPU-Pumpen-/Lüfterkurve",
            lambda: self.apply_curve(channel, table),
        ):
            return
        access = self.has_kraken_write_access()
        if access is False:
            self.show_permission_error("/dev/hidraw für USB 1e71:300e ist nicht les- und schreibbar.")
            return
        points: list[tuple[int, int]] = []
        try:
            for row in range(table.rowCount()):
                temp = self.temperature_c_from_display(int(table.item(row, 0).text()))
                duty = int(table.item(row, 1).text())
                if temp < 20 or temp > 100 or duty < (20 if channel == "pump" else 0) or duty > 100:
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
        safe_limit = self.selected_cpu_profile.critical_temp if self.selected_cpu_profile else 90
        if points[-1][0] > safe_limit or points[-1][1] != 100:
            self.show_error(
                f"Eine sichere CPU-Kurve muss spätestens bei {self.format_temperature(safe_limit, 0)} einen Endpunkt mit 100 % besitzen."
            )
            return
        low_limit = LOW_PUMP_WARNING if channel == "pump" else LOW_FAN_WARNING
        low_points = [(temp, duty) for temp, duty in points if duty < low_limit]
        if low_points:
            low_text = ", ".join(f"{self.format_temperature(temp, 0)}/{duty} %" for temp, duty in low_points)
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
        cpu_temp, sensor_label = self.read_amd_cpu_temperature()
        if cpu_temp is None:
            self.show_error(
                "Die CPU-Kurve kann nicht aktiviert werden, weil kein CPU-Temperatursensor verfügbar ist.\n\n"
                + sensor_label
            )
            return
        target = self.quantize_curve_duty(self.interpolate_curve(points, float(cpu_temp)))
        target = max(20 if channel == "pump" else 0, target)
        self.settings.setValue("cooling/curve_source", "cpu")
        self.cpu_curve_filtered_temp = float(cpu_temp)
        self.apply_cpu_curve_targets(
            {channel: target},
            float(cpu_temp),
            action="CPU-Pumpenkurve" if channel == "pump" else "CPU-Lüfterkurve",
            force=True,
            activate_channels={channel},
        )

    # ---------- RGB ----------
    def update_rgb_controls(self) -> None:
        mode_key = str(self.rgb_mode.currentData() or "Aus")
        _, count = self.rgb_modes[mode_key]
        self.color1_button.setEnabled(count >= 1)
        self.color2_button.setEnabled(count >= 2)
        mode = self.rgb_modes[mode_key][0]
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
        self.rgb_channel.setCurrentIndex(max(0, self.rgb_channel.findData("sync")))
        self.rgb_mode.setCurrentIndex(max(0, self.rgb_mode.findData("Statisch")))
        self.color1_hex = color
        self.color1_button.setText(f"Farbe 1 · #{color}")
        self.apply_rgb()

    def apply_rgb(self) -> None:
        mode_key = str(self.rgb_mode.currentData() or "Aus")
        mode, color_count = self.rgb_modes[mode_key]
        args = Backend.rgb_args() + ["set", str(self.rgb_channel.currentData() or "sync"), "color", mode]
        if color_count >= 1:
            args.append(self.color1_hex)
        if color_count >= 2:
            args.append(self.color2_hex)
        if mode not in ("off", "fixed"):
            args.extend(["--speed", str(self.rgb_speed.currentData() or "normal")])
        directional_modes = {
            "spectrum-wave", "marquee-4", "moving-alternating-4",
            "rainbow-flow", "super-rainbow", "rainbow-pulse"
        }
        if mode in directional_modes:
            args.extend(["--direction", str(self.rgb_direction.currentData() or "forward")])

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
        if self.is_gif_stream_running():
            self.stop_gif_stream(lambda: self.apply_lcd_display_settings())
            return
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
        if self.is_gif_stream_running():
            self.stop_gif_stream(lambda: self.send_lcd_now())
            return
        self.stop_hardware_lcd_mode(update_status=False, clear_marker=False)
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
            def resent(result: CommandResult) -> None:
                if result.ok:
                    self.lcd_failure_count = 0
                else:
                    self.record_lcd_failure(
                        "LCD-Bild-Fallback",
                        result.combined or "unbekannter Fehler",
                    )

            self.send_static_lcd(self.prepared_lcd_file, quiet=True, completion=resent)

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
        if self.is_gif_stream_running():
            self.stop_gif_stream(lambda: self.show_liquid_screen())
            return
        self.stop_hardware_lcd_mode(update_status=False, clear_marker=False)
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
                self.lcd_failure_count = 0
                self.lcd_recovery_required = False
                self.settings.setValue("lcd/recovery_required", False)
                self.clear_experimental_lcd_marker()
                self.update_experimental_notice_status()
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
        if enabled and self.is_gif_stream_running():
            self.stop_gif_stream(lambda: self.toggle_lcd_keepalive(True))
            return
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
            self.settings.setValue("lcd/keepalive_warning_ack", True)
            self.settings.sync()
            self.update_experimental_notice_status()
            self.log_message("LCD-FALLBACK: Experimentalhinweis dauerhaft bestätigt.")
        elif enabled:
            self.log_message("LCD-FALLBACK: Experimentalhinweis bereits bestätigt · Aktivierung ohne Dialog.")
        if enabled and self.lcd_recovery_required:
            self.keep_lcd_checkbox.blockSignals(True)
            self.keep_lcd_checkbox.setChecked(False)
            self.keep_lcd_checkbox.blockSignals(False)
            self.show_error("Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.")
            return
        if enabled:
            self.stop_hardware_lcd_mode(update_status=False, clear_marker=False)
            self.stop_clock_mode(update_status=False, clear_marker=False)
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
                    self.lcd_failure_count = 0
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
                    self.clear_experimental_lcd_marker()

            # Der Crash-Marker wird erst gesetzt, wenn die Voraussetzungen für den experimentellen Modus erfüllt sind.
            self.experimental_autostart_blocked = False
            self.mark_experimental_lcd_active("keepalive")
            # Erst nach einem erfolgreichen Upload startet der Wiederholungs-Timer.
            self.send_static_lcd(self.prepared_lcd_file, quiet=False, completion=uploaded)
        else:
            self.lcd_keepalive_timer.stop()
            if not self.clock_active:
                self.clear_experimental_lcd_marker()
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
        if getattr(self, "hardware_animation_movie", None) is not None:
            self.hardware_animation_movie.stop()
            self.hardware_animation_movie = None
            self.preview.clear()
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

    # ---------- rounded live hardware dashboards ----------
    def update_hardware_text_scales(self, _value: int = 0) -> None:
        self.hardware_label_scale_label.setText(f"{self.hardware_label_scale.value()} %")
        self.hardware_value_scale_label.setText(f"{self.hardware_value_scale.value()} %")
        self.settings.setValue("hardware_lcd/label_scale", self.hardware_label_scale.value())
        self.settings.setValue("hardware_lcd/value_scale", self.hardware_value_scale.value())

    def apply_hardware_color_preset(self, _index: int = -1) -> None:
        value = str(self.hardware_color_preset_combo.currentData() or "custom")
        if value != "custom":
            self.hardware_color_input.setText(value)
            self.validate_hardware_color_input(show_message=False)

    def validate_hardware_color_input(self, *, show_message: bool = True) -> bool:
        color = normalize_hex_color(self.hardware_color_input.text())
        if color is None:
            self.hardware_color_input.setStyleSheet("border: 2px solid #ff4058;")
            if show_message:
                self.show_error("Bitte einen gültigen Hex-Farbwert im Format #RRGGBB eingeben.")
            return False
        self.hardware_color_input.setText(color)
        self.hardware_color_input.setStyleSheet("")
        preset_index = self.hardware_color_preset_combo.findData(color)
        if preset_index < 0:
            preset_index = self.hardware_color_preset_combo.findData("custom")
        self.hardware_color_preset_combo.blockSignals(True)
        self.hardware_color_preset_combo.setCurrentIndex(max(0, preset_index))
        self.hardware_color_preset_combo.blockSignals(False)
        return True

    def pick_hardware_color(self) -> None:
        current = normalize_hex_color(self.hardware_color_input.text()) or DEFAULT_ACCENT
        color = QColorDialog.getColor(QColor(current), self, self.tr_static("LCD-Akzentfarbe auswählen"))
        if not color.isValid():
            return
        self.hardware_color_input.setText(color.name())
        self.validate_hardware_color_input(show_message=False)

    def validate_hardware_text_colors(self, *, show_message: bool = True) -> bool:
        valid = True
        for field in (self.hardware_label_color_input, self.hardware_value_color_input):
            color = normalize_hex_color(field.text())
            if color is None:
                field.setStyleSheet("border: 2px solid #ff4058;")
                valid = False
            else:
                field.setText(color)
                field.setStyleSheet("")
        if not valid and show_message:
            self.show_error("Bitte für Beschriftung und Temperaturzahl gültige Hex-Farben im Format #RRGGBB eingeben.")
        return valid

    def pick_hardware_text_color(self, field: QLineEdit, title: str) -> None:
        fallback = DEFAULT_LABEL_COLOR if field is self.hardware_label_color_input else DEFAULT_VALUE_COLOR
        current = normalize_hex_color(field.text()) or fallback
        color = QColorDialog.getColor(QColor(current), self, self.tr_static(title))
        if not color.isValid():
            return
        field.setText(color.name())
        self.validate_hardware_text_colors(show_message=False)

    def render_hardware_lcd_image(self) -> Path:
        if not self.validate_hardware_color_input(show_message=False) or not self.validate_hardware_text_colors(show_message=False):
            raise ValueError("Ungültiger Hex-Farbwert; erwartet wird #RRGGBB.")
        design_id = str(self.hardware_design_combo.currentData() or "water_halo")
        render_hardware_design(
            design_id,
            self.hardware_color_input.text(),
            self.current_liquid_temp,
            self.current_cpu_temp,
            self.current_gpu_temp,
            self.hardware_lcd_image_file,
            language=self.ui_language,
            font_scale_percent=self.hardware_value_scale.value(),
            label_color_hex=self.hardware_label_color_input.text(),
            value_color_hex=self.hardware_value_color_input.text(),
            label_scale_percent=self.hardware_label_scale.value(),
            value_scale_percent=self.hardware_value_scale.value(),
            temperature_unit=self.temperature_unit,
        )
        self.show_round_preview(self.hardware_lcd_image_file)
        self.file_name_label.setText(
            f"{self.tr_static('Live-Hardwaredesign')} · {self.hardware_design_combo.currentText()}"
        )
        return self.hardware_lcd_image_file

    def preview_hardware_lcd(self) -> None:
        try:
            self.render_hardware_lcd_image()
            self.hardware_lcd_status_label.setText(
                self.tr_static("Designvorschau aktualisiert · noch nicht auf das LCD übertragen.")
            )
        except Exception as exc:  # noqa: BLE001
            self.show_error(f"{self.tr_static('Die Designvorschau konnte nicht erzeugt werden:')}\n{exc}")

    def start_hardware_lcd_mode(self) -> None:
        if self.is_gif_stream_running():
            self.stop_gif_stream(self.start_hardware_lcd_mode)
            return
        if not self.devices_ready:
            self.show_error(self.tr_static("Die Kraken ist noch nicht verbunden."))
            return
        if self.lcd_recovery_required:
            self.show_error(self.tr_static("Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur."))
            return
        if not self.validate_hardware_color_input() or not self.validate_hardware_text_colors():
            return
        if not self.hardware_lcd_warning_acknowledged:
            answer = QMessageBox.warning(
                self,
                self.tr_static("Experimentelles Live-Hardwaredesign"),
                self.tr_static(
                    "Das Live-Design überträgt im gewählten Intervall ein neues statisches Bild mit aktuellen "
                    "Sensordaten. Die langfristige Wirkung häufiger Uploads auf den Displayspeicher ist nicht ausreichend "
                    "bekannt. Live-Design trotzdem starten?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.hardware_lcd_warning_acknowledged = True
            self.settings.setValue("hardware_lcd/experimental_warning_ack", True)
            self.settings.sync()
            self.update_experimental_notice_status()
        self.stop_clock_mode(update_status=False, clear_marker=False)
        self.lcd_keepalive_timer.stop()
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(False)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(False)
        self.hardware_lcd_active = True
        self.hardware_start_button.setEnabled(False)
        self.hardware_stop_button.setEnabled(True)
        self.experimental_autostart_blocked = False
        self.mark_experimental_lcd_active("hardware")
        self.settings.setValue("hardware_lcd/active", True)
        self.settings.setValue("lcd/keepalive", False)
        self.update_hardware_lcd_interval()
        self.update_hardware_lcd(force=True)

    def stop_hardware_lcd_mode(
        self,
        _checked: bool = False,
        *,
        update_status: bool = True,
        clear_marker: bool = True,
    ) -> None:
        self.hardware_lcd_active = False
        self.hardware_lcd_timer.stop()
        if hasattr(self, "hardware_start_button"):
            self.hardware_start_button.setEnabled(True)
            self.hardware_stop_button.setEnabled(False)
        self.settings.setValue("hardware_lcd/active", False)
        if hasattr(self, "hardware_start_button"):
            self.hardware_start_button.setEnabled(True)
            self.hardware_stop_button.setEnabled(False)
        if clear_marker and not self.clock_active and not self.is_gif_stream_running() and not self.keep_lcd_checkbox.isChecked():
            self.clear_experimental_lcd_marker()
        if update_status:
            self.hardware_lcd_status_label.setText(
                self.tr_static("Live-Hardwaredesign angehalten · das letzte Bild kann sichtbar bleiben.")
            )
            self.footer_status.setText(self.tr_static("Live-Hardwaredesign angehalten"))

    def update_hardware_lcd_interval(self) -> None:
        if not hasattr(self, "hardware_lcd_timer"):
            return
        self.hardware_lcd_timer.setInterval(self.hardware_update_interval.value() * 1000)
        if self.hardware_lcd_timer.isActive():
            self.hardware_lcd_timer.start()
        self.settings.setValue("hardware_lcd/interval", self.hardware_update_interval.value())

    def update_hardware_lcd(self, force: bool = False) -> None:
        if not self.hardware_lcd_active or not self.devices_ready:
            return
        if self.lcd_busy or self.kraken_write_busy or self.status_busy:
            if force:
                QTimer.singleShot(1000, lambda: self.update_hardware_lcd(force=True))
            return
        try:
            image_path = self.render_hardware_lcd_image()
        except Exception as exc:  # noqa: BLE001
            self.log_message(f"LCD-HARDWARE: Rendererfehler · {exc}")
            self.activate_lcd_safe_mode(f"Live-Hardwaredesign-Rendererfehler: {exc}")
            return

        def uploaded(result: CommandResult) -> None:
            if result.ok and self.hardware_lcd_active:
                self.lcd_failure_count = 0
                self.hardware_lcd_timer.start()
                self.lcd_mode_label.setText(
                    f"{self.tr_static('LCD-Modus: Live-Hardwaredesign')} · {self.hardware_design_combo.currentText()}"
                )
                self.hardware_lcd_status_label.setText(
                    f"{self.tr_static('Live aktiv')} · {self.tr_static('Aktualisierung alle')} "
                    f"{self.hardware_update_interval.value()} {self.tr_static('Sekunden')}"
                )
                self.footer_status.setText(self.tr_static("Live-Hardwaredesign aktiv"))
            elif not result.ok:
                detail = result.combined or "unbekannter Fehler"
                if not self.record_lcd_failure("Live-Hardwaredesign-Upload", detail):
                    self.hardware_lcd_timer.start(3000)

        self.send_static_lcd(image_path, quiet=True, completion=uploaded)

    # ---------- animated hardware dashboards ----------
    def render_hardware_animation_file(self) -> Path:
        if not self.validate_hardware_color_input(show_message=False) or not self.validate_hardware_text_colors(show_message=False):
            raise ValueError("Ungültiger Hex-Farbwert; erwartet wird #RRGGBB.")
        if self.hardware_animation_movie is not None:
            self.hardware_animation_movie.stop()
            self.hardware_animation_movie = None
            self.preview.clear()
        design_id = str(self.hardware_animation_design_combo.currentData() or "water_halo")
        fps = int(self.hardware_animation_fps_combo.currentData() or 25)
        render_hardware_animation(
            design_id,
            self.hardware_color_input.text(),
            self.current_liquid_temp,
            self.current_cpu_temp,
            self.current_gpu_temp,
            self.hardware_animation_file,
            language=self.ui_language,
            font_scale_percent=self.hardware_value_scale.value(),
            label_color_hex=self.hardware_label_color_input.text(),
            value_color_hex=self.hardware_value_color_input.text(),
            label_scale_percent=self.hardware_label_scale.value(),
            value_scale_percent=self.hardware_value_scale.value(),
            temperature_unit=self.temperature_unit,
            fps=fps,
        )
        spec = {
            "schema": 1,
            "design_id": design_id,
            "accent_hex": self.hardware_color_input.text(),
            "liquid": self.current_liquid_temp,
            "cpu": self.current_cpu_temp,
            "gpu": self.current_gpu_temp,
            "language": self.ui_language,
            "font_scale_percent": self.hardware_value_scale.value(),
            "label_color_hex": self.hardware_label_color_input.text(),
            "value_color_hex": self.hardware_value_color_input.text(),
            "label_scale_percent": self.hardware_label_scale.value(),
            "value_scale_percent": self.hardware_value_scale.value(),
            "temperature_unit": self.temperature_unit,
            "content_fps": fps,
        }
        temporary_spec = self.hardware_animation_spec_file.with_suffix(".json.tmp")
        temporary_spec.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary_spec.replace(self.hardware_animation_spec_file)
        return self.hardware_animation_file

    def show_hardware_animation_preview(self, path: Path) -> None:
        if self.hardware_animation_movie is not None:
            self.hardware_animation_movie.stop()
        movie = QMovie(str(path))
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.setScaledSize(QSize(270, 270))
        self.hardware_animation_movie = movie
        self.preview.clear()
        self.preview.setMovie(movie)
        movie.start()
        self.file_name_label.setText(
            f"{self.tr_static('Animierte Hardwaredaten')} · {self.hardware_animation_design_combo.currentText()}"
        )

    def preview_hardware_animation(self) -> None:
        try:
            path = self.render_hardware_animation_file()
            self.show_hardware_animation_preview(path)
            self.hardware_animation_status_label.setText(
                self.tr_static("Animierte Vorschau läuft · noch nicht auf das LCD übertragen.")
            )
        except Exception as exc:  # noqa: BLE001
            self.show_error(f"{self.tr_static('Die Hardwareanimation konnte nicht erzeugt werden:')}\n{exc}")

    def start_hardware_animation(self) -> None:
        if self.is_gif_stream_running() or self.gif_start_pending:
            if self.gif_generated_hardware_mode:
                return
            self.stop_gif_stream(self.start_hardware_animation)
            return
        if not self.devices_ready:
            self.show_error(self.tr_static("Die Kraken ist noch nicht verbunden."))
            return
        if self.lcd_recovery_required:
            self.show_error(self.tr_static("Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur."))
            return
        if not self.validate_hardware_color_input() or not self.validate_hardware_text_colors():
            return
        if not self.hardware_animation_warning_acknowledged:
            answer = QMessageBox.warning(
                self,
                self.tr_static("Experimentelle Hardwareanimation"),
                self.tr_static(_GIF_COOLING_WARNING),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.hardware_animation_warning_acknowledged = True
            self.settings.setValue("hardware_animation/experimental_warning_ack", True)
            self.settings.sync()
            self.update_experimental_notice_status()
        try:
            animation_path = self.render_hardware_animation_file()
            self.show_hardware_animation_preview(animation_path)
        except Exception as exc:  # noqa: BLE001
            self.show_error(f"{self.tr_static('Die Hardwareanimation konnte nicht erzeugt werden:')}\n{exc}")
            return
        fps = int(self.hardware_animation_fps_combo.currentData() or 25)
        self.hardware_animation_status_label.setText(self.tr_static("Hardwareanimation wird vorbereitet …"))
        self.start_gif_stream(
            source_path=animation_path,
            generated_hardware=True,
            fps_override=fps,
            interpolate_override=False,
        )

    def stop_hardware_animation(self) -> None:
        if not self.gif_generated_hardware_mode:
            return
        self.stop_gif_stream()

    def update_hardware_animation_controls(self) -> None:
        active = self.gif_generated_hardware_mode and (self.gif_start_pending or self.is_gif_stream_running())
        if hasattr(self, "hardware_animation_start_button"):
            self.hardware_animation_start_button.setEnabled(not active)
            self.hardware_animation_stop_button.setEnabled(active)
            self.hardware_animation_design_combo.setEnabled(not active)
            self.hardware_animation_fps_combo.setEnabled(not active)

    # ---------- experimental firmware-2.x GIF streaming ----------
    def populate_gif_fps_options(self, advanced: bool) -> None:
        """Keep normal choices simple while retaining low-rate diagnostics."""
        previous = self.gif_fps_combo.currentData() if self.gif_fps_combo.count() else 0
        self.gif_fps_combo.blockSignals(True)
        self.gif_fps_combo.clear()
        self.gif_fps_combo.addItem("CAM-nah · automatisch · empfohlen · max. 25 FPS", 0)
        self.gif_fps_combo.addItem("24 FPS Inhalt", 24)
        self.gif_fps_combo.addItem("25 FPS Inhalt · empfohlen", 25)
        if advanced:
            self.gif_fps_combo.insertSeparator(self.gif_fps_combo.count())
            for fps in (5, 8, 10, 12, 15, 20):
                self.gif_fps_combo.addItem(f"{fps} FPS Inhalt · Diagnose", fps)
        index = self.gif_fps_combo.findData(previous)
        self.gif_fps_combo.setCurrentIndex(index if index >= 0 else 0)
        self.gif_fps_combo.blockSignals(False)

    def set_gif_advanced_options_visible(self, visible: bool) -> None:
        self.populate_gif_fps_options(bool(visible))
        self.gif_transport_combo.setVisible(bool(visible))
        if not visible:
            cam_index = self.gif_transport_combo.findData("cam")
            self.gif_transport_combo.setCurrentIndex(max(0, cam_index))
        if getattr(self, "gif_transport_label", None) is not None:
            self.gif_transport_label.setVisible(bool(visible))

    def is_gif_stream_running(self) -> bool:
        return hasattr(self, "gif_process") and self.gif_process.state() != QProcess.ProcessState.NotRunning

    def update_gif_controls(self) -> None:
        running = self.is_gif_stream_running()
        active_or_pending = running or self.gif_start_pending
        if hasattr(self, "gif_start_button"):
            self.gif_start_button.setEnabled(not active_or_pending)
        if hasattr(self, "gif_stop_button"):
            self.gif_stop_button.setEnabled(active_or_pending)
        if hasattr(self, "gif_fps_combo"):
            self.gif_fps_combo.setEnabled(not active_or_pending)
        if hasattr(self, "gif_transport_combo"):
            self.gif_transport_combo.setEnabled(not active_or_pending)
        if hasattr(self, "gif_advanced_checkbox"):
            self.gif_advanced_checkbox.setEnabled(not active_or_pending)
        if hasattr(self, "gif_interpolate_checkbox"):
            self.gif_interpolate_checkbox.setEnabled(not active_or_pending)
        self.update_hardware_animation_controls()

    def gif_kraken_backend_idle(self) -> bool:
        return (
            not self.status_busy
            and not self.kraken_write_busy
            and not self.lcd_busy
            and self.backend.is_idle()
        )

    def pause_kraken_io_for_gif(self) -> None:
        if self.gif_kraken_io_paused:
            return
        self.gif_kraken_io_paused = True
        self.status_timer.stop()
        self.refresh_button.setEnabled(False)
        self.log_message(
            "LCD-GIF: Exklusiver Kraken-Zugriff vorgemerkt · normale Kraken-Statusabfragen pausieren. "
            "CPU-Kurven lesen Linux-hwmon weiter; relevante Pumpen-/Lüfteränderungen nutzen die koordinierte "
            "USB-Kurzpause und setzen anschließend denselben Framecache fort."
        )

    def resume_kraken_io_after_gif(self, *, schedule_refresh: bool = True) -> None:
        if not self.gif_kraken_io_paused:
            return
        self.gif_kraken_io_paused = False
        self.refresh_button.setEnabled(True)
        if self.devices_ready:
            self.status_timer.start(self.refresh_interval.value() * 1000)
            if schedule_refresh:
                QTimer.singleShot(500, self.refresh_status)
        self.log_message(
            "LCD-GIF: Exklusiver Kraken-Zugriff beendet · Statusabfragen und Kühlbefehle wieder freigegeben."
        )

    def defer_cooling_action_for_gif(self, action: str, callback: Callable[[], None]) -> bool:
        """Temporarily release the streamer's USB ownership for one cooling write.

        The streamer process and its prepared frame cache stay alive.  Only the
        Kraken device handles are closed until the GUI's serial liquidctl queue
        has completed the requested pump/fan transaction.
        """
        if self.gif_cooling_window_open:
            return False
        if self.gif_cooling_transaction_active:
            self.footer_status.setText("Eine Kühlungsänderung während der Animation läuft bereits …")
            self.log_message(f"LCD-GIF-KÜHLUNG: {action} nicht zusätzlich gestartet · Transaktion bereits aktiv.")
            return True
        if self.is_gif_stream_running():
            self.gif_cooling_transaction_active = True
            self.gif_cooling_waiting_resume = False
            self.gif_cooling_deadline = time.monotonic() + 5.0
            self.gif_cooling_action = action
            self.gif_cooling_callback = callback
            self.gif_status_label.setText("GIF-Stream: pausiert kurz für Kühlungsänderung …")
            self.footer_status.setText(f"{action}: Animation gibt den Kraken-Zugriff kurz frei …")
            self.log_message(
                f"LCD-GIF-KÜHLUNG: {action} angefordert · Stream und Framecache bleiben aktiv · "
                "USB-Zugriff wird koordiniert freigegeben."
            )
            written = self.gif_process.write(b"PAUSE\n")
            self.gif_process.waitForBytesWritten(100)
            if written < 0:
                self.abort_gif_cooling_transaction("PAUSE konnte nicht an den Streamer gesendet werden")
            else:
                QTimer.singleShot(5100, self.check_gif_cooling_handoff_timeout)
            return True
        if self.gif_start_pending or self.gif_kraken_io_paused:
            self.footer_status.setText(f"{action} wartet · GIF-Stream übernimmt gerade den Kraken-Zugriff")
            self.log_message(f"LCD-GIF-KÜHLUNG: {action} während Streamstart nicht möglich.")
            return True
        return False

    def begin_deferred_gif_cooling_action(self) -> None:
        if not self.gif_cooling_transaction_active or self.gif_cooling_callback is None:
            self.abort_gif_cooling_transaction("PAUSE-Bestätigung ohne wartenden Kühlungsbefehl")
            return
        self.gif_watchdog_timer.stop()
        self.gif_last_heartbeat = 0.0
        self.gif_cooling_window_open = True
        self.gif_cooling_deadline = 0.0
        callback, self.gif_cooling_callback = self.gif_cooling_callback, None
        self.gif_status_label.setText("GIF-Stream: USB freigegeben · Kühlungsänderung läuft …")
        self.log_message(
            f"LCD-GIF-KÜHLUNG: Streamer hat USB freigegeben · {self.gif_cooling_action} wird jetzt exklusiv übertragen."
        )
        QTimer.singleShot(0, callback)
        QTimer.singleShot(0, self.finish_gif_cooling_when_idle)

    def finish_gif_cooling_when_idle(self) -> None:
        if not self.gif_cooling_transaction_active or not self.gif_cooling_window_open:
            return
        if self.kraken_write_busy or self.status_busy or self.lcd_busy or not self.backend.is_idle():
            QTimer.singleShot(75, self.finish_gif_cooling_when_idle)
            return
        if not self.is_gif_stream_running():
            self.reset_gif_cooling_transaction()
            return
        self.gif_cooling_window_open = False
        self.gif_cooling_waiting_resume = True
        self.gif_cooling_deadline = time.monotonic() + 8.0
        self.gif_status_label.setText("GIF-Stream: USB-Befehlsfenster beendet · Animation wird fortgesetzt …")
        self.footer_status.setText("Kraken-Zugriff beendet · Animation wird fortgesetzt …")
        self.log_message(
            f"LCD-GIF-KÜHLUNG: USB-Befehlsfenster für {self.gif_cooling_action} beendet · "
            "Streamer übernimmt USB wieder."
        )
        written = self.gif_process.write(b"RESUME\n")
        self.gif_process.waitForBytesWritten(100)
        if written < 0:
            self.abort_gif_cooling_transaction("RESUME konnte nicht an den Streamer gesendet werden")
        else:
            QTimer.singleShot(8100, self.check_gif_cooling_handoff_timeout)

    def check_gif_cooling_handoff_timeout(self) -> None:
        if not self.gif_cooling_transaction_active or self.gif_cooling_deadline <= 0.0:
            return
        if time.monotonic() < self.gif_cooling_deadline:
            return
        phase = "Fortsetzen" if self.gif_cooling_waiting_resume else "USB-Freigabe"
        self.abort_gif_cooling_transaction(f"Zeitüberschreitung bei {phase} des GIF-Streamers")

    def complete_gif_cooling_transaction(self, pause_ms: object) -> None:
        action = self.gif_cooling_action or "Kühlungsänderung"
        self.reset_gif_cooling_transaction()
        self.gif_last_heartbeat = time.monotonic()
        self.gif_watchdog_timer.start()
        self.gif_status_label.setText("GIF-Stream: aktiv · nach Kühlungsänderung fortgesetzt")
        self.footer_status.setText("GIF-Animation läuft nach der USB-Übergabe weiter")
        self.log_message(
            f"LCD-GIF-KÜHLUNG: USB-Übergabe für {action} abgeschlossen · Animation nach {pause_ms} ms "
            "mit bestehendem Framecache fortgesetzt."
        )

    def abort_gif_cooling_transaction(self, reason: str) -> None:
        self.log_message(f"LCD-GIF-KÜHLUNG-FEHLER: {reason}")
        self.reset_gif_cooling_transaction()
        if self.is_gif_stream_running():
            self.gif_safety_stop = True
            self.gif_process.terminate()
            self.gif_force_stop_timer.start(1500)
        else:
            self.show_error(reason)

    def reset_gif_cooling_transaction(self) -> None:
        self.gif_cooling_transaction_active = False
        self.gif_cooling_window_open = False
        self.gif_cooling_waiting_resume = False
        self.gif_cooling_deadline = 0.0
        self.gif_cooling_action = ""
        self.gif_cooling_callback = None

    def kraken_command_blocked_by_gif(self, action: str) -> bool:
        if not (self.gif_kraken_io_paused or self.gif_start_pending or self.is_gif_stream_running()):
            return False
        self.footer_status.setText(f"{action} pausiert · GIF-Stream besitzt exklusiven Kraken-Zugriff")
        self.log_message(
            f"LCD-GIF: {action} nicht gestartet · der CAM-Raw-Stream besitzt exklusiven Kraken-Zugriff."
        )
        return True

    def start_gif_stream(
        self,
        _checked: bool = False,
        *,
        source_path: Path | None = None,
        generated_hardware: bool = False,
        fps_override: int | None = None,
        interpolate_override: bool | None = None,
    ) -> None:
        if self.is_gif_stream_running() or self.gif_start_pending:
            return
        # A timeout armed for a previous stream must never terminate this new QProcess.
        self.gif_force_stop_timer.stop()
        if not self.devices_ready:
            self.show_error("Die Kraken ist noch nicht verbunden.")
            return
        if self.lcd_recovery_required:
            self.show_error("Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.")
            return
        stream_source = Path(source_path) if source_path is not None else self.selected_lcd_file
        if not stream_source or stream_source.suffix.lower() != ".gif":
            self.show_error("Bitte zuerst eine animierte GIF-Datei auswählen.")
            return
        helper = Path(__file__).with_name(GIF_HELPER_NAME)
        if not helper.exists():
            self.show_error(f"GIF-Helfer fehlt: {helper.name}")
            return
        if not generated_hardware and not self.gif_warning_acknowledged:
            answer = QMessageBox.warning(
                self,
                "Experimenteller Firmware-2.x-GIF-Streamer",
                "Firmware 2.x bietet in liquidctl keinen nativen GIF-Modus. Kraken Control emuliert die Animation, indem "
                "vorbereitete 240×240-Frames wiederholt über den liquidctl-Treiber an das LCD übertragen werden. Die "
                "Langzeitwirkung häufiger Uploads ist nicht ausreichend bekannt. GIF-Stream trotzdem starten?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.gif_warning_acknowledged = True
            self.settings.setValue("gif/experimental_warning_ack", True)
            self.settings.sync()
            self.update_experimental_notice_status()
            self.log_message("LCD-GIF: Experimentalhinweis dauerhaft bestätigt.")
        else:
            if not generated_hardware:
                self.log_message("LCD-GIF: Experimentalhinweis bereits bestätigt · Start ohne Dialog.")

        self.gif_stream_source_file = stream_source
        self.gif_stream_fps_override = fps_override
        self.gif_stream_interpolate_override = interpolate_override
        self.gif_generated_hardware_mode = generated_hardware

        # Only one experimental LCD writer may be active.  Stop timers before
        # the helper acquires its persistent liquidctl connection.
        self.stop_hardware_lcd_mode(update_status=False, clear_marker=False)
        self.stop_clock_mode(update_status=False, clear_marker=False)
        self.lcd_keepalive_timer.stop()
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(False)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(False)
        self.settings.setValue("lcd/keepalive", False)
        self.settings.setValue("clock/active", False)

        self.gif_start_pending = True
        self.gif_start_wait_deadline = time.monotonic() + GIF_STREAM_START_WAIT_SECONDS
        self.pause_kraken_io_for_gif()
        self.gif_status_label.setText("GIF-Stream: wartet auf exklusiven Kraken-Zugriff …")
        self.footer_status.setText("GIF-Animation wartet auf Abschluss laufender Kraken-Befehle …")
        self.update_gif_controls()
        QTimer.singleShot(0, self.launch_gif_stream_when_idle)

    def launch_gif_stream_when_idle(self) -> None:
        if not self.gif_start_pending:
            return
        if not self.gif_kraken_backend_idle():
            if time.monotonic() >= self.gif_start_wait_deadline:
                self.gif_start_pending = False
                self.resume_kraken_io_after_gif()
                was_generated = self.gif_generated_hardware_mode
                self.gif_generated_hardware_mode = False
                self.gif_stream_source_file = None
                self.gif_stream_fps_override = None
                self.gif_stream_interpolate_override = None
                self.update_gif_controls()
                self.gif_status_label.setText("GIF-Stream: Start abgebrochen")
                if was_generated:
                    self.hardware_animation_status_label.setText(self.tr_static("Hardwareanimation: Start abgebrochen"))
                self.show_error(
                    "Der GIF-Stream konnte den exklusiven Kraken-Zugriff nicht innerhalb von 15 Sekunden übernehmen. "
                    "Bitte den laufenden Befehl abschließen lassen und erneut starten."
                )
                return
            QTimer.singleShot(100, self.launch_gif_stream_when_idle)
            return

        stream_source = self.gif_stream_source_file
        hardware_spec_missing = self.gif_generated_hardware_mode and not self.hardware_animation_spec_file.exists()
        if not stream_source or not stream_source.exists() or hardware_spec_missing:
            self.gif_start_pending = False
            self.resume_kraken_io_after_gif()
            was_generated = self.gif_generated_hardware_mode
            self.gif_generated_hardware_mode = False
            self.gif_stream_source_file = None
            self.gif_stream_fps_override = None
            self.gif_stream_interpolate_override = None
            self.update_gif_controls()
            self.gif_status_label.setText("GIF-Stream: Datei nicht mehr vorhanden")
            if was_generated:
                self.hardware_animation_status_label.setText(self.tr_static("Hardwareanimation: Datei nicht mehr vorhanden"))
            self.show_error("Die ausgewählte GIF-Datei ist vor dem Streamstart nicht mehr verfügbar.")
            return

        self.gif_start_pending = False
        helper = Path(__file__).with_name(GIF_HELPER_NAME)
        fps = self.gif_stream_fps_override if self.gif_stream_fps_override is not None else int(self.gif_fps_combo.currentData() or 0)
        transport_mode = str(self.gif_transport_combo.currentData() or "cam")
        interpolate = self.gif_stream_interpolate_override if self.gif_stream_interpolate_override is not None else self.gif_interpolate_checkbox.isChecked()
        args = [str(helper)]
        if self.gif_generated_hardware_mode:
            args.extend(["--hardware-spec", str(self.hardware_animation_spec_file)])
        else:
            args.extend(["--file", str(stream_source)])
        args.extend([
            "--orientation", self.lcd_orientation.currentText(),
            "--fps", str(fps),
            "--transport", transport_mode,
        ])
        if interpolate:
            args.append("--interpolate")
        self.gif_user_stop_requested = False
        self.gif_safety_stop = False
        self.reset_gif_cooling_transaction()
        self.gif_stream_active = False
        self.gif_stop_callbacks.clear()
        self.gif_stdout_buffer = ""
        self.gif_last_heartbeat = 0.0
        self.gif_watchdog_timer.stop()
        self.experimental_autostart_blocked = False
        self.mark_experimental_lcd_active("hardware_animation" if self.gif_generated_hardware_mode else "gif")
        if not self.gif_generated_hardware_mode:
            self.settings.setValue("gif/fps", fps)
            self.settings.setValue("gif/transport_mode", transport_mode)
            self.settings.setValue("gif/interpolate", interpolate)
        self.gif_status_label.setText("GIF-Stream: Frames werden vorbereitet …")
        self.gif_loop_warning_label.hide()
        self.gif_loop_warning_label.clear()
        self.footer_status.setText("GIF-Animation wird vorbereitet …")
        self.gif_process.setProgram(sys.executable)
        self.gif_process.setArguments(args)
        self.gif_process.setWorkingDirectory(str(helper.parent))
        self.gif_process.start()
        self.update_gif_controls()
        content_text = "CAM-nah · automatisch · Inhalt max. 25 FPS" if fps == 0 else f"Inhalt {fps} FPS"
        transport_text = {
            "cam": "CAM-Raw-LCD-Transport 26,667 Hz · phasenstabil · Standard",
            "safe": "CAM-Raw-LCD-Transport fest 25,6 Hz · sicher",
        }.get(transport_mode, f"LCD-Transport {transport_mode}")
        rate_text = f"{content_text} · {transport_text}"
        self.log_message(
            f"LCD-GIF: Stream wird vorbereitet · Datei {stream_source.name} · "
            f"Ausrichtung {self.lcd_orientation.currentText()}° · {rate_text} · "
            f"Motion-Interpolation {'ein' if interpolate else 'aus'} · exklusiver Kraken-Zugriff aktiv"
        )

    def stop_gif_stream(self, on_stopped: Callable[[], None] | None = None) -> None:
        if on_stopped is not None:
            self.gif_stop_callbacks.append(on_stopped)
        if self.gif_start_pending and not self.is_gif_stream_running():
            self.gif_start_pending = False
            self.resume_kraken_io_after_gif()
            was_generated = self.gif_generated_hardware_mode
            self.gif_generated_hardware_mode = False
            self.gif_stream_source_file = None
            self.gif_stream_fps_override = None
            self.gif_stream_interpolate_override = None
            self.update_gif_controls()
            self.gif_status_label.setText("GIF-Stream: Start abgebrochen")
            if was_generated:
                self.hardware_animation_status_label.setText(self.tr_static("Hardwareanimation: Start abgebrochen"))
            callbacks, self.gif_stop_callbacks = self.gif_stop_callbacks, []
            for callback in callbacks:
                QTimer.singleShot(0, callback)
            return
        if not self.is_gif_stream_running():
            if self.gif_generated_hardware_mode:
                self.gif_generated_hardware_mode = False
                self.gif_stream_source_file = None
                self.gif_stream_fps_override = None
                self.gif_stream_interpolate_override = None
                self.update_hardware_animation_controls()
            callbacks, self.gif_stop_callbacks = self.gif_stop_callbacks, []
            for callback in callbacks:
                QTimer.singleShot(0, callback)
            return
        if not self.gif_user_stop_requested:
            self.gif_user_stop_requested = True
            self.gif_status_label.setText("GIF-Stream: wird sauber beendet …")
            self.gif_process.write(b"STOP\n")
            self.gif_process.waitForBytesWritten(100)
            self.gif_force_stop_timer.start(3500)

    def force_stop_gif_stream_if_needed(self) -> None:
        if self.is_gif_stream_running() and (self.gif_user_stop_requested or self.gif_safety_stop):
            self.log_message("LCD-GIF: Helfer reagierte nicht rechtzeitig · Prozess wird beendet.")
            self.gif_process.terminate()
            if not self.gif_process.waitForFinished(800):
                self.gif_process.kill()

    def check_gif_stream_watchdog(self) -> None:
        if (
            not self.is_gif_stream_running()
            or self.gif_user_stop_requested
            or self.gif_last_heartbeat <= 0.0
        ):
            return
        stalled_for = time.monotonic() - self.gif_last_heartbeat
        if stalled_for <= GIF_STREAM_WATCHDOG_SECONDS:
            return
        self.gif_last_heartbeat = 0.0
        self.gif_safety_stop = True
        self.gif_status_label.setText("GIF-Stream: USB-Übertragung reagiert nicht · Sicherheitsstopp …")
        self.log_message(
            f"LCD-GIF-SICHERHEIT: seit {stalled_for:.1f} Sekunden kein Lebenszeichen · "
            "Streamer wird beendet und Flüssigkeitstemperatur wiederhergestellt."
        )
        self.gif_process.terminate()
        self.gif_force_stop_timer.start(1500)

    def shutdown_gif_stream_sync(self) -> None:
        self.gif_start_pending = False
        self.gif_watchdog_timer.stop()
        if not self.is_gif_stream_running():
            return
        self.gif_user_stop_requested = True
        self.gif_process.write(b"STOP\n")
        self.gif_process.waitForBytesWritten(100)
        if not self.gif_process.waitForFinished(2500):
            self.gif_process.terminate()
            if not self.gif_process.waitForFinished(700):
                self.gif_process.kill()
                self.gif_process.waitForFinished(700)
        self.gif_stream_active = False
        self.gif_force_stop_timer.stop()

    def on_gif_stream_stdout(self) -> None:
        raw = bytes(self.gif_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self.gif_stdout_buffer += raw
        while "\n" in self.gif_stdout_buffer:
            line, self.gif_stdout_buffer = self.gif_stdout_buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                self.log_message("LCD-GIF-Helfer: " + line)
                continue
            kind = str(event.get("event", ""))
            if kind == "ready":
                self.gif_last_heartbeat = time.monotonic()
                self.gif_watchdog_timer.start()
                source_frames = event.get("source_frames", "?")
                transport_frames = event.get("transport_cache_frames", event.get("output_frames", event.get("frames", "?")))
                content_frames = event.get("content_frames", "?")
                content_fps = event.get("content_fps", event.get("output_fps", "?"))
                target_fps = event.get("target_fps", content_fps)
                transport_fps = event.get("transport_fps", content_fps)
                interpolation = "ein" if event.get("interpolation", False) else "aus"
                blended = event.get("interpolated_transport_frames", 0)
                self.gif_status_label.setText(
                    f"GIF-Stream: {content_frames} Inhaltsframes → {transport_frames} LCD-Phasenbilder · {content_fps} FPS Inhalt · {transport_fps} Hz LCD"
                )
                if self.gif_generated_hardware_mode:
                    self.hardware_animation_status_label.setText(
                        f"{self.tr_static('Hardwareanimation vorbereitet')} · {content_frames} {self.tr_static('Frames')} · {content_fps} FPS"
                    )
                self.log_message(
                    f"LCD-GIF: {source_frames} Quellframes → {content_frames} Inhaltsframes → {transport_frames} LCD-Phasenbilder · "
                    f"Zielinhalt {target_fps} FPS · tatsächlicher Inhaltstakt {content_fps} FPS · LCD-Nennrate {transport_fps} Hz · "
                    f"Motion-Interpolation {interpolation} · Zwischenphasen {blended} · erkannte Bewegungs-Paare {event.get('motion_pairs', 0)} · eindeutige LCD-Frames {event.get('unique_transport_frames', '?')} · Cache {event.get('transport_cache_fps', '?')} Bilder/s · "
                    f"Quelllaufzeit {event.get('source_duration_ms', '?')} ms · Schutzabstand {event.get('guard_ms', '?')} ms · "
                    f"ACK-Zuordnung {'aktiv' if event.get('ack_matching', False) else 'aus'} · "
                    f"Vorbereitung {event.get('prepare_ms', '?')} ms · liquidctl {event.get('liquidctl', '?')}"
                )
                if event.get("loop_warning", False):
                    warning = "Der Loop dieser GIF-Datei enthält wahrscheinlich einen sichtbaren Übergang."
                    self.gif_loop_warning_label.setText(warning)
                    self.gif_loop_warning_label.show()
                    self.log_message(
                        f"LCD-GIF-HINWEIS: {warning} · Übergangswert {event.get('loop_transition_score', '?')} · "
                        f"typisch {event.get('typical_transition_score', '?')} · Verhältnis {event.get('loop_warning_ratio', '?')}×"
                    )
                else:
                    self.gif_loop_warning_label.hide()
                    self.gif_loop_warning_label.clear()
            elif kind == "started":
                self.gif_last_heartbeat = time.monotonic()
                self.gif_stream_active = True
                pacing_text = (
                    "26,667-Hz-CAM-Takt · phasenstabil"
                    if event.get("phase_locked", False) and event.get("transport_mode") == "cam"
                    else "fester 25,6-Hz-Takt · phasenstabil"
                )
                self.gif_status_label.setText(f"GIF-Stream: aktiv · CAM-Rohtransport · {pacing_text}")
                if self.gif_generated_hardware_mode:
                    self.lcd_mode_label.setText(self.tr_static("LCD-Modus: animierte Hardwaredaten · experimentell"))
                    self.footer_status.setText(self.tr_static("Hardwareanimation aktiv"))
                    self.hardware_animation_status_label.setText(
                        f"{self.tr_static('Hardwareanimation aktiv')} · {event.get('content_fps', event.get('output_fps', '?'))} FPS · "
                        f"{self.animated_hardware_live_summary(str(event.get('hardware_design') or 'water_halo'))}"
                    )
                else:
                    self.lcd_mode_label.setText("LCD-Modus: GIF-Stream · experimentell")
                    self.footer_status.setText("Experimentelle GIF-Animation aktiv")
                interp = "ein" if event.get("interpolation", False) else "aus"
                self.log_message(
                    f"LCD-GIF: CAM-Raw-Stream {APP_VERSION} gestartet · {event.get('transport_cache_frames', event.get('frames', '?'))} LCD-Phasenbilder · "
                    f"Inhalt {event.get('content_fps', event.get('output_fps', '?'))} FPS · LCD-Nennrate {event.get('transport_fps', '?')} Hz · "
                    f"Transportmodus {event.get('transport_mode', '?')} · Rohpfad {'ja' if event.get('raw_transport', False) else 'nein'} · Motion-Interpolation {interp} · Bewegungs-Paare {event.get('motion_pairs', 0)} · "
                    f"Framebuffer-Priming {event.get('prime_ms', '?')} ms · Schutzabstand {event.get('guard_ms', '?')} ms · "
                    f"ACK-Zuordnung {'aktiv' if event.get('ack_matching', False) else 'aus'} · fremde HID-Berichte {event.get('unrelated_hid_reports', 0)} · "
                    f"LCD-Phasen = streng fortlaufend"
                )
            elif kind == "paused":
                self.gif_last_heartbeat = 0.0
                self.begin_deferred_gif_cooling_action()
            elif kind == "resumed":
                if not self.gif_cooling_transaction_active or not self.gif_cooling_waiting_resume:
                    self.abort_gif_cooling_transaction("unerwartete RESUME-Bestätigung des Streamers")
                    continue
                self.complete_gif_cooling_transaction(event.get("pause_ms", "?"))
            elif kind == "sensor_update":
                self.gif_last_heartbeat = time.monotonic()

                def sensor_text(value: object) -> str:
                    try:
                        return f"{float(value):.0f}°"
                    except (TypeError, ValueError):
                        return "—"

                cpu_text = sensor_text(event.get("cpu"))
                gpu_text = sensor_text(event.get("gpu"))
                liquid_text = sensor_text(event.get("liquid_snapshot"))
                design_id = str(event.get("hardware_design") or "water_halo")
                values: list[str] = []
                if bool(event.get("cpu_live", False)):
                    values.append(f"CPU {cpu_text}")
                if bool(event.get("gpu_live", False)):
                    values.append(f"GPU {gpu_text}")
                if design_id in {"water_halo", "system_trio"}:
                    values.append(f"{self.tr_static('Wasser zuletzt')} {liquid_text}")
                self.hardware_animation_status_label.setText(
                    f"{self.tr_static('Livewerte aktualisiert')} · {' · '.join(values)}"
                )
                self.log_message(
                    f"LCD-HARDWARE-LIVE: CPU {cpu_text} · GPU {gpu_text} · Wasser zuletzt {liquid_text} · "
                    f"Cache {event.get('transport_cache_frames', '?')} Frames · Erzeugung {event.get('generation_ms', '?')} ms"
                )
            elif kind == "sensor_update_error":
                self.gif_last_heartbeat = time.monotonic()
                detail = str(event.get("message", "unbekannter Fehler"))
                self.hardware_animation_status_label.setText(
                    f"{self.tr_static('Livewert-Aktualisierung fehlgeschlagen')} · {detail}"
                )
                self.log_message(f"LCD-HARDWARE-LIVE: Aktualisierung fehlgeschlagen · {detail}")
            elif kind == "stats":
                self.gif_last_heartbeat = time.monotonic()
                fps = event.get("effective_fps", "?")
                upload = event.get("last_upload_ms", "?")
                mode = event.get("pacing", "?")
                misses = event.get("deadline_misses", 0)
                repeats = event.get("content_repeats", 0)
                content_skips = event.get("content_skips", 0)
                lcd_repeats = event.get("lcd_frame_repeats", 0)
                lcd_skips = event.get("lcd_frame_skips", 0)
                transport = event.get("transport_fps", "?")
                content = event.get("content_fps", "?")
                hist = event.get("histogram", {}) or {}
                self.gif_status_label.setText(
                    f"GIF-Stream: aktiv · {fps} Hz effektiv · Inhalt {content} FPS · LCD-Nennrate {transport} Hz · Zeitfenster voll {misses}"
                )
                if self.gif_generated_hardware_mode:
                    self.hardware_animation_status_label.setText(
                        f"{self.tr_static('Hardwareanimation aktiv')} · {fps} Hz · {self.tr_static('Upload')} {upload} ms"
                    )
                self.log_message(
                    f"LCD-GIF: Messung · effektiv {fps} Hz · Inhalt {content} FPS · LCD-Nennrate {transport} Hz · "
                    f"Upload {upload} ms · EMA {event.get('upload_ema_ms', '?')} ms · P90 {event.get('p90_upload_ms', '?')} ms · "
                    f"Maximum {event.get('max_upload_ms', '?')} ms · Zeitfenster voll {misses} · "
                    f"Überlauf gesamt {event.get('total_overrun_ms', 0)} ms · max. Überlauf {event.get('max_overrun_ms', 0)} ms · "
                    f"LCD-Frame-Wiederholungen {lcd_repeats} · LCD-Frame-Sprünge {lcd_skips} · "
                    f"logische Inhaltsphasen wiederholt {repeats} · Inhalts-Sprünge {content_skips} · "
                    f"Jitter <20/{hist.get('lt20', 0)} 20–30/{hist.get('20_30', 0)} "
                    f"30–35/{hist.get('30_35', 0)} 35–42/{hist.get('35_42', 0)} ≥42/{hist.get('ge42', 0)} · "
                    f"fremde HID-Berichte {event.get('unrelated_hid_reports', 0)} · "
                    f"Transportframes übersprungen 0 · Taktung {mode}"
                )
            elif kind == "stopped":
                self.gif_last_heartbeat = time.monotonic()
                self.log_message(
                    f"LCD-GIF: Stream sauber beendet · Transportframes {event.get('frames_sent', '?')} · "
                    f"Transportframes übersprungen 0 · Zeitfenster voll {event.get('deadline_misses', 0)} · "
                    f"LCD-Frame-Wiederholungen {event.get('lcd_frame_repeats', 0)} · LCD-Frame-Sprünge {event.get('lcd_frame_skips', 0)} · "
                    f"logische Inhaltsphasen wiederholt {event.get('content_repeats', 0)} · Inhalts-Sprünge {event.get('content_skips', 0)} · "
                    f"fremde HID-Berichte {event.get('unrelated_hid_reports', 0)}"
                )
            elif kind == "error":
                self.log_message("LCD-GIF-FEHLER: " + str(event.get("message", "unbekannter Fehler")))

    def on_gif_stream_stderr(self) -> None:
        raw = bytes(self.gif_process.readAllStandardError()).decode("utf-8", errors="replace").strip()
        if raw:
            self.log_message("LCD-GIF-Helfer: " + raw)

    def on_gif_stream_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self.gif_force_stop_timer.stop()
        self.gif_watchdog_timer.stop()
        self.gif_last_heartbeat = 0.0
        was_requested = self.gif_user_stop_requested
        was_safety = self.gif_safety_stop
        was_generated = self.gif_generated_hardware_mode
        self.reset_gif_cooling_transaction()
        self.gif_stream_active = False
        self.gif_user_stop_requested = False
        self.gif_safety_stop = False
        self.gif_generated_hardware_mode = False
        self.gif_stream_source_file = None
        self.gif_stream_fps_override = None
        self.gif_stream_interpolate_override = None
        self.update_gif_controls()
        callbacks, self.gif_stop_callbacks = self.gif_stop_callbacks, []
        self.resume_kraken_io_after_gif(schedule_refresh=not was_safety and (exit_code == 0 or was_requested))
        if was_safety:
            self.gif_status_label.setText("GIF-Stream: Sicherheitsstopp")
            self.activate_lcd_safe_mode("GIF-Streamer ohne Lebenszeichen beendet")
        elif exit_code == 0 or was_requested:
            if not self.lcd_recovery_required and not self.clock_active and not self.keep_lcd_checkbox.isChecked():
                self.clear_experimental_lcd_marker()
            self.gif_status_label.setText("GIF-Stream: angehalten")
            if was_generated:
                self.hardware_animation_status_label.setText(
                    self.tr_static("Hardwareanimation angehalten · das letzte Bild kann sichtbar bleiben.")
                )
                self.footer_status.setText(self.tr_static("Hardwareanimation angehalten"))
            else:
                self.footer_status.setText("GIF-Animation angehalten")
            if not was_safety:
                self.log_message("LCD-GIF: Stream beendet.")
        else:
            self.gif_status_label.setText(f"GIF-Stream: Fehler · Exit {exit_code}")
            if was_generated:
                self.hardware_animation_status_label.setText(f"{self.tr_static('Hardwareanimation: Fehler')} · Exit {exit_code}")
            self.activate_lcd_safe_mode(f"GIF-Streamer unerwartet beendet (Exit {exit_code})")
        for callback in callbacks:
            QTimer.singleShot(0, callback)

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
            self.update_clock_lcd(force=True)

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
        if self.is_gif_stream_running():
            self.stop_gif_stream(lambda: self.start_clock_mode())
            return
        if not self.devices_ready:
            self.show_error("Die Kraken ist noch nicht verbunden.")
            return
        if self.lcd_recovery_required:
            self.show_error("Der LCD-Sicherheitsmodus wartet noch auf die Wiederherstellung der Flüssigkeitstemperatur.")
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
            self.settings.setValue("clock/experimental_warning_ack", True)
            self.settings.sync()
            self.update_experimental_notice_status()
            self.log_message("LCD-UHR: Experimentalhinweis dauerhaft bestätigt.")
        else:
            self.log_message("LCD-UHR: Experimentalhinweis bereits bestätigt · Start ohne Dialog.")
        self.stop_hardware_lcd_mode(update_status=False, clear_marker=False)
        self.lcd_keepalive_timer.stop()
        self.keep_lcd_checkbox.blockSignals(True)
        self.keep_lcd_checkbox.setChecked(False)
        self.keep_lcd_checkbox.blockSignals(False)
        self.set_keepalive_controls(False)
        self.clock_active = True
        self.experimental_autostart_blocked = False
        self.mark_experimental_lcd_active("clock")
        self.settings.setValue("clock/active", True)
        self.settings.setValue("lcd/keepalive", False)
        fmt = "24h" if str(self.clock_format.currentData()) == "24" else "12h AM/PM"
        resend = f"alle {self.clock_resend_interval.value()} s" if self.clock_auto_resend.isChecked() else "aus"
        self.log_message(f"LCD-UHR: gestartet · Format {fmt} · Datum={'ein' if self.clock_show_date.isChecked() else 'aus'} · automatisches Senden {resend}")
        self.update_clock_lcd(force=True)

    def stop_clock_mode(self, update_status: bool = True, clear_marker: bool = True) -> None:
        self.clock_active = False
        self.clock_timer.stop()
        self.clock_keepalive_timer.stop()
        self.settings.setValue("clock/active", False)
        if clear_marker and not (hasattr(self, "keep_lcd_checkbox") and self.keep_lcd_checkbox.isChecked()):
            self.clear_experimental_lcd_marker()
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

    def update_clock_lcd(self, force: bool = False) -> None:
        if not self.clock_active:
            return
        current_minute_key = time.strftime("%Y%m%d%H%M")
        if not force and self.clock_last_minute_upload_key == current_minute_key:
            self.schedule_next_clock_update()
            return
        if self.lcd_busy or self.kraken_write_busy:
            self.clock_timer.start(2000)
            return
        try:
            image_path = self.render_clock_image()
        except Exception as exc:  # noqa: BLE001
            self.log_message(f"LCD-UHR: Rendererfehler · {exc}")
            self.activate_lcd_safe_mode(f"LCD-Uhr-Rendererfehler: {exc}")
            return

        def uploaded(result: CommandResult) -> None:
            if result.ok and self.clock_active:
                self.lcd_failure_count = 0
                self.clock_last_minute_upload_key = self.clock_render_key
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
                    QTimer.singleShot(100, lambda: self.update_clock_lcd(force=True))
                else:
                    self.schedule_next_clock_update()
            elif not result.ok:
                detail = result.combined or "unbekannter Fehler"
                if not self.record_lcd_failure("LCD-Uhr-Upload", detail):
                    self.clock_status_label.setText(
                        f"Uhr: Uploadfehler {self.lcd_failure_count}/{LCD_FAILURE_LIMIT} · erneuter Versuch folgt."
                    )
                    if self.clock_active:
                        self.clock_timer.start(3000)

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
            if result.ok:
                self.lcd_failure_count = 0
            else:
                detail = result.combined or "unbekannter Fehler"
                if not self.record_lcd_failure("LCD-Uhr-Fallback", detail):
                    self.clock_status_label.setText(
                        f"Uhr bleibt aktiv · Fallbackfehler {self.lcd_failure_count}/{LCD_FAILURE_LIMIT}."
                    )

        # Das vorhandene Minutenbild wird erneut gesendet; neu gerendert wird erst zum Minutenwechsel.
        self.send_static_lcd(self.clock_image_file, quiet=True, completion=resent)

    # ---------- LCD experimental safety ----------
    def update_experimental_notice_status(self) -> None:
        if not hasattr(self, "experimental_notice_status"):
            return
        clock_ack = getattr(self, "clock_warning_acknowledged", self.settings.value("clock/experimental_warning_ack", False, type=bool))
        keepalive_ack = getattr(self, "keepalive_warning_acknowledged", self.settings.value("lcd/keepalive_warning_ack", False, type=bool))
        gif_ack = getattr(self, "gif_warning_acknowledged", self.settings.value("gif/experimental_warning_ack", False, type=bool))
        hardware_ack = getattr(self, "hardware_lcd_warning_acknowledged", self.settings.value("hardware_lcd/experimental_warning_ack", False, type=bool))
        animation_ack = getattr(self, "hardware_animation_warning_acknowledged", self.settings.value("hardware_animation/experimental_warning_ack", False, type=bool))
        clock = "✓" if clock_ack else "○"
        keepalive = "✓" if keepalive_ack else "○"
        gif = "✓" if gif_ack else "○"
        hardware = "✓" if hardware_ack else "○"
        animation = "✓" if animation_ack else "○"
        recovery = f" · {self.tr_static('LCD-Sicherheitswiederherstellung vorgemerkt')}" if self.lcd_recovery_required else ""
        self.experimental_notice_status.setText(
            f"{clock} {self.tr_static('LCD-Uhr-Hinweis')} · {keepalive} {self.tr_static('LCD-Fallback-Hinweis')} · "
            f"{gif} {self.tr_static('GIF-Streamer-Hinweis')} · {hardware} {self.tr_static('Live-Hardwaredesign-Hinweis')} · "
            f"{animation} {self.tr_static('Hardwareanimation-Hinweis')}{recovery}"
        )

    def reset_experimental_warnings(self) -> None:
        self.clock_warning_acknowledged = False
        self.keepalive_warning_acknowledged = False
        self.gif_warning_acknowledged = False
        self.hardware_lcd_warning_acknowledged = False
        self.hardware_animation_warning_acknowledged = False
        self.settings.setValue("clock/experimental_warning_ack", False)
        self.settings.setValue("lcd/keepalive_warning_ack", False)
        self.settings.setValue("gif/experimental_warning_ack", False)
        self.settings.setValue("hardware_lcd/experimental_warning_ack", False)
        self.settings.setValue("hardware_animation/experimental_warning_ack", False)
        self.settings.sync()
        self.update_experimental_notice_status()
        self.log_message("LCD: Experimentalhinweise zurückgesetzt · Hinweise werden beim nächsten Aktivieren wieder angezeigt.")
        QMessageBox.information(
            self,
            DISPLAY_NAME,
            "Die Experimentalhinweise wurden zurückgesetzt und werden beim nächsten Aktivieren wieder angezeigt.",
        )

    def mark_experimental_lcd_active(self, mode: str) -> None:
        self.settings.setValue("lcd/experimental_session_active", True)
        self.settings.setValue("lcd/experimental_mode", mode)
        self.settings.sync()

    def clear_experimental_lcd_marker(self) -> None:
        self.settings.setValue("lcd/experimental_session_active", False)
        self.settings.remove("lcd/experimental_mode")
        self.settings.sync()

    def mark_clean_shutdown(self) -> None:
        # A clean exit is different from stopping the feature: clock/active may
        # remain true so a deliberately enabled clock can resume next boot, but
        # the crash marker must be removed.
        self.clear_experimental_lcd_marker()

    def arm_lcd_recovery(self, reason: str) -> None:
        self.lcd_safety_reason = reason
        self.lcd_recovery_required = True
        if self.gif_start_pending or self.is_gif_stream_running():
            self.gif_safety_stop = True
            self.stop_gif_stream()
        self.hardware_lcd_active = False
        self.hardware_lcd_timer.stop()
        self.clock_active = False
        self.clock_timer.stop()
        self.clock_keepalive_timer.stop()
        self.lcd_keepalive_timer.stop()
        if hasattr(self, "keep_lcd_checkbox"):
            self.keep_lcd_checkbox.blockSignals(True)
            self.keep_lcd_checkbox.setChecked(False)
            self.keep_lcd_checkbox.blockSignals(False)
            self.set_keepalive_controls(False)
        self.settings.setValue("clock/active", False)
        self.settings.setValue("hardware_lcd/active", False)
        self.settings.setValue("lcd/keepalive", False)
        self.settings.setValue("lcd/recovery_required", True)
        self.settings.setValue("lcd/experimental_session_active", False)
        self.settings.sync()
        self.update_experimental_notice_status()
        self.log_message(f"SICHERHEIT: experimentelle LCD-Funktion gestoppt · {reason}")

    def activate_lcd_safe_mode(self, reason: str, *, preserve_recovery: bool = False, retry: int = 0) -> None:
        if retry == 0:
            self.arm_lcd_recovery(reason)
        if self.is_gif_stream_running():
            self.gif_safety_stop = True
            self.stop_gif_stream(lambda: self.activate_lcd_safe_mode(reason, preserve_recovery=True, retry=retry + 1))
            return
        if not self.devices_ready:
            self.log_message("SICHERHEIT: Flüssigkeitstemperatur-Fallback vorgemerkt · Kraken derzeit nicht verbunden.")
            return
        if self.lcd_busy or self.kraken_write_busy:
            if retry < 5:
                QTimer.singleShot(1000, lambda: self.activate_lcd_safe_mode(reason, preserve_recovery=True, retry=retry + 1))
            else:
                self.log_message("SICHERHEIT: Flüssigkeitstemperatur-Fallback konnte wegen dauerhaft belegtem Gerät noch nicht ausgeführt werden.")
            return
        self.kraken_write_busy = True

        def done(result: CommandResult) -> None:
            self.kraken_write_busy = False
            if result.ok:
                self.lcd_failure_count = 0
                self.lcd_recovery_required = False
                self.settings.setValue("lcd/recovery_required", False)
                self.settings.sync()
                self.lcd_mode_label.setText("LCD-Modus: Flüssigkeitstemperatur · Sicherheitsfallback")
                self.clock_status_label.setText("LCD-Sicherheitsmodus aktiv · experimentelle Funktion angehalten.")
                self.hardware_lcd_status_label.setText("LCD-Sicherheitsmodus aktiv · Live-Hardwaredesign angehalten.")
                self.hardware_animation_status_label.setText("LCD-Sicherheitsmodus aktiv · Hardwareanimation angehalten.")
                self.footer_status.setText("LCD-Sicherheitsfallback: Flüssigkeitstemperatur")
                self.update_experimental_notice_status()
                self.log_message("SICHERHEIT: Standardanzeige Flüssigkeitstemperatur erfolgreich wiederhergestellt.")
            else:
                self.lcd_recovery_required = True
                self.settings.setValue("lcd/recovery_required", True)
                self.settings.sync()
                self.log_message("SICHERHEIT: Flüssigkeitstemperatur-Fallback fehlgeschlagen · " + (result.combined or "unbekannter Fehler"))

        self.backend.run_async(
            Backend.kraken_args() + ["set", "lcd", "screen", "liquid"],
            callback=done,
            timeout=20,
        )

    def record_lcd_failure(self, context: str, detail: str, *, severe: bool = False) -> bool:
        self.lcd_failure_count += 1
        self.log_message(f"LCD-FEHLER: {context} · {self.lcd_failure_count}/{LCD_FAILURE_LIMIT} · {detail}")
        if severe or self.lcd_failure_count >= LCD_FAILURE_LIMIT:
            self.activate_lcd_safe_mode(f"{context}: {detail}")
            return True
        return False

    def should_start_minimized_from_autostart(self) -> bool:
        return (
            self.launched_from_autostart
            and self.settings.value("setup/completed", False, type=bool)
            and self.settings.value("app/autostart_minimized", True, type=bool)
        )

    def apply_initial_window_state(self) -> None:
        if not self.should_start_minimized_from_autostart():
            self.show()
            return
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            self.log_message("AUTOSTART: Hauptfenster bleibt minimiert/im Tray · Einstellungen werden im Hintergrund angewendet.")
        else:
            self.showMinimized()
            self.log_message("AUTOSTART: Kein Tray verfügbar · Hauptfenster minimiert gestartet.")

    # ---------- app settings ----------
    def update_status_interval(self) -> None:
        self.status_timer.setInterval(self.refresh_interval.value() * 1000)

    @staticmethod
    def autostart_file() -> Path:
        return Path.home() / ".config" / "autostart" / "open-hardware-control.desktop"

    @staticmethod
    def legacy_autostart_file() -> Path:
        return Path.home() / ".config" / "autostart" / "kraken-control.desktop"

    def set_autostart(self, enabled: bool) -> None:
        path = self.autostart_file()
        try:
            if enabled:
                path.parent.mkdir(parents=True, exist_ok=True)
                executable = shutil.which("open-hardware-control") or str(Path(__file__).resolve())
                exec_line = executable if executable.endswith("open-hardware-control") else f"python3 {executable}"
                exec_line += " --autostart"
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
                legacy_path = self.legacy_autostart_file()
                if legacy_path.exists():
                    legacy_path.unlink()
            else:
                for candidate in (path, self.legacy_autostart_file()):
                    if candidate.exists():
                        candidate.unlink()
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
        default_name = Path.home() / f"open-hardware-control-{time.strftime('%Y%m%d-%H%M%S')}.log"
        filename, _ = QFileDialog.getSaveFileName(self, "Open-Hardware-Control-Log speichern", str(default_name), "Logdateien (*.log *.txt)")
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


def install_session_signal_handlers(window: KrakenControl) -> None:
    """Forward common Unix session-stop signals into Qt's event loop."""
    def request_shutdown(_signum, _frame) -> None:  # noqa: ANN001
        window.mark_clean_shutdown()
        QTimer.singleShot(0, window.request_session_shutdown)

    for signal_name in ("SIGTERM", "SIGINT"):
        signum = getattr(signal, signal_name, None)
        if signum is not None:
            signal.signal(signum, request_shutdown)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setQuitOnLastWindowClosed(True)
    window = KrakenControl()
    app.aboutToQuit.connect(window.backend.shutdown)
    install_session_signal_handlers(window)
    window.apply_initial_window_state()
    sys.exit(app.exec())

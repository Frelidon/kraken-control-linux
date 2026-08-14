import importlib.util
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

class Dummy:
    class _Enum:
        def __getattr__(self, _name):
            return 1
    def __init__(self,*a,**k): pass
    def __call__(self,*a,**k): return Dummy()
    def __getattr__(self,n):
        if n in {"ApplicationState", "StandardLocation", "DialogCode", "WizardStyle", "SelectionBehavior", "SelectionMode", "ItemDataRole", "ItemFlag", "PenStyle", "PenCapStyle", "RenderHint", "ColorRole", "AlignmentFlag", "Orientation", "Key"}:
            return self._Enum()
        return Dummy()
    def __or__(self,other): return self
    def __and__(self,other): return self
    def __invert__(self): return self
    def __int__(self): return 0
    def __float__(self): return 1.0
    def __iter__(self): return iter(())

class SignalDummy(Dummy):
    pass

qtcore=types.ModuleType('PySide6.QtCore')
for n in ['QEvent','QObject','QProcess','QSettings','QSize','QTimer','QPointF','QRectF','QUrl','QStandardPaths']:
    setattr(qtcore,n,Dummy)
qtcore.Signal=SignalDummy
qtcore.qVersion=lambda: 'test'
qtcore.Qt=Dummy()
qtgui=types.ModuleType('PySide6.QtGui')
for n in ['QAction','QBrush','QColor','QCloseEvent','QFont','QIcon','QImage','QImageReader','QPixmap','QMovie','QPainter','QPainterPath','QPen','QPalette','QMouseEvent','QKeyEvent','QDesktopServices','QKeySequence','QLinearGradient','QRadialGradient']:
    setattr(qtgui,n,Dummy)
qtwidgets=types.ModuleType('PySide6.QtWidgets')
for n in ['QApplication','QAbstractButton','QAbstractItemView','QCheckBox','QColorDialog','QComboBox','QDialog','QFileDialog','QFormLayout','QFrame','QGridLayout','QGroupBox','QHBoxLayout','QInputDialog','QLabel','QLineEdit','QMainWindow','QMenu','QMessageBox','QPushButton','QScrollArea','QSlider','QSpinBox','QStackedLayout','QStackedWidget','QSystemTrayIcon','QTabBar','QTabWidget','QTableWidget','QTableWidgetItem','QTreeWidget','QTreeWidgetItem','QVBoxLayout','QWidget','QPlainTextEdit','QWizard','QWizardPage']:
    setattr(qtwidgets,n,Dummy)
pyside=types.ModuleType('PySide6')
pyside.__version__='test'
sys.modules.update({'PySide6':pyside,'PySide6.QtCore':qtcore,'PySide6.QtGui':qtgui,'PySide6.QtWidgets':qtwidgets})

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec=importlib.util.spec_from_file_location('kraken_v29',str(ROOT / 'kraken_control.py'))
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
assert mod.APP_VERSION=='3.0.9'
assert mod.APP_NAME=='Open Hardware Control'
assert len(mod.AM5_CPU_PROFILES)>=20
assert len(mod.AnimatedBackgroundWidget.THEMES) >= 10
assert hasattr(mod, 'InteractionAuditLogger')
assert mod.DEFAULT_BACKGROUND_THEME in mod.AnimatedBackgroundWidget.THEMES
p=mod.CPU_PROFILE_BY_MODEL['AMD Ryzen 7 9800X3D']
assert (p.tjmax,p.boost_temp,p.critical_temp)==(95,80,90)
p=mod.CPU_PROFILE_BY_MODEL['AMD Ryzen 7 7800X3D']
assert (p.tjmax,p.boost_temp,p.critical_temp)==(89,75,85)
args=mod.KrakenControl.curve_args('fan',[(25,30),(45,100)])
assert args[-5:]==['speed','25','30','45','100']
assert '--direct-access' in args and '--match' in args and 'NZXT Kraken 2023' in args
assert mod.DEFAULT_PUMP_CURVE[-1] == (90, 100)
assert mod.DEFAULT_FAN_CURVE[-1] == (90, 100)
assert mod.KrakenControl.interpolate_curve([(30, 40), (50, 60), (90, 100)], 30) == 40
assert mod.KrakenControl.interpolate_curve([(30, 40), (50, 60), (90, 100)], 40) == 50
assert mod.KrakenControl.interpolate_curve([(30, 40), (50, 60), (90, 100)], 95) == 100
assert mod.KrakenControl.quantize_curve_duty(53) == 52
assert mod.KrakenControl.should_update_curve_duty(None, 40, 0.0)
assert not mod.KrakenControl.should_update_curve_duty(40, 42, 30.0)
assert not mod.KrakenControl.should_update_curve_duty(40, 44, 2.9)
assert mod.KrakenControl.should_update_curve_duty(40, 44, 3.0)
assert not mod.KrakenControl.should_update_curve_duty(60, 54, 11.9)
assert mod.KrakenControl.should_update_curve_duty(60, 54, 12.0)
assert mod.KrakenControl.should_update_curve_duty(60, 100, 0.0, emergency=True)
assert mod.KrakenControl.normalize_profile_cpu_curve([(25, 30), (45, 100)], list(mod.DEFAULT_FAN_CURVE)) == list(mod.DEFAULT_FAN_CURVE)
assert mod.KrakenControl.normalize_profile_cpu_curve([(30, 25), (90, 100)], list(mod.DEFAULT_FAN_CURVE)) == [(30, 25), (90, 100)]
assert mod.AUTOSTART_LCD_DELAY_MS == 5000
assert mod.normalize_temperature_unit('Fahrenheit') == 'f'
assert mod.celsius_to_display(0, 'f') == 32
assert mod.display_to_celsius(212, 'f') == 100
assert mod.temperature_symbol('f') == '°F'

class QuitLcdFake:
    def __init__(self): self.logs = []
    def log_message(self, text): self.logs.append(text)

quit_lcd = QuitLcdFake()
with patch.object(mod.subprocess, 'run', return_value=types.SimpleNamespace(returncode=0, stdout='', stderr='')) as run:
    mod.KrakenControl.restore_original_lcd_sync_on_quit(quit_lcd)
    assert run.call_args.args[0][-4:] == ['set', 'lcd', 'screen', 'liquid']
    assert any('Wassertemperatur wiederhergestellt' in line for line in quit_lcd.logs)
assert mod.KrakenControl.resolve_profile_lcd_mode({'mode': 'hardware_animation'}) == 'hardware_animation'
assert mod.KrakenControl.resolve_profile_lcd_mode({'file': '/tmp/demo.gif'}) == 'gif'
assert mod.KrakenControl.resolve_profile_lcd_mode({'file': '/tmp/demo.png'}) == 'image'
assert mod.KrakenControl.resolve_profile_lcd_mode({'clock_active': True, 'file': '/tmp/demo.gif'}) == 'clock'

class StartupDelayFake:
    launched_from_autostart = True
    autostart_launch_monotonic = mod.time.monotonic() - 2.0

delay_ms = mod.KrakenControl.startup_lcd_delay_ms(StartupDelayFake(), 1200)
assert 2800 <= delay_ms <= 3200
StartupDelayFake.launched_from_autostart = False
assert mod.KrakenControl.startup_lcd_delay_ms(StartupDelayFake(), 1200) == 1200

class LcdModeFake:
    gif_start_pending = False
    gif_generated_hardware_mode = False
    hardware_lcd_active = False
    clock_active = False
    prepared_lcd_file = None
    keep_lcd_checkbox = Dummy()
    def is_gif_stream_running(self): return False

lcd_mode = LcdModeFake()
lcd_mode.gif_start_pending = True
assert mod.KrakenControl.current_lcd_profile_mode(lcd_mode) == 'gif'
lcd_mode.gif_generated_hardware_mode = True
assert mod.KrakenControl.current_lcd_profile_mode(lcd_mode) == 'hardware_animation'
red=mod.redact_private_text('/home/florian/a serial number: abc\nmachine-id: deadbeef')
assert 'florian' not in red and 'deadbeef' not in red
assert mod.KrakenControl.classify_aspect_ratio(16/9) == '16:9'
assert mod.KrakenControl.classify_aspect_ratio(32/9) == '32:9'
profiles=mod.KrakenControl.builtin_profiles()
assert any(p['name']=='Leise' for p in profiles)
assert any(p['category']=='Design' for p in profiles)
print('Stub import/runtime logic checks passed.')

assert set(mod.SUPPORTED_UI_LANGUAGES) == {"de", "en", "es", "fr"}
assert mod.LCD_FAILURE_LIMIT == 3
assert "Übersicht" in mod.UI_TRANSLATIONS["en"]
assert mod.UI_TRANSLATIONS["es"]["Einstellungen"] == "Ajustes"
assert mod.UI_TRANSLATIONS["fr"]["Kühlung"] == "Refroidissement"

class SafetyFake:
    def __init__(self):
        self.lcd_failure_count = 0
        self.logs = []
        self.safe = []
    def log_message(self, text):
        self.logs.append(text)
    def activate_lcd_safe_mode(self, reason):
        self.safe.append(reason)

fake = SafetyFake()
assert mod.KrakenControl.record_lcd_failure(fake, 'clock', 'x') is False
assert mod.KrakenControl.record_lcd_failure(fake, 'clock', 'x') is False
assert mod.KrakenControl.record_lcd_failure(fake, 'clock', 'x') is True
assert len(fake.safe) == 1

class LangFake:
    ui_language = 'en'
assert mod.KrakenControl.tr_static(LangFake(), 'Übersicht') == 'Overview'
LangFake.ui_language = 'de'
assert mod.KrakenControl.tr_static(LangFake(), 'Übersicht') == 'Übersicht'

assert mod.GIF_HELPER_NAME == "kraken_cam_streamer.py"
assert mod.UI_TRANSLATIONS["en"]["Beim Systemstart minimiert/im Tray starten"].startswith("Start minimized")

assert mod.UI_TRANSLATIONS['en']['Bewegungsglättung (Motion-Interpolation)'].startswith('Motion')

assert mod.KrakenControl.cooling_mode_kind('Feste Drehzahl') == 'manual'
assert mod.KrakenControl.cooling_mode_kind('CPU-Assistenz') == 'manual'
assert mod.KrakenControl.cooling_mode_kind('Temperaturkurve') == 'curve'
assert mod.KrakenControl.cooling_mode_kind('CPU-Temperaturkurve') == 'curve'
assert mod.KrakenControl.cooling_mode_kind('curve') == 'curve'
assert mod.KrakenControl.cooling_mode_kind('unbekannt') is None

class ModeButtonFake:
    def __init__(self):
        self.properties = {'coolingState': 'inactive'}
        self.description = ''
        self.repolished = 0
    def property(self, name): return self.properties.get(name)
    def setProperty(self, name, value): self.properties[name] = value
    def style(self): return self
    def unpolish(self, _button): self.repolished += 1
    def polish(self, _button): self.repolished += 1
    def update(self): pass
    def setAccessibleDescription(self, text): self.description = text

class ModeStateFake:
    cooling_mode_kind = staticmethod(mod.KrakenControl.cooling_mode_kind)
    cooling_modes = {
        'pump': ('Temperaturkurve', '7 Punkte'),
        'fan': ('Feste Drehzahl', '52 %'),
    }
    cooling_mode_buttons = {
        'pump': {'manual': ModeButtonFake(), 'curve': ModeButtonFake()},
        'fan': {'manual': ModeButtonFake(), 'curve': ModeButtonFake()},
    }

mode_state = ModeStateFake()
mod.KrakenControl.update_cooling_mode_buttons(mode_state)
assert mode_state.cooling_mode_buttons['pump']['curve'].properties['coolingState'] == 'active'
assert mode_state.cooling_mode_buttons['pump']['manual'].properties['coolingState'] == 'inactive'
assert mode_state.cooling_mode_buttons['fan']['manual'].properties['coolingState'] == 'active'
assert mode_state.cooling_mode_buttons['fan']['curve'].properties['coolingState'] == 'inactive'
assert mode_state.cooling_mode_buttons['pump']['curve'].repolished == 2
assert mode_state.cooling_mode_buttons['fan']['manual'].repolished == 2

class ValueFake:
    def __init__(self, value): self._value = value
    def value(self): return self._value

class SwitchFake:
    pump_slider = ValueFake(61)
    fan_slider = ValueFake(47)
    pump_curve_table = (None, 'pump-table', None)
    fan_curve_table = (None, 'fan-table', None)
    calls = []
    def update_cooling_mode_buttons(self): self.calls.append(('refresh',))
    def set_fixed_speed(self, channel, value): self.calls.append(('manual', channel, value))
    def apply_curve(self, channel, table): self.calls.append(('curve', channel, table))
    def show_error(self, message): self.calls.append(('error', message))

switch_state = SwitchFake()
mod.KrakenControl.switch_cooling_mode(switch_state, 'pump', 'manual')
mod.KrakenControl.switch_cooling_mode(switch_state, 'fan', 'curve')
assert switch_state.calls == [
    ('refresh',), ('manual', 'pump', 61),
    ('refresh',), ('curve', 'fan', 'fan-table'),
]

assert mod.UI_TRANSLATIONS['en']['LCD-Transport'] == 'LCD transport'
for language in ('en', 'es', 'fr'):
    for source in (
        'Schrift- und Zahlen-Größe',
        'Animierte Hardwaredaten · Ringe und Orbits',
        'Animierte Vorschau erzeugen',
        'Hardwareanimation starten',
        'Hardwareanimation anhalten',
        'Hardwareanimation-Hinweis',
        'LCD-Modus: Live-Hardwaredesign',
        'Live-Hardwaredesign angehalten · das letzte Bild kann sichtbar bleiben.',
        'CPU/GPU live · Wasser letzter sicherer Wert',
        'Livewerte aktualisiert',
        'Livewert-Aktualisierung fehlgeschlagen',
    ):
        assert mod.UI_TRANSLATIONS[language].get(source, source) != source

fake_drm = Path(tempfile.mkdtemp(prefix='kraken-gpu-sensor-'))
for card_name, vram, temp in (('card0', 512 * 1024**2, 45000), ('card1', 16 * 1024**3, 62000)):
    device = fake_drm / card_name / 'device'
    hwmon = device / 'hwmon' / 'hwmon0'
    hwmon.mkdir(parents=True)
    (device / 'vendor').write_text('0x1002\n', encoding='ascii')
    (device / 'mem_info_vram_total').write_text(f'{vram}\n', encoding='ascii')
    (hwmon / 'name').write_text('amdgpu\n', encoding='ascii')
    (hwmon / 'temp1_input').write_text(f'{temp}\n', encoding='ascii')
    (hwmon / 'temp1_label').write_text('edge\n', encoding='ascii')
gpu_temp, gpu_label = mod.KrakenControl.read_amd_gpu_temperature(fake_drm)
assert gpu_temp == 62.0 and 'card1' in gpu_label

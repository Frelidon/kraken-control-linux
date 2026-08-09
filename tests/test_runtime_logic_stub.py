import importlib.util
import sys
import types
from pathlib import Path

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
for n in ['QAction','QBrush','QColor','QCloseEvent','QFont','QIcon','QImage','QPixmap','QPainter','QPainterPath','QPen','QPalette','QMouseEvent','QKeyEvent','QDesktopServices','QKeySequence','QLinearGradient','QRadialGradient']:
    setattr(qtgui,n,Dummy)
qtwidgets=types.ModuleType('PySide6.QtWidgets')
for n in ['QApplication','QAbstractButton','QAbstractItemView','QCheckBox','QColorDialog','QComboBox','QDialog','QFileDialog','QFormLayout','QFrame','QGridLayout','QGroupBox','QHBoxLayout','QInputDialog','QLabel','QMainWindow','QMessageBox','QPushButton','QScrollArea','QSlider','QSpinBox','QStackedLayout','QStackedWidget','QSystemTrayIcon','QTabBar','QTabWidget','QTableWidget','QTableWidgetItem','QVBoxLayout','QWidget','QPlainTextEdit','QLineEdit','QWizard','QWizardPage']:
    setattr(qtwidgets,n,Dummy)
pyside=types.ModuleType('PySide6')
pyside.__version__='test'
sys.modules.update({'PySide6':pyside,'PySide6.QtCore':qtcore,'PySide6.QtGui':qtgui,'PySide6.QtWidgets':qtwidgets})

spec=importlib.util.spec_from_file_location('kraken_v29',str(Path(__file__).resolve().parents[1] / 'kraken_control.py'))
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
assert mod.APP_VERSION=='2.9.6'
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
red=mod.redact_private_text('/home/exampleuser/a serial number: abc\nmachine-id: deadbeef')
assert 'exampleuser' not in red and 'deadbeef' not in red
assert mod.KrakenControl.classify_aspect_ratio(16/9) == '16:9'
assert mod.KrakenControl.classify_aspect_ratio(32/9) == '32:9'
profiles=mod.KrakenControl.builtin_profiles()
assert any(p['name']=='Leise' for p in profiles)
assert any(p['category']=='Design' for p in profiles)
print('Stub import/runtime logic checks passed.')

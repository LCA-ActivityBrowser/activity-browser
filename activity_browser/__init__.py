try:
    import PySide6
except ImportError:
    import qtpy

from .ui.application import application
from .signals import signals

def run_activity_browser():
    from .__main__ import run_activity_browser

print(__name__)
import sys
from logging import getLogger

try:
    import PySide6
except ImportError:
    import qtpy

from .loader import application
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .info import __version__ as version
from .layouts.main import MainWindow


log = getLogger(__name__)


def run_activity_browser():
    log.info(f"Activity Browser version: {version}")
    application.main_window = MainWindow()
    # load_settings()
    application.show()

    sys.exit(application.exec_())

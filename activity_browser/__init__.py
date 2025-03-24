import sys
from logging import getLogger

try:
    import PySide6
except ImportError:
    import qtpy

from .logger import log_file_location, setup_ab_logging
from .mod import bw2data
from .application import application
from .signals import signals
from .settings import ab_settings, project_settings
from .info import __version__ as version
from .layouts.main import MainWindow

log = getLogger(__name__)


def load_settings() -> None:
    if ab_settings.settings:
        from pathlib import Path

        base_dir = Path(ab_settings.current_bw_dir)
        project_name = ab_settings.startup_project

        bw2data.projects.change_base_directories(base_dir, project_name=project_name, update=False)

    if not bw2data.projects.twofive:
        from .actions import ProjectSwitch
        log.warning(f"Project: {bw2data.projects.current} is not yet BW25 compatible")
        ProjectSwitch.set_warning_bar()

    log.info(f"Brightway2 data directory: {bw2data.projects._base_data_dir}")
    log.info(f"Brightway2 current project: {bw2data.projects.current}")


def run_activity_browser():
    setup_ab_logging()
    log.info(f"Activity Browser version: {version}")
    if log_file_location:
        log.info(f"The log file can be found at {log_file_location}")

    application.main_window = MainWindow()
    load_settings()
    application.show()

    sys.exit(application.exec_())

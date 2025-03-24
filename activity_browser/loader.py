try:
    import PySide6
    import qtpy
except ImportError:
    import qtpy

import os
from logging import getLogger

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt

from .application import application
from .logger import log_file_location, setup_ab_logging
from .static.icons import main

log = getLogger(__name__)


class ABSplashScreen(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFixedSize(self.size())

        logo_pixmap = QtGui.QPixmap(os.path.join(main.__path__[0], "activitybrowser.png"))
        logo_label = QtWidgets.QLabel(self)
        logo_label.setPixmap(logo_pixmap)

        loading_bar = QtWidgets.QProgressBar(self)
        loading_bar.setRange(0, 0)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addWidget(loading_bar)
        self.setLayout(layout)

        self.load_thread = LoadThread(self)

        self.thread().eventDispatcher().awake.connect(self.load_modules, type=Qt.ConnectionType.SingleShotConnection)

    def load_modules(self):
        self.load_thread.start()
        self.load_thread.finished.connect(self.load_finished)

    def load_finished(self):
        self.deleteLater()
        application.exit(0)


class LoadThread(QtCore.QThread):
    def run(self):
        print("Importing numpy")
        import numpy
        print("Importing pandas")
        import pandas
        print("Importing bw2data")
        import bw2data
        print("Importing bw2calc")
        import bw2calc
        print("Importing bw2io")
        import bw2io
        print("Setting up logging")
        setup_ab_logging()
        if log_file_location:
            log.info(f"The log file can be found at {log_file_location}")
        print("Loading view")
        from .layouts.main import MainWindow
        application.main_window = MainWindow()
        print("Loading project")
        load_settings()


def load_settings() -> None:
    print("importing")
    import bw2data
    print("importing settings")
    from .settings import ab_settings
    print("importing done")

    if ab_settings.settings:
        from pathlib import Path

        base_dir = Path(ab_settings.current_bw_dir)
        project_name = ab_settings.startup_project
        print("changing dirs")
        bw2data.projects.change_base_directories(base_dir, project_name=project_name, update=False)

    if not bw2data.projects.twofive:
        from .actions import ProjectSwitch
        log.warning(f"Project: {bw2data.projects.current} is not yet BW25 compatible")
        ProjectSwitch.set_warning_bar()

    print("logging")
    log.info(f"Brightway2 data directory: {bw2data.projects._base_data_dir}")
    log.info(f"Brightway2 current project: {bw2data.projects.current}")


splash = ABSplashScreen()
splash.show()
application.exec_()


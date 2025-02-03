from logging import getLogger

from qtpy import QtWidgets, QtGui

import bw2data as bd

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import icons

from .project_migrate25 import ProjectMigrate25

log = getLogger(__name__)


class ProjectSwitch(ABAction):
    """
    ABAction to switch to another project.
    """

    text = "Switch project"
    tool_tip = "Switch the project"

    @staticmethod
    @exception_dialogs
    def run(project_name: str):
        
        # compare the new to the current project name and switch to the new one if the two are not the same
        if not project_name == bd.projects.current:
            bd.projects.set_current(project_name, update=False)

            if not bd.projects.twofive:
                log.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
                ProjectSwitch.set_warning_bar()

            log.info(f"Brightway2 current project: {project_name}")
            
        # if the project to be switched to is already the current project, do nothing
        else: 
            log.debug(f"Brightway2 already selected: {project_name}")

    @staticmethod
    def set_warning_bar():
        application.main_window.addToolBar(ProjectWarningBar())


class ProjectWarningBar(QtWidgets.QToolBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(False)

        warning_label = QtWidgets.QLabel("  This project is not Brightway25 compatible. ")
        height = warning_label.minimumSizeHint().height()

        warning_icon = QtWidgets.QLabel(self)
        qicon = application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning)
        pixmap = qicon.pixmap(height, height)
        warning_icon.setPixmap(pixmap)

        migrate_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Migrate project now</a>")
        migrate_label.mouseReleaseEvent = lambda x: ProjectMigrate25.run(bd.projects.current)

        self.addWidget(warning_icon)
        self.addWidget(warning_label)
        self.addWidget(migrate_label)

        signals.project.changed.connect(self.deleteLater)

    def contextMenuEvent(self, event):
        return None


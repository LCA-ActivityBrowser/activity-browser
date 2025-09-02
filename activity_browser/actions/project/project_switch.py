import datetime
from logging import getLogger

from qtpy import QtWidgets, QtCore

import bw2data as bd

from activity_browser import application, signals
from activity_browser.actions.base import ABAction, exception_dialogs

from .project_migrate25 import ProjectMigrate25

log = getLogger(__name__)


class ProjectSwitch(ABAction):
    """
    Switch to a specified Brightway2 project.

    This method compares the given project name with the currently active project.
    If the specified project is different, it switches to the new project, updates
    the last opened timestamp, and logs the change. If the project is not Brightway25
    compatible, a warning is displayed. If the specified project is already active,
    no action is taken.

    Args:
        project_name (str): The name of the project to switch to.

    Logs:
        Warning: If the project is not Brightway25 compatible.
        Info: When the project is successfully switched.
        Debug: If the specified project is already the current project.
    """

    text = "Switch project"
    tool_tip = "Switch the project"

    @staticmethod
    @exception_dialogs
    def run(project_name: str):
        # compare the new to the current project name and switch to the new one if the two are not the same
        if project_name == bd.projects.current:
            log.debug(f"Brightway2 already selected: {project_name}")
            return

        dialog = ProjectChangeDialog(project_name, application.main_window)
        dialog.show()
        application.thread().eventDispatcher().processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

        # switch to the new project, don't auto update to brightway25
        bd.projects.set_current(project_name, update=False)

        dialog.close()

        if not bd.projects.twofive:
            log.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
            ProjectSwitch.set_warning_bar()

        log.info(f"Brightway2 current project: {project_name}")

        # update the last opened timestamp
        bd.projects.dataset.data["last_opened"] = datetime.datetime.now().isoformat()
        bd.projects.dataset.save()

    @staticmethod
    def set_warning_bar():
        application.main_window.addToolBar(ProjectWarningBar())


class ProjectChangeDialog(QtWidgets.QDialog):
    def __init__(self, project_name: str, parent=None):
        super().__init__(parent, QtCore.Qt.WindowTitleHint)
        self.setWindowTitle(f"Switching project")
        self.setModal(True)

        self.label = QtWidgets.QLabel(f"Switching to project: <b>{project_name}</b>", self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)


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


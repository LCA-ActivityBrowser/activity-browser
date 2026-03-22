import datetime
from loguru import logger

from qtpy import QtWidgets, QtCore

import bw2data as bd

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.core.application import global_shortcut

from .project_migrate25 import ProjectMigrate25




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
    def run(project_name: str, reload: bool = False):
        # compare the new to the current project name and switch to the new one if the two are not the same
        if project_name == bd.projects.current and not reload:
            logger.debug(f"Brightway2 already selected: {project_name}")
            return

        dialog = ProjectChangeDialog(project_name, reload, app.main_window)
        dialog.show()
        app.application.processEvents()

        # switch to the new project, don't auto update to brightway25
        bd.projects.set_current(project_name, update=False)

        if not bd.projects.twofive:
            logger.warning(f"Project: {bd.projects.current} is not yet BW25 compatible")
            ProjectSwitch.set_warning_bar()

        logger.info(f"Brightway2 current project: {project_name}")

        # update the last opened timestamp
        bd.projects.dataset.data["last_opened"] = datetime.datetime.now().isoformat()
        bd.projects.dataset.save()

        app.application.processEvents()
        dialog.close()

    @staticmethod
    def set_warning_bar():
        app.main_window.addToolBar(ProjectWarningBar())

    @global_shortcut("F5")
    @staticmethod
    def reload_project():
        ProjectSwitch.run(bd.projects.current, reload=True)


class ProjectChangeDialog(QtWidgets.QDialog):
    def __init__(self, project_name: str, reload: bool, parent=None):
        super().__init__(parent, QtCore.Qt.WindowTitleHint)

        title = "Reloading project" if reload else "Switching project"
        subtitle = f"Reloading project: <b>{project_name}</b>" if reload else f"Switching to project: <b>{project_name}</b>"

        self.setWindowTitle(title)
        self.setModal(True)

        self.label = QtWidgets.QLabel(subtitle, self)

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
        qicon = app.application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning)
        pixmap = qicon.pixmap(height, height)
        warning_icon.setPixmap(pixmap)

        migrate_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Migrate project now</a>")
        migrate_label.mouseReleaseEvent = lambda x: ProjectMigrate25.run(bd.projects.current)

        self.addWidget(warning_icon)
        self.addWidget(warning_label)
        self.addWidget(migrate_label)

        app.signals.project.changed.connect(self.deleteLater)

    def contextMenuEvent(self, event):
        return None


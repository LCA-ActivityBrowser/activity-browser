import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.controllers import project_controller


class ProjectDuplicate(ABAction):
    icon = qicons.copy
    title = "Duplicate"
    tool_tip = "Duplicate the project"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Duplicate current project",
            f"Duplicate current project ({bw.projects.current}) to new name:" + " " * 10
        )

        if not ok or not name: return

        if name in bw.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists."
            )
            return

        project_controller.duplicate_project(name)

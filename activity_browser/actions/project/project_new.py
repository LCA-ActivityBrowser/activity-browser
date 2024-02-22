import brightway2 as bw
from PySide2 import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction
from activity_browser.ui.icons import qicons
from activity_browser.controllers import project_controller


class ProjectNew(ABAction):
    icon = qicons.add
    title = "New"
    tool_tip = "Make a new project"

    def onTrigger(self, toggled):
        name, ok = QtWidgets.QInputDialog.getText(
            application.main_window,
            "Create new project",
            "Name of new project:" + " " * 25
        )

        if not ok or not name: return

        if name in bw.projects:
            QtWidgets.QMessageBox.information(
                application.main_window,
                "Not possible.",
                "A project with this name already exists."
            )
            return

        project_controller.new_project(name)

from qtpy import QtCore

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs

from activity_browser.ui.icons import qicons


class ProjectManagerOpen(ABAction):
    """
    ABAction to delete a database from the project. Asks the user for confirmation. If confirmed, instructs the
    DatabaseController to delete the database in question.
    """

    icon = qicons.delete
    text = "Open project manager"

    @staticmethod
    @exception_dialogs
    def run():
        from activity_browser.app.panes import ProjectManagerPane

        project_manager = ProjectManagerPane(app.main_window)
        app.main_window.addDockWidget(
            QtCore.Qt.LeftDockWidgetArea,
            project_manager.getDockWidget(app.main_window))

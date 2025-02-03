from activity_browser import application, project_settings
from activity_browser.actions.base import ABAction, exception_dialogs

from activity_browser.ui.icons import qicons
from activity_browser.layouts.panes import ProjectManager


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
        project_manager = ProjectManager(application.main_window)
        application.windows.append(project_manager)
        project_manager.show()
        project_manager.destroyed.connect(lambda: application.windows.remove(project_manager))

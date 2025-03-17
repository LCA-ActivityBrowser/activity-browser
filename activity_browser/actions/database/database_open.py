from logging import getLogger

from qtpy.QtCore import Qt

from activity_browser import application
from activity_browser.ui import widgets
from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class DatabaseOpen(ABAction):
    text = "Open Database"

    @staticmethod
    @exception_dialogs
    def run(database_names: list[str]):
        from activity_browser.layouts import main, panes

        for db_name in database_names:
            db_pane = panes.DatabaseFunctionsPane(application.main_window, db_name)
            dock_widget = widgets.ABDockWidget(db_name, application.main_window)
            dock_widget.setWidget(db_pane)
            application.main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_widget)


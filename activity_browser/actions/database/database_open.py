from logging import getLogger

from qtpy.QtCore import Qt, QEventLoop

from activity_browser import application
from activity_browser.ui import widgets
from activity_browser.actions.base import ABAction, exception_dialogs

log = getLogger(__name__)


class DatabaseOpen(ABAction):
    text = "Open Database"

    @staticmethod
    @exception_dialogs
    def run(database_names: list[str]):
        from activity_browser.layouts import panes

        sibling = DatabaseOpen.find_sibling()

        for db_name in database_names:
            db_pane = panes.DatabaseProductsPane(application.main_window, db_name)
            dock_widget = db_pane.getDockWidget(application.main_window)

            application.main_window.addDockWidget(DatabaseOpen.get_area(), dock_widget)

            if sibling:
                application.main_window.tabifyDockWidget(sibling, dock_widget)

                application.thread().eventDispatcher().processEvents(QEventLoop.ProcessEventsFlags.AllEvents)
                dock_widget.raise_()

            dock_widget.show()

    @staticmethod
    def find_sibling():
        """
        Find the dockwidget location where the database pane should be opened.
        """
        from activity_browser.layouts import panes

        all_dws = application.main_window.findChildren(widgets.ABDockWidget)
        databases_dw = application.main_window.findChild(widgets.ABDockWidget, "dockwidget-databases_pane")

        products_dws = [w for w in all_dws if
                        isinstance(w.widget(), panes.DatabaseProductsPane) and
                        application.main_window.dockWidgetArea(w) == application.main_window.dockWidgetArea(databases_dw) and
                        not w.visibleRegion().isNull()
                        ]
        return products_dws[0] if products_dws else None

    @staticmethod
    def get_area():
        """
        Find the dockwidget location where the database pane should be opened.
        """
        databases_dw = application.main_window.findChild(widgets.ABDockWidget, "dockwidget-databases_pane")
        return application.main_window.dockWidgetArea(databases_dw)

from qtpy.QtCore import Qt, QEventLoop

from activity_browser import app
from activity_browser.ui import widgets
from activity_browser.app.actions.base import ABAction, exception_dialogs




class DatabaseOpen(ABAction):
    text = "Open Database"

    @staticmethod
    @exception_dialogs
    def run(database_names: list[str]):
        from activity_browser.app import panes

        sibling = DatabaseOpen.find_sibling()

        for db_name in database_names:
            db_pane = panes.DatabaseProductsPane(app.main_window, db_name)
            dock_widget = db_pane.getDockWidget(app.main_window)
            dock_widget.resize(dock_widget.width(), app.main_window.height() // 2)

            app.main_window.addDockWidget(DatabaseOpen.get_area(), dock_widget)

            if sibling:
                app.main_window.tabifyDockWidget(sibling, dock_widget)

                app.application.thread().eventDispatcher().processEvents(QEventLoop.ProcessEventsFlags.AllEvents)
                dock_widget.raise_()
                dock_widget.show()
            else:
                dock_widget.show()
                app.main_window.resizeDocks(
                    [dock_widget],
                    [1000],
                    Qt.Vertical
                )

    @staticmethod
    def find_sibling():
        """
        Find the dockwidget location where the database pane should be opened.
        """
        from activity_browser.app import panes

        all_dws = app.main_window.findChildren(widgets.ABDockWidget)
        databases_dw = app.main_window.findChild(widgets.ABDockWidget, "dockwidget-databases_pane")

        products_dws = [w for w in all_dws if
                        isinstance(w.widget(), panes.DatabaseProductsPane) and
                        app.main_window.dockWidgetArea(w) == app.main_window.dockWidgetArea(databases_dw) and
                        not w.visibleRegion().isNull()
                        ]
        return products_dws[0] if products_dws else None

    @staticmethod
    def get_area():
        """
        Find the dockwidget location where the database pane should be opened.
        """
        databases_dw = app.main_window.findChild(widgets.ABDockWidget, "dockwidget-databases_pane")
        return app.main_window.dockWidgetArea(databases_dw)

from qtpy import QtCore, QtWidgets

from activity_browser import actions, signals
from activity_browser.layouts.panels import ABTab
from activity_browser.layouts import panes

from ...ui.style import header


class ProjectTab(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ProjectTab, self).__init__(parent)
        # main widgets
        self.databases_widget = panes.DatabasesPane(self)
        self.activity_biosphere_tabs = ActivityBiosphereTabs(self)

        # Layout
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.databases_widget)
        self.splitter.addWidget(self.activity_biosphere_tabs)
        self.splitter.moveSplitter(0, 1)

        self.overall_layout = QtWidgets.QVBoxLayout()
        self.overall_layout.setAlignment(QtCore.Qt.AlignTop)
        self.overall_layout.addWidget(self.splitter)
        self.setLayout(self.overall_layout)

        self.connect_signals()

    def connect_signals(self):
        signals.project.changed.connect(self.change_project)
        signals.meta.databases_changed.connect(self.update_widgets)

        signals.database_selected.connect(self.update_widgets)

    def change_project(self):
        self.update_widgets()

    def update_widgets(self):
        """Update widgets when a new database has been selected or the project has been changed.
        Hide empty widgets (e.g. Biosphere Flows table when an inventory database is selected).
        """
        no_databases = len(self.activity_biosphere_tabs.tabs) == 0

        self.activity_biosphere_tabs.setVisible(not no_databases)


class ActivityBiosphereTabs(ABTab):
    def __init__(self, parent=None):
        super(ActivityBiosphereTabs, self).__init__(parent)
        self.setTabsClosable(True)

        self.connect_signals()

    def connect_signals(self) -> None:
        signals.project.changed.connect(self.close_all)

        self.tabCloseRequested.connect(self.close_tab)
        signals.database_selected.connect(self.open_or_focus_tab)

    def open_or_focus_tab(self, db_name: str) -> None:
        """Put focus on tab, if not open yet, open it."""
        # create the tab if it doesn't exist yet
        if not self.tabs.get(db_name, False):
            widget = panes.DatabaseProductsPane(parent=self, db_name=db_name)
            self.add_tab(widget, db_name)

            widget.destroyed.connect(
                lambda: self.tabs.pop(db_name) if db_name in self.tabs else None
            )

        # put the focus on this tab + send signal that this is the open db
        self.select_tab(self.tabs[db_name])

    def current_index_changed(self, current_index: int) -> None:
        if current_index < 0:
            self.hide()
            return
        db_name = self.get_tab_name_from_index(current_index)
        signals.database_tab_open.emit(db_name)


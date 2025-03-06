import datetime

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions, project_settings, bwutils
from activity_browser.ui import widgets, icons
from activity_browser.ui.tables import delegates


class Databases(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.view = DatabasesView()
        self.model = DatabasesModel()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(True)

        # Buttons
        self.new_database_button = actions.DatabaseNew.get_QButton()
        self.import_database_button = actions.DatabaseImport.get_QButton()

        self.setMinimumHeight(200)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        signals.meta.databases_changed.connect(self.sync)
        signals.project.changed.connect(self.sync)
        signals.database_read_only_changed.connect(self.sync)

    def build_layout(self):
        # self.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def sync(self):
        self.model.setDataFrame(self.build_df())
        self.view.resizeColumnToContents(0)
        self.view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)

    def build_df(self) -> pd.DataFrame:
        data = []
        for name in bd.databases:
            # get the modified time, in case it doesn't exist, just write 'now' in the correct format
            dt = bd.databases[name].get("modified", datetime.datetime.now().isoformat())
            dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f")

            # final column includes interactive checkbox which shows read-only state of db
            database_read_only = project_settings.db_is_readonly(name)
            data.append(
                {
                    "name": name,
                    "depends": ", ".join(bd.databases[name].get("depends", [])),
                    "modified": dt,
                    "records": bwutils.commontasks.count_database_records(name),
                    "read_only": database_read_only,
                    "default_allocation": bd.databases[name].get("default_allocation", "unspecified"),
                    "backend": bd.databases[name].get("backend")
                }
            )

        cols = ["read_only", "name", "records", "depends", "default_allocation", "modified", "backend"]

        return pd.DataFrame(data, columns=cols)


class DatabasesView(widgets.ABTreeView):

    defaultColumnDelegates = {
        "modified": delegates.DateTimeDelegate,
    }

    class ContextMenu(QtWidgets.QMenu):
        def __init__(self, pos, view: "DatabasesView"):
            """
            Initializes the ContextMenu.

            Args:
                pos: The position of the context menu.
                view (ExchangesView): The view displaying the exchanges.
            """
            super().__init__(view)
            self.relink_action = actions.DatabaseRelink.get_QAction(view.selected_database)
            self.new_process_action = actions.ActivityNewProcess.get_QAction(view.selected_database)
            self.new_product_action = actions.ActivityNewProduct.get_QAction(view.selected_database)
            self.delete_db_action = actions.DatabaseDelete.get_QAction(view.selected_database)
            self.duplicate_db_action = actions.DatabaseDuplicate.get_QAction(view.selected_database)
            self.re_allocate_action = actions.DatabaseRedoAllocation.get_QAction(view.selected_database)
            self.open_explorer_action = actions.DatabaseExplorerOpen.get_QAction(view.selected_database)
            self.process_db_action = actions.DatabaseProcess.get_QAction(view.selected_database)

            self.addAction(self.delete_db_action)
            self.addAction(self.relink_action)
            self.addAction(self.duplicate_db_action)
            self.addAction(self.new_process_action)
            self.addAction(self.new_product_action)
            self.addAction(self.open_explorer_action)
            self.addAction(self.process_db_action)

    class HeaderMenu(QtWidgets.QMenu):
        def __init__(self, *args, **kwargs):
            super().__init__()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.setIndentation(0)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if not self.selectedIndexes():
            return
        index = self.indexAt(event.pos())
        if index.column() == 0:
            database = index.internalPointer()["name"]
            read_only = index.internalPointer()["read_only"]
            project_settings.modify_db(database, not read_only)
            signals.database_read_only_changed.emit(database, not read_only)
            return

        signals.database_selected.emit(self.selected_database())

    def _handle_click(self, index: QtCore.QModelIndex):
        if (index.isValid()
                and index.column() == 4
                and index.data() != DatabasesModel.NOT_APPLICABLE):
            read_only_idx = self.proxy_model.index(index.row(), 2)
            rd_only = self.proxy_model.data(read_only_idx)
            if not rd_only:
                self.model.show_custom_allocation_editor(index)

    def selected_database(self) -> str:
        """Return the database name of the user-selected index."""
        return self.currentIndex().internalPointer()["name"]

    def _handle_data_changed(self, top_left: QtCore.QModelIndex,
            bottom_right: QtCore.QModelIndex):
        """Handle the change of the read-only state"""
        if (top_left.isValid() and bottom_right.isValid() and
                top_left.column() <= 2 <= bottom_right.column()):
            for i in range(top_left.row(), bottom_right.row() + 1):
                index = self.model.index(i, 2)
                # Flip the read-only value for the database
                read_only = index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
                db_name = self.model.get_db_name(index)
                project_settings.modify_db(db_name, read_only)
                signals.database_read_only_changed.emit(db_name, read_only)


class DatabasesItem(widgets.ABDataItem):
    def decorationData(self, col: int, key: str):
        if key == "read_only":
            return icons.qicons.locked if self["read_only"] else icons.qicons.empty
        return super().decorationData(col, key)

    def displayData(self, col: int, key: str):
        if key == "read_only":
            return None
        return super().displayData(col, key)

    def fontData(self, col: int, key: str):
        font = super().fontData(col, key)
        if key == "name":
            font.setBold(True)
        return font


class DatabasesModel(widgets.ABAbstractItemModel):
    dataItemClass = DatabasesItem

    def headerData(self, section, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole):
        if section == 0 and role == Qt.ItemDataRole.DisplayRole:
            return ""
        if section == 0 and role == Qt.ItemDataRole.DecorationRole:
            return icons.qicons.unlocked
        return super().headerData(section, orientation, role)



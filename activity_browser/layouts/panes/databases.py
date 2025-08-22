import datetime

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import signals, actions, bwutils
from activity_browser.ui import widgets, icons, delegates
from activity_browser.ui.menu_bar import ImportDatabaseMenu


class DatabasesPane(widgets.ABAbstractPane):
    """
    A widget that displays the databases and their details.

    Attributes:
        view (DatabasesView): The view displaying the databases.
        model (DatabasesModel): The model containing the data for the databases.
    """
    title = "Databases"
    unique = True

    def __init__(self, parent):
        """
        Initializes the DatabasesPane widget.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.view = DatabasesView()
        self.model = DatabasesModel()
        self.view.setModel(self.model)

        self.view.setAlternatingRowColors(True)
        self.view.setIndentation(0)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signals to the appropriate slots.
        """
        signals.meta.databases_changed.connect(self.sync)
        signals.project.changed.connect(self.sync)
        signals.database.deleted.connect(self.sync)
        signals.database_read_only_changed.connect(self.sync)

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(5, 0, 5, 5)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the model with the current state of the databases.
        """
        self.model.setDataFrame(self.build_df())
        self.view.resizeColumnToContents(0)
        self.view.header().setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the databases.

        Returns:
            pd.DataFrame: The DataFrame containing the databases data.
        """
        data = []
        for name in bd.databases:
            # get the modified time, in case it doesn't exist, just write 'now' in the correct format
            dt = bd.databases[name].get("modified", datetime.datetime.now().isoformat())
            dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f")

            # final column includes interactive checkbox which shows read-only state of db
            data.append(
                {
                    "name": name,
                    "depends": ", ".join(bd.databases[name].get("depends", [])),
                    "modified": dt,
                    "records": bwutils.commontasks.count_database_records(name),
                    "read_only": bd.databases[name].get("read_only", True),
                    "default_allocation": bd.databases[name].get("default_allocation", "unspecified"),
                    "backend": bd.databases[name].get("backend")
                }
            )

        cols = ["read_only", "name", "records", "depends", "default_allocation", "modified", "backend"]

        return pd.DataFrame(data, columns=cols)


class DatabasesView(widgets.ABTreeView):
    """
    A view that displays the databases in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "modified": delegates.DateTimeDelegate,
    }

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(actions.DatabaseNew),
            lambda m: m.addMenu(ImportDatabaseMenu(m)),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.DatabaseDelete, p.selected_databases[0] if p.selected_databases else None,
                               enable=len(p.selected_databases) == 1),
            lambda m, p: m.add(actions.DatabaseDuplicate, p.selected_databases[0] if p.selected_databases else None,
                               enable=len(p.selected_databases) == 1),
            lambda m, p: m.add(actions.DatabaseProcess, p.selected_databases[0] if p.selected_databases else None,
                               enable=len(p.selected_databases) == 1),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.DatabaseSetReadonly, p.selected_databases[0] if p.selected_databases else None,
                               not m.selected_readonly,
                               enable=len(p.selected_databases) == 1,
                               text="Unlock database" if m.selected_readonly else "Lock database",
                               ),
        ]

        @property
        def selected_readonly(self):
            """
            Returns the read-only state of the selected database.

            Returns:
                bool: The read-only state of the selected database.
            """
            if not self.parent().selected_databases:
                return None
            return self.parent().selectedIndexes()[0].internalPointer()["read_only"]

    class HeaderMenu(QtWidgets.QMenu):
        """
        A header menu for the DatabasesView. Currently not used.
        """

        def __init__(self, *args, **kwargs):
            super().__init__()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        """
        Handles the mouse double click event to toggle the read-only state or select the database.

        Args:
            event (QtGui.QMouseEvent): The mouse double click event.
        """
        index = self.indexAt(event.pos())

        if not index.isValid():
            return super().mouseDoubleClickEvent(event)

        db_name = index.internalPointer()["name"]

        if index.column() == 0:
            read_only = index.internalPointer()["read_only"]
            actions.DatabaseSetReadonly.run(db_name, not read_only)
            return

        actions.DatabaseOpen.run([db_name])

    @property
    def selected_databases(self) -> list:
        """
        Returns the database name of the user-selected index.

        Returns:
            str: The name of the selected database.
        """
        if not self.selectedIndexes():
            return []
        return list(set([i.internalPointer()["name"] for i in self.selectedIndexes()]))


class DatabasesItem(widgets.ABDataItem):
    """
    An item representing a database in the tree view.
    """

    def decorationData(self, col: int, key: str):
        """
        Provides decoration data for the item.

        Args:
            col (int): The column index.
            key (str): The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
        if key == "read_only":
            return icons.qicons.locked if self["read_only"] else icons.qicons.empty
        return super().decorationData(col, key)

    def displayData(self, col: int, key: str):
        """
        Provides display data for the item.

        Args:
            col (int): The column index.
            key (str): The key for which to provide display data.

        Returns:
            The display data for the item.
        """
        if key == "read_only":
            return None
        return super().displayData(col, key)

    def fontData(self, col: int, key: str):
        """
        Provides font data for the item.

        Args:
            col (int): The column index.
            key (str): The key for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the item.
        """
        font = super().fontData(col, key)
        if key == "name":
            font.setWeight(QtGui.QFont.Weight.DemiBold)
        return font


class DatabasesModel(widgets.ABItemModel):
    """
    A model representing the data for the databases.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = DatabasesItem

    def headerData(self, section, orientation=Qt.Orientation.Horizontal, role=Qt.ItemDataRole.DisplayRole):
        """
        Provides header data for the model.

        Args:
            section (int): The section index.
            orientation (Qt.Orientation): The orientation of the header.
            role (Qt.ItemDataRole): The role for which to provide header data.

        Returns:
            The header data for the model.
        """
        if section == 0 and role == Qt.ItemDataRole.DisplayRole:
            return ""
        if section == 0 and role == Qt.ItemDataRole.DecorationRole:
            return icons.qicons.unlocked
        return super().headerData(section, orientation, role)

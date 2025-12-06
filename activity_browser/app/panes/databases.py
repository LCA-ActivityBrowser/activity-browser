import datetime
from loguru import logger

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt

import bw2data as bd
import pandas as pd

from activity_browser import app
from activity_browser.bwutils.commontasks import count_database_records
from activity_browser.ui import widgets, icons, delegates, core
from activity_browser.app.menu_bar import ImportDatabaseMenu


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
        self.model = DatabasesModel(parent=self)
        self.view = DatabasesView()
        self.view.setModel(self.model)

        self.view.setAlternatingRowColors(True)
        self.view.setIndentation(0)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signals to the appropriate slots.
        """
        app.signals.meta.databases_changed.connect(self.sync)
        app.signals.metadata.synced.connect(self.sync)
        app.signals.database.deleted.connect(self.sync)
        app.signals.database_read_only_changed.connect(self.sync)

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        layout.setContentsMargins(5, 0, 5, 5)
        self.setLayout(layout)

    @QtCore.Slot()
    def sync(self):
        """
        Synchronizes the model with the current state of the databases.
        """
        logger.debug(f"Syncing {self.__class__.__name__}")

        df = self.build_df()
        self.model.set_dataframe(df)
        self.view.resizeColumnToContents(1)
        self.view.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Fixed)

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
                    "records": count_database_records(name),
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

    class ExportDatabaseContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.setTitle("Export database" if len(m.parent().selected_databases) == 1 else "Export databases"),
            lambda m, p: m.add(app.actions.DatabaseExportExcel, p.selected_databases if p.selected_databases else [],
                               enable=len(p.selected_databases) >= 1,
                               text="to .xlsx",
                               ),
            lambda m, p: m.add(app.actions.DatabaseExportBW2Package, p.selected_databases if p.selected_databases else [],
                               enable=len(p.selected_databases) >= 1,
                               text="to .bw2package",
                               ),
        ]

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.DatabaseNew),
            lambda m: m.addMenu(ImportDatabaseMenu(m)),
            lambda m, p: m.addMenu(DatabasesView.ExportDatabaseContextMenu(parent=p)),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.DatabaseDelete, p.selected_databases if p.selected_databases else [],
                               enable=len(p.selected_databases) >= 1,
                               text="Delete databases" if len(p.selected_databases) > 1 else "Delete database",
                               ),
            lambda m, p: m.add(app.actions.DatabaseDuplicate, p.selected_databases[0] if p.selected_databases else None,
                               enable=len(p.selected_databases) == 1),
            lambda m, p: m.add(app.actions.DatabaseRelink, p.selected_databases[0] if p.selected_databases else None),
            lambda m, p: m.add(app.actions.DatabaseProcess, p.selected_databases[0] if p.selected_databases else None,
                               enable=len(p.selected_databases) == 1),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.DatabaseSetReadonly, p.selected_databases[0] if p.selected_databases else None,
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
            index = self.parent().selectedIndexes()[0]
            row = self.parent().model().row(index)
            return row.get("read_only") if row is not None else None

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

        row = self.model().row(index)
        if row is None:
            return super().mouseDoubleClickEvent(event)

        db_name = row.get("name")

        if index.column() == 1:
            read_only = row.get("read_only")
            app.actions.DatabaseSetReadonly.run(db_name, not read_only)
            return

        app.actions.DatabaseOpen.run([db_name])

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        """
        Handles key press events. Specifically handles the Delete key to delete selected databases.

        Args:
            event (QtGui.QKeyEvent): The key press event.
        """
        if event.key() == Qt.Key_Delete:
            if self.selected_databases:
                app.actions.DatabaseDelete.run(self.selected_databases)
                return
        
        super().keyPressEvent(event)

    @property
    def selected_databases(self) -> list:
        """
        Returns the database name of the user-selected index.

        Returns:
            str: The name of the selected database.
        """
        if not self.selectedIndexes():
            return []
        names = self.model().values_from_indices("name", self.selectedIndexes())
        return list(set(names))


class DatabasesModel(core.ABTreeModel):
    """
    A model representing the data for the databases.
    """

    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data for the index.
        """
        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return None

        if column_name == "read_only":
            return icons.qicons.locked if row.get("read_only") else icons.qicons.empty

        return None

    def displayData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides display data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide display data.

        Returns:
            The display data for the index.
        """
        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return None

        if column_name == "read_only":
            return None

        return row.get(column_name)

    def fontData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides font data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        column_name = self.column_name(index)

        if column_name == "name":
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font

        return None

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
        if section == 1 and role == Qt.ItemDataRole.DisplayRole:
            return ""
        if section == 1 and role == Qt.ItemDataRole.DecorationRole:
            return icons.qicons.unlocked
        return super().headerData(section, orientation, role)

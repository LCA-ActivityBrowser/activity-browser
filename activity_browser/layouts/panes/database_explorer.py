from logging import getLogger

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui

import bw2data as bd

from activity_browser import signals
from activity_browser.bwutils import AB_metadata
from activity_browser.ui import widgets, application

log = getLogger(__name__)

COLUMNS = ["name", "type", "exchanges", "database", "code"]
DETAILS_COLUMNS = ["input", "output", "type", "amount"]


DEFAULT_STATE = {
    "columns": ["Activity", "Product", "Type", "Unit", "Location"],
    "visible_columns": ["Activity", "Product", "Type", "Unit", "Location"],
}


NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}


class DatabaseExplorerPane(widgets.ABAbstractPane):

    def __init__(self, db_name: str, parent=None):
        super().__init__(parent, QtCore.Qt.WindowType.Window)
        self.title = "Database Explorer - " + db_name
        self.database = bd.Database(db_name)
        self.model = NodeModel(self)

        # Create the QTableView and set the model
        self.table_view = NodeView(self)
        self.table_view.setModel(self.model)
        self.model.setDataFrame(self.build_df())

        self.search = QtWidgets.QLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.search.textChanged.connect(self.table_view.setAllFilter)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.table_view)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.search)
        self.layout().addWidget(self.splitter)

        # connect signals
        signals.database.deleted.connect(self.deleteLater)
        signals.project.changed.connect(self.deleteLater)
        AB_metadata.synced.connect(self.sync)
        self.table_view.filtered.connect(self.search_error)

    def sync(self):
        self.model.setDataFrame(self.build_df())

    def build_df(self) -> pd.DataFrame:
        import sqlite3
        from bw2data.backends import sqlite3_lci_db

        full_df = AB_metadata.get_database_metadata(self.database.name)

        con = sqlite3.connect(sqlite3_lci_db._filepath)
        sql = f"SELECT output_code FROM exchangedataset WHERE output_database == '{self.database.name}'"
        excs = pd.read_sql(sql, con)
        con.close()

        count = excs.groupby(excs.columns.tolist()).size()
        count.name = "exchanges"
        full_df = full_df.join(count, "code")

        return full_df

    def search_error(self, reset=False):
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class NodeView(widgets.ABTreeView):

    def __init__(self, above: QtWidgets.QWidget=None, parent=None):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.setSelectionBehavior(widgets.ABTreeView.SelectionBehavior.SelectItems)
        self.setSelectionMode(widgets.ABTreeView.SelectionMode.ExtendedSelection)

        self.above = above
        self.below: QtWidgets.QWidget = QtWidgets.QWidget(self)

    def deleteLater(self):
        super().deleteLater()
        self.below.deleteLater()

    def mouseReleaseEvent(self, event):
        self.below.deleteLater()
        self.below = QtWidgets.QWidget(self)

        if not self.selectedIndexes():
            return

        idx = self.selectedIndexes()[0]
        col_name = self.model().columns()[idx.column()]
        item = idx.internalPointer()
        data = item[col_name]

        if col_name == "exchanges":
            act = bd.get_node(database=item["database"], code=item["code"])
            model = NodeModel()
            model.setDataFrame(pd.DataFrame(act.exchanges()))

            self.below = NodeView(self)
            self.below.setModel(model)

            self.parent().addWidget(self.below)

        elif isinstance(data, (dict, list, tuple)):
            if isinstance(data, dict):
                df = pd.DataFrame.from_dict(data, orient="index")
                df.reset_index(inplace=True)
            else:
                df = pd.DataFrame(data)
            model = NodeModel(dataframe=df)

            self.below = NodeView(self)
            self.below.setModel(model)

            self.parent().addWidget(self.below)

        elif isinstance(data, (str, float, int)):

            if isinstance(data, float) and pd.isna(data):
                return

            self.below = QtWidgets.QPlainTextEdit(str(data), self)
            self.parent().addWidget(self.below)


class NodeItem(widgets.ABDataItem):

    def displayData(self, col: int, key: str):
        data = self[key]

        if data is None:
            return None

        if isinstance(data, (str, float, int)):
            if key == "exchanges":
                return f"Exchanges: {data}" if not pd.isna(data) else "Exchanges: 0"


            rep = str(data).replace("\n", " ")
            if len(rep) > 200:
                return rep[:200] + "..."
            return rep

        elif hasattr(data, "__len__"):
            return f"{type(data).__name__.capitalize()}: {len(data)}"

        else:
            return str(type(data))


class NodeModel(widgets.ABItemModel):
    dataItemClass = NodeItem


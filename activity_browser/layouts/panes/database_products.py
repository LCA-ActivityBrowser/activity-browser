from logging import getLogger
from time import time

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import bw2data as bd

from activity_browser import actions, ui, signals, application
from activity_browser.settings import project_settings
from activity_browser.ui import core, widgets, delegates
from activity_browser.bwutils import AB_metadata, database_is_locked, database_is_legacy

log = getLogger(__name__)

DEFAULT_STATE = {
    "columns": ["activity", "product", "Type", "Unit", "Location"],
    "visible_columns": ["activity", "product", "type", "unit", "location"],
}

NODETYPES = {
    "all_nodes": [],
    "processes": ["process", "multifunctional", "processwithreferenceproduct", "nonfunctional"],
    "products": ["product", "processwithreferenceproduct", "waste"],
    "biosphere": ["natural resource", "emission", "inventory indicator", "economic", "social"],
}


class DatabaseProductsPane(widgets.ABAbstractPane):
    """
    A widget that displays products related to a specific database.

    Attributes:
        database (bd.Database): The database to display products for.
        model (ProductModel): The model containing the data for the products.
        table_view (ProductView): The view displaying the products.
        search (widgets.ABLineEdit): The search bar for quick search.
    """
    def __init__(self, parent, db_name: str):
        """
        Initializes the DatabaseProductsPane widget.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
            db_name (str): The name of the database to display products for.
        """
        self.name = "database_products_pane_" + db_name

        super().__init__(parent)
        self.database = bd.Database(db_name)
        self.title = db_name
        self.model = ProductModel(self)

        # Create the QTableView and set the model
        self.table_view = ProductView(self)
        self.table_view.setModel(self.model)
        self.model.setDataFrame(self.build_df())

        self.search = widgets.ABLineEdit(self)
        self.search.setMaximumHeight(30)
        self.search.setPlaceholderText("Quick Search")

        self.build_layout()
        self.connect_signals()

    def build_layout(self):
            table_layout = QtWidgets.QHBoxLayout()
            table_layout.setSpacing(0)
            table_layout.addWidget(self.table_view)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(self.search)
            layout.addLayout(table_layout)

            # Set the table view as the central widget of the window
            self.setLayout(layout)

    def connect_signals(self):
        AB_metadata.synced.connect(self.sync)
        signals.database.deleted.connect(self.on_database_deleted)

        self.table_view.filtered.connect(self.search_error)
        self.search.textChangedDebounce.connect(self.table_view.setAllFilter)

    def saveState(self):
        """
        Save the state of the pane.
        """
        return {
            "database_name": self.database.name,
            "header_state": self.table_view.header().saveState(),
            "group_by": self.model.grouped_columns,
        }

    @classmethod
    def fromState(cls, state: dict, parent=None):
        """
        Restore the state of the pane.
        """
        pane = cls(parent, state["database_name"])
        pane.model.grouped_columns = state.get("group_by", [])
        if "header_state" in state:
            pane.table_view.header().restoreState(state["header_state"])
        return pane


    def sync(self):
        """
        Synchronizes the widget with the current state of the database.
        """
        t = time()
        self.model.setDataFrame(self.build_df())
        log.debug(f"Synced DatabaseProductsPane in {time() - t:.2f} seconds")

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the database products.

        Returns:
            pd.DataFrame: The DataFrame containing the products data.
        """
        t = time()
        cols = ["name", "key", "processor", "product", "type", "unit", "location", "id", "categories", "properties"]
        if self.database.name in AB_metadata.databases:
            full_df = AB_metadata.dataframe.loc[self.database.name].reindex(cols, axis="columns")
        else:
            full_df = pd.DataFrame(columns=cols)
        full_df["processor"] = full_df["processor"].astype(object)

        df = full_df.merge(
            full_df[["name", "key"]].rename({"name": "processor_name", "key": "processor_key"}, axis="columns"),
            left_on="processor",
            right_on="processor_key",
            how="left",
        )

        # "activity"
        # node.name by default, but processor.name in case of a Product
        df["activity"] = df["name"]
        df.update(df["processor_name"].rename("activity"))

        # "product"
        # node.name for "product"-types, overwritten by node.product
        df["product_name"] = df[df.type.isin(["product", "waste"])]["name"]
        df.update(df["product"].rename("product_name"))
        df["product"] = df["product_name"]

        # "activity_key"
        # activity that's opened on double click
        # node.key by default, but node.processor in case of a Product
        df["activity_key"] = df["key"]
        df.update(df["processor"].rename("activity_key"))

        # "product_key"
        #  product of an activity
        df["product_key"] = df["key"]

        # drop all processes that have products
        df = df.drop(df[df.key.isin(df.processor)].index)

        if not df.properties.isna().all():
            props_df = df[df.properties.notna()]
            props_df = pd.DataFrame(list(props_df.get("properties")), index=props_df.key)
            props_df.rename(lambda col: f"property_{col}", axis="columns", inplace=True)

            df = df.merge(
                props_df,
                left_on="key",
                right_index=True,
                how="left",
            )

        cols = ["activity", "product", "type", "unit", "location", "categories", "activity_key", "product_key"]
        cols += [col for col in df.columns if col.startswith("property")]

        log.debug(f"Built DatabaseProductsPane dataframe in {time() - t:.2f} seconds")

        return df[cols]

    def on_database_deleted(self, db_name: str):
        """
        Handles the database deleted signal by closing the widget if the database is deleted.

        Args:
            db_name (str): The name of the deleted database.
        """
        if db_name == self.database.name:
            self.deleteLater()

    def event(self, event):
        """
        Handles the event to save the state to settings on deferred delete.

        Args:
            event: The event to handle.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type() == QtCore.QEvent.Type.DeferredDelete:
            self.save_state_to_settings()

        return super().event(event)

    def save_state_to_settings(self):
        """
        Saves the state of the table view to the project settings.
        """
        project_settings.settings["database_explorer"] = project_settings.settings.get("database_explorer", {})
        project_settings.settings["database_explorer"][self.database.name] = self.table_view.saveState()
        project_settings.write_settings()

    def get_state_from_settings(self):
        """
        Gets the state from the project settings.

        Returns:
            dict: The state of the table view.
        """
        return DEFAULT_STATE

    def search_error(self, reset=False):
        """
        Handles the search error by changing the search bar color.

        Args:
            reset (bool, optional): Whether to reset the search bar color. Defaults to False.
        """
        if reset:
            self.search.setPalette(application.palette())
            return

        palette = self.search.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search.setPalette(palette)


class ProductView(ui.widgets.ABTreeView):
    """
    A view that displays the products in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "categories": delegates.ListDelegate,
        "activity_key": delegates.StringDelegate,
        "product_key": delegates.StringDelegate,
    }

    class ContextMenu(ui.widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(actions.ActivityOpen, p.selected_activities,
                               text="Open process" if len(p.selected_activities) == 1 else "Open processes",
                               enable=len(p.selected_activities) > 0
                               ),
            lambda m, p: m.add(actions.ActivityGraph, p.selected_activities,
                               enable=len(p.selected_activities) > 0,
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.ActivityNewProcess, m.database_name,
                               enable=not database_is_locked(m.database_name),
                               ),
            lambda m, p: m.add(actions.ActivityDuplicate, p.selected_activities,
                               text="Duplicate process" if len(p.selected_activities) == 1 else "Duplicate processes",
                               enable=len(p.selected_activities) > 0 and not database_is_locked(m.database_name),
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.ActivityDelete, p.selected_activities,
                               text="Delete process" if len(p.selected_activities) == 1 else "Delete processes",
                               enable=len(p.selected_activities) > 0 and not database_is_locked(m.database_name),
                               ),
            lambda m, p: m.add(actions.ActivityDelete, p.selected_products,
                               text="Delete product" if len(p.selected_products) == 1 else "Delete products",
                               enable=len(p.selected_products) > 0 and not
                               database_is_locked(m.database_name) and not
                               database_is_legacy(m.database_name),
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(actions.CSNew,
                               functional_units=[{prod: m.get_functional_unit_amount(prod)} for prod in p.selected_products],
                               enable=len(p.selected_products) > 0,
                               text="Create setup"
                               ),
            lambda m, p: m.add(actions.ActivitySDFToClipboard, p.selected_products,
                               enable=len(p.selected_products) > 0,
                               ),
        ]

        @staticmethod
        def get_functional_unit_amount(key):
            from activity_browser.bwutils import refresh_node
            excs = list(refresh_node(key).upstream(["production"]))
            exc = excs[0] if len(excs) == 1 else {}
            return exc.get("amount", 1.0)

        @property
        def database_name(self):
            return self.parent().parent().database.name

    def __init__(self, parent: DatabaseProductsPane):
        """
        Initializes the ProductView.

        Args:
            parent (DatabaseProductsPane): The parent widget.
        """
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragOnly)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)

        self.propertyDelegate = delegates.PropertyDelegate(self)

    def setDefaultColumnDelegates(self):
        """
        Sets the default column delegates for the view.
        """
        super().setDefaultColumnDelegates()

        columns = self.model().columns()
        for i, col_name in enumerate(columns):
            if not col_name.startswith("property_"):
                continue
            # Set the delegate for property columns
            self.setItemDelegateForColumn(i, self.propertyDelegate)

    def mouseDoubleClickEvent(self, event) -> None:
        """
        Handles the mouse double click event to open the selected activities.

        Args:
            event: The mouse double click event.
        """
        if self.selected_activities:
            actions.ActivityOpen.run(self.selected_activities)

    @property
    def selected_products(self) -> [tuple]:
        """
        Returns the selected products.

        Returns:
            list[tuple]: The list of selected products.
        """
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["product_key"] for item in items if item["product_key"] is not None})

    @property
    def selected_activities(self) -> [tuple]:
        """
        Returns the selected activities.

        Returns:
            list[tuple]: The list of selected activities.
        """
        items = [i.internalPointer() for i in self.selectedIndexes() if isinstance(i.internalPointer(), ProductItem)]
        return list({item["activity_key"] for item in items if item["activity_key"] is not None})


class ProductItem(ui.widgets.ABDataItem):
    """
    An item representing a product in the tree view.
    """
    def decorationData(self, col, key):
        """
        Provides decoration data for the item.

        Args:
            col: The column index.
            key: The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
        if key == "activity" and self["activity"]:
            if self["type"] == "processwithreferenceproduct":
                return ui.icons.qicons.processproduct
            if self["type"] in NODETYPES["biosphere"]:
                return ui.icons.qicons.biosphere
            return ui.icons.qicons.process
        if key == "product":
            if self["type"] in ["product", "processwithreferenceproduct"]:
                return ui.icons.qicons.product
            elif self["type"] == "waste":
                return ui.icons.qicons.waste

    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        return super().flags(col, key) | Qt.ItemFlag.ItemIsDragEnabled

    def displayData(self, col: int, key: str):
        if key.startswith("property_") and not pd.isna(self[key]) and self[key]["normalize"]:
            prop = self[key].copy()
            prop["unit"] = prop['unit'] + f" / {self['unit']}"
            return prop
        return super().displayData(col, key)


class ProductModel(ui.widgets.ABItemModel):
    """
    A model representing the data for the products.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ProductItem

    def mimeData(self, indices: [QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        keys = set(self.values_from_indices("activity_key", indices))
        keys.update(self.values_from_indices("product_key", indices))
        keys = {key for key in keys if isinstance(key, tuple)}
        data.setPickleData("application/bw-nodekeylist", list(keys))
        return data

    @staticmethod
    def values_from_indices(key: str, indices: list[QtCore.QModelIndex]):
        """
        Returns the values from the given indices.

        Args:
            key (str): The key to get the values for.
            indices (list[QtCore.QModelIndex]): The indices to get the values for.

        Returns:
            list: The list of values.
        """
        values = []
        for index in indices:
            item = index.internalPointer()
            if not item or item[key] is None:
                continue
            values.append(item[key])
        return values

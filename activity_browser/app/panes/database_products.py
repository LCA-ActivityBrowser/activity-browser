from loguru import logger
from time import time

import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt, QModelIndex

import bw2data as bd

from activity_browser import ui, app
from activity_browser.ui import core, widgets, delegates, icons
from activity_browser.bwutils.commontasks import database_is_locked, database_is_legacy, is_node_biosphere


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
        self.simple = True

        # initialize the model
        self.model = ProductModel(parent=self, chunk_size=50)

        # Create the QTableView and set the model
        self.table_view = ProductView(self, db_name=db_name)
        self.table_view.setModel(self.model)

        self.search_bar = widgets.MetaDataAutoCompleteTextEdit(self)
        self.search_bar.database_name = db_name
        self.search_bar.setMaximumHeight(30)
        self.search_bar.setPlaceholderText("Quick Search")

        # Create loading indicator with spinner
        self.loading_spinner = QtWidgets.QProgressBar()
        self.loading_spinner.setRange(0, 0)  # Indeterminate/busy indicator
        self.loading_spinner.setTextVisible(False)
        self.loading_spinner.setMaximumWidth(200)
        self.loading_spinner.setMaximumHeight(20)
        
        self.loading_label = widgets.ABLabel("Loading database...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.loading_label.font()
        font.setPointSize(14)
        self.loading_label.setFont(font)
        self.loading_label.setStyleSheet("color: gray; padding: 10px;")

        # Create simple/detailed view toggle
        self.view_toggle = QtWidgets.QCheckBox("Details")
        self.view_toggle.setChecked(not self.simple)
        self.view_toggle.setToolTip("Toggle between simple and detailed view")

        self.build_layout()
        self.connect_signals()
        self.update_loading_state()
        self.sync()

    def build_layout(self):
        # Create a stacked layout to switch between loading and table view
        self.stacked_layout = QtWidgets.QStackedLayout()
        
        # Page 0: Loading indicator with spinner
        loading_widget = QtWidgets.QWidget(self)
        loading_layout = QtWidgets.QVBoxLayout(loading_widget)
        loading_layout.addStretch()
        loading_layout.addWidget(self.loading_spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_label)
        loading_layout.addStretch()
        self.stacked_layout.addWidget(loading_widget)
        
        # Page 1: Table view
        table_widget = QtWidgets.QWidget(self)
        table_layout = QtWidgets.QVBoxLayout(table_widget)
        table_layout.setSpacing(0)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.addWidget(self.table_view)
        self.stacked_layout.addWidget(table_widget)

        # Create top bar with search and toggle
        top_bar = QtWidgets.QHBoxLayout()
        top_bar.addWidget(self.search_bar)
        top_bar.addWidget(self.view_toggle)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(top_bar)
        layout.addLayout(self.stacked_layout)

        # Set the table view as the central widget of the window
        self.setLayout(layout)

    def connect_signals(self):
        app.signals.metadata.synced.connect(self.on_metadata_changed)
        app.signals.database.deleted.connect(self.on_database_deleted)

        self.table_view.filtered.connect(self.search_error)
        self.search_bar.textChangedDebounce.connect(self.search)
        self.view_toggle.checkStateChanged.connect(self.on_mode_switch)

    def on_metadata_changed(self, added, updated, deleted):
        # Check if primary data has finished loading
        self.update_loading_state()
        
        if any(db == self.database.name for db, code in added | updated | deleted):
            self.sync()

    def update_loading_state(self):
        """
        Updates the loading state based on whether primary metadata has loaded.
        Shows the loading indicator if primary data is still loading, otherwise shows the table.
        """
        if app.metadata.loader.secondary_status == "done":
            # Show table view
            self.stacked_layout.setCurrentIndex(1)
        else:
            # Show loading indicator
            self.stacked_layout.setCurrentIndex(0)

    def sync(self):
        """
        Synchronizes the widget with the current state of the database.
        """
        t = time()
        df = self.build_df()

        self.model.set_dataframe(df)

        self.table_view.header().setHidden(self.simple)
        self.table_view.viewport().setBackgroundRole(
            QtGui.QPalette.ColorRole.Window if self.simple else QtGui.QPalette.ColorRole.Base)
        self.table_view.setFrameShape(
            QtWidgets.QFrame.Shape.NoFrame if self.simple else QtWidgets.QFrame.Shape.StyledPanel)

        for col in self.model.columns():
            if col == "index" or col == "node":
                continue
            index = self.model.columns().index(col)

            if df[col].isna().all() or self.simple:
                self.table_view.hideColumn(index)
            else:
                self.table_view.showColumn(index)

        logger.debug(f"Synced DatabaseProductsPane in {time() - t:.2f} seconds")

    def build_df(self) -> pd.DataFrame:
        """
        Builds a DataFrame from the database products.

        Returns:
            pd.DataFrame: The DataFrame containing the products data.
        """
        t = time()
        cols = ["name", "key", "processor", "product", "type", "unit", "location", "id", "categories", "properties"]

        query = self.search_bar.toPlainText()
        if query:
            df = app.metadata.search_database(query, self.database.name, cols)
        else:
            df = app.metadata.get_database_metadata(self.database.name, cols)

        processors = set(df["processor"].dropna().unique())
        df = df.drop(processors, errors="ignore")
        df.rename(columns={"id": "_id"}, inplace=True)

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

        df["node"] = None

        cols = ["name", "product", "categories", "unit", "location", "key", "processor", "type"]
        if self.simple:
            cols += ["node"]
        cols += [col for col in df.columns if col.startswith("property")]
        cols += ["_id"]

        logger.debug(f"Built DatabaseProductsPane dataframe in {time() - t:.2f} seconds")

        return df[cols].reset_index(drop=True)

    def on_database_deleted(self, db_name: str):
        """
        Handles the database deleted signal by closing the widget if the database is deleted.

        Args:
            db_name (str): The name of the deleted database.
        """
        if db_name == self.database.name:
            self.deleteLater()

    def on_mode_switch(self, check: Qt.CheckState):
        """
        Handles the mode switch between simple and detailed view.

        Args:
            check (Qt.CheckState): The check state of the toggle.
        """
        self.simple = check == Qt.CheckState.Unchecked
        self.sync()

    def search_error(self, reset=False):
        """
        Handles the search error by changing the search bar color.

        Args:
            reset (bool, optional): Whether to reset the search bar color. Defaults to False.
        """
        if reset:
            self.search_bar.setPalette(app.application.palette())
            return

        palette = self.search_bar.palette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(255, 128, 128))
        self.search_bar.setPalette(palette)

    def search(self, query: str):
        """
        Applies the search query to the table view.

        Args:
            query (str): The search query.
        """
        self.sync()


class ProductView(ui.widgets.ABTreeView):
    """
    A view that displays the products in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "categories": delegates.ListDelegate,
        "key": delegates.StringDelegate,
        "processor": delegates.StringDelegate,
        "node": delegates.CardDelegate,
    }

    class ContextMenu(ui.widgets.ABMenu):
        menuSetup = [
            lambda m, p: m.add(app.actions.ActivityOpen, p.selected_activities,
                               text="Open process" if len(p.selected_activities) == 1 else "Open processes",
                               enable=len(p.selected_activities) > 0
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.ActivityNewProcess, p.db_name,
                               enable=not database_is_locked(p.db_name),
                               ),
            lambda m, p: m.add(app.actions.ActivityDuplicate, p.selected_activities,
                               text="Duplicate process" if len(p.selected_activities) == 1 else "Duplicate processes",
                               enable=len(p.selected_activities) > 0 and not database_is_locked(p.db_name),
                               ),
            lambda m, p: m.add(app.actions.ActivityDuplicateToDB, p.selected_activities,
                               text="Duplicate process to database" if len(p.selected_activities) == 1 else "Duplicate processes to database",
                               enable=len(p.selected_activities) > 0 and not database_is_locked(p.db_name),
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.ActivityDelete, p.selected_activities,
                               text="Delete process" if len(p.selected_activities) == 1 else "Delete processes",
                               enable=len(p.selected_activities) > 0 and not database_is_locked(p.db_name),
                               ),
            lambda m, p: m.add(app.actions.ActivityDelete, p.selected_products,
                               text="Delete product" if len(p.selected_products) == 1 else "Delete products",
                               enable=len(p.selected_products) > 0 and not
                               database_is_locked(p.db_name) and not
                               database_is_legacy(p.db_name),
                               ),
            lambda m: m.addSeparator(),
            lambda m, p: m.add(app.actions.CSNew,
                               functional_units=[{prod: m.get_functional_unit_amount(prod)} for prod in p.selected_products],
                               enable=len(p.selected_products) > 0,
                               text="Create setup"
                               ),
            lambda m, p: m.add(app.actions.ActivitySDFToClipboard, p.selected_products,
                               enable=len(p.selected_products) > 0,
                               ),
        ]

        @staticmethod
        def get_functional_unit_amount(key):
            from activity_browser.bwutils.commontasks import refresh_node
            excs = list(refresh_node(key).upstream(["production"]))
            exc = excs[0] if len(excs) == 1 else {}
            return exc.get("amount", 1.0)

    def __init__(self, parent: DatabaseProductsPane, db_name: str):
        """
        Initializes the ProductView.

        Args:
            parent (DatabaseProductsPane): The parent widget.
            db_name (str): The name of the database.
        """
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QTableView.DragDropMode.DragDrop)
        self.setSelectionBehavior(ui.widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(ui.widgets.ABTreeView.SelectionMode.ExtendedSelection)

        self.db_name = db_name
        self.pane = parent

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
            app.actions.ActivityOpen.run(self.selected_activities)

    def keyPressEvent(self, event) -> None:
        """
        Handles key press events. Specifically handles Ctrl+C to copy selected data.

        Args:
            event: The key press event.
        """
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_C:  # Copy
                self.copy_selection_to_clipboard()
                return
            if event.key() == Qt.Key.Key_V:
                self.copy_from_clipboard()
            if event.key() == Qt.Key.Key_A:  # Select All
                self.selectAll()
                return
            if event.key() == Qt.Key.Key_F:  # Find
                self.pane.search_bar.setFocus()
                return
        if event.key() == Qt.Key.Key_Delete:
            if database_is_locked(self.db_name):
                return
            if self.selected_products:
                app.actions.ActivityDelete.run(self.selected_products)
                return

        super().keyPressEvent(event)

    def copy_selection_to_clipboard(self):
        selection = self.selectedIndexes()
        mime_data = self.model().mimeData(selection)

        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setMimeData(mime_data)

    def copy_from_clipboard(self):
        if database_is_locked(self.db_name):
            return

        clipboard = QtWidgets.QApplication.clipboard()
        mime_data = clipboard.mimeData()

        if mime_data.hasFormat("application/bw-nodekeylist"):
            keys: list = mime_data.retrievePickleData("application/bw-nodekeylist")
            keys = list(set(keys))

            app.actions.ActivityDuplicateToDB.run(keys, self.db_name)

    def dragEnterEvent(self, event):
        """
        Handles the drag enter event.

        Args:
            event: The drag enter event.
        """
        if event.source() == self:
            return

        if database_is_locked(self.db_name):
            return

        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")

            if any(is_node_biosphere(key) for key in keys):
                return

            self.overlay = widgets.ABDropOverlay(self, text="Drop here to duplicate to this database")
            self.overlay.show()
            event.accept()

    def dragMoveEvent(self, event):
        pass

    def dragLeaveEvent(self, event):
        """
        Handles the drag leave event.

        Args:
            event: The drag leave event.
        """
        # Reset the palette on drag leave
        self.overlay.deleteLater()

    def dropEvent(self, event):
        """
        Handles the drop event.

        Args:
            event: The drop event.
        """
        logger.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        # Reset the palette on drop
        self.overlay.deleteLater()

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        keys = list(set(keys))

        app.actions.ActivityDuplicateToDB.run(keys, self.db_name)

    @property
    def selected_products(self) -> list[tuple]:
        """
        Returns the selected products.

        Returns:
            list[tuple]: The list of selected products.
        """
        keys = self.model().values_from_indices("key", self.selectedIndexes())
        types = self.model().values_from_indices("type", self.selectedIndexes())

        return list({key for key, type in zip(keys, types) if not type == "nonfunctional"})

    @property
    def selected_activities(self) -> list[tuple]:
        """
        Returns the selected activities.

        Returns:
            list[tuple]: The list of selected activities.
        """
        processors = self.model().values_from_indices("processor", self.selectedIndexes())
        keys = self.model().values_from_indices("key", self.selectedIndexes())

        return list({processor if not pd.isna(processor) else key for processor, key in zip(processors, keys)})


class ProductModel(ui.core.ABTreeModel):
    #-- flag overrides ---
    def indexDragEnabled(self, index: QtCore.QModelIndex) -> bool:
        return True

    def displayData(self, index: QModelIndex) -> any:
        column_name = self.column_name(index)
        if column_name != "node":
            return super().displayData(index)

        row = self.row(index)

        # Get the product or name for title
        title = row.get("product") or row.get("name")

        # Build subtitle with name (if product exists) or type
        subtitle_parts = []
        if row.get("product") and row.get("name"):
            # If there's both product and name, show name as subtitle
            subtitle_parts.append(row.get("name"))
        elif row.get("type"):
            # Otherwise show type
            subtitle_parts.append(row.get("type").capitalize())

        subtitle = " | ".join(subtitle_parts) if subtitle_parts else None

        # Build categories list from unit, location, database
        categories = []
        if row.get("unit"):
            categories.append(str(row.get("unit")))
        if row.get("location"):
            categories.append(str(row.get("location")))
        if row.get("key") and isinstance(row.get("key"), tuple):
            categories.append(str(row.get("key")[0]))  # database name

        # Add actual categories if they exist
        node_categories = row.get("categories")
        if node_categories and isinstance(node_categories, (list, tuple)):
            categories.extend([str(cat) for cat in node_categories if str(cat).strip()])

        return {
            "title": title,
            "subtitle": subtitle,
            "categories": categories if categories else None,
        }

    #-- data overrides ---
    def decorationData(self, index: QtCore.QModelIndex) -> any:
        column_name = self.column_name(index)
        node_type = self.get(index, "type")
        
        if column_name not in ["name", "product", "node"]:
            return None
        if column_name == "product" and node_type in ["product", "processwithreferenceproduct"]:
            return icons.qicons.product
        if column_name == "product" and node_type == "waste":
            return icons.qicons.waste
        if node_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if node_type in NODETYPES["biosphere"]:
            return icons.qicons.biosphere
        return icons.qicons.process
    
    def toolTipData(self, index: QtCore.QModelIndex) -> str:
        column_name = self.column_name(index)
        if column_name not in ["name", "product"]:
            return None
        
        row = self.row(index)

        html_tooltip = f"""
        <b>{row.get('product')}</b><br>
        <i>{row.get('name')}</i><br>
        <br>
        {row.get('unit')} | {row.get('location')} | {row.get('type')}
        """

        return html_tooltip

    def mimeData(self, indices: list[QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        keys = set(self.values_from_indices("key", indices))
        keys.update(self.values_from_indices("processor", indices))
        keys = {key for key in keys if isinstance(key, tuple)}
        data.setPickleData("application/bw-nodekeylist", list(keys))

        # Add text data for Excel/external apps
        # Get selected rows and build tab-separated text
        rows = [self.row(i) for i in indices]
        columns = [c for c in self.columns() if c not in ["index", "node"]]
        text_lines = ["\t".join(columns)]  # Header line

        for row in rows:
            # Select relevant columns for export
            text_lines.append("\t".join(str(row.get(col, "")) for col in columns))

        data.setText("\n".join(text_lines))

        return data

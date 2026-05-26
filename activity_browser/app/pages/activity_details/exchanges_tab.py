from PySide6.QtCore import QModelIndex
from loguru import logger
from typing import Literal

from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd

import bw_functional as bf

from activity_browser import app
from activity_browser.bwutils.commontasks import (refresh_node, database_is_locked, database_is_legacy,
                                                  is_node_product_or_waste, is_node_biosphere, parameters_in_scope,
                                                  is_node_product, is_node_waste)
from activity_browser.ui import widgets, icons, delegates, core



EXCHANGE_MAP = {
    "natural resource": "biosphere", "emission": "biosphere", "inventory indicator": "biosphere",
    "economic": "biosphere", "social": "biosphere", "product": "technosphere",
    "processwithreferenceproduct": "technosphere", "waste": "technosphere",
}


class ExchangesTab(QtWidgets.QWidget):
    """
    A widget that displays exchanges related to a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display exchanges for.
        output_view (ExchangesView): The view displaying the output exchanges.
        output_model (ExchangesModel): The model containing the data for the output exchanges.
        input_view (ExchangesView): The view displaying the input exchanges.
        input_model (ExchangesModel): The model containing the data for the input exchanges.
    """
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        """
        Initializes the ExchangesTab widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display exchanges for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self.setAcceptDrops(True)

        # Refresh the activity node
        self.activity = refresh_node(activity)

        # Output Table
        self.output_view = ExchangesView(self)
        self.output_model = ExchangesModel(tab=self)
        self.output_view.setModel(self.output_model)

        # Set indentation for output view
        self.output_view.setIndentation(0)

        # Input Table
        self.input_view = ExchangesView(self)
        self.input_model = ExchangesModel(tab=self)
        self.input_view.setModel(self.input_model)

        # Set indentation for input view
        self.input_view.setIndentation(0)

        # Overlay for drag and drop
        self.overlay = None

        # Build the layout of the widget
        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        # Add output label and view to the layout
        output = QtWidgets.QWidget(self)
        output_layout = QtWidgets.QVBoxLayout(output)
        output_layout.addWidget(widgets.ABLabel.demiBold(" Output:", self))
        output_layout.addWidget(self.output_view)

        # Add input label and view to the layout
        input = QtWidgets.QWidget(self)
        input_layout = QtWidgets.QVBoxLayout(input)
        input_layout.addWidget(widgets.ABLabel.demiBold(" Input:", self))
        input_layout.addWidget(self.input_view)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 1)
        splitter = QtWidgets.QSplitter(Qt.Orientation.Vertical, self, childrenCollapsible=False)
        splitter.addWidget(output)
        splitter.addWidget(input)
        layout.addWidget(splitter)

    def sync(self) -> None:
        """
        Synchronizes the widget with the current state of the activity.
        """
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        # Refresh the activity node
        self.activity = refresh_node(self.activity)

        # Get the production, technosphere, and biosphere exchanges
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()
        substitution = self.activity.substitution()

        # Filter inputs and outputs based on the amount and type
        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)] +
                  [x for x in substitution if x["amount"] < 0]
                  )

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)] +
                   [x for x in substitution if x["amount"] >= 0]
                   )

        # Update the models with the new data
        output_df = self.build_df(outputs)
        output_df.reset_index(drop=True, inplace=True)
        self.output_model.set_dataframe(output_df)
        self.output_view.drag_drop_hint.setVisible(output_df.empty)

        input_df = self.build_df(inputs)
        input_df.reset_index(drop=True, inplace=True)
        self.input_model.set_dataframe(input_df)
        self.input_view.drag_drop_hint.setVisible(input_df.empty)

    def build_df(self, exchanges) -> pd.DataFrame:
        """
        Builds a DataFrame from the given exchanges.

        Args:
            exchanges (list): The list of exchanges to build the DataFrame from.

        Returns:
            pd.DataFrame: The DataFrame containing the exchanges data.
        """
        # Define the columns for the metadata
        cols = ["key", "unit", "name", "product", "location", "database", "allocation_factor",
                "properties", "processor", "categories", "type"]

        # Create a DataFrame from the exchanges
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "formula", "comment", "type"])
        exc_df["uncertainty"] = [x.uncertainty for x in exchanges]
        act_df = app.metadata.get_metadata(exc_df["input"].unique(), cols).rename(columns={"type": "_producer_type"})

        # Merge the exchanges DataFrame with the metadata DataFrame
        df = exc_df.merge(
            act_df,
            left_on="input",
            right_on="key"
        ).drop(columns=["key"])

        # Set allocation_factor to NA for non-production exchanges
        df.loc[df["type"] != "production", "allocation_factor"] = pd.NA

        # Handle properties data if available
        if not act_df.properties.isna().all():
            props_df = act_df[act_df.properties.notna()]
            props_df = pd.DataFrame(list(props_df.get("properties")), index=props_df.key)
            props_df.rename(lambda col: f"property_{col}", axis="columns", inplace=True)

            df = df.merge(
                props_df,
                left_on="input",
                right_index=True,
                how="left",
            )

        # Add allocation and activity type information
        df["_allocate_by"] = self.activity.get("allocation")
        df["_activity_type"] = self.activity.get("type")
        df["_exchange"] = exchanges

        # Drop the properties column and rename some columns
        df.drop(columns=["properties"], inplace=True)
        df.rename({
            "input": "_input_key",
            "processor": "_processor_key",
            "type": "_exchange_type",
            "name": "producer",
        }, axis="columns", inplace=True)

        # Define the order of columns for the final DataFrame
        cols = ["amount", "unit", "product", "producer", "location", "categories", "database"]
        cols += ["allocation_factor"] if not database_is_legacy(self.activity.get("database")) else []
        cols += [col for col in df.columns if col.startswith("property")]
        cols += ["formula", "comment", "uncertainty"]
        cols += [col for col in df.columns if col.startswith("_")]

        return df[cols]

    def dragEnterEvent(self, event):
        """
        Handles the drag enter event.

        Args:
            event: The drag enter event.
        """
        if database_is_locked(self.activity["database"]):
            return

        has_nodes = event.mimeData().hasFormat("application/bw-nodekeylist")
        has_exchanges = event.mimeData().hasFormat("application/bw-exchangelist")

        if not has_nodes and not has_exchanges:
            return

        event.accept()
        action = self.action_from_mime(event.mimeData())

        self.input_view.overlay.show()
        self.output_view.overlay.show()

        if action == "product":
            self.output_view.overlay.setText("Drop to substitute production")
            self.input_view.overlay.setText("Drop to consume product")
            return

        if action == "waste":
            self.output_view.overlay.setText("Drop to produce waste")
            self.input_view.overlay.setText("Drop to substitute waste consumption")
            return

        if action == "resource":
            self.output_view.overlay.hide()
            self.input_view.overlay.setText("Drop to consume natural resource")
            return

        if action == "emission":
            self.input_view.overlay.hide()
            self.output_view.overlay.setText("Drop to emit to environment")
            return


    def dragMoveEvent(self, event):
        """
        Handles the drag move event to adjust overlay opacity based on hover position.

        Args:
            event: The drag move event.
        """
        has_nodes = event.mimeData().hasFormat("application/bw-nodekeylist")
        has_exchanges = event.mimeData().hasFormat("application/bw-exchangelist")

        if not has_nodes and not has_exchanges:
            return

        if self.input_view.overlay.hovering():
            self.input_view.overlay.setOpacity("high")
            self.output_view.overlay.setOpacity("medium")
        elif self.output_view.overlay.hovering():
            self.output_view.overlay.setOpacity("high")
            self.input_view.overlay.setOpacity("medium")
        else:
            self.input_view.overlay.setOpacity("medium")
            self.output_view.overlay.setOpacity("medium")
            event.ignore()
            return

        event.accept()

    def dragLeaveEvent(self, event):
        """
        Handles the drag leave event.

        Args:
            event: The drag leave event.
        """
        # Reset the palette on drag leave
        self.input_view.overlay.hide()
        self.output_view.overlay.hide()

    def dropEvent(self, event):
        """
        Handles the drop event.

        Args:
            event: The drop event.
        """
        logger.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")

        self.input_view.overlay.hide()
        self.output_view.overlay.hide()

        output = self.output_view.overlay.hovering()
        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")

        positive_exchanges = {"technosphere": set(), "biosphere": set(), "substitution": set()}
        negative_exchanges = {"technosphere": set(), "substitution": set()}

        for key in keys:
            exc_type = get_exchange_type(key, output=output)
            if exc_type is None:
                continue
            if exc_type.startswith("-"):
                negative_exchanges[exc_type[1:]].add(key)
            else:
                positive_exchanges[exc_type].add(key)

        # Run the action for new exchanges
        for exc_type, keys in positive_exchanges.items():
            app.actions.ExchangeNew.run(keys, self.activity.key, exc_type)
        for exc_type, keys in negative_exchanges.items():
            app.actions.ExchangeNew.run(keys, self.activity.key, exc_type, amount=-1)

    def action_from_mime(self, mime: core.ABMimeData) -> Literal["product", "waste", "resource", "emission", "generic"]:
        """
        Determines the appropriate action based on the mime data.

        Args:
            mime (core.ABMimeData): The mime data.

        """
        keys = mime.retrievePickleData("application/bw-nodekeylist")
        data = app.metadata.get_metadata(keys, ["type"])
        data = set(data["type"].unique())
        data.discard("process")
        data.discard("multifunctional")
        data.discard("nonfunctional")

        if len(data) != 1:
            return "generic"

        node_type = data.pop()
        if node_type in ["product", "processwithreferenceproduct"]:
            return "product"
        if node_type == "waste":
            return "waste"
        if node_type == "natural resource":
            return "resource"
        if node_type == "emission":
            return "emission"
        else:
            return "generic"

def get_exchange_type(activity_key: tuple, output=False) -> str | None:
    if is_node_product(activity_key):
        return "substitution" if output else "technosphere"
    if is_node_waste(activity_key):
        return "-technosphere" if output else "-substitution"
    elif is_node_biosphere(activity_key):
        return "biosphere"
    return None


class RelinkDelegate(delegates.StringDelegate):
    matched: pd.DataFrame

    def createEditor(self, parent, option, index):
        model: ExchangesModel = index.model()
        
        column = model.column_name(index)
        column = "name" if column == "producer" else column

        if column == "product" and model.functional(index):
            return super().createEditor(parent, option, index)
        
        row = model.row(index)

        setup = {
            "database": row["database"],
            "name": row["producer"],
            "product": row["product"],
            "categories": row["categories"],
            "location": row["location"],
            "type": row["_producer_type"],
        }

        del setup[column]  # remove the column being edited because we are looking for alternatives

        self.matched = app.metadata.match(**setup)

        combo = QtWidgets.QComboBox(parent)
        combo.addItems(list(self.matched.get(column, []).astype(str)))
        return combo

    def setEditorData(self, editor: QtWidgets.QComboBox, index):
        model: ExchangesModel = index.model()
        column = model.column_name(index)
        column = "name" if column == "producer" else column

        if column == "product" and model.functional(index):
            return super().setEditorData(editor, index)

        value = index.data()
        if value:
            i = editor.findText(str(value))
            if i >= 0:
                editor.setCurrentIndex(i)

    def setModelData(self, editor: QtWidgets.QComboBox, model, index):
        model: ExchangesModel = index.model()
        column = model.column_name(index)
        column = "name" if column == "producer" else column

        if column == "product" and model.functional(index):
            return super().setModelData(editor, model, index)

        choice = editor.currentIndex()
        key = self.matched.iloc[choice].key
        row = model.row(index)

        app.actions.ExchangeModify.run(
            row.get("_exchange"),
            {"input": key}
        )


class ExchangesView(widgets.ABTreeView):
    """
    A view that displays the exchanges in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
    """
    defaultColumnDelegates = {
        "amount": delegates.AbsoluteAmountDelegate,
        "allocation_factor": delegates.FloatDelegate,
        "substitution_factor": delegates.FloatDelegate,
        "unit": delegates.StringDelegate,
        "producer": RelinkDelegate,
        "location": RelinkDelegate,
        "product": RelinkDelegate,
        "database": RelinkDelegate,
        "categories": RelinkDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }

    class HeaderMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.setup_view_menu(),
            lambda m: m.setup_allocation(),
        ]

        def setup_view_menu(self):
            table_view: ExchangesView = self.parent()
            table_model: ExchangesModel = table_view.model()

            def toggle_slot(action: QtWidgets.QAction):
                """
                Toggles the visibility of columns based on the action triggered.

                Args:
                    action (QtWidgets.QAction): The action triggered.
                """
                indices = action.data()
                for index in indices:
                    hidden = table_view.isColumnHidden(index)
                    table_view.setColumnHidden(index, not hidden)

            # Create the view menu
            view_menu = QtWidgets.QMenu(table_view)
            view_menu.setTitle("View")

            props_indices = []

            # Add actions for each column to the view menu
            for i, col in enumerate(table_model.columns()):
                if col.startswith("property"):
                    props_indices.append(i)
                    continue

                action = QtWidgets.QAction(table_model.columns()[i], self)
                action.setCheckable(True)
                action.setChecked(not table_view.isColumnHidden(i))
                action.setData([i])

                view_menu.addAction(action)

            # Add a combined action for property columns
            if props_indices:
                action = QtWidgets.QAction("properties", self)
                action.setCheckable(True)
                action.setChecked(not table_view.isColumnHidden(props_indices[0]))
                action.setData(props_indices)
                view_menu.addAction(action)

            # Connect the view menu actions to the toggle slot
            view_menu.triggered.connect(toggle_slot)

            # Add the view menu to the context menu
            self.addMenu(view_menu)

        def setup_allocation(self):
            table_view: ExchangesView = self.parent()

            if database_is_locked(table_view.activity["database"]) or not self.column.startswith("property"):
                return

            action = app.actions.ActivityModify.get_QAction(table_view.activity.key,
                                                        "allocation",
                                                        self.column[9:],
                                                        parent=self)
            action.setText(f"Allocate by {self.column[9:]}")
            self.addAction(action)

        @property
        def column(self):
            view, model, pos = self.parent(), self.parent().model(), QtGui.QCursor.pos()
            col_index = view.columnAt(view.mapFromGlobal(pos).x())
            return model.columns()[col_index]

    class ContextMenu(widgets.ABMenu):
        menuSetup = [
            lambda m: m.add(app.actions.ActivityNewProduct, [m.activity.key],
                            enable=not m.locked and not database_is_legacy(m.activity["database"])
                            ),
            lambda m: m.add(app.actions.ActivityNewProduct, [m.activity.key], "waste",
                            enable=not m.locked and not database_is_legacy(m.activity["database"]),
                            text="Create waste"
                            ),
            lambda m: m.addSeparator(),
            lambda m: m.add(app.actions.ExchangeDelete, m.exchanges, enable=bool(m.exchanges) and not m.locked),
            lambda m: m.add(app.actions.ExchangeSDFToClipboard, m.exchanges, enable=bool(m.exchanges)),
            lambda m: m.add(app.actions.ActivityOpen, [x.input for x in m.exchanges],
                            enable=bool(m.exchanges),
                            text="Open processs" if len(m.exchanges) == 1 else "Open processes",
                            ),
        ]

        @property
        def locked(self):
            return database_is_locked(self.activity["database"])

        @property
        def activity(self):
            return self.parent().activity

        @property
        def exchanges(self):
            indexes = self.parent().selectedIndexes()
            exchanges = [i.model().get(i, "_exchange") for i in indexes]
            return list(set(exchanges))

    def __init__(self, parent):
        """
        Initializes the ExchangesView.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.setSortingEnabled(True)

        # Enable drag and drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

        self.drag_drop_hint = QtWidgets.QLabel("Drag products here to create new exchanges.", self)
        fnt = self.drag_drop_hint.font()
        fnt.setPointSize(fnt.pointSize() + 2)
        fnt.setWeight(QtGui.QFont.Weight.ExtraLight)
        self.drag_drop_hint.setFont(fnt)

        # Set up the layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.drag_drop_hint, alignment=Qt.AlignmentFlag.AlignCenter)  # Center horizontally
        layout.addStretch()

        # Set the property delegate
        self.propertyDelegate = delegates.PropertyDelegate(self)
        self.overlay = widgets.ABDropOverlay(self)
        self.overlay.hide()

    @property
    def activity(self):
        """
        Returns the activity associated with the view.

        Returns:
            The activity associated with the view.
        """
        return self.parent().parent().parent().activity

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

    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        """
        Initiates a drag operation with the selected exchanges.

        Args:
            supportedActions: The supported drop actions.
        """
        if database_is_locked(self.activity["database"]):
            return

        super().startDrag(supportedActions)


class ExchangesModel(core.ABTreeModel):
    """
    A model representing the data for the exchanges.
    """
    def __init__(self, tab: ExchangesTab):
        super().__init__(parent=tab, enable_sorting=True)
        self.tab = tab

    def mimeTypes(self) -> list[str]:
        """
        Returns the list of MIME types that this model supports.

        Returns:
            list[str]: List of supported MIME types.
        """
        return ["application/bw-exchangelist"]

    def mimeData(self, indices: list[QtCore.QModelIndex]) -> core.ABMimeData:
        """
        Returns the MIME data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the MIME data for.

        Returns:
            core.ABMimeData: The MIME data containing the exchanges.
        """
        data = core.ABMimeData()
        exchanges = [self.get(index, "_exchange") for index in indices if index.isValid() and index.column() == 0]
        exchanges = [exc for exc in exchanges if exc is not None]
        data.setPickleData("application/bw-exchangelist", exchanges)
        return data

    def uncertainty_editor_initial(self, index: QtCore.QModelIndex) -> dict:
        initial = super().uncertainty_editor_initial(index)
        if initial:
            return initial
        row = self.row(index)
        if row is None:
            return {}
        ex = row.get("_exchange")
        if ex is None:
            return {}
        u = getattr(ex, "uncertainty", None)  # retrieve the existing uncertainty dict
        if isinstance(u, dict):
            return dict(u)
        return {}

    def uncertainty_editor_read_only(self, index: QtCore.QModelIndex) -> bool:
        if self.column_name(index) != "uncertainty":
            return False
        database = self.get(index, "_exchange")["output"][0]
        return database_is_locked(database)

    def setData(self, index: QtCore.QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        """
        Sets the data for the given index.

        Args:
            index (QtCore.QModelIndex): The index to set data for.
            value: The value to set.
            role (int): The role for which to set the data.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if role != Qt.ItemDataRole.EditRole:
            return False

        column_name = self.column_name(index)
        row = self.row(index)

        if row is None:
            return False

        exchange = row.get("_exchange")
        if exchange is None:
            return False

        if column_name in ["amount", "formula", "comment"]:
            if column_name == "formula" and not str(value).strip():
                app.actions.ExchangeFormulaRemove.run([exchange])
                return True

            app.actions.ExchangeModify.run(exchange, {column_name.lower(): value})
            return True

        if column_name in ["unit", "product", "location", "substitution_factor", "allocation_factor"]:
            act = exchange.input
            app.actions.ActivityModify.run(act.key, column_name.lower(), value)
            return True

        if column_name == "uncertainty":
            if database_is_locked(exchange.output[0]):
                return False
            app.actions.ExchangeUncertaintyModify.run([exchange], uncertainty_dict=value)
            return True

        if column_name.startswith("property_"):
            # should move this process to a separate action
            process = exchange.output
            product = exchange.input

            if not isinstance(process, bf.Process) or not isinstance(product, bf.Product):
                logger.warning(f"Expected a Process and Product, got {type(process)} and {type(product)} instead.")
                return False

            prop_key = column_name[9:]

            prop = process.property_template(prop_key, value)

            props = product.get("properties", {})
            props[prop_key] = prop

            app.actions.ActivityModify.run(product, "properties", props)
            return True

        return False
    
    def decorationData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides decoration data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide decoration data.

        Returns:
            The decoration data for the index.
        """
        column_name = self.column_name(index)

        if column_name in ["product", "producer"]:
            activity_type = self.get(index, "_producer_type")
            if activity_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
                return icons.qicons.biosphere if column_name == "producer" else None
            if activity_type == "processwithreferenceproduct":
                return icons.qicons.processproduct if column_name == "producer" else icons.qicons.product
            if activity_type in ["product", "process", "multifunctional", "nonfunctional"]:
                return icons.qicons.process if column_name == "producer" else icons.qicons.product
            if activity_type == "waste":
                return icons.qicons.process if column_name == "producer" else icons.qicons.waste

        if column_name == "amount":
            formula = self.get(index, "formula")
            if pd.isna(formula) or formula is None or formula == "":
                return None
            return icons.qicons.parameterized

        return None
    
    def fontData(self, index: QtCore.QModelIndex) -> any:
        """
        Provides font data for the model.

        Args:
            index (QtCore.QModelIndex): The index for which to provide font data.

        Returns:
            QtGui.QFont: The font data for the index.
        """
        if self.substituted(index):
            font = QtGui.QFont()
            font.setItalic(True)
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font

        if self.functional(index):
            font = QtGui.QFont()
            font.setWeight(QtGui.QFont.Weight.DemiBold)
            return font

        return None

    def indexEditable(self, index):
        column_name = self.column_name(index)
        database = self.get(index, "_exchange")["output"][0]

        # Prevent editing if the database is locked (uncertainty remains openable read-only)
        if database_is_locked(database):
            return column_name == "uncertainty"

        functional = self.functional(index)

        # Allow editing for specific keys: "amount", "formula", and "uncertainty".
        if column_name in ["amount", "formula", "uncertainty", "comment"]:
            return True

        # Allow editing for "unit", "name", and "substitution_factor" if the exchange is functional.
        if column_name in ["unit", "product"] and functional:
            return True

        # Allow editing for "producer", "location", "categories", and "database" if the exchange is not functional.
        if column_name in ["producer", "product", "location", "categories", "database"] and not functional:
            return True

        # Allow editing for properties (keys starting with "property_") if the exchange is functional.
        if column_name.startswith("property_") and functional:
            return True
        
        # Allow editing for allocation_factor if functional and allocation is manual
        if column_name == "allocation_factor" and functional and self.tab.activity.get("allocation") == "manual":
            return True

        return False

    def indexDragEnabled(self, index: QModelIndex) -> bool:
        return True
    
    def functional(self, index):
        """
        Returns whether the index is functional.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is functional, False otherwise.
        """
        return self.get(index, "_exchange_type") == "production"

    def substituted(self, index):
        """
        Returns whether the index is functional.

        Args:
            index (QtCore.QModelIndex): The index to check.

        Returns:
            bool: True if the index is functional, False otherwise.
        """
        return self.get(index, "_exchange_type") == "substitution"
    
    def scoped_parameters(self, index):
        """
        Returns the scoped parameters for the index.

        Args:
            index (QtCore.QModelIndex): The index to get scoped parameters for.

        Returns:
            list: A list of scoped parameters for the index.
        """
        exchange = self.get(index, "_exchange")
        return parameters_in_scope(exchange.output)
    
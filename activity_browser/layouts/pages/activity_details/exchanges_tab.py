from logging import getLogger

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils
from activity_browser.bwutils import refresh_node, AB_metadata, database_is_locked, database_is_legacy
from activity_browser.ui import widgets, icons, delegates

log = getLogger(__name__)

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
        self.output_model = ExchangesModel(self)
        self.output_view.setModel(self.output_model)

        # Set indentation for output view
        self.output_view.setIndentation(0)

        # Input Table
        self.input_view = ExchangesView(self)
        self.input_model = ExchangesModel(self)
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
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)

        # Add output label and view to the layout
        layout.addWidget(widgets.ABLabel.demiBold(" Output:", self))
        layout.addWidget(self.output_view)

        # Add input label and view to the layout
        layout.addWidget(widgets.ABLabel.demiBold(" Input:", self))
        layout.addWidget(self.input_view)

        # Set the layout for the widget
        self.setLayout(layout)

    def sync(self) -> None:
        """
        Synchronizes the widget with the current state of the activity.
        """
        # Refresh the activity node
        self.activity = refresh_node(self.activity)

        # Get the production, technosphere, and biosphere exchanges
        production = self.activity.production()
        technosphere = self.activity.technosphere()
        biosphere = self.activity.biosphere()

        # Filter inputs and outputs based on the amount and type
        inputs = ([x for x in production if x["amount"] < 0] +
                  [x for x in technosphere if x["amount"] >= 0] +
                  [x for x in biosphere if (x.input["type"] != "emission" and x["amount"] >= 0) or (x.input["type"] == "emission" and x["amount"] < 0)])

        outputs = ([x for x in production if x["amount"] >= 0] +
                   [x for x in technosphere if x["amount"] < 0] +
                   [x for x in biosphere if (x.input["type"] == "emission" and x["amount"] >= 0) or (x.input["type"] != "emission" and x["amount"] < 0)])

        # Update the models with the new data
        output_df = self.build_df(outputs)
        self.output_model.setDataFrame(output_df)
        self.output_view.drag_drop_hint.setVisible(output_df.empty)

        input_df = self.build_df(inputs)
        self.input_model.setDataFrame(input_df)
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
        cols = ["key", "unit", "name", "product", "location", "database", "substitute", "substitution_factor", "allocation_factor",
                "properties", "processor", "categories"]

        # Create a DataFrame from the exchanges
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "formula", "uncertainty type", "comment"])
        act_df = AB_metadata.get_metadata(exc_df["input"].unique(), cols)

        # Merge the exchanges DataFrame with the metadata DataFrame
        df = exc_df.merge(
            act_df,
            left_on="input",
            right_on="key"
        ).drop(columns=["key"])

        # Use "product" if available otherwise use "name"
        df.update(df["product"].rename("name"))

        # Handle substitute data if available
        if not df["substitute"].isna().all():
            df = df.merge(
                AB_metadata.dataframe[["key", "name"]].rename({"name": "substitute_name"}, axis="columns"),
                left_on="substitute",
                right_on="key",
                how="left",
            ).drop(columns=["key"])
        else:
            df.drop(columns=["substitute", "substitution_factor"], inplace=True)

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
        df.rename({"input": "_input_key", "substitute": "_substitute_key", "processor": "_processor_key",
                   "uncertainty type": "uncertainty"},
            axis="columns", inplace=True)

        # Define the order of columns for the final DataFrame
        cols = ["amount", "unit", "name", "location", "categories", "database"]
        cols += ["substitute_name", "substitution_factor"] if "substitute_name" in df.columns else []
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

        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            self.overlay = DropOverlay(self)
            self.overlay.show()
            event.accept()

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
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        # Reset the palette on drop
        self.overlay.deleteLater()

        keys: list = event.mimeData().retrievePickleData("application/bw-nodekeylist")
        exchanges = {"technosphere": set(), "biosphere": set()}

        for key in keys:
            act = bd.get_node(key=key)
            if act["type"] not in EXCHANGE_MAP:
                continue
            exc_type = EXCHANGE_MAP[act["type"]]
            exchanges[exc_type].add(act.key)

        # Run the action for new exchanges
        for exc_type, keys in exchanges.items():
            actions.ExchangeNew.run(keys, self.activity.key, exc_type)


class DropOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.resize(parent.size())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 100, 255, 200))  # Semi-transparent blue
        painter.setPen(Qt.white)

        font = self.font()
        font.setBold(True)

        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "Drop here to create new exchanges")


class ExchangeAmountDelegate(QtWidgets.QStyledItemDelegate):
    def displayText(self, value, locale):
        import math
        try:
            value = float(value)
        except ValueError:
            value = math.nan

        if math.isnan(value):
            return ""
        return str(abs(value))

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QLineEdit(parent)
        locale = QtCore.QLocale(QtCore.QLocale.English)
        locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        validator = QtGui.QDoubleValidator()
        validator.setLocale(locale)
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        import math

        data = index.data(QtCore.Qt.DisplayRole)

        try:
            value = abs(float(data))
        except ValueError:
            value = math.nan

        editor.setText(format(value, '.10f').rstrip('0').rstrip('.'))

    def setModelData(
            self,
            editor: QtWidgets.QLineEdit,
            model: QtCore.QAbstractItemModel,
            index: QtCore.QModelIndex,
    ):
        """Take the editor, read the given value and set it in the model"""
        try:
            value = float(editor.text())
            old = float(index.data(QtCore.Qt.DisplayRole))

            if old < 0:
                value = value * -1

            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass


class ExchangesView(widgets.ABTreeView):
    """
    A view that displays the exchanges in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
        hovered_item (ExchangesItem): The item currently being hovered over.
    """
    defaultColumnDelegates = {
        "amount": ExchangeAmountDelegate,
        "allocation_factor": delegates.FloatDelegate,
        "substitution_factor": delegates.FloatDelegate,
        "unit": delegates.StringDelegate,
        "name": delegates.StringDelegate,
        "location": delegates.StringDelegate,
        "product": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
        "categories": delegates.ListDelegate,
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

            action = actions.ActivityModify.get_QAction(table_view.activity.key,
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
            lambda m: m.add(actions.ActivityNewProduct, [m.activity.key],
                            enable=not m.locked and not database_is_legacy(m.activity["database"])
                            ),
            lambda m: m.add(actions.ExchangeDelete, m.exchanges, enable=bool(m.exchanges) and not m.locked),
            lambda m: m.add(actions.ExchangeSDFToClipboard, m.exchanges, enable=bool(m.exchanges)),
            lambda m: m.add(actions.ActivityOpen, [x.input for x in m.exchanges],
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
            return list(set(idx.internalPointer().exchange for idx in indexes if idx.isValid()))

    def __init__(self, parent):
        """
        Initializes the ExchangesView.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.setSortingEnabled(True)

        self.drag_drop_hint = QtWidgets.QLabel("Drag products here to create new exchanges.", self)
        fnt = self.drag_drop_hint.font()
        fnt.setPointSize(fnt.pointSize() + 2)
        fnt.setWeight(QtGui.QFont.Weight.ExtraLight)
        self.drag_drop_hint.setFont(fnt)

        # Set up the layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.drag_drop_hint, alignment=Qt.AlignCenter)  # Center horizontally
        layout.addStretch()

        # Set the property delegate
        self.propertyDelegate = delegates.PropertyDelegate(self)

    @property
    def activity(self):
        """
        Returns the activity associated with the view.

        Returns:
            The activity associated with the view.
        """
        return self.parent().activity

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


class ExchangesItem(widgets.ABDataItem):
    """
    An item representing an exchange in the tree view.

    Attributes:
        background_color (str): The background color of the item.
    """
    background_color = None

    @property
    def exchange(self):
        """
        Returns the exchange associated with the item.

        Returns:
            The exchange associated with the item.
        """
        return self["_exchange"]

    @property
    def functional(self):
        """
        Returns whether the exchange is functional.

        Returns:
            bool: True if the exchange is functional, False otherwise.
        """
        return self["_exchange"].get("type") == "production"

    @property
    def scoped_parameters(self):
        """
        Returns the parameters in scope of the current exchange.

        Returns:
            dict: The parameters in scope.
        """
        return bwutils.parameters_in_scope(self["_exchange"].output)

    def flags(self, col: int, key: str):
        """
        Returns the item flags for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the flags.

        Returns:
            QtCore.Qt.ItemFlags: The item flags.
        """
        flags = super().flags(col, key)
        # Check if the database is read-only. If it is, return the default flags.
        if database_is_locked(self.exchange.output["database"]):
            return flags

        # Allow editing for specific keys: "amount", "formula", and "uncertainty".
        if key in ["amount", "formula", "uncertainty", "comment"]:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Allow editing for "unit", "name", "location", and "substitution_factor" if the exchange is functional.
        if key in ["unit", "name", "location", "substitution_factor"] and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Allow editing for properties (keys starting with "property_") if the exchange is functional.
        if key.startswith("property_") and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Allow editing for "allocation_factor" if the allocation is manual and the exchange is functional.
        if key == "allocation_factor" and self.exchange.output.get("allocation") == "manual" and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable

        # Return the default flags if none of the above conditions are met.
        return flags

    def displayData(self, col: int, key: str):
        """
        Returns the display data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the display data.

        Returns:
            str: The display data.
        """
        if key in ["allocation_factor", "substitute", "substitution_factor"] and not self.functional:
            return None

        if key.startswith("property_") and not self.functional:
            return None

        if key.startswith("property_") and isinstance(self[key], float):
            return {
                "amount": self[key],
                "unit": "undefined",
                "normalize": False,
            }

        if key.startswith("property_") and self[key].get("normalize", True):
            prop = self[key].copy()
            prop["unit"] = prop['unit'] + f" / {self['unit']}"
            return prop

        return super().displayData(col, key)

    def decorationData(self, col, key):
        """
        Provides decoration data for the item.

        Args:
            col: The column index.
            key: The key for which to provide decoration data.

        Returns:
            The decoration data for the item.
        """
        if key not in ["name", "substitute_name", "amount"] or not self.displayData(col, key):
            return

        if key == "amount":
            if pd.isna(self["formula"]) or self["formula"] is None:
                # empty icon to align the values
                return icons.qicons.empty
            return icons.qicons.parameterized

        if key == "name":
            activity_type = self.exchange.input.get("type")
        else:  # key is "substitute_name"
            activity_type = bd.get_node(key=self["_substitute_key"])["type"]

        if activity_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        if activity_type in ["product", "processwithreferenceproduct"]:
            return icons.qicons.product
        if activity_type == "waste":
            return icons.qicons.waste

    def fontData(self, col: int, key: str):
        """
        Returns the font data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the font data.

        Returns:
            QtGui.QFont: The font data.
        """
        font = super().fontData(col, key)

        # set the font to bold if it's a production/functional exchange
        if self.functional:
            font.setWeight(QtGui.QFont.Weight.DemiBold)
        return font

    def backgroundData(self, col: int, key: str):
        """
        Returns the background data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to return the background data.

        Returns:
            QtGui.QBrush: The background brush for the item.
        """
        if self.background_color:
            return QtGui.QBrush(QtGui.QColor(self.background_color))

        if key == f"property_{self['_allocate_by']}":
            from activity_browser import application
            return application.palette().alternateBase()

    def setData(self, col: int, key: str, value) -> bool:
        """
        Sets the data for the given column and key.

        Args:
            col (int): The column index.
            key (str): The key for which to set the data.
            value: The value to set.

        Returns:
            bool: True if the data was set successfully, False otherwise.
        """
        if key in ["amount", "formula", "comment"]:
            if key == "formula" and not str(value).strip():
                actions.ExchangeFormulaRemove.run([self.exchange])
                return True

            actions.ExchangeModify.run(self.exchange, {key.lower(): value})
            return True

        if key in ["unit", "name", "location", "substitution_factor", "allocation_factor"]:
            act = self.exchange.input

            # if we're dealing with a legacy activity, we need to set to the product field here
            if key == "name" and not isinstance(act, bf.Product):
                key = "reference product"

            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("property_"):
            # should move this process to a separate action
            process = self.exchange.output
            product = self.exchange.input

            if not isinstance(process, bf.Process) or not isinstance(product, bf.Product):
                log.warning(f"Expected a Process and Product, got {type(process)} and {type(product)} instead.")
                return False

            prop_key = key[9:]

            prop = process.property_template(prop_key, value)

            props = product.get("properties", {})
            props[prop_key] = prop

            actions.ActivityModify.run(product, "properties", props)

        return False


class ExchangesModel(widgets.ABItemModel):
    """
    A model representing the data for the exchanges.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ExchangesItem


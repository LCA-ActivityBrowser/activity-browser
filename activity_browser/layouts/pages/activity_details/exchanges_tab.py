from logging import getLogger

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt

import pandas as pd
import bw2data as bd

from activity_browser import actions, bwutils
from activity_browser.bwutils import refresh_node, AB_metadata
from activity_browser.ui import widgets, icons
from activity_browser.ui.tables import delegates

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

        # Build the layout of the widget
        self.build_layout()

    def build_layout(self):
        """
        Builds the layout of the widget.
        """
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 10, 0, 1)

        # Add output label and view to the layout
        layout.addWidget(QtWidgets.QLabel("<b>⠀Output:</b>"))
        layout.addWidget(self.output_view)

        # Add input label and view to the layout
        layout.addWidget(QtWidgets.QLabel("<b>⠀Input:</b>"))
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
        self.output_model.setDataFrame(self.build_df(outputs))
        self.input_model.setDataFrame(self.build_df(inputs))

    def build_df(self, exchanges) -> pd.DataFrame:
        """
        Builds a DataFrame from the given exchanges.

        Args:
            exchanges (list): The list of exchanges to build the DataFrame from.

        Returns:
            pd.DataFrame: The DataFrame containing the exchanges data.
        """
        # Define the columns for the metadata
        cols = ["key", "unit", "name", "location", "substitute", "substitution_factor", "allocation_factor",
                "properties", "processor"]

        # Create a DataFrame from the exchanges
        exc_df = pd.DataFrame(exchanges, columns=["amount", "input", "formula", "uncertainty type",])
        act_df = AB_metadata.get_metadata(exc_df["input"].unique(), cols)

        # Merge the exchanges DataFrame with the metadata DataFrame
        df = exc_df.merge(
            act_df,
            left_on="input",
            right_on="key"
        ).drop(columns=["key"])

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
        cols = ["amount", "unit", "name", "location"]
        cols += ["substitute_name", "substitution_factor"] if "substitute_name" in df.columns else []
        cols += ["allocation_factor"]
        cols += [col for col in df.columns if col.startswith("property")]
        cols += ["formula", "uncertainty"]
        cols += [col for col in df.columns if col.startswith("_")]

        return df[cols]


class ExchangesView(widgets.ABTreeView):
    """
    A view that displays the exchanges in a tree structure.

    Attributes:
        defaultColumnDelegates (dict): The default column delegates for the view.
        hovered_item (ExchangesItem): The item currently being hovered over.
    """
    defaultColumnDelegates = {
        "amount": delegates.FloatDelegate,
        "allocation_factor": delegates.FloatDelegate,
        "substitution_factor": delegates.FloatDelegate,
        "unit": delegates.StringDelegate,
        "name": delegates.StringDelegate,
        "location": delegates.StringDelegate,
        "product": delegates.StringDelegate,
        "formula": delegates.NewFormulaDelegate,
        "comment": delegates.StringDelegate,
        "uncertainty": delegates.UncertaintyDelegate,
    }
    hovered_item: "ExchangesItem" = None

    class HeaderMenu(QtWidgets.QMenu):
        """
        A context menu for the header of the ExchangesView.

        Attributes:
            view_actions (list): The list of actions for the view menu.
            set_alloc (QAction): The action to set the allocation.
        """

        def __init__(self, pos: QtCore.QPoint, view: "ExchangesView"):
            """
            Initializes the HeaderMenu.

            Args:
                pos: The position of the context menu.
                view (ExchangesView): The view displaying the exchanges.
            """
            super().__init__(view)

            model = view.model()

            # Get the column index and name based on the position
            col_index = view.columnAt(pos.x())
            col_name = model.columns()[col_index]

            def toggle_slot(action: QtWidgets.QAction):
                """
                Toggles the visibility of columns based on the action triggered.

                Args:
                    action (QtWidgets.QAction): The action triggered.
                """
                indices = action.data()
                for index in indices:
                    hidden = view.isColumnHidden(index)
                    view.setColumnHidden(index, not hidden)

            # Create the view menu
            view_menu = QtWidgets.QMenu(view)
            view_menu.setTitle("View")

            self.view_actions = []
            props_indices = []

            # Add actions for each column to the view menu
            for i, col in enumerate(model.columns()):
                if col.startswith("property"):
                    props_indices.append(i)
                    continue

                action = QtWidgets.QAction(model.columns()[i])
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(i))
                action.setData([i])
                self.view_actions.append(action)

                view_menu.addAction(action)

            # Add a combined action for property columns
            if props_indices:
                action = QtWidgets.QAction("properties")
                action.setCheckable(True)
                action.setChecked(not view.isColumnHidden(props_indices[0]))
                action.setData(props_indices)
                self.view_actions.append(action)
                view_menu.addAction(action)

            # Connect the view menu actions to the toggle slot
            view_menu.triggered.connect(toggle_slot)

            # Add the view menu to the context menu
            self.addMenu(view_menu)

            # Add an allocation action if the column is a property
            if col_name.startswith("property"):
                self.set_alloc = actions.ActivityModify.get_QAction(view.activity.key, "allocation", col_name[9:])
                self.set_alloc.setText(f"Allocate by {col_name[9:]}")
                self.addAction(self.set_alloc)

    class ContextMenu(QtWidgets.QMenu):
        """
        A context menu for the ExchangesView.

        Attributes:
            add_product_action (QAction): The action to add a new product.
            delete_exc_action (QAction): The action to delete an exchange.
            exc_to_sdf_action (QAction): The action to copy the exchange to SDF.
            remove_sub_action (QAction): The action to remove a substitute.
        """

        def __init__(self, pos, view: "ExchangesView"):
            """
            Initializes the ContextMenu.

            Args:
                pos: The position of the context menu.
                view (ExchangesView): The view displaying the exchanges.
            """
            super().__init__(view)

            # Add the action to add a new product
            self.add_product_action = actions.ActivityNewProduct.get_QAction(view.activity.key)
            self.addAction(self.add_product_action)

            index = view.indexAt(pos)
            if index.isValid():
                item: ExchangesItem = index.internalPointer()

                # Add actions for deleting an exchange and copying to SDF
                self.delete_exc_action = actions.ExchangeDelete.get_QAction([item.exchange])
                self.exc_to_sdf_action = actions.ExchangeSDFToClipboard.get_QAction([item.exchange])
                self.addAction(self.delete_exc_action)
                self.addAction(self.exc_to_sdf_action)

                # Add action to remove a substitute if it exists
                if not pd.isna(item["substitute"]):
                    self.remove_sub_action = actions.FunctionSubstituteRemove.get_QAction(item.exchange.input)
                    self.addAction(self.remove_sub_action)

    def __init__(self, parent):
        """
        Initializes the ExchangesView.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        # Enable drag and drop functionality
        self.setAcceptDrops(True)
        # Enable sorting of columns
        self.setSortingEnabled(True)

        # Set the property delegate
        self.propertyDelegate = PropertyDelegate(self)

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

    def dragMoveEvent(self, event) -> None:
        """
        Handles the drag move event.

        Args:
            event: The drag move event.
        """
        index = self.indexAt(event.pos())
        item = index.internalPointer()

        if self.hovered_item:
            if item == self.hovered_item:
                pass
            elif isinstance(item, ExchangesItem):
                self.hovered_item.background_color = None
                self.hovered_item = item
            else:
                self.hovered_item.background_color = None
                self.hovered_item = None
        elif isinstance(item, ExchangesItem):
            self.hovered_item = item

        if self.hovered_item and self.hovered_item.acceptsDragDrop(event):
            # Highlight the hovered item
            self.hovered_item.background_color = "#ADD8E6"
            self.setPalette(QtGui.QGuiApplication.palette())
            event.acceptProposedAction()
        else:
            self.dragEnterEvent(event)
            event.acceptProposedAction()

    def dragEnterEvent(self, event):
        """
        Handles the drag enter event.

        Args:
            event: The drag enter event.
        """
        if event.mimeData().hasFormat("application/bw-nodekeylist"):
            palette = self.palette()
            # Change background color on drag enter
            palette.setColor(palette.ColorGroup.All, palette.ColorRole.Base, QtGui.QColor("#e8f4f8"))
            self.setPalette(palette)
            event.accept()

    def dragLeaveEvent(self, event):
        """
        Handles the drag leave event.

        Args:
            event: The drag leave event.
        """
        if self.hovered_item:
            self.hovered_item.background_color = None
            self.hovered_item = None
        # Reset the palette on drag leave
        self.setPalette(QtGui.QGuiApplication.palette())

    def dropEvent(self, event):
        """
        Handles the drop event.

        Args:
            event: The drop event.
        """
        log.debug(f"Dropevent from: {type(event.source()).__name__} to: {self.__class__.__name__}")
        # Reset the palette on drop
        self.setPalette(QtGui.QGuiApplication.palette())

        if self.hovered_item and self.hovered_item.acceptsDragDrop(event):
            self.hovered_item.onDrop(event)
            self.hovered_item.background_color = None
            self.setPalette(QtGui.QGuiApplication.palette())
            return

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
        if key in ["amount", "formula", "uncertainty"]:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key in ["unit", "name", "location", "substitution_factor"] and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key.startswith("property_") and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
        if key == "allocation_factor" and self.exchange.output.get("allocation") == "manual" and self.functional:
            return flags | Qt.ItemFlag.ItemIsEditable
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

        if key.startswith("property_") and self[key]["normalize"]:
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
            font.setBold(True)
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
            return QtGui.QBrush(Qt.GlobalColor.lightGray)

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
        if key in ["amount", "formula"]:
            if key == "formula" and not str(value).strip():
                actions.ExchangeFormulaRemove.run([self.exchange])
                return True

            actions.ExchangeModify.run(self.exchange, {key.lower(): value})
            return True

        if key in ["unit", "name", "location", "substitution_factor", "allocation_factor"]:
            act = self.exchange.input
            actions.ActivityModify.run(act.key, key.lower(), value)

        if key.startswith("property_"):
            act = self.exchange.input
            prop_key = key[9:]
            props = act["properties"]
            props[prop_key].update({"amount": value})

            actions.ActivityModify.run(act.key, "properties", props)

        return False

    def acceptsDragDrop(self, event) -> bool:
        """
        Determines if the item accepts the drag and drop event.

        Args:
            event: The drag and drop event.

        Returns:
            bool: True if the item accepts the drag and drop event, False otherwise.
        """
        if not self.functional:
            return False

        if not event.mimeData().hasFormat("application/bw-nodekeylist"):
            return False

        keys = set(event.mimeData().retrievePickleData("application/bw-nodekeylist"))
        acts = [bd.get_node(key=key) for key in keys]
        acts = [act for act in acts if act["type"] in ["product", "waste", "processwithreferenceproduct"]]

        if len(acts) != 1:
            return False

        act = acts[0]

        if act["unit"] != self["unit"] or act.key == self.exchange.input.key:
            return False

        return True

    def onDrop(self, event):
        """
        Handles the drop event.

        Args:
            event: The drop event.
        """
        keys = set(event.mimeData().retrievePickleData("application/bw-nodekeylist"))
        acts = [bd.get_node(key=key) for key in keys]
        act = [act for act in acts if act["type"] in ["product", "waste", "processwithreferenceproduct"]][0]
        actions.FunctionSubstitute.run(self.exchange.input, act)


class ExchangesModel(widgets.ABAbstractItemModel):
    """
    A model representing the data for the exchanges.

    Attributes:
        dataItemClass (type): The class of the data items.
    """
    dataItemClass = ExchangesItem


class PropertyDelegate(QtWidgets.QStyledItemDelegate):
    """
    A delegate for displaying and editing property values in the tree view.
    """

    def displayText(self, value, locale):
        """
        Returns the display text for the given value.

        Args:
            value: The value to display.
            locale: The locale to use for formatting.

        Returns:
            str: The display text.
        """
        if not isinstance(value, dict):
            return "Undefined"

        if sorted(value.keys()) != ["amount", "normalize", "unit"]:
            return "Faulty property"

        display = f"{value['amount']} {value['unit']}"
        return display

    def createEditor(self, parent, option, index):
        """
        Creates an editor for the given index.

        Args:
            parent: The parent widget.
            option: The style options.
            index: The index to edit.

        Returns:
            QtWidgets.QLineEdit: The editor widget.
        """
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        if not data:
            return None

        editor = QtWidgets.QLineEdit(parent)
        validator = QtGui.QDoubleValidator()
        editor.setValidator(validator)
        return editor

    def setEditorData(self, editor: QtWidgets.QLineEdit, index: QtCore.QModelIndex):
        """
        Populates the editor with data if editing an existing field.

        Args:
            editor (QtWidgets.QLineEdit): The editor widget.
            index (QtCore.QModelIndex): The index to edit.
        """
        data = index.data(QtCore.Qt.ItemDataRole.DisplayRole)
        editor.setText(str(data["amount"]))

    def setModelData(self, editor: QtWidgets.QLineEdit, model: QtCore.QAbstractItemModel, index: QtCore.QModelIndex):
        """
        Takes the editor, reads the given value, and sets it in the model.

        Args:
            editor (QtWidgets.QLineEdit): The editor widget.
            model (QtCore.QAbstractItemModel): The model to update.
            index (QtCore.QModelIndex): The index to update.
        """
        try:
            value = float(editor.text())
            model.setData(index, value, QtCore.Qt.EditRole)
        except ValueError:
            pass

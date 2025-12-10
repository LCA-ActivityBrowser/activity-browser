from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd

from activity_browser.ui import widgets, core, delegates, icons
from activity_browser.app import metadata
from activity_browser.bwutils.commontasks import refresh_node


class NodeSelectDialog(QtWidgets.QDialog):
    node_selected = QtCore.Signal(dict)

    def __init__(self, parent=None, drag_enabled=False):
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.WindowType.Popup |
            QtCore.Qt.WindowType.FramelessWindowHint
        )
        self.setFixedWidth(400)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Maximum)

        self.edit = widgets.ABLineEdit(self)
        self.edit.setPlaceholderText("Enter text to search for a node")
        self.edit.textChangedDebounce.connect(self.on_search)

        # Create model and tree view for results
        self.model = NodeSearchModel(parent=self)
        self.tree_view = NodeSearchView(self)
        self.tree_view.setModel(self.model)

        self.tree_view.clicked.connect(self.accept)
        self.tree_view.dragStarted.connect(self.on_drag_started)
        self.tree_view.setDragEnabled(drag_enabled)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 0)
        layout.addWidget(self.edit)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.setFixedHeight(self.sizeHint().height())

    def showEvent(self, event):
        super().showEvent(event)
        self.edit.setFocus()

    def on_search(self, text: str):
        if not text.strip():
            # Clear results
            self.model.set_dataframe(pd.DataFrame())
            self.tree_view.setFixedHeight(0)
            self.adjustSize()
            self.setFixedHeight(self.sizeHint().height())
            return

        # Search and get results
        result_df = metadata.search(text)
        result_df = result_df[0:10] if len(result_df) > 10 else result_df

        # Add a placeholder "node" column for the CardDelegate
        result_df["node"] = None

        # Update model with search results
        self.model.set_dataframe(result_df)

        # Adjust height based on results
        if len(result_df) > 0:
            self.tree_view.setFixedHeight(min(400, len(result_df) * 80 + 20))
        else:
            self.tree_view.setFixedHeight(0)

        # Adjust dialog to minimum size
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def on_drag_started(self):
        """Handle when a drag operation is started"""
        self.hide()  # Close the dialog

    def get_selected_node(self):
        """Return the currently selected node data"""
        index = self.tree_view.currentIndex()
        if not index.isValid():
            return None
        node_id = self.model.get(index, "id")
        if not node_id:
            return None
        return refresh_node(node_id)


class NodeSearchModel(core.ABTreeModel):
    """Model for displaying search results in the node select dialog."""

    def columns(self) -> list[str]:
        return ["index", "node"]

    def indexDragEnabled(self, index: QtCore.QModelIndex) -> bool:
        return True

    def displayData(self, index: QtCore.QModelIndex) -> any:
        if not index.isValid():
            return None

        column_name = self.columns()[index.column()]
        if not column_name == "node":
            return super().displayData(index)

        row_data = self.row(index).copy()
        row_data.dropna(inplace=True)

        # Get the product or name for title
        title = row_data.get("product") or row_data.get("name")

        # Build subtitle with type and database
        if row_data.get("categories"):
            subtitle = ", ".join([str(cat) for cat in row_data.get("categories")])
        elif row_data.get("product"):
            subtitle = row_data.get("name")
        else:
            subtitle = ""

        # Build categories list from unit, location
        categories = []
        if row_data.get("unit"):
            categories.append(str(row_data.get("unit")))
        if row_data.get("location"):
            categories.append(str(row_data.get("location")))
        if row_data.get("database"):
            categories.append(str(row_data.get("database")))

        return {
            "title": title,
            "subtitle": subtitle,
            "categories": categories if categories else None,
        }

    def decorationData(self, index: QtCore.QModelIndex) -> QtGui.QIcon:
        if not index.isValid():
            return icons.qicons.empty

        node_type = self.get(index, "type")

        if node_type == "product":
            return icons.qicons.product
        if node_type == "waste":
            return icons.qicons.waste
        if node_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if node_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        return icons.qicons.process

    def mimeData(self, indices: list[QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        keys = [self.row(index).get("key") for index in indices if index.isValid()]
        keys = {key for key in keys if isinstance(key, tuple)}
        data.setPickleData("application/bw-nodekeylist", list(keys))
        return data


class NodeSearchView(widgets.ABTreeView):
    """Tree view for displaying node search results."""
    dragStarted: QtCore.SignalInstance = QtCore.Signal()

    defaultColumnDelegates = {
        "node": delegates.CardDelegate,
    }

    def __init__(self, parent: NodeSelectDialog):
        super().__init__(parent)
        self.setSelectionBehavior(widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(widgets.ABTreeView.SelectionMode.SingleSelection)
        self.viewport().setBackgroundRole(QtGui.QPalette.ColorRole.Window)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.setHeaderHidden(True)

        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setFixedHeight(0)


    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        self.dragStarted.emit()
        super().startDrag(supportedActions)


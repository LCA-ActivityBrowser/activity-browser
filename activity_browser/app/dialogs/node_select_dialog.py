from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt
import pandas as pd

from activity_browser.ui import widgets, core, delegates
from activity_browser.app import metadata, actions


class NodeSelectDialog(QtWidgets.QDialog):
    node_selected = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.WindowType.Sheet |
            QtCore.Qt.WindowType.CustomizeWindowHint
        )
        self.setModal(True)
        self.setFixedWidth(400)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Maximum)

        self.edit = widgets.ABLineEdit(self)
        self.edit.setPlaceholderText("Enter text to search for a node")
        self.edit.textChangedDebounce.connect(self.on_search)

        # Create model and tree view for results
        self.model = NodeSearchModel(parent=self)
        self.tree_view = NodeSearchView(self)
        self.tree_view.setModel(self.model)

        self.tree_view.doubleClicked.connect(self.on_node_double_clicked)
        self.tree_view.dragStarted.connect(self.on_drag_started)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(self.edit)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.setFixedHeight(self.sizeHint().height())

    def showEvent(self, event):
        """Position the dialog 200px higher than default centered position"""
        super().showEvent(event)
        if self.parent():
            parent_rect = self.parent().geometry()
            dialog_rect = self.geometry()

            # Center horizontally, but move up 200px from center vertically
            x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2 - 200

            self.move(x, y)

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

        # Prepare data for display
        result_df["node"] = result_df.apply(lambda row: {
            "database": row.get("database"),
            "name": row.get("name"),
            "product": row.get("product"),
            "unit": row.get("unit"),
            "location": row.get("location"),
            "type": row.get("type"),
            "categories": row.get("categories"),
            "id": row.get("id"),
            "key": row.get("key"),
        }, axis=1)

        # Update model with search results
        self.model.set_dataframe(result_df[["node"]])

        # Adjust height based on results
        if len(result_df) > 0:
            self.tree_view.setFixedHeight(min(400, len(result_df) * 80 + 20))
        else:
            self.tree_view.setFixedHeight(0)

        # Adjust dialog to minimum size
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def on_node_double_clicked(self, index: QtCore.QModelIndex):
        """Handle when a node is double-clicked in the tree view"""
        if not index.isValid():
            return

        # Get node data from the model
        node_data = self.model.get(index, "node")
        if node_data:
            self.node_selected.emit(node_data)
            actions.ActivityOpen.run([node_data.get("id")])
            self.accept()  # Close the dialog

    def on_drag_started(self):
        """Handle when a drag operation is started"""
        self.hide()  # Close the dialog

class NodeSearchModel(core.ABTreeModel):
    """Model for displaying search results in the node select dialog."""

    def indexDragEnabled(self, index: QtCore.QModelIndex) -> bool:
        return True

    def mimeData(self, indices: list[QtCore.QModelIndex]):
        """
        Returns the mime data for the given indices.

        Args:
            indices (list[QtCore.QModelIndex]): The indices to get the mime data for.

        Returns:
            core.ABMimeData: The mime data.
        """
        data = core.ABMimeData()
        keys = [index.data().get("key") for index in indices if index.isValid()]
        keys = {key for key in keys if isinstance(key, tuple)}
        data.setPickleData("application/bw-nodekeylist", list(keys))
        return data


class NodeSearchView(widgets.ABTreeView):
    """Tree view for displaying node search results."""
    dragStarted: QtCore.SignalInstance = QtCore.Signal()

    defaultColumnDelegates = {
        "node": delegates.NodeDelegate,
    }

    def __init__(self, parent: NodeSelectDialog):
        super().__init__(parent)
        self.setSelectionBehavior(widgets.ABTreeView.SelectionBehavior.SelectRows)
        self.setSelectionMode(widgets.ABTreeView.SelectionMode.SingleSelection)
        self.viewport().setBackgroundRole(QtGui.QPalette.ColorRole.Window)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.setHeaderHidden(True)
        self.setDragEnabled(True)

        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setFixedHeight(0)


    def startDrag(self, supportedActions: Qt.DropAction) -> None:
        self.dragStarted.emit()
        super().startDrag(supportedActions)


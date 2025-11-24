from qtpy import QtWidgets, QtCore

from activity_browser.ui import widgets
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

        print(self.sizeHint())

        self.edit = widgets.ABLineEdit(self)
        self.edit.setPlaceholderText("Enter text to search for a node")
        self.edit.textChangedDebounce.connect(self.on_search)

        # Create scroll area for results
        self.scroll_area = QtWidgets.QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFixedHeight(0)  # Start with height 0

        # Container widget for results
        self.results_container = QtWidgets.QWidget()
        self.results_layout = QtWidgets.QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(2)
        self.results_layout.addStretch()

        self.scroll_area.setWidget(self.results_container)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(self.edit)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

        self.min_height = self.sizeHint().height()

        self.setFixedHeight(self.min_height)

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
        # Clear existing results
        while self.results_layout.count() > 1:  # Keep the stretch item
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not text.strip():
            self.scroll_area.setFixedHeight(0)
            self.adjustSize()
            self.setFixedHeight(self.sizeHint().height())
            return

        result = metadata.search(text)
        result = result[0:10] if len(result) > 10 else result
        result.reverse()
        result = metadata.dataframe.loc[metadata.dataframe["id"].isin(result)].copy()
        result["rank_map"] = result["id"].apply(lambda x: result["id"].tolist().index(x))
        result = result.sort_values(by=["rank_map"]).drop(columns=["rank_map"])

        # Create NodeResult widgets for each result
        if len(result) > 0:
            for idx, row in result.iterrows():
                node_data = row.to_dict()
                node_widget = NodeResult(node_data, self)
                node_widget.clicked.connect(self.on_node_selected)
                self.results_layout.insertWidget(self.results_layout.count() - 1, node_widget)
            # Set scroll area height to show results (max 300px)
            self.scroll_area.setFixedHeight(400)
        else:
            self.scroll_area.setFixedHeight(0)

        # Adjust dialog to minimum size
        self.adjustSize()
        self.setFixedHeight(self.sizeHint().height())

    def on_node_selected(self, node_data: dict):
        """Handle when a node is clicked"""
        self.node_selected.emit(node_data)

        actions.ActivityOpen.run([node_data.get("id")])

        self.accept()  # Close the dialog

class NodeResult(QtWidgets.QFrame):
    clicked = QtCore.Signal(dict)

    def __init__(self, node_data: dict, parent=None):
        super().__init__(parent)
        
        self.node_data = node_data

        # Set frame shape for proper rendering
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

        # Set cursor to pointer to indicate clickability
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        # Set minimum height
        self.setMinimumHeight(40)

        # Apply stylesheet with actual color values
        self.setStyleSheet("""
            NodeResult {
                border: 1px solid palette(mid);
                border-radius: 3px;
                margin: 2px;
            }
            NodeResult:hover {
                border: 1px solid palette(highlight);
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)

        name_label = QtWidgets.QLabel(
        f"""
        <i>{self.node_data.get('database', '')}</i><br>
        <b>{self.node_data.get('name', '')}</b><br>
        {node_data.get('unit')} | {node_data.get('location')} | {node_data.get('type')}
        """
        )
        name_label.setWordWrap(True)
        name_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        layout.addWidget(name_label)

        self.setLayout(layout)

    def mousePressEvent(self, event):
        """Handle mouse click events"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.node_data)
        super().mousePressEvent(event)

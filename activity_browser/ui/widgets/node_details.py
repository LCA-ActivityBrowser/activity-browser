from typing import TypedDict

import pandas as pd

from PySide6 import QtGui
from qtpy import QtCore, QtWidgets

from activity_browser.ui import icons

class NodeData(TypedDict):
    database: str
    name: str
    product: str | None
    unit: str
    location: str | None
    categories: list[str] | None
    type: str


class NodeDetails(QtWidgets.QFrame):
    clicked = QtCore.Signal(dict)

    def __init__(self, node_data: NodeData, parent=None, selected=False):
        super().__init__(parent)

        self.node_data = node_data
        self.selected = selected

        # Get the icon for this node type
        node_type = node_data.get('type', '')
        self.icon = self.decorationData(node_type)

        # Set frame shape for proper rendering
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)

        # Set cursor to pointer to indicate clickability
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        # Set minimum height
        self.setMinimumHeight(40)

        # Apply stylesheet with actual color values
        # Use the highlight border when selected
        border_color = "palette(highlight)" if selected else "palette(mid)"
        self.setStyleSheet(f"""
            NodeDetails {{
                border: 1px solid {border_color};
                border-radius: 3px;
                margin: 2px;
                background-color: palette(base);
            }}
            NodeDetails:hover {{
                border: 1px solid palette(highlight);
            }}
        """)

        line_height = self.fontMetrics().height()

        layout = QtWidgets.QVBoxLayout(self)

        name = self.node_data.get('product') or self.node_data.get('name')
        name_font = self.font()
        name_font.setPointSize(10)
        name_font.setWeight(QtGui.QFont.Weight.DemiBold)
        name_label = QtWidgets.QLabel(name)
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        name_label.setFont(name_font)
        name_label.setWordWrap(True)
        name_label.setFixedHeight(int(line_height * 2.2))

        producer = self.node_data.get("name") if self.node_data.get("product") else ""
        producer_font = self.font()
        producer_font.setPointSize(7)
        producer_label = QtWidgets.QLabel(producer)
        producer_label.setFont(producer_font)
        producer_label.setFixedHeight(line_height)

        categories = self.node_data.get("categories", [])
        categories = [] if pd.isna(categories) else categories
        categories = ", ".join(categories)
        categories_font = producer_font
        categories_label = QtWidgets.QLabel(categories)
        categories_label.setFont(categories_font)
        categories_label.setFixedHeight(line_height)

        crumbs = [node_data.get('unit'), node_data.get('location'), node_data.get('database')]
        crumbs = [str(crumb) for crumb in crumbs if str(crumb).strip() not in ("nan", "None", "")]
        crumbs_text = "  |  ".join(crumbs)
        crumbs_font = self.font()
        crumbs_font.setPointSize(6)
        crumbs_label = QtWidgets.QLabel(crumbs_text)
        crumbs_label.setFont(crumbs_font)
        crumbs_label.setFixedHeight(int(line_height * 0.8))

        layout.addWidget(name_label)
        layout.addWidget(producer_label) if producer else layout.addWidget(categories_label)
        layout.addWidget(crumbs_label, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    def decorationData(self, node_type: str) -> QtGui.QIcon:
        if node_type == "product":
            return icons.qicons.product
        if node_type == "waste":
            return icons.qicons.waste
        if node_type == "processwithreferenceproduct":
            return icons.qicons.processproduct
        if node_type in ["natural resource", "emission", "inventory indicator", "economic", "social"]:
            return icons.qicons.biosphere
        return icons.qicons.process

    def paintEvent(self, event):
        """Paint the frame with icon in background"""
        super().paintEvent(event)

        if self.icon and not self.icon.isNull():
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

            # Set opacity for the background icon
            painter.setOpacity(0.1)

            # Calculate icon size and position (right side of the frame)
            icon_size = int(self.height() * 0.8)
            x = self.width() - icon_size - 10
            y = (self.height() - icon_size) // 2

            # Draw the icon
            pixmap = self.icon.pixmap(icon_size, icon_size)
            painter.drawPixmap(x, y, pixmap)

            painter.end()

    def mousePressEvent(self, event):
        """Handle mouse click events"""
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.clicked.emit(self.node_data)
        super().mousePressEvent(event)
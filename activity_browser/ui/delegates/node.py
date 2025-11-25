from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtGui import QFontMetrics, QFont, QPixmap
from qtpy.QtCore import Qt

from activity_browser.ui.widgets import NodeDetails


class NodeDelegate(QtWidgets.QStyledItemDelegate):
    """For managing and validating entered float values."""

    def sizeHint(self, option, index):
        if index.data() is None:
            return super().sizeHint(option, index)

        # Create a temporary widget to calculate the required size
        viewport = self.parent().findChild(QtWidgets.QWidget, "qt_scrollarea_viewport")
        is_selected = option.state & QtWidgets.QStyle.StateFlag.State_Selected
        node_details = NodeDetails(index.data(), viewport, selected=is_selected)
        node_details.setFixedWidth(option.rect.width())
        node_details.adjustSize()
        node_details.ensurePolished()

        size = node_details.sizeHint()
        node_details.deleteLater()

        return size

    def displayText(self, value, locale):
        return f"<b>{value}</b>"

    def paint(self, painter, option: QtWidgets.QStyleOptionViewItem, index):
        if index.data() is None:
            super().paint(painter, option, index)
            return

        painter.save()

        viewport = self.parent().findChild(QtWidgets.QWidget, "qt_scrollarea_viewport")
        is_selected = option.state & QtWidgets.QStyle.StateFlag.State_Selected
        node_details = NodeDetails(index.data(), viewport, selected=is_selected)
        node_details.resize(option.rect.width(), option.rect.height())
        node_details.ensurePolished()

        # Create high-DPI aware pixmap
        device_pixel_ratio = painter.device().devicePixelRatio()
        pixmap = QPixmap(node_details.size() * device_pixel_ratio)
        pixmap.setDevicePixelRatio(device_pixel_ratio)
        pixmap.fill(Qt.transparent)

        # Render directly to pixmap
        node_details.render(pixmap, QtCore.QPoint(), QtGui.QRegion(),
                            QtWidgets.QWidget.DrawChildren)

        painter.drawPixmap(option.rect.topLeft(), pixmap)
        painter.restore()
        return

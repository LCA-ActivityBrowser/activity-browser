from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QFontMetrics, QFont
from qtpy.QtCore import Qt


class NewFormulaDelegate(QtWidgets.QStyledItemDelegate):
    """For managing and validating entered float values."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)

        h = QFontMetrics(QFont("JetBrains Mono", 10)).height() + 4
        size.setHeight(h)  # Set your custom row height here
        return size

    def displayText(self, value, locale):
        return f"<b>{value}</b>"

    def paint(self, painter, option: QtWidgets.QStyleOptionViewItem, index):
        if index.data() is None:
            return super().paint(painter, option, index)

        painter.save()

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.color(option.palette.ColorRole.Highlight))
            painter.setPen(option.palette.color(option.palette.ColorRole.HighlightedText))
        else:
            painter.setPen(Qt.NoPen)

        if hasattr(index.internalPointer(), 'scoped_parameters'):
            scope = index.internalPointer().scoped_parameters
        else:
            scope = {}

        from activity_browser.ui.widgets import ABFormulaEdit
        viewport = self.parent().findChild(QtWidgets.QWidget, "qt_scrollarea_viewport")
        formula = ABFormulaEdit(viewport, scope, index.data())

        painter.setClipRect(option.rect)
        painter.translate(option.rect.topLeft())

        formula.setGeometry(option.rect)
        formula.paint_text(painter)

        painter.restore()

    def createEditor(self, parent, option, index):
        from activity_browser.ui.widgets import ABFormulaEdit
        if hasattr(index.internalPointer(), 'scoped_parameters'):
            scope = index.internalPointer().scoped_parameters
        else:
            scope = {}
        editor = ABFormulaEdit(parent, scope)
        return editor

    def setEditorData(self, editor, index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        value = index.data(QtCore.Qt.DisplayRole)
        # Avoid setting 'None' type value as a string
        value = str(value) if value else ""
        editor.text = value
        editor.cursor_pos = len(value)  # move cursor to the end of the field

    def updateEditorGeometry(self, editor, option, index):
        super().updateEditorGeometry(editor, option, index)

    def setModelData(
        self,
        editor: QtWidgets.QLineEdit,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        model.setData(index, editor.text, QtCore.Qt.EditRole)

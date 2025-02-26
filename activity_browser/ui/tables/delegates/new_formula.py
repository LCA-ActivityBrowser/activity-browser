import re
import asteval as ast

from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QPen, QPainter, QColor, QFontMetrics, QSyntaxHighlighter, QTextCharFormat, QFont, QTextCursor
from qtpy.QtCore import Qt, QRect, QRegularExpression


PARAM_TYPE_COLORS = {
    "project": QColor("Salmon"),
    "database": QColor("LightBlue"),
    "activity": QColor("LightGreen"),
}


class NewFormulaDelegate(QtWidgets.QStyledItemDelegate):
    """For managing and validating entered float values."""

    def displayText(self, value, locale):
        return f"<b>{value}</b>"

    def paint(self, painter, option, index):
        if index.data() is None:
            return super().paint(painter, option, index)
        if hasattr(index.internalPointer(), 'scoped_parameters'):
            scope = index.internalPointer().scoped_parameters
        else:
            scope = {}
        # Prepare the painter
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRect(option.rect)
        painter.translate(option.rect.topLeft())

        draw_expression(index.data(), scope, painter, option.rect.width(), option.rect.height())
        painter.restore()

    def createEditor(self, parent, option, index):
        if hasattr(index.internalPointer(), 'scoped_parameters'):
            scope = index.internalPointer().scoped_parameters
        else:
            scope = {}
        editor = FormulaEdit(scope, parent)
        return editor

    def setEditorData(self, editor: "FormulaEdit", index: QtCore.QModelIndex):
        """Populate the editor with data if editing an existing field."""
        value = index.data(QtCore.Qt.DisplayRole)
        # Avoid setting 'None' type value as a string
        value = str(value) if value else ""
        editor.setText(value)

    def setModelData(
        self,
        editor: QtWidgets.QLineEdit,
        model: QtCore.QAbstractItemModel,
        index: QtCore.QModelIndex,
    ):
        return super().setModelData(editor, model, index)


class FormulaEdit(QtWidgets.QLineEdit):

    def __init__(self, scope, parent):
        super().__init__(parent)
        # self.setStyleSheet("* { background-color: rgba(0, 0, 0, 0); }")
        self.scope = scope

        completer = QtWidgets.QCompleter(list(scope.keys()), self)
        self.setCompleter(completer)
    #
    # def paintEvent(self, event):
    #     tokens = re.findall(r"\b[a-zA-Z_]\w*\b|[\d.]+|[+\-*/^()=]", self.text())
    #     font_metrics = QFontMetrics(self.font())
    #     painter = QPainter(self)
    #     painter.setBrush(QColor('white'))
    #     painter.setPen(Qt.NoPen)
    #     painter.drawRect(self.rect())
    #     painter.translate(self.rect().topLeft())
    #
    #     text = self.text()
    #     for token in tokens:
    #         if token in self.scope:
    #             i = text.find(token)
    #             x = font_metrics.horizontalAdvance(text[:i]) + 2
    #             y = 0
    #             width = font_metrics.width(token)
    #             height = self.height()
    #             painter.setBrush(PARAM_TYPE_COLORS[self.scope[token]["type"]])
    #             painter.drawRect(x, y, width, height)
    #
    #     painter.end()
    #     super().paintEvent(event)


def draw_expression(expression: str, scope: dict, painter: QPainter, width: int, height: int):
    # Find all matches in the expression
    tokens = re.findall(r"\b[a-zA-Z_]\w*\b|[\d.]+|[+\-*/^()=]", expression)
    builtins = ast.make_symbol_table()

    full_width = 0
    for token in tokens:
        if token in scope:
            full_width += draw_parameter(token, painter, height, PARAM_TYPE_COLORS[scope[token]["type"]])
        else:
            full_width += draw_standard_text(token, painter, height)

    if full_width > width:
        painter.translate(width - full_width - 20, 0)
        painter.drawText(5, 1, width, height, Qt.AlignmentFlag.AlignTop, "•••")


def draw_parameter(text: str, painter: QPainter, height: int, color: QColor) -> int:
    painter.save()
    painter.setBrush(color)

    font_metrics = QFontMetrics(painter.font())
    text_width = font_metrics.horizontalAdvance(text)

    painter.drawRoundedRect(2, 1, text_width + 10, height - 2, 3, 3)
    painter.drawText(5, 1, text_width, height, Qt.AlignmentFlag.AlignTop, text)

    painter.restore()
    painter.translate(text_width + 14, 0)

    return text_width + 14


def draw_standard_text(text: str, painter: QPainter, height: int) -> int:
    painter.save()

    font_metrics = QFontMetrics(painter.font())
    text_width = font_metrics.horizontalAdvance(text)

    painter.drawText(2, 1, text_width, height, Qt.AlignmentFlag.AlignTop, text)

    painter.restore()
    painter.translate(text_width + 4, 0)

    return text_width + 4


def is_valid_number(string):
    try:
        float(string)  # float will work for both integers and floats
        return True
    except ValueError:
        return False

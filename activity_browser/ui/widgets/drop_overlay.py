from typing import Literal

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt


class ABDropOverlay(QtWidgets.QWidget):
    opacityMap = {
        "low": 100,
        "medium": 150,
        "high": 200,
    }

    def __init__(self, parent=None, text="Drop here to create new exchanges"):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.resize(parent.size())

        self._text = text
        self._opacity: Literal["low", "medium", "high"] = "medium"

    def hovering(self) -> bool:
        cursor_pos = QtGui.QCursor.pos()
        widget_rect = self.rect()
        local_pos = self.mapFromGlobal(cursor_pos)
        return widget_rect.contains(local_pos)

    def setOpacity(self, level: Literal["low", "medium", "high"]):
        if level in self.opacityMap:
            self._opacity = level
            self.update()

    def opacity(self):
        return self._opacity

    def text(self):
        return self._text

    def setText(self, text: str):
        self._text = text
        self.update()

    def showEvent(self, event):
        self.resize(self.parent().size())
        super().showEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 100, 255, self.opacityMap[self.opacity()]))  # Semi-transparent blue
        painter.setPen(Qt.GlobalColor.white)

        font = self.font()
        font.setBold(True)

        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt


class ABDropOverlay(QtWidgets.QWidget):
    def __init__(self, parent=None, text="Drop here to create new exchanges"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.resize(parent.size())
        self.text = text

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 100, 255, 200))  # Semi-transparent blue
        painter.setPen(Qt.white)

        font = self.font()
        font.setBold(True)

        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)

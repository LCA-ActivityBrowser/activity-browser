from qtpy import QtWidgets, QtGui


class ABLabel(QtWidgets.QLabel):
    @classmethod
    def demiBold(cls, *args, **kwargs):
        obj = cls(*args, **kwargs)

        font = obj.font()
        font.setWeight(QtGui.QFont.DemiBold)
        obj.setFont(font)
        return obj

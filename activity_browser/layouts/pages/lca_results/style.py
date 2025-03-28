from qtpy import QtWidgets, QtGui

def horizontal_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def vertical_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.VLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def header(text):
    label = QtWidgets.QLabel(text)

    bold_font = QtGui.QFont()
    bold_font.setBold(True)
    bold_font.setPointSize(12)

    label.setFont(bold_font)
    return label
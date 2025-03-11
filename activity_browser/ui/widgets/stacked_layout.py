from qtpy import QtWidgets


class ABStackedLayout(QtWidgets.QStackedLayout):

    def addLayout(self, layout: QtWidgets.QLayout):
        widget = LayoutWidget(self.parentWidget())
        widget.setLayout(layout)
        self.addWidget(widget)

    def sizeHint(self):
        return self.currentWidget().sizeHint()

    def minimumSize(self):
        return self.currentWidget().minimumSizeHint()


class LayoutWidget(QtWidgets.QWidget):
    pass

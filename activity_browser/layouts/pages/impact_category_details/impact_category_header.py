from qtpy import QtWidgets, QtCore
from activity_browser import actions
from activity_browser.ui import widgets


class ImpactCategoryHeader(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget):
        """
        Initializes the ActivityHeader widget.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.impact_category = parent.impact_category

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.impact_category = self.parent().impact_category

        self.clear_layout()
        self.layout().addLayout(self.build_grid())

    def clear_layout(self, layout: QtWidgets.QLayout = None):
        layout = layout or self.layout()

        if layout is None:
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

    def build_grid(self) -> QtWidgets.QGridLayout:
        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(0, 5, 0, 5)
        grid.setSpacing(10)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        name_label = QtWidgets.QLabel(f"<a href='/'>{' | '.join(self.impact_category.name)}</a>",  self)
        name_label.linkActivated.connect(lambda: actions.MethodRename.run(self.impact_category.name))

        setup = [
            ("Name:", name_label),
            ("Unit:", ImpactCategoryUnit(self)),
        ]

        # Arrange widgets for display as a grid
        for i, (title, widget) in enumerate(setup):
            grid.addWidget(widgets.ABLabel.demiBold(title, self), i, 1)
            grid.addWidget(widget, i, 2, 1, 4)

        return grid


class ImpactCategoryUnit(QtWidgets.QLineEdit):

    def __init__(self, parent: ImpactCategoryHeader):
        name = parent.impact_category.metadata.get("unit", "Undefined")

        super().__init__(name, parent)

        self.editingFinished.connect(self.change_unit)

    def change_unit(self):
        if self.text() == self.parent().impact_category.metadata.get("unit", "Undefined"):
            return
        actions.MethodMetaModify.run(self.parent().impact_category.name, "unit", self.text())
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

        setup = [
            ("Name:", QtWidgets.QLabel(str(self.impact_category.name)),),
            ("Unit:", QtWidgets.QLabel(str(self.impact_category.metadata.get("unit", "Undefined"))),),
        ]

        # Arrange widgets for display as a grid
        for i, (title, widget) in enumerate(setup):
            grid.addWidget(widgets.ABLabel.demiBold(title, self), i, 1)
            grid.addWidget(widget, i, 2, 1, 4)

        return grid


class ImpactCategoryName(QtWidgets.QLineEdit):
    """
    A widget that displays and edits the name of the activity.
    """

    def __init__(self, parent: ImpactCategoryHeader):
        """
        Initializes the ActivityName widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(str(parent.impact_category.name), parent)
        self.editingFinished.connect(self.change_name)

    def change_name(self):
        """
        Changes the name of the activity if it has been modified.
        """
        if self.text() == self.parent().impact_category.name:
            return
        # actions.ActivityModify.run(self.parent().activity, "name", self.text())
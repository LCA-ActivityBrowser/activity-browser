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

        # check if the method is editable
        editable = self.parent().is_editable
        if editable:
            name_label = QtWidgets.QLabel(f"<a href='/'>{' | '.join(self.impact_category.name)}</a>", self)
            name_label.linkActivated.connect(lambda: actions.MethodRename.run(self.impact_category.name))
            unit = ImpactCategoryUnit(parent=self)
        else:
            name_label = QtWidgets.QLabel(" | ".join(self.impact_category.name), self)
            unit = QtWidgets.QLabel(self.impact_category.metadata.get("unit", "Undefined"), self)

        # create edit button
        editable_button = QtWidgets.QPushButton("Lock" if editable else "Unlock", self)
        editable_button.clicked.connect(self.on_editable_changed)

        setup = [
            ("Name:", name_label),
            ("Unit:", unit),
        ]

        grid.addWidget(editable_button, 0, 8, len(setup), 1, QtCore.Qt.AlignmentFlag.AlignTop)

        # Arrange widgets for display as a grid
        for i, (title, widget) in enumerate(setup):
            grid.addWidget(widgets.ABLabel.demiBold(title, self), i, 1, 1, 2)
            grid.addWidget(widget, i, 2, 1, 5)

        return grid

    def on_editable_changed(self):
        """
        Called when the editable checkbox state changes.
        Notifies the parent page to update the view accordingly.
        """
        self.parent().is_editable = not self.parent().is_editable
        self.parent().sync()


class ImpactCategoryUnit(QtWidgets.QLineEdit):

    def __init__(self, parent: ImpactCategoryHeader):
        name = parent.impact_category.metadata.get("unit", "Undefined")

        super().__init__(name, parent)

        self.editingFinished.connect(self.change_unit)

    def change_unit(self):
        if self.text() == self.parent().impact_category.metadata.get("unit", "Undefined"):
            return
        actions.MethodMetaModify.run(self.parent().impact_category.name, "unit", self.text())
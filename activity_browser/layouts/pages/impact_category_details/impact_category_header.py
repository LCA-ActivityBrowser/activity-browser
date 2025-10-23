from qtpy import QtWidgets, QtCore
from activity_browser import actions
from activity_browser.ui import widgets


class ImpactCategoryHeader(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget):
        """
        Initializes the ImpactCategoryHeader widget with a stack layout
        that switches between editable and view-only headers.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.impact_category = parent.impact_category

        # Set size policy to only take needed vertical space
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Maximum
        )

        # Create stack layout to hold both header types
        self.stack = QtWidgets.QStackedLayout()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetMinimumSize)
        
        # Create both header widgets
        self.view_only_header = ViewOnlyHeader(self)
        self.editable_header = EditableHeader(self)
        
        # Add headers to stack
        self.stack.addWidget(self.view_only_header)  # Index 0
        self.stack.addWidget(self.editable_header)   # Index 1
        
        self.setLayout(self.stack)

    def sync(self):
        """
        Synchronizes the widget with the current state of the impact category.
        Switches between editable and view-only headers based on edit mode.
        """
        self.impact_category = self.parent().impact_category
        
        # Update both headers with current data
        self.view_only_header.sync()
        self.editable_header.sync()
        
        # Switch to appropriate header based on edit mode
        if self.parent().is_editable:
            self.stack.setCurrentIndex(1)  # Show editable header
        else:
            self.stack.setCurrentIndex(0)  # Show view-only header

    def on_editable_changed(self):
        """
        Called when the edit button is clicked.
        Notifies the parent page to update the view accordingly.
        """
        self.parent().is_editable = not self.parent().is_editable
        self.parent().sync()


class ViewOnlyHeader(QtWidgets.QWidget):
    """
    A read-only header widget that displays impact category information.
    """

    def __init__(self, parent: ImpactCategoryHeader):
        """
        Initializes the view-only header.

        Args:
            parent (ImpactCategoryHeader): The parent header widget.
        """
        super().__init__(parent)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setContentsMargins(0, 5, 0, 5)
        self.grid.setSpacing(10)
        self.grid.setColumnStretch(0, 0)  # Column 0 doesn't stretch
        self.grid.setColumnStretch(1, 1)  # Column 1 takes remaining space
        self.grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.grid)
        
        # Create widgets
        self.name_label = QtWidgets.QLabel(self)
        self.unit_label = QtWidgets.QLabel(self)
        self.edit_button = QtWidgets.QPushButton("Edit Impact Category", self)
        self.edit_button.clicked.connect(parent.on_editable_changed)
        
        # Layout widgets
        self.grid.addWidget(widgets.ABLabel.demiBold("Name:", self), 0, 0)
        self.grid.addWidget(self.name_label, 0, 1)
        self.grid.addWidget(self.edit_button, 0, 1, QtCore.Qt.AlignmentFlag.AlignRight)
        self.grid.addWidget(widgets.ABLabel.demiBold("Unit:", self), 1, 0)
        self.grid.addWidget(self.unit_label, 1, 1)

    def sync(self):
        """
        Updates the displayed information from the current impact category.
        """
        impact_category = self.parent().impact_category
        self.name_label.setText(" | ".join(impact_category.name))
        self.unit_label.setText(impact_category.metadata.get("unit", "Undefined"))


class EditableHeader(QtWidgets.QWidget):
    """
    An editable header widget that allows modifying impact category information.
    """

    def __init__(self, parent: ImpactCategoryHeader):
        """
        Initializes the editable header.

        Args:
            parent (ImpactCategoryHeader): The parent header widget.
        """
        super().__init__(parent)
        self.grid = QtWidgets.QGridLayout()
        self.grid.setContentsMargins(0, 5, 0, 5)
        self.grid.setSpacing(10)
        self.grid.setColumnStretch(0, 0)  # Column 0 doesn't stretch
        self.grid.setColumnStretch(1, 1)  # Column 1 takes remaining space
        self.grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.grid)
        
        # Create widgets
        self.name_label = QtWidgets.QLabel(self)
        self.name_label.linkActivated.connect(self._rename_method)
        self.unit_edit = ImpactCategoryUnit(self)
        self.done_button = QtWidgets.QPushButton("Done editing", self)
        self.done_button.clicked.connect(parent.on_editable_changed)
        
        # Layout widgets
        self.grid.addWidget(widgets.ABLabel.demiBold("Name:", self), 0, 0)
        self.grid.addWidget(self.name_label, 0, 1)
        self.grid.addWidget(self.done_button, 0, 1, QtCore.Qt.AlignmentFlag.AlignRight)
        self.grid.addWidget(widgets.ABLabel.demiBold("Unit:", self), 1, 0)
        self.grid.addWidget(self.unit_edit, 1, 1)

    def sync(self):
        """
        Updates the displayed information from the current impact category.
        """
        impact_category = self.parent().impact_category
        self.name_label.setText(f"<a href='/'>{' | '.join(impact_category.name)}</a>")
        self.unit_edit.setText(impact_category.metadata.get("unit", "Undefined"))

    def _rename_method(self):
        """
        Triggers the method rename action.
        """
        actions.MethodRename.run(self.parent().impact_category.name)


class ImpactCategoryUnit(QtWidgets.QLineEdit):
    """
    A line edit widget for editing the impact category unit.
    """

    def __init__(self, parent: EditableHeader):
        """
        Initializes the unit edit widget.

        Args:
            parent (EditableHeader): The parent editable header widget.
        """
        super().__init__(parent)
        self.editingFinished.connect(self.change_unit)

    def change_unit(self):
        """
        Updates the impact category unit when editing is finished.
        """
        impact_category = self.parent().parent().impact_category
        current_unit = impact_category.metadata.get("unit", "Undefined")
        
        if self.text() == current_unit:
            return
        
        actions.MethodMetaModify.run(impact_category.name, "unit", self.text())
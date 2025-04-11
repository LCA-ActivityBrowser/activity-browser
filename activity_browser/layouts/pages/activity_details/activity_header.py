from qtpy import QtWidgets, QtCore, QtGui

import bw_functional as bf

from activity_browser import actions, bwutils
from activity_browser.ui import widgets


class ActivityHeader(QtWidgets.QWidget):
    """
    A widget that displays the header information of a specific activity.

    Attributes:
        DATABASE_DEFINED_ALLOCATION (str): Constant for database default allocation.
        CUSTOM_ALLOCATION (str): Constant for custom allocation.
        activity (bd.Node): The activity to display the header for.
    """
    DATABASE_DEFINED_ALLOCATION = "(database default)"
    CUSTOM_ALLOCATION = "Custom..."

    def __init__(self, parent: QtWidgets.QWidget):
        """
        Initializes the ActivityHeader widget.

        Args:
            parent (QtWidgets.QWidget): The parent widget.
        """
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.activity = parent.activity

        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(0, 5, 0, 5)
        grid.setSpacing(10)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(grid)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = bwutils.refresh_node(self.activity)

        for child in self.children():
            if isinstance(child, QtWidgets.QWidget) and child is not self.layout():
                self.layout().removeWidget(child)
                child.deleteLater()

        setup = {
            "Name:": ActivityName(self),
            "Location:": ActivityLocation(self),
            "Properties:": ActivityProperties(self),
        }

        # Add allocation strategy selector if the activity is multifunctional
        if self.activity.get("type") == "multifunctional":
            setup["Allocation:"] = ActivityAllocation(self)

        # Arrange widgets for display as a grid
        for i, (title, widget) in enumerate(setup.items()):
            self.layout().addWidget(widgets.ABLabel.demiBold(title, self), i, 1)
            self.layout().addWidget(widget, i, 2, 1, 4)


class ActivityName(QtWidgets.QLineEdit):
    """
    A widget that displays and edits the name of the activity.
    """

    def __init__(self, parent: ActivityHeader):
        """
        Initializes the ActivityName widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(parent.activity["name"], parent)
        self.editingFinished.connect(self.change_name)

    def change_name(self):
        """
        Changes the name of the activity if it has been modified.
        """
        if self.text() == self.parent().activity["name"]:
            return
        actions.ActivityModify.run(self.parent().activity, "name", self.text())


class ActivityLocation(QtWidgets.QLineEdit):
    """
    A widget that displays and edits the location of the activity.
    """

    def __init__(self, parent: ActivityHeader):
        """
        Initializes the ActivityLocation widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(parent.activity.get("location"), parent)
        self.editingFinished.connect(self.change_location)

        locations = set(bwutils.AB_metadata.dataframe.get("location", ["GLO"]))
        completer = QtWidgets.QCompleter(locations, self)
        self.setCompleter(completer)

    def change_location(self):
        """
        Changes the location of the activity if it has been modified.
        """
        if self.text() == self.parent().activity.get("location"):
            return
        actions.ActivityModify.run(self.parent().activity, "location", self.text())


class ActivityProperties(QtWidgets.QWidget):
    """
    A widget that displays and edits the properties of the activity.
    """

    def __init__(self, parent: ActivityHeader):
        """
        Initializes the ActivityProperties widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        for property_name in parent.activity.get("default_properties", {}):
            layout.addWidget(ActivityProperty(parent.activity, property_name))

        add_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Add property</a>")
        add_label.mouseReleaseEvent = lambda x: actions.ProcessDefaultPropertyModify.run(parent.activity)

        layout.addWidget(add_label)

        layout.addStretch(1)


class ActivityProperty(QtWidgets.QPushButton):
    """
    A widget that represents a single property of the activity.
    """

    def __init__(self, activity, property_name):
        """
        Initializes the ActivityProperty widget.

        Args:
            activity (bd.Node): The activity to which the property belongs.
            property_name (str): The name of the property.
        """
        super().__init__(property_name, None)

        self.modify_action = actions.ProcessDefaultPropertyModify.get_QAction(activity, property_name)
        self.remove_action = actions.ProcessDefaultPropertyRemove.get_QAction(activity, property_name)

        self.menu = QtWidgets.QMenu(self)
        self.menu.addAction(self.modify_action)
        self.menu.addAction(self.remove_action)

        self.setStyleSheet("""
        QPushButton {
            border: 1px solid #8f8f91;
            border-radius: 0px;
            padding: 1px 10px 1px 10px;
            min-width: 0px;
        }
        """)

    def mouseReleaseEvent(self, e):
        """
        Handles the mouse release event to show the context menu.

        Args:
            e: The mouse release event.
        """
        pos = self.geometry().bottomLeft()
        pos = self.parent().mapToGlobal(pos)
        self.menu.exec_(pos)
        e.accept()


class ActivityAllocation(QtWidgets.QComboBox):
    """
    A widget that displays and edits the allocation strategy of the activity.
    """

    def __init__(self, parent: ActivityHeader):
        """
        Initializes the ActivityAllocation widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(parent)
        self.addItems(sorted(bf.allocation_strategies))
        if props := parent.activity.get("default_properties", {}):
            self.insertSeparator(1000)  # Large number to make sure it's appended at the end
            self.addItems(sorted(props))

        i = self.findText(parent.activity.get("allocation"))
        self.setCurrentIndex(i)

        self.currentTextChanged.connect(self.change_allocation)

    def change_allocation(self, allocation: str):
        """
        Changes the allocation strategy of the activity if it has been modified.

        Args:
            allocation (str): The new allocation strategy.
        """
        act = self.parent().activity
        if act.get("allocation") == allocation:
            return
        actions.ActivityModify.run(act, "allocation", allocation)

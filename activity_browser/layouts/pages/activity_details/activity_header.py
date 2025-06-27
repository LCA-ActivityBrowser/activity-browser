from qtpy import QtWidgets, QtCore, QtGui

import bw2data as bd
import bw_functional as bf

from activity_browser import actions, bwutils, application
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
        self.activity = parent.activity

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = bwutils.refresh_node(self.activity)

        self.clear_layout()

        if bwutils.database_is_locked(self.activity["database"]):
            self.layout().addWidget(LockedWarningBar(self))

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
            ("Name:", ActivityName(self),),
            ("Location:", ActivityLocation(self),),
            ("Properties:", ActivityProperties(self),),
        ]

        # Add allocation strategy selector if the activity is multifunctional
        if self.activity.get("type") == "multifunctional":
            setup.append(("Allocation:", ActivityAllocation(self),))

        # Arrange widgets for display as a grid
        for i, (title, widget) in enumerate(setup):
            grid.addWidget(widgets.ABLabel.demiBold(title, self), i, 1)
            grid.addWidget(widget, i, 2, 1, 4)
            widget.setDisabled(bwutils.database_is_locked(self.activity["database"]))

        return grid




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

        if not isinstance(parent.activity, bf.Process):
            return

        for property_name in parent.activity.available_properties():
            layout.addWidget(ActivityProperty(parent.activity, property_name))

        add_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Add property</a>")
        add_label.mouseReleaseEvent = lambda x: actions.ProcessPropertyModify.run(parent.activity)

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

        self.modify_action = actions.ProcessPropertyModify.get_QAction(activity, property_name)
        self.remove_action = actions.ProcessPropertyRemove.get_QAction(activity, property_name)

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
        if not isinstance(parent.activity, bf.Process):
            raise TypeError("ActivityAllocation can only be used with bf.Process instances.")

        super().__init__(parent)

        self.addItems(sorted(bf.allocation_strategies))
        if props := parent.activity.available_properties():
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


class LockedWarningBar(QtWidgets.QToolBar):
    def __init__(self, parent: ActivityHeader):
        super().__init__(parent)
        self.setMovable(False)
        self.setContentsMargins(0, 0, 0, 0)

        warning_label = QtWidgets.QLabel("The database of this activity is currently locked.")
        height = warning_label.minimumSizeHint().height()

        warning_icon = QtWidgets.QLabel(self)
        qicon = application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning)
        pixmap = qicon.pixmap(height, height)
        warning_icon.setPixmap(pixmap)

        migrate_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Unlock database</a>")
        migrate_label.mouseReleaseEvent = lambda x: actions.DatabaseSetReadonly.run(parent.activity["database"], False)

        self.addWidget(warning_icon)
        self.addWidget(warning_label)
        self.addWidget(migrate_label)

    def contextMenuEvent(self, event):
        return None


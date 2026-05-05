from qtpy import QtWidgets, QtCore, QtGui
from loguru import logger

import bw2data as bd
import bw_functional as bf

from activity_browser import app
from activity_browser.bwutils.commontasks import refresh_node, database_is_locked
from activity_browser.ui import widgets, icons


def _apply_compact_single_line_edit_metrics(edit: QtWidgets.QLineEdit) -> None:
    """Shorter line edits so header rows match label height and vertical gaps read evenly."""
    fm = QtGui.QFontMetrics(edit.font())
    edit.setFixedHeight(fm.height() + 6)
    edit.setStyleSheet("QLineEdit { padding: 1px 4px; }")


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
        self._database_backend = "sqlite"

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        logger.log("SYNC", f"{self.__class__.__name__}: {id(self)}")

        self.activity = refresh_node(self.activity)
        self._database_backend = bd.databases[self.activity["database"]].get("backend", "sqlite")

        self.clear_layout()

        if database_is_locked(self.activity["database"]):
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
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        db_locked = database_is_locked(self.activity["database"])

        process_widget = (ActivityNameReadOnly(self) if db_locked else ActivityName(self))
        location_widget = (
            QtWidgets.QLabel(self.activity.get("location") or "unspecified", self)
            if db_locked else ActivityLocation(self)
        )
        database_widget = QtWidgets.QLabel(self.activity.get("database", "unspecified"), self)

        # Tooltip texts
        tooltip_process = "ProcessWithReferenceProduct (sqlite backend)" if self._database_backend == "sqlite" else "Process (functional_sqlite backend)"
        tooltip_location = "Location"
        tooltip_database = "Database"
        tooltip_properties = "Properties"

        process_icon = "processproduct" if self._database_backend == "sqlite" else "process"

        rows = [
            (self._icon_label(process_icon, tooltip_process), process_widget),
            (self._icon_label("location", tooltip_location), location_widget),
            (self._icon_label("database", tooltip_database), database_widget),
        ]

        if isinstance(self.activity, bf.Process):
            rows.append((self._icon_label("properties", tooltip_properties), ActivityProperties(self, disabled=db_locked)))

        if self.activity.get("type") == "multifunctional":
            allocation_widget = (
                QtWidgets.QLabel(self.activity.get("allocation", "unspecified"), self)
                if db_locked else ActivityAllocation(self)
            )
            rows.append((widgets.ABLabel.demiBold("Alloc:", self), allocation_widget))

        for row, (left, right) in enumerate(rows):
            grid.addWidget(left, row, 0, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
            grid.addWidget(right, row, 1)

        grid.setColumnStretch(1, 1)
        return grid

    def _icon_label(self, icon_name, tool_tip_text) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(self)
        pixmap = getattr(icons.qicons, icon_name).pixmap(18, 18)
        label.setPixmap(pixmap)
        label.setFixedWidth(20)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignHCenter)
        label.setToolTip(tool_tip_text)
        return label

    def activity_name(self) -> str:
        return self.activity.get("name", "unspecified")



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
        super().__init__(parent.activity_name())
        font = self.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        self.setFont(font)
        self.setFrame(False)
        self.setStyleSheet("QLineEdit { padding: 0px; }")
        fm = QtGui.QFontMetrics(self.font())
        self.setFixedHeight(fm.height() + 4)
        # else:
        #     _apply_compact_single_line_edit_metrics(self)
        self.editingFinished.connect(self.change_name)

    def change_name(self):
        """
        Changes the name of the activity if it has been modified.
        """
        if self.text() == self.parent().activity["name"]:
            return
        app.actions.ActivityModify.run(self.parent().activity, "name", self.text())


class ActivityNameReadOnly(QtWidgets.QLabel):
    def __init__(self, parent: ActivityHeader):
        super().__init__(parent.activity_name(), parent)
        font = self.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        self.setFont(font)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)


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
        _apply_compact_single_line_edit_metrics(self)
        self.editingFinished.connect(self.change_location)

        locations = set(app.metadata.dataframe.get("location", ["GLO"]))
        completer = QtWidgets.QCompleter(locations, self)
        self.setCompleter(completer)

    def change_location(self):
        """
        Changes the location of the activity if it has been modified.
        """
        if self.text() == self.parent().activity.get("location"):
            return
        app.actions.ActivityModify.run(self.parent().activity, "location", self.text())


class ActivityProperties(QtWidgets.QWidget):
    """
    A widget that displays and edits the properties of the activity.
    """

    def __init__(self, parent: ActivityHeader, disabled: bool = False):
        """
        Initializes the ActivityProperties widget.

        Args:
            parent (ActivityHeader): The parent widget.
        """
        super().__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if not isinstance(parent.activity, bf.Process):
            return

        for property_name in parent.activity.available_properties():
            if disabled:
                prop = QtWidgets.QLabel(property_name, self)
                prop.setStyleSheet("QLabel { border: 1px solid #8f8f91; padding: 1px 6px; }")
                layout.addWidget(prop)
            else:
                layout.addWidget(ActivityProperty(parent.activity, property_name))

        add_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Add property</a>")
        if disabled:
            add_label.setText("Add property")
        else:
            add_label.mouseReleaseEvent = lambda x: app.actions.ProcessPropertyModify.run(parent.activity)
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

        self.modify_action = app.actions.ProcessPropertyModify.get_QAction(activity, property_name)
        self.remove_action = app.actions.ProcessPropertyRemove.get_QAction(activity, property_name)

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
        app.actions.ActivityModify.run(act, "allocation", allocation)


class LockedWarningBar(QtWidgets.QToolBar):
    def __init__(self, parent: ActivityHeader):
        super().__init__(parent)
        self.setMovable(False)
        self.setContentsMargins(0, 0, 0, 0)

        warning_label = QtWidgets.QLabel("The database of this activity is currently locked.")
        height = warning_label.minimumSizeHint().height()

        warning_icon = QtWidgets.QLabel(self)
        qicon = app.application.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning)
        pixmap = qicon.pixmap(height, height)
        warning_icon.setPixmap(pixmap)

        migrate_label = QtWidgets.QLabel("<a style='text-decoration:underline;'>Unlock database</a>")
        migrate_label.mouseReleaseEvent = lambda x: app.actions.DatabaseSetReadonly.run(parent.activity["database"], False)

        self.addWidget(warning_icon)
        self.addWidget(warning_label)
        self.addWidget(migrate_label)

    def contextMenuEvent(self, event):
        return None


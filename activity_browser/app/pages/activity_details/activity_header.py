from qtpy import QtWidgets, QtCore, QtGui
from loguru import logger

import bw2data as bd
import bw_functional as bf

from activity_browser import app
from activity_browser.bwutils.commontasks import refresh_node, database_is_locked
from activity_browser.ui import icons


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

        process_widget = LockedProcessTitleRow(self) if db_locked else UnlockedProcessTitleRow(self)
        # Tooltip texts
        tooltip_process = "ProcessWithReferenceProduct (sqlite backend)" if self._database_backend == "sqlite" else "Process (functional_sqlite backend)"

        process_icon = "processproduct" if self._database_backend == "sqlite" else "process"

        rows = [
            (self._icon_label(process_icon, tooltip_process), process_widget),
            (self._icon_label("location", "Location"), LocationDatabaseRowWidget(self, disabled=db_locked)),
        ]

        is_multifunctional = self.activity.get("type") == "multifunctional"
        has_props = isinstance(self.activity, bf.Process)

        if is_multifunctional:
            rows.append(
                (
                    self._icon_label("allocation", "Allocation"),
                    AllocationAndPropertiesRow(self, disabled=db_locked),
                )
            )
        elif has_props:
            rows.append(
                (self._icon_label("properties", "Properties"), ActivityProperties(self, disabled=db_locked))
            )

        for row, (left, right) in enumerate(rows):
            # Row 0: keep process icon, title, and lock icon vertically centered together.
            row_align = (
                QtCore.Qt.AlignmentFlag.AlignVCenter
                if row == 0
                else QtCore.Qt.AlignmentFlag.AlignTop
            )
            grid.addWidget(left, row, 0, alignment=row_align)
            grid.addWidget(right, row, 1, alignment=row_align)

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

    _WIDTH_PAD_PX = 14
    _MIN_WIDTH_PX = 40

    def __init__(self, header: ActivityHeader):
        """
        Initializes the ActivityName widget.

        Args:
            header (ActivityHeader): Header owning the activity (Qt parent may be a row widget).
        """
        self._header = header
        super().__init__(header.activity_name(), header)
        font = self.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        self.setFont(font)
        self.setFrame(False)
        self.setStyleSheet("QLineEdit { padding: 0px; }")
        fm = QtGui.QFontMetrics(self.font())
        self.setFixedHeight(fm.height() + 4)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.textChanged.connect(self._adjust_width_to_text)
        self._adjust_width_to_text()
        self.editingFinished.connect(self.change_name)

    def _adjust_width_to_text(self) -> None:
        fm = QtGui.QFontMetrics(self.font())
        t = self.text()
        text_w = fm.horizontalAdvance(t) if t else fm.horizontalAdvance(" ")
        self.setFixedWidth(max(text_w + self._WIDTH_PAD_PX, self._MIN_WIDTH_PX))

    def change_name(self):
        """
        Changes the name of the activity if it has been modified.
        """
        if self.text() == self._header.activity["name"]:
            return
        app.actions.ActivityModify.run(self._header.activity, "name", self.text())


class ActivityNameReadOnly(QtWidgets.QLabel):
    def __init__(self, header: ActivityHeader):
        super().__init__(header.activity_name(), header)
        font = self.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 3)
        self.setFont(font)
        self.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Fixed)
        fm = QtGui.QFontMetrics(self.font())
        self.setFixedHeight(fm.height() + 4)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft)


class DatabaseLockIconLabel(QtWidgets.QLabel):
    """Lock pixmap that unlocks the activity's database on double-click."""

    _TOOLTIP = (
        "The database of this activity is currently locked.\n\n"
        "Double-click this icon to unlock the database."
    )

    def __init__(self, header: ActivityHeader, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._header = header
        self.setPixmap(icons.qicons.locked.pixmap(18, 18))
        self.setFixedSize(20, 18)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setToolTip(self._TOOLTIP)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        app.actions.DatabaseSetReadonly.run(self._header.activity["database"], False)
        event.accept()


class UnlockedProcessTitleRow(QtWidgets.QWidget):
    """Editable process title row (width follows text); vertically aligns with the process icon."""

    def __init__(self, header: ActivityHeader):
        super().__init__(header)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(ActivityName(header), 0)
        layout.addStretch(1)


class LockedProcessTitleRow(QtWidgets.QWidget):
    """Read-only process title with lock affordance when the database is read-only."""

    def __init__(self, header: ActivityHeader):
        super().__init__(header)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        name = ActivityNameReadOnly(header)
        fm = QtGui.QFontMetrics(name.font())
        text_w = fm.horizontalAdvance(name.text()) if name.text() else fm.horizontalAdvance(" ")
        name.setFixedWidth(max(text_w + 8, 32))

        layout.addWidget(name, 0)
        layout.addWidget(DatabaseLockIconLabel(header, self), 0)
        layout.addStretch(1)


class ActivityLocation(QtWidgets.QLineEdit):
    """
    A widget that displays and edits the location of the activity.
    """

    _WIDTH_PAD_PX = 14
    _MIN_WIDTH_PX = 32

    def __init__(self, header: ActivityHeader):
        """
        Initializes the ActivityLocation widget.

        Args:
            header (ActivityHeader): Header owning the activity (Qt parent may be a row widget).
        """
        self._header = header
        super().__init__(header.activity.get("location"), header)
        font = self.font()
        font.setBold(False)
        self.setFont(font)
        self.setFrame(False)
        self.setStyleSheet("QLineEdit { padding: 0px; }")
        fm = QtGui.QFontMetrics(self.font())
        self.setFixedHeight(fm.height() + 4)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        self.textChanged.connect(self._adjust_width_to_text)
        self._adjust_width_to_text()
        self.editingFinished.connect(self.change_location)

        locations = set(app.metadata.dataframe.get("location", ["GLO"]))
        completer = QtWidgets.QCompleter(locations, self)
        self.setCompleter(completer)

    def _adjust_width_to_text(self) -> None:
        fm = QtGui.QFontMetrics(self.font())
        t = self.text()
        text_w = fm.horizontalAdvance(t) if t else fm.horizontalAdvance(" ")
        self.setFixedWidth(max(text_w + self._WIDTH_PAD_PX, self._MIN_WIDTH_PX))

    def change_location(self):
        """
        Changes the location of the activity if it has been modified.
        """
        if self.text() == self._header.activity.get("location"):
            return
        app.actions.ActivityModify.run(self._header.activity, "location", self.text())


class LocationDatabaseRowWidget(QtWidgets.QWidget):
    """
    A widget that puts location and database widgets into one row
    """
    def __init__(self, parent: ActivityHeader, disabled: bool = False):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        location_widget = (
            QtWidgets.QLabel(parent.activity.get("location") or "unspecified", self)
            if disabled else ActivityLocation(parent)
        )
        if isinstance(location_widget, QtWidgets.QLabel):
            location_widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Maximum,
                QtWidgets.QSizePolicy.Policy.Preferred,
            )
        database_widget = QtWidgets.QLabel(parent.activity.get("database", "unspecified"), self)
        database_widget.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(location_widget, 0)
        layout.addWidget(parent._icon_label("database", "Database"))
        layout.addWidget(database_widget, 1)


class AllocationAndPropertiesRow(QtWidgets.QWidget):
    """
    A widget that puts Allocation and Properties widgets into one row.
    Used only for multifunctional processes.
    The allocation icon is the grid's leading cell — not repeated here.
    """

    def __init__(self, parent: ActivityHeader, disabled: bool = False):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        allocation_widget = (
            QtWidgets.QLabel(parent.activity.get("allocation", "unspecified"), self)
            if disabled
            else ActivityAllocation(parent)
        )
        layout.addWidget(allocation_widget, 0)

        if isinstance(parent.activity, bf.Process):
            layout.addWidget(parent._icon_label("properties", "Properties"))
            layout.addWidget(ActivityProperties(parent, disabled=disabled), 1)


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

    def __init__(self, header: ActivityHeader):
        """
        Initializes the ActivityAllocation widget.

        Args:
            header (ActivityHeader): Header owning the activity (Qt parent may be a row widget).
        """
        if not isinstance(header.activity, bf.Process):
            raise TypeError("ActivityAllocation can only be used with bf.Process instances.")

        self._header = header
        super().__init__(header)

        self.addItems(sorted(bf.allocation_strategies))
        if props := header.activity.available_properties():
            self.insertSeparator(1000)  # Large number to make sure it's appended at the end
            self.addItems(sorted(props))

        i = self.findText(header.activity.get("allocation"))
        self.setCurrentIndex(i)

        self.currentTextChanged.connect(self.change_allocation)

    def change_allocation(self, allocation: str):
        """
        Changes the allocation strategy of the activity if it has been modified.

        Args:
            allocation (str): The new allocation strategy.
        """
        act = self._header.activity
        if act.get("allocation") == allocation:
            return
        app.actions.ActivityModify.run(act, "allocation", allocation)


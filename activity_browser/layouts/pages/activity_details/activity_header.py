from qtpy import QtWidgets, QtCore

import bw_functional as bf

from activity_browser import actions, bwutils


class ActivityHeader(QtWidgets.QWidget):
    DATABASE_DEFINED_ALLOCATION = "(database default)"
    CUSTOM_ALLOCATION = "Custom..."

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.activity = parent.activity

        grid = QtWidgets.QGridLayout(self)
        grid.setContentsMargins(0, 5, 0, 5)
        grid.setSpacing(10)
        grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.setLayout(grid)

    def sync(self):
        self.activity = bwutils.refresh_node(self.activity)

        for child in self.children():
            if child is not self.layout():
                self.layout().removeWidget(child)
                child.deleteLater()

        setup = {
            "Name:": ActivityName(self),
            "Location:": ActivityLocation(self),
            "Properties:": ActivityProperties(self),
            "Allocation:": ActivityAllocation(self),
        }

        # arrange widgets for display as a grid
        for i, (label, widget) in enumerate(setup.items()):
            self.layout().addWidget(QtWidgets.QLabel(f"<b>{label}</b>"), i, 1)
            self.layout().addWidget(widget, i, 2, 1, 4)



class ActivityName(QtWidgets.QLineEdit):

    def __init__(self, parent: ActivityHeader):
        super().__init__(parent.activity["name"], parent)
        self.editingFinished.connect(self.change_name)

    def change_name(self):
        if self.text() == self.parent().activity["name"]:
            return
        actions.ActivityModify.run(self.parent().activity, "name", self.text())


class ActivityLocation(QtWidgets.QLineEdit):
    def __init__(self, parent: ActivityHeader):
        super().__init__(parent.activity.get("location"), parent)
        self.editingFinished.connect(self.change_location)

        locations = set(bwutils.AB_metadata.dataframe.get("location", ["GLO"]))
        completer = QtWidgets.QCompleter(locations, self)
        self.setCompleter(completer)

    def change_location(self):
        if self.text() == self.parent().activity.get("location"):
            return
        actions.ActivityModify.run(self.parent().activity, "location", self.text())


class ActivityProperties(QtWidgets.QWidget):
    def __init__(self, parent: ActivityHeader):
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
    def __init__(self, activity, property_name):
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
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #f6f7fa, stop: 1 #dadbde);
            min-width: 0px;
        }
        
        QPushButton:pressed {
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                              stop: 0 #dadbde, stop: 1 #f6f7fa);
        }
        """)

    def mouseReleaseEvent(self, e):
        pos = self.geometry().bottomLeft()
        pos = self.parent().mapToGlobal(pos)
        self.menu.exec_(pos)
        e.accept()


class ActivityAllocation(QtWidgets.QComboBox):
    def __init__(self, parent: ActivityHeader):
        super().__init__(parent)
        self.addItems(sorted(bf.allocation_strategies))
        if props := parent.activity.get("default_properties", {}):
            self.insertSeparator(1000)  # large number to make sure it's appended at the end
            self.addItems(sorted(props))

        i = self.findText(parent.activity.get("allocation"))
        self.setCurrentIndex(i)

        self.currentTextChanged.connect(self.change_allocation)

    def change_allocation(self, allocation: str):
        act = self.parent().activity
        if act.get("allocation") == allocation:
            return
        actions.ActivityModify.run(act, "allocation", allocation)

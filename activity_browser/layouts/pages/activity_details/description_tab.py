from qtpy import QtWidgets, QtGui

import bw2data as bd

from activity_browser import bwutils, actions


class DescriptionTab(QtWidgets.QTextEdit):
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        self.activity = bwutils.refresh_node(activity)
        super().__init__(parent, self.activity.get("comment", ""))

    def sync(self):
        self.activity = bwutils.refresh_node(self.activity)
        self.setText(self.activity.get("comment", ""))
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    def focusOutEvent(self, e):
        if self.toPlainText() == self.activity.get("comment", ""):
            return
        actions.ActivityModify.run(self.activity, "comment", self.toPlainText())

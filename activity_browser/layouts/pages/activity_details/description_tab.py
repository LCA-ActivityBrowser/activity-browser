from qtpy import QtWidgets, QtGui

import bw2data as bd

from activity_browser import bwutils, actions


class DescriptionTab(QtWidgets.QTextEdit):
    """
    A widget that displays and edits the description (comment) of a specific activity.

    Attributes:
        activity (tuple | int | bd.Node): The activity to display and edit the description for.
    """
    def __init__(self, activity: tuple | int | bd.Node, parent=None):
        """
        Initializes the DescriptionTab widget.

        Args:
            activity (tuple | int | bd.Node): The activity to display and edit the description for.
            parent (QtWidgets.QWidget, optional): The parent widget. Defaults to None.
        """
        self.activity = bwutils.refresh_node(activity)
        super().__init__(parent, self.activity.get("comment", ""))
        self.setPlaceholderText("Click here to edit the description of this activity...")

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        self.activity = bwutils.refresh_node(self.activity)
        self.setText(self.activity.get("comment", ""))
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        # Set the read-only state based on the activity's database
        self.setDisabled(bwutils.database_is_locked(self.activity["database"]))

    def focusOutEvent(self, e):
        """
        Handles the focus out event to save the comment if it has changed.

        Args:
            e: The focus out event.
        """
        if self.toPlainText() == self.activity.get("comment", ""):
            return
        actions.ActivityModify.run(self.activity, "comment", self.toPlainText())

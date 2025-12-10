from qtpy import QtWidgets, QtGui
from loguru import logger

import bw2data as bd

from activity_browser import app
from activity_browser.bwutils.commontasks import refresh_node, database_is_locked


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
        self.activity = refresh_node(activity)
        super().__init__(parent, self.activity.get("comment", ""))
        self.setPlaceholderText("Click here to edit the description of this activity...")

    def sync(self):
        """
        Synchronizes the widget with the current state of the activity.
        """
        logger.debug(f"Syncing {self.__class__.__name__}: {id(self)}")

        self.activity = refresh_node(self.activity)
        self.setText(self.activity.get("comment", ""))
        self.moveCursor(QtGui.QTextCursor.MoveOperation.End)

        # Set the read-only state based on the activity's database
        self.setReadOnly(database_is_locked(self.activity["database"]))

    def focusOutEvent(self, e):
        """
        Handles the focus out event to save the comment if it has changed.

        Args:
            e: The focus out event.
        """
        if self.toPlainText() == self.activity.get("comment", ""):
            return
        app.actions.ActivityModify.run(self.activity, "comment", self.toPlainText())

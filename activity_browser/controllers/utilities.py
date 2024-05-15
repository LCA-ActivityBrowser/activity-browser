# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Slot

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata
from activity_browser.brightway import bd


class UtilitiesController(QObject):
    """The controller that handles all of the AB features that are not directly
    pulled from brightway.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.edit_activity.connect(self.print_convenience_information)

    @staticmethod
    @Slot(str, name="printDatabaseInformation")
    def print_convenience_information(db_name: str) -> None:
        AB_metadata.print_convenience_information(db_name)


utilities_controller = UtilitiesController(application)

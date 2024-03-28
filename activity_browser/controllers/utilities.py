# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Slot

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata


class UtilitiesController(QObject):
    """The controller that handles all of the AB features that are not directly
    pulled from brightway.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.project_selected.connect(self.reset_metadata)
        signals.edit_activity.connect(self.print_convenience_information)

    @staticmethod
    @Slot(name="triggerMetadataReset")
    def reset_metadata() -> None:
        AB_metadata.reset_metadata()

    @staticmethod
    @Slot(str, name="printDatabaseInformation")
    def print_convenience_information(db_name: str) -> None:
        AB_metadata.print_convenience_information(db_name)


utilities_controller = UtilitiesController(application)

# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Slot

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata
from ..ui.wizards.settings_wizard import SettingsWizard


class UtilitiesController(QObject):
    """The controller that handles all of the AB features that are not directly
    pulled from brightway.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.project_selected.connect(self.reset_metadata)
        signals.edit_activity.connect(self.print_convenience_information)
        signals.edit_settings.connect(self.open_settings_wizard)

    @staticmethod
    @Slot(name="triggerMetadataReset")
    def reset_metadata() -> None:
        AB_metadata.reset_metadata()

    @staticmethod
    @Slot(str, name="printDatabaseInformation")
    def print_convenience_information(db_name: str) -> None:
        AB_metadata.print_convenience_information(db_name)

    @Slot(name="settingsWizard")
    def open_settings_wizard(self) -> None:
        wizard = SettingsWizard(application.main_window)
        wizard.show()

utilities_controller = UtilitiesController(application)
# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Slot

from activity_browser.bwutils import AB_metadata, presamples as pc
from activity_browser.signals import signals


class UtilitiesController(QObject):
    """The controller that handles all of the AB features that are not directly
    pulled from brightway.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        signals.project_selected.connect(self.reset_metadata)
        signals.edit_activity.connect(self.print_convenience_information)
        signals.presample_package_delete.connect(self.remove_presamples_package)

    @staticmethod
    @Slot(name="triggerMetadataReset")
    def reset_metadata() -> None:
        AB_metadata.reset_metadata()

    @staticmethod
    @Slot(str, name="printDatabaseInformation")
    def print_convenience_information(db_name: str) -> None:
        AB_metadata.print_convenience_information(db_name)

    @staticmethod
    @Slot(str, name="removePresamplesPackage")
    def remove_presamples_package(name_id: str) -> None:
        path = pc.get_package_path(name_id)
        resource = pc.clear_resource_by_name(name_id)
        if path is None and not resource:
            raise ValueError(
                "Given presample package '{}' could not be found.".format(name_id)
            )
        print("Removed PresampleResource object?", resource)
        files = pc.remove_package(path)
        print("Removed Presample files?", files)
        signals.presample_package_removed.emit()

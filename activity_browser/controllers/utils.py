# -*- coding: utf-8 -*-

import brightway2 as bw
from PySide2.QtCore import QObject, Slot

from ..bwutils import AB_metadata, commontasks as bc, presamples as pc
from ..settings import ab_settings
from ..signals import signals
from .project import ProjectController


class DataController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.project_selected.emit()
        self.load_settings()
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)
        signals.project_selected.connect(self.reset_metadata)
        signals.metadata_changed.connect(self.update_metadata)
        signals.edit_activity.connect(self.print_convenience_information)
        signals.presample_package_delete.connect(self.remove_presamples_package)

    def switch_brightway2_dir_path(self, dirpath):
        if bc.switch_brightway2_dir(dirpath):
            ProjectController.change_project(ab_settings.startup_project, reload=True)
            signals.databases_changed.emit()

    def load_settings(self):
        if ab_settings.settings:
            print("Loading user settings:")
            self.switch_brightway2_dir_path(dirpath=ab_settings.custom_bw_dir)
            ProjectController.change_project(ab_settings.startup_project)

    @staticmethod
    @Slot(name="triggerMetadataReset")
    def reset_metadata() -> None:
        AB_metadata.reset_metadata()

    @staticmethod
    @Slot(tuple, name="updateMetadataActivity")
    def update_metadata(key: tuple) -> None:
        AB_metadata.update_metadata(key)

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

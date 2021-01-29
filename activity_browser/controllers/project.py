# -*- coding: utf-8 -*-

import brightway2 as bw
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from ..settings import ab_settings
from ..signals import signals


class ProjectController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.change_project.connect(self.change_project)
        signals.new_project.connect(self.new_project)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)

    @staticmethod
    @Slot(str, name="changeProject")
    def change_project(name: str, reload: bool = False) -> None:
        """Change the project, this clears all tabs and metadata related to
        the current project.
        """
        assert name, "No project name given."
        if name not in bw.projects:
            print("Project does not exist: {}".format(name))
            return

        if name != bw.projects.current or reload:
            bw.projects.set_current(name)
            signals.project_selected.emit()
            print("Loaded project:", name)

    @Slot(name="createProject")
    def new_project(self, name=None):
        if name is None:
            name, ok = QtWidgets.QInputDialog.getText(
                self.window,
                "Create new project",
                "Name of new project:" + " " * 25
            )
            if not ok or not name:
                return

        if name and name not in bw.projects:
            bw.projects.set_current(name)
            self.change_project(name, reload=True)
            signals.projects_changed.emit()
        elif name in bw.projects:
            QtWidgets.QMessageBox.information(
                self.window, "Not possible.",
                "A project with this name already exists."
            )

    @Slot(name="copyProject")
    def copy_project(self):
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Copy current project",
            "Copy current project ({}) to new name:".format(bw.projects.current) + " " * 10
        )
        if ok and name:
            if name not in bw.projects:
                bw.projects.copy_project(name, switch=True)
                self.change_project(name)
                signals.projects_changed.emit()
            else:
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible.",
                    "A project with this name already exists."
                )

    @Slot(name="deleteProject")
    def delete_project(self):
        if len(bw.projects) == 1:
            QtWidgets.QMessageBox.information(
                self.window, "Not possible", "Can't delete last project."
            )
            return
        reply = QtWidgets.QMessageBox.question(
            self.window,
            'Confirm project deletion',
            ("Are you sure you want to delete project '{}'? It has {} databases" +
             " and {} LCI methods").format(
                bw.projects.current,
                len(bw.databases),
                len(bw.methods)
            )
        )
        if reply == QtWidgets.QMessageBox.Yes:
            bw.projects.delete_project(bw.projects.current, delete_dir=False)
            self.change_project(ab_settings.startup_project, reload=True)
            signals.projects_changed.emit()


class CSetupController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.new_calculation_setup.connect(self.new_calculation_setup)
        signals.rename_calculation_setup.connect(self.rename_calculation_setup)
        signals.delete_calculation_setup.connect(self.delete_calculation_setup)

    @Slot(name="createCalculationSetup")
    def new_calculation_setup(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Create new calculation setup",
            "Name of new calculation setup:" + " " * 10
        )
        if ok and name:
            if name not in bw.calculation_setups.keys():
                bw.calculation_setups[name] = {'inv': [], 'ia': []}
                signals.calculation_setup_selected.emit(name)
                print("New calculation setup: {}".format(name))
            else:
                QtWidgets.QMessageBox.information(
                    self.window, "Not possible",
                    "A calculation setup with this name already exists."
                )

    @Slot(str, name="copyCalculationSetup")
    def copy_calculation_setup(self, current: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Copy '{}'".format(current),
            "Name of the copied calculation setup:" + " " * 10
        )
        if ok and new_name:
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            signals.calculation_setup_selected.emit(new_name)
            print("Copied calculation setup {} as {}".format(current, new_name))

    @Slot(str, name="deleteCalculationSetup")
    def delete_calculation_setup(self, name: str) -> None:
        del bw.calculation_setups[name]
        signals.set_default_calculation_setup.emit()
        print("Deleted calculation setup: {}".format(name))

    @Slot(str, name="renameCalculationSetup")
    def rename_calculation_setup(self, current: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Rename '{}'".format(current),
            "New name of this calculation setup:" + " " * 10
        )
        if ok and new_name:
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            # print("Current setups:", list(bw.calculation_setups.keys()))
            del bw.calculation_setups[current]
            # print("After deletion of {}:".format(current), list(bw.calculation_setups.keys()))
            signals.calculation_setup_selected.emit(new_name)
            print("Renamed calculation setup from {} to {}".format(current, new_name))

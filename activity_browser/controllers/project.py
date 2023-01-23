# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser.bwutils import commontasks as bc
from activity_browser.settings import ab_settings
from activity_browser.signals import signals
from activity_browser.ui.widgets import TupleNameDialog, ProjectDeletionDialog


class ProjectController(QObject):
    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.project_selected.emit()
        self.load_settings()

        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)
        signals.change_project.connect(self.change_project)
        signals.new_project.connect(self.new_project)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)

    @Slot(str, name="switchBwDirPath")
    def switch_brightway2_dir_path(self, dirpath: str) -> None:
        if bc.switch_brightway2_dir(dirpath):
            self.change_project(ab_settings.startup_project, reload=True)
            signals.databases_changed.emit()

    def load_settings(self) -> None:
        if ab_settings.settings:
            print("Loading user settings:")
            self.switch_brightway2_dir_path(dirpath=ab_settings.current_bw_dir)
            self.change_project(ab_settings.startup_project)
        print('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        print('Brightway2 active project: {}'.format(bw.projects.current))

    @staticmethod
    @Slot(str, name="changeProject")
    def change_project(name: str, reload: bool = False) -> None:
        """Change the project, this clears all tabs and metadata related to
        the current project.
        """
#        assert name, "No project name given."
        name = "default" if not name else name
        if name not in bw.projects:
            print("Project does not exist: {}, creating!".format(name))
            bw.projects.create_project(name)

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

        delete_dialog = ProjectDeletionDialog.construct_project_deletion_dialog(self.window, bw.projects.current)

        if delete_dialog.exec_() == ProjectDeletionDialog.Accepted:
            if delete_dialog.deletion_warning_checked():
                bw.projects.delete_project(bw.projects.current, delete_dir=True)
                self.change_project(ab_settings.startup_project, reload=True)
                signals.projects_changed.emit()
            else:
                bw.projects.delete_project(bw.projects.current, delete_dir=False)
                self.change_project(ab_settings.startup_project, reload=True)
                signals.projects_changed.emit()


class CSetupController(QObject):
    """The controller that handles brightway features related to
    calculation setups.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.new_calculation_setup.connect(self.new_calculation_setup)
        signals.copy_calculation_setup.connect(self.copy_calculation_setup)
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
            if not self._can_use_cs_name(name):
                return
            bw.calculation_setups[name] = {'inv': [], 'ia': []}
            signals.calculation_setup_selected.emit(name)
            print("New calculation setup: {}".format(name))

    @Slot(str, name="copyCalculationSetup")
    def copy_calculation_setup(self, current: str) -> None:
        new_name, ok = QtWidgets.QInputDialog.getText(
            self.window,
            "Copy '{}'".format(current),
            "Name of the copied calculation setup:" + " " * 10
        )
        if ok and new_name:
            if not self._can_use_cs_name(new_name):
                return
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
            if not self._can_use_cs_name(new_name):
                return
            bw.calculation_setups[new_name] = bw.calculation_setups[current].copy()
            # print("Current setups:", list(bw.calculation_setups.keys()))
            del bw.calculation_setups[current]
            # print("After deletion of {}:".format(current), list(bw.calculation_setups.keys()))
            signals.calculation_setup_selected.emit(new_name)
            print("Renamed calculation setup from {} to {}".format(current, new_name))

    def _can_use_cs_name(self, new_name: str) -> bool:
        if new_name in bw.calculation_setups.keys():
            QtWidgets.QMessageBox.warning(
                self.window, "Not possible",
                "A calculation setup with this name already exists."
            )
            return False
        return True


class ImpactCategoryController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        signals.copy_method.connect(self.copy_method)
        signals.edit_method_cf.connect(self.modify_method_with_cf)
        signals.remove_cf_uncertainties.connect(self.remove_uncertainty)

    @Slot(tuple, name="copyMethod")
    def copy_method(self, method: tuple) -> None:
        """Call copy on the (first) selected method and present rename dialog."""
        method = bw.Method(method)
        dialog = TupleNameDialog.get_combined_name(
            self.window, "Impact category name", "Combined name:", method.name, "Copy"
        )
        if dialog.exec_() == TupleNameDialog.Accepted:
            new_name = dialog.result_tuple
            if new_name in bw.methods:
                warn = "Impact Category with name '{}' already exists!".format(new_name)
                QtWidgets.QMessageBox.warning(self.window, "Copy failed", warn)
                return
            method.copy(new_name)
            print("Copied method {} into {}".format(str(method.name), str(new_name)))
            signals.new_method.emit(new_name)

    @Slot(list, tuple, name="removeCFUncertainty")
    def remove_uncertainty(self, removed: list, method: tuple) -> None:
        """Remove all uncertainty information from the selected CFs.

        NOTE: Does not affect any selected CF that does not have uncertainty
        information.
        """
        def unset(cf: tuple) -> tuple:
            data = [*cf]
            data[1] = data[1].get("amount")
            return tuple(data)

        method = bw.Method(method)
        modified_cfs = (
            unset(cf) for cf in removed if isinstance(cf[1], dict)
        )
        cfs = method.load()
        for cf in modified_cfs:
            idx = next(i for i, c in enumerate(cfs) if c[0] == cf[0])
            cfs[idx] = cf
        method.write(cfs)
        signals.method_modified.emit(method.name)

    @Slot(tuple, tuple, name="modifyMethodWithCf")
    def modify_method_with_cf(self, cf: tuple, method: tuple) -> None:
        """ Take the given CF tuple, add it to the method object stored in
        `self.method` and call .write() & .process() to finalize.

        NOTE: if the flow key matches one of the CFs in method, that CF
        will be edited, if not, a new CF will be added to the method.
        """
        method = bw.Method(method)
        cfs = method.load()
        idx = next((i for i, c in enumerate(cfs) if c[0] == cf[0]), None)
        if idx is None:
            cfs.append(cf)
        else:
            cfs[idx] = cf
        method.write(cfs)
        signals.method_modified.emit(method.name)

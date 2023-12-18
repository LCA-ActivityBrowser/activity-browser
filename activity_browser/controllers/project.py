# -*- coding: utf-8 -*-
import brightway2 as bw
import bw2data.utils
from bw2io import backup
from PySide2.QtCore import QObject, Slot, Qt
from PySide2 import QtWidgets

import os
import shutil

from activity_browser.bwutils import commontasks as bc
from activity_browser.settings import ab_settings
from activity_browser.signals import signals
from activity_browser.ui.widgets import TupleNameDialog, ProjectDeletionDialog

import logging
from activity_browser.logger import ABHandler

logger = logging.getLogger('ab_logs')
log = ABHandler.setup_with_logger(logger, __name__)


class ProjectController(QObject):
    """The controller that handles all of the AB features on the level of
    a brightway project.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.load_settings()

        signals.switch_bw2_dir_path.connect(self.switch_brightway2_dir_path)
        signals.change_project.connect(self.change_project)
        signals.new_project.connect(self.new_project)
        signals.import_project.connect(self.import_project)
        signals.export_project.connect(self.export_project)
        signals.copy_project.connect(self.copy_project)
        signals.delete_project.connect(self.delete_project)

    @Slot(str, name="switchBwDirPath")
    def switch_brightway2_dir_path(self, dirpath: str) -> None:
        if bc.switch_brightway2_dir(dirpath):
            self.change_project(ab_settings.startup_project, reload=True)
            signals.databases_changed.emit()

    def load_settings(self) -> None:
        if ab_settings.settings:
            log.info("Loading user settings:")
            self.switch_brightway2_dir_path(dirpath=ab_settings.current_bw_dir)
            self.change_project(ab_settings.startup_project)
        log.info('Brightway2 data directory: {}'.format(bw.projects._base_data_dir))
        log.info('Brightway2 active project: {}'.format(bw.projects.current))

    @staticmethod
    @Slot(str, name="changeProject")
    def change_project(name: str = "default", reload: bool = False) -> None:
        """Change the project, this clears all tabs and metadata related to
        the current project.
        """
        # check whether the project does exist, otherwise return
        if name not in bw.projects: 
            log.info(f"Project does not exist: {name}")
            return
        
        if name != bw.projects.current or reload:
            bw.projects.set_current(name)
        signals.project_selected.emit()
        log.info("Loaded project:", name)

    def get_project_name(self, suggestion: str = '') -> str:
        """Ask for a project name, if it exists, inform user and ask again."""
        project_name, _ = QtWidgets.QInputDialog.getText(
            self.window,
            'Choose project name',
            'Choose a name for your project',
            text=suggestion
        )
        if not project_name: return

        if project_name in bw.projects:
            # this name already exists, inform user and ask again.
            QtWidgets.QMessageBox.information(
                self.window, "Not possible.",
                "A project with this name already exists."
            )
            project_name = self.get_project_name(suggestion)
        return project_name

    @Slot(name="createProject")
    def new_project(self):
        name = self.get_project_name()
        if not name: return

        bw.projects.set_current(name)
        self.change_project(name, reload=True)
        signals.projects_changed.emit()

    @Slot(name="importProject")
    def import_project(self) -> None:
        """Import a project into AB based on file chosen by user."""

        # get the path from the user
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent=self.window,
            caption='Choose project file to import',
            filter='Tar archive (*.tar.gz);; All files (*.*)'
        )
        if not path: return

        # create a name suggestion based on the file name
        _, suggestion = os.path.split(path)
        suggestion = suggestion.split('.')[0]  # get only the file_name
        suggestion = suggestion.replace('brightway2-project-', '')

        # get a new project name from the user:
        name = self.get_project_name(suggestion=suggestion)
        if not name: return

        # start the import
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        log.debug('Starting project import:'
                  f'\nPATH: {path}'
                  f'\nNAME: {name}')

        backup.restore_project_directory(fp=path, project_name=name)

        QtWidgets.QApplication.restoreOverrideCursor()
        log.info(f'Project `{name}` imported.')

        # change to the newly imported project
        signals.change_project.emit(name)

    @Slot(name="exportProject")
    def export_project(self) -> None:
        """Export the current project to a folder chosen by the user."""

        # project name
        name = bw.projects.current

        # project target folder
        target_folder = QtWidgets.QFileDialog.getExistingDirectory(
            self.window,
            f'Select a folder to export the project `{name}` to'
        )
        if not target_folder: return

        # start actual export
        log.debug(f'Starting project export for `{name}`:'
                  f'\nPATH: {target_folder}')
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)

        # export the project
        backup.backup_project_directory(name)

        # bw2io.backup.backup_project_directory() only exports to the home folder,
        # now move to location chosen by user
        home_dir = os.path.expanduser('~')
        # get all files that fit this export name
        files = [f for f in os.listdir(home_dir) if f.startswith(f'brightway2-project-{name}') and f.endswith('tar.gz')]
        if len(files) > 1:
            # there are multiple backups of this project, take the most recent one
            times = [os.path.getctime(os.path.join(home_dir, f)) for f in files]
            file = files[times.index(max(times))]
        else:
            file = files[0]

        # move the file to the correct folder
        shutil.move(os.path.join(home_dir, file), target_folder)

        QtWidgets.QApplication.restoreOverrideCursor()
        log.info(f'Project `{name}` exported.')

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
        """
        Delete the currently active project. Reject if it's the last one.
        """
        project_to_delete: str = bw.projects.current

        # if it's the startup project: reject deletion and inform user
        if project_to_delete == ab_settings.startup_project:
            QtWidgets.QMessageBox.information(
                self.window, "Not possible", "Can't delete the startup project. Please select another startup project in the settings first."
            )
            return

        # open a delete dialog for the user to confirm, return if user rejects
        delete_dialog = ProjectDeletionDialog.construct_project_deletion_dialog(self.window, bw.projects.current)
        if delete_dialog.exec_() != ProjectDeletionDialog.Accepted: return

        # change from the project to be deleted, to the startup project
        self.change_project(ab_settings.startup_project, reload=True)

        # try to delete the project, delete directory if user specified so
        try:
            bw.projects.delete_project(
                project_to_delete, 
                delete_dir=delete_dialog.deletion_warning_checked()
                )
        # if an exception occurs, show warning box en log exception
        except Exception as exception:
            log.error(str(exception))
            QtWidgets.QMessageBox.warning(
                self.window,
                "An error occured",
                "An error occured during project deletion. Please check the logs for more information."
            )            
        # if all goes well show info box that the project is deleted
        else:
            QtWidgets.QMessageBox.information(
                self.window,
                "Project deleted",
                "Project succesfully deleted"
            )

        # emit that the project list has changed because of the deletion,
        # regardless of a possible exception (which may have deleted the project anyways) 
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
            log.info("New calculation setup: {}".format(name))

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
            log.info("Copied calculation setup {} as {}".format(current, new_name))

    @Slot(str, name="deleteCalculationSetup")
    def delete_calculation_setup(self, name: str) -> None:
        del bw.calculation_setups[name]
        signals.set_default_calculation_setup.emit()
        log.info("Deleted calculation setup: {}".format(name))

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
            del bw.calculation_setups[current]
            signals.calculation_setup_selected.emit(new_name)
            log.info("Renamed calculation setup from {} to {}".format(current, new_name))

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
        signals.delete_method.connect(self.delete_method)
        signals.edit_method_cf.connect(self.modify_method_with_cf)
        signals.remove_cf_uncertainties.connect(self.remove_uncertainty)
        signals.add_cf_method.connect(self.add_method_to_cf)
        signals.delete_cf_method.connect(self.delete_method_from_cf)

    @Slot(tuple, name="copyMethod")
    def copy_method(self, method: tuple, level: str = None) -> None:
        """Calls copy depending on the level, if level is 'leaf', or None,
        then a single method is copied. Otherwise sets are used to identify
        the appropriate methods"""
        if level is not None and level != 'leaf':
            methods = [bw.Method(mthd) for mthd in bw.methods if set(method).issubset(mthd)]
        else:
            methods = [bw.Method(method)]
        dialog = TupleNameDialog.get_combined_name(
            self.window, "Impact category name", "Combined name:", method, " - Copy"
        )
        if dialog.exec_() == TupleNameDialog.Accepted:
            new_name = dialog.result_tuple
            for mthd in methods:
                new_method = new_name + mthd.name[len(new_name):]
                if new_method in bw.methods:
                    warn = "Impact Category with name '{}' already exists!".format(new_method)
                    QtWidgets.QMessageBox.warning(self.window, "Copy failed", warn)
                    return
                mthd.copy(new_method)
                log.info("Copied method {} into {}".format(str(mthd.name), str(new_method)))
            signals.new_method.emit()

    @Slot(tuple, name="deleteMethod")
    def delete_method(self, method_: tuple, level:str = None) -> None:
        """Call delete on the (first) selected method and present confirmation dialog."""
        if level is not None and level != 'leaf':
            methods = [bw.Method(mthd) for mthd in bw.methods if set(method_).issubset(mthd)]
        else:
            methods = [bw.Method(method_)]
        method = bw.Method(method_)
        dialog = QtWidgets.QMessageBox()
        dialog.setWindowTitle("Are you sure you want to delete this method?")
        dialog.setText("You are about to PERMANENTLY delete the following Impact Category:\n("
                       +", ".join(method.name)+
                       ")\nAre you sure you want to continue?")
        dialog.setIcon(QtWidgets.QMessageBox.Warning)
        dialog.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        dialog.setDefaultButton(QtWidgets.QMessageBox.No)
        if dialog.exec_() == QtWidgets.QMessageBox.Yes:
            for mthd in methods:
                mthd.deregister()
                log.info("Deleted method {}".format(str(mthd.name)))
            signals.method_deleted.emit()

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

    @Slot(tuple, tuple, name="addMethodToCF")
    def add_method_to_cf(self, cf: tuple, method: tuple):
        method = bw.Method(method)
        cfs = method.load()
        # fill in default values for a new cf row
        cfdata = (cf, {
            'uncertainty type': 0,
            'loc': float('nan'),
            'scale': float('nan'),
            'shape': float('nan'),
            'minimum': float('nan'),
            'maximum': float('nan'),
            'negative': False,
            'amount': 0
        })
        cfs.append(cfdata)
        method.write(cfs)
        signals.method_modified.emit(method.name)

    @Slot(tuple, tuple, name="deleteMethodFromCF")
    def delete_method_from_cf(self, to_delete: tuple, method: tuple):
        method = bw.Method(method)
        cfs = method.load()
        delete_list = []
        for i in cfs:
            for d in to_delete:
                if i[0][0] == d[0][0] and i[0][1] == d[0][1]:
                    delete_list.append(i)
        for d in delete_list:
            cfs.remove(d)
        method.write(cfs)
        signals.method_modified.emit(method.name)
# -*- coding: utf-8 -*-
import brightway2 as bw
from PySide2.QtCore import QObject, Slot
from PySide2 import QtWidgets

from activity_browser import log, signals, application
from activity_browser.ui.widgets import TupleNameDialog


class ImpactCategoryController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
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
            application.main_window, "Impact category name", "Combined name:", method, " - Copy"
        )
        if dialog.exec_() != TupleNameDialog.Accepted: return

        new_name = dialog.result_tuple
        for mthd in methods:
            new_method = new_name + mthd.name[len(new_name):]
            print('+', mthd)
            if new_method in bw.methods:
                warn = f"Impact Category with name '{new_method}' already exists!"
                QtWidgets.QMessageBox.warning(application.main_window, "Copy failed", warn)
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

impact_category_controller = ImpactCategoryController(application)

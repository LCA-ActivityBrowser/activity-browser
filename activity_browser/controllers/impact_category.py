# -*- coding: utf-8 -*-
from typing import List

import brightway2 as bw
from PySide2.QtCore import QObject, Slot

from activity_browser import log, signals, application


class ImpactCategoryController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        signals.delete_cf_method.connect(self.delete_method_from_cf)

    def duplicate_methods(self, methods: List[bw.Method], new_names: List[tuple]):
        for method, new_name in zip(methods, new_names):
            if new_name in bw.methods:
                raise Exception("New method name already in use")
            method.copy(new_name)
            log.info(f"Copied method {method.name} into {new_name}")
        signals.new_method.emit()

    def delete_methods(self, methods: List[bw.Method]) -> None:
        """Call delete on the (first) selected method and present confirmation dialog."""
        for method in methods:
            method.deregister()
            log.info(f"Deleted method {method.name}")
        signals.method_deleted.emit()

    def write_char_factors(self, method: tuple, char_factors: List[tuple], overwrite=True):
        method = bw.Method(method)
        cfs = method.load()

        for cf in char_factors:
            index = next((i for i, c in enumerate(cfs) if c[0] == cf[0]), None)

            if index is not None and overwrite:
                cfs[index] = cf
            elif index is not None and not overwrite:
                raise Exception("CF already exist in method, will not overwrite")
            else:
                cfs.append(cf)

        method.write(cfs)
        signals.method_modified.emit(method.name)

    def delete_char_factors(self, method, char_factors: List[tuple]):
        if not char_factors: return

        method = bw.Method(method)
        cfs = method.load()
        delete_keys, _ = list(zip(*char_factors))

        new_cfs = [cf for cf in cfs if cf[0] not in delete_keys]

        method.write(new_cfs)
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

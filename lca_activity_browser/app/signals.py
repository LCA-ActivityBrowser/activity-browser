# -*- coding: utf-8 -*-
from PyQt5 import QtCore


class Signals(QtCore.QObject):

    # General Settings
    switch_bw2_dir_path = QtCore.pyqtSignal()



    new_activity = QtCore.pyqtSignal(str)
    activity_selected = QtCore.pyqtSignal(tuple)

    # Activity key, field, new value
    activity_modified = QtCore.pyqtSignal(tuple, str, object)
    copy_activity = QtCore.pyqtSignal(tuple)
    open_activity_tab = QtCore.pyqtSignal(str, tuple)
    activity_tabs_changed = QtCore.pyqtSignal()
    delete_activity = QtCore.pyqtSignal(tuple)

    exchanges_output_modified = QtCore.pyqtSignal(list, tuple)
    exchanges_deleted = QtCore.pyqtSignal(list)
    exchanges_add = QtCore.pyqtSignal(list, tuple)
    exchange_amount_modified = QtCore.pyqtSignal(object, float)

    calculation_setup_changed = QtCore.pyqtSignal()
    calculation_setup_selected = QtCore.pyqtSignal(str)

    # Database operations
    import_database = QtCore.pyqtSignal()
    database_selected = QtCore.pyqtSignal(str)
    databases_changed = QtCore.pyqtSignal()
    database_changed = QtCore.pyqtSignal(str)

    lca_calculation = QtCore.pyqtSignal(str)

    method_selected = QtCore.pyqtSignal(tuple)

    project_selected = QtCore.pyqtSignal(str)


signals = Signals()

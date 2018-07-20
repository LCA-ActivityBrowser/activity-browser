# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class Signals(QtCore.QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # General Settings
    switch_bw2_dir_path = QtCore.pyqtSignal(str)

    # Copy Text (Clipboard)
    copy_selection_to_clipboard = QtCore.pyqtSignal(str)

    # bw2 directory
    # directory_changed = QtCore.pyqtSignal()

    # Project
    change_project = QtCore.pyqtSignal(str)
    change_project_dialog = QtCore.pyqtSignal()
    new_project = QtCore.pyqtSignal()
    copy_project = QtCore.pyqtSignal()
    delete_project = QtCore.pyqtSignal()
    project_selected = QtCore.pyqtSignal()
    projects_changed = QtCore.pyqtSignal()

    # Database
    add_database = QtCore.pyqtSignal()
    delete_database = QtCore.pyqtSignal(str)
    copy_database = QtCore.pyqtSignal(str)
    install_default_data = QtCore.pyqtSignal()
    import_database = QtCore.pyqtSignal()

    database_selected = QtCore.pyqtSignal(str)
    databases_changed = QtCore.pyqtSignal()
    database_changed = QtCore.pyqtSignal(str)

    # Activity (key, field, new value)
    new_activity = QtCore.pyqtSignal(str)
    add_activity_to_history = QtCore.pyqtSignal(tuple)

    activity_modified = QtCore.pyqtSignal(tuple, str, object)
    copy_activity = QtCore.pyqtSignal(tuple)
    open_activity_tab = QtCore.pyqtSignal(str, tuple)
    activity_tabs_changed = QtCore.pyqtSignal()
    delete_activity = QtCore.pyqtSignal(tuple)
    copy_to_db = QtCore.pyqtSignal(tuple)

    # Exchanges
    exchanges_output_modified = QtCore.pyqtSignal(list, tuple)
    exchanges_deleted = QtCore.pyqtSignal(list)
    exchanges_add = QtCore.pyqtSignal(list, tuple)
    exchange_amount_modified = QtCore.pyqtSignal(object, float)

    # Calculation Setups
    new_calculation_setup = QtCore.pyqtSignal()
    delete_calculation_setup = QtCore.pyqtSignal(str)
    rename_calculation_setup = QtCore.pyqtSignal(str)
    set_default_calculation_setup = QtCore.pyqtSignal()

    calculation_setup_changed = QtCore.pyqtSignal()
    calculation_setup_selected = QtCore.pyqtSignal(str)

    # LCA Calculation
    lca_calculation = QtCore.pyqtSignal(str)

    method_selected = QtCore.pyqtSignal(tuple)
    method_tabs_changed = QtCore.pyqtSignal()

    # Qt Windows
    update_windows = QtCore.pyqtSignal()

    # Plugins
    launch_plugin_lcopt = QtCore.pyqtSignal()


signals = Signals()

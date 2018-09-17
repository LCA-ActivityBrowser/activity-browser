# -*- coding: utf-8 -*-
from PySide2 import QtCore, QtWidgets


class Signals(QtCore.QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # General Settings
    switch_bw2_dir_path = QtCore.Signal(str)

    # Copy Text (Clipboard)
    copy_selection_to_clipboard = QtCore.Signal(str)

    # bw2 directory
    # directory_changed = QtCore.Signal()

    # Project
    change_project = QtCore.Signal(str)
    change_project_dialog = QtCore.Signal()
    new_project = QtCore.Signal()
    copy_project = QtCore.Signal()
    delete_project = QtCore.Signal()
    project_selected = QtCore.Signal()
    projects_changed = QtCore.Signal()

    # Database
    add_database = QtCore.Signal()
    delete_database = QtCore.Signal(str)
    copy_database = QtCore.Signal(str)
    install_default_data = QtCore.Signal()
    import_database = QtCore.Signal()

    database_selected = QtCore.Signal(str)
    databases_changed = QtCore.Signal()
    database_changed = QtCore.Signal(str)

    # Activity (key, field, new value)
    new_activity = QtCore.Signal(str)
    add_activity_to_history = QtCore.Signal(tuple)

    activity_modified = QtCore.Signal(tuple, str, object)
    copy_activity = QtCore.Signal(tuple)
    open_activity_tab = QtCore.Signal(str, tuple)
    activity_tabs_changed = QtCore.Signal()
    delete_activity = QtCore.Signal(tuple)
    copy_to_db = QtCore.Signal(tuple)

    # Exchanges
    exchanges_output_modified = QtCore.Signal(list, tuple)
    exchanges_deleted = QtCore.Signal(list)
    exchanges_add = QtCore.Signal(list, tuple)
    exchange_amount_modified = QtCore.Signal(object, float)

    # Calculation Setups
    new_calculation_setup = QtCore.Signal()
    delete_calculation_setup = QtCore.Signal(str)
    rename_calculation_setup = QtCore.Signal(str)
    set_default_calculation_setup = QtCore.Signal()

    calculation_setup_changed = QtCore.Signal()
    calculation_setup_selected = QtCore.Signal(str)

    # LCA Calculation
    lca_calculation = QtCore.Signal(str)

    method_selected = QtCore.Signal(tuple)
    method_tabs_changed = QtCore.Signal()

    # Qt Windows
    update_windows = QtCore.Signal()


signals = Signals()

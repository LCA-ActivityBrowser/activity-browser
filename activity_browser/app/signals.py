# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets


class Signals(QtCore.QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # General Settings

    # Copy Text (Clipboard)
    copy_selection_to_clipboard = QtCore.pyqtSignal(str)

    # bw2 directory
    switch_bw2_dir_path = QtCore.pyqtSignal(str)
    # directory_changed = QtCore.pyqtSignal()

    # Project
    change_project = QtCore.pyqtSignal(str)
    # change_project_dialog = QtCore.pyqtSignal()
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
    database_read_only_changed = QtCore.pyqtSignal(str, bool)

    # Activity (key, field, new value)
    new_activity = QtCore.pyqtSignal(str)
    add_activity_to_history = QtCore.pyqtSignal(tuple)
    duplicate_activity = QtCore.pyqtSignal(tuple)
    duplicate_activity_to_db = QtCore.pyqtSignal(str, object)
    show_duplicate_to_db_interface = QtCore.pyqtSignal(tuple)
    open_activity_tab = QtCore.pyqtSignal(tuple)
    open_activity_graph_tab = QtCore.pyqtSignal(tuple)
    delete_activity = QtCore.pyqtSignal(tuple)

    # Activity editing
    edit_activity = QtCore.pyqtSignal(str)  # db_name
    activity_modified = QtCore.pyqtSignal(tuple, str, object)

    # Exchanges
    # exchanges_output_modified = QtCore.pyqtSignal(list, tuple)
    exchanges_deleted = QtCore.pyqtSignal(list)
    exchanges_add = QtCore.pyqtSignal(list, tuple)
    exchange_amount_modified = QtCore.pyqtSignal(object, float)
    exchange_modified = QtCore.pyqtSignal(object, str, object)

    # Parameters
    add_activity_parameter = QtCore.pyqtSignal(tuple)
    parameters_changed = QtCore.pyqtSignal()
    # Pass the key of the activity holding the exchange
    exchange_formula_changed = QtCore.pyqtSignal(tuple)

    # Calculation Setups
    new_calculation_setup = QtCore.pyqtSignal()
    delete_calculation_setup = QtCore.pyqtSignal(str)
    rename_calculation_setup = QtCore.pyqtSignal(str)
    set_default_calculation_setup = QtCore.pyqtSignal()

    calculation_setup_changed = QtCore.pyqtSignal()
    calculation_setup_selected = QtCore.pyqtSignal(str)

    # LCA Results
    lca_calculation = QtCore.pyqtSignal(str)
    lca_results_tabs_changed = QtCore.pyqtSignal()

    method_selected = QtCore.pyqtSignal(tuple)
    method_tabs_changed = QtCore.pyqtSignal()

    # Qt Windows
    update_windows = QtCore.pyqtSignal()
    new_statusbar_message = QtCore.pyqtSignal(str)

    # Tabs
    toggle_show_or_hide_tab = QtCore.pyqtSignal(str)
    show_tab = QtCore.pyqtSignal(str)
    hide_tab = QtCore.pyqtSignal(str)
    hide_when_empty = QtCore.pyqtSignal()

    # Metadata
    metadata_changed = QtCore.pyqtSignal(tuple)  # key


signals = Signals()

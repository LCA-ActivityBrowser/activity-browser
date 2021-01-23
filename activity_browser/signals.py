# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Signal


class Signals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # General Settings

    # bw2 directory
    switch_bw2_dir_path = Signal(str)
    # directory_changed = Signal()

    # Project
    change_project = Signal(str)
    # change_project_dialog = Signal()
    new_project = Signal()
    copy_project = Signal()
    delete_project = Signal()
    project_selected = Signal()
    projects_changed = Signal()

    # Database
    add_database = Signal()
    delete_database = Signal(str)
    copy_database = Signal(str, QObject)
    install_default_data = Signal()
    import_database = Signal(QObject)
    relink_database = Signal(str, QObject)

    database_selected = Signal(str)
    databases_changed = Signal()
    database_changed = Signal(str)
    database_read_only_changed = Signal(str, bool)

    # Activity (key, field, new value)
    new_activity = Signal(str)
    add_activity_to_history = Signal(tuple)
    duplicate_activity = Signal(tuple)
    duplicate_activity_to_db = Signal(str, object)
    show_duplicate_to_db_interface = Signal(tuple)
    open_activity_tab = Signal(tuple)
    open_activity_graph_tab = Signal(tuple)
    delete_activity = Signal(tuple)

    # Activity editing
    edit_activity = Signal(str)  # db_name
    activity_modified = Signal(tuple, str, object)

    # Exchanges
    # exchanges_output_modified = Signal(list, tuple)
    exchanges_deleted = Signal(list)
    exchanges_add = Signal(list, tuple)
    exchange_amount_modified = Signal(object, float)
    exchange_modified = Signal(object, str, object)
    # Exchange object and uncertainty dictionary
    exchange_uncertainty_modified = Signal(object, object)
    exchange_pedigree_modified = Signal(object, object)

    # Parameters
    add_activity_parameter = Signal(tuple)
    parameters_changed = Signal()
    parameter_renamed = Signal(str, str, str)  # old, group, new
    # Pass the key of the activity holding the exchange
    exchange_formula_changed = Signal(tuple)
    # Parameter, field, value for field
    parameter_modified = Signal(object, str, object)
    # Parameter object and uncertainty dictionary
    parameter_uncertainty_modified = Signal(object, object)
    parameter_pedigree_modified = Signal(object, object)
    parameter_scenario_sync = Signal(int, object)
    parameter_superstructure_built = Signal(int, object)
    clear_activity_parameter = Signal(str, str, str)

    # Presamples
    presample_package_created = Signal(str)
    presample_package_delete = Signal(str)
    presample_package_removed = Signal()

    # Calculation Setups
    new_calculation_setup = Signal()
    delete_calculation_setup = Signal(str)
    rename_calculation_setup = Signal(str)
    set_default_calculation_setup = Signal()

    calculation_setup_changed = Signal()
    calculation_setup_selected = Signal(str)

    # LCA Results
    lca_calculation = Signal(str)
    lca_presamples_calculation = Signal(str, str)
    lca_scenario_calculation = Signal(str, object)
    lca_results_tabs_changed = Signal()

    method_selected = Signal(tuple)
    method_tabs_changed = Signal()

    # Monte Carlo LCA
    monte_carlo_finished = Signal()

    # Qt Windows
    update_windows = Signal()
    new_statusbar_message = Signal(str)

    # Tabs
    toggle_show_or_hide_tab = Signal(str)
    show_tab = Signal(str)
    hide_tab = Signal(str)
    hide_when_empty = Signal()

    # Metadata
    metadata_changed = Signal(tuple)  # key


signals = Signals()

# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Signal


class Signals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible. """

    # General Settings

    # bw2 directory
    switch_bw2_dir_path = Signal(str)
    edit_settings = Signal()

    # Project
    change_project = Signal(str)
    new_project = Signal()
    copy_project = Signal()
    delete_project = Signal()
    project_selected = Signal()
    projects_changed = Signal()

    # Database
    add_database = Signal()
    delete_database = Signal(str)
    copy_database = Signal(str)
    install_default_data = Signal()
    import_database = Signal()
    export_database = Signal()
    relink_database = Signal(str)
    update_biosphere = Signal()
    database_selected = Signal(str)
    databases_changed = Signal()
    database_changed = Signal(str)
    database_read_only_changed = Signal(str, bool)

    # Activity (key, field, new value)
    new_activity = Signal(str)
    add_activity_to_history = Signal(tuple)
    duplicate_activity = Signal(tuple)
    duplicate_activities = Signal(list)
    duplicate_activity_to_db = Signal(str, object)
    duplicate_to_db_interface = Signal(tuple, str)
    duplicate_to_db_interface_multiple = Signal(list, str)
    safe_open_activity_tab = Signal(tuple)
    unsafe_open_activity_tab = Signal(tuple)
    open_activity_tab = Signal(tuple)
    close_activity_tab = Signal(tuple)
    open_activity_graph_tab = Signal(tuple)
    delete_activity = Signal(tuple)
    delete_activities = Signal(list)

    # Activity editing
    edit_activity = Signal(str)  # db_name
    activity_modified = Signal(tuple, str, object)
    relink_activity = Signal(tuple)


    # Exchanges
    exchanges_deleted = Signal(list)
    exchanges_add = Signal(list, tuple)
    exchange_modified = Signal(object, str, object)
    # Exchange object and uncertainty dictionary
    exchange_uncertainty_wizard = Signal(object)
    exchange_uncertainty_modified = Signal(object, object)
    exchange_pedigree_modified = Signal(object, object)

    # Parameters
    add_parameter = Signal(tuple)
    add_activity_parameter = Signal(tuple)
    add_activity_parameters = Signal(list)
    added_parameter = Signal(str, str, str)
    parameters_changed = Signal()
    rename_parameter = Signal(object, str)
    parameter_renamed = Signal(str, str, str)  # old, group, new
    # Pass the key of the activity holding the exchange
    exchange_formula_changed = Signal(tuple)
    # Parameter, field, value for field
    parameter_modified = Signal(object, str, object)
    # Parameter object and uncertainty dictionary
    parameter_uncertainty_modified = Signal(object, object)
    parameter_pedigree_modified = Signal(object, object)
    delete_parameter = Signal(object)
    parameter_scenario_sync = Signal(int, object, bool)
    parameter_superstructure_built = Signal(int, object)
    clear_activity_parameter = Signal(str, str, str)

    # Calculation Setups
    new_calculation_setup = Signal()
    copy_calculation_setup = Signal(str)
    delete_calculation_setup = Signal(str)
    rename_calculation_setup = Signal(str)
    set_default_calculation_setup = Signal()

    calculation_setup_changed = Signal()
    calculation_setup_selected = Signal(str)

    # LCA Results
    lca_calculation = Signal(dict)
    lca_results_tabs_changed = Signal()

    # Impact Categories & Characterization Factors
    new_method = Signal(tuple)
    copy_method = Signal(tuple)
    edit_method_cf = Signal(tuple, tuple)
    remove_cf_uncertainties = Signal(list, tuple)
    method_modified = Signal(tuple)
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

    # Plugins
    plugin_selected = Signal(str)
    plugin_deselected = Signal(str)
    manage_plugins = Signal()

signals = Signals()

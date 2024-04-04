# -*- coding: utf-8 -*-
from PySide2.QtCore import QObject, Signal


class ABSignals(QObject):
    """ Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible.
    Every signal should have a comment (no matter how descriptive the name of the signal) that describes what a
    signal is used for and after a pipe (|), what variables are sent, if any.
    """
    # Project
    project_selected = Signal()  # A project was selected (opened)

    # Database
    delete_database_confirmed = Signal(str)  # This database has been deleted | name of database
    database_selected = Signal(str)  # This database was selected (opened) | name of database
    databases_changed = Signal()  # The list of databases in this project has changed e.g. a database was added
    database_changed = Signal(str)  # This database has changed e.g. an activity was added to it | name of database
    database_read_only_changed = Signal(str, bool)  # The read_only state of database changed | name of database, read-only state
    database_tab_open = Signal(str)  # This database tab is being viewed by user | name of database

    # Activity
    add_activity_to_history = Signal(tuple)  # Add this activity to history | key of activity
    safe_open_activity_tab = Signal(tuple)  # Open activity details tab in read-only mode | key of activity
    unsafe_open_activity_tab = Signal(tuple)  # Open activity details tab in editable mode | key of activity
    close_activity_tab = Signal(tuple)  # Close this activity details tab | key of activity
    open_activity_graph_tab = Signal(tuple)  # Open the graph-view tab | key of activity

    # Activity editing
    edit_activity = Signal(str)  # An activity in this database may now be edited | name of database

    # Parameters
    add_parameter = Signal(tuple)  # Trigger dialog to add parameter to this exchange | key of exchange
    add_activity_parameter = Signal(tuple)  # Add a parameter to this exchange | key of exchange
    add_activity_parameters = Signal(list)  # Add parameter to these exchanges | list of exchange keys
    added_parameter = Signal(str, str, str)  # This parameter has been added | name of the parameter, amount, type (project, database or activity)
    parameters_changed = Signal()  # The parameters have changed
    rename_parameter = Signal(object, str)  # Trigger dialog to rename parameter | parameter object, type (project, database or activity)
    parameter_renamed = Signal(str, str, str)  # This parameter was renamed | old name, type (project, database or activity), new name
    exchange_formula_changed = Signal(tuple)  # The formula for an exchange in this activity was changed | key of activity
    parameter_modified = Signal(object, str, object)  # This parameter was modified | parameter object, name of the changed field, new content of the field
    parameter_uncertainty_modified = Signal(object, dict)  # The uncertainty data for this parameter was modified | parameter object, uncertainty data
    parameter_pedigree_modified = Signal(object, object)  # The pedigree uncertainty data for this parameter was modified | parameter object, pedigree data
    delete_parameter = Signal(object)  # Delete this parameter | proxy index of the table view of the parameter
    parameter_scenario_sync = Signal(int, object, bool)  # Synchronize this data for table | index of the table, dataframe with scenario data, include default scenario
    parameter_superstructure_built = Signal(int, object)  # Superstructure built from scenarios | index of the table, dataframe with scenario data
    clear_activity_parameter = Signal(str, str, str)  # Clear this parameter | name of database, name of code, name of group

    # Calculation Setups
    new_calculation_setup = Signal()  # Trigger dialog for a new calculation setup
    copy_calculation_setup = Signal(str)  # Trigger dialog for copying this calculation setup | name of calculation setup
    delete_calculation_setup = Signal(str)  # Delete this calculation setup | name of calculation setup
    rename_calculation_setup = Signal(str)  # Trigger dialog to rename this calculation setup | name of calculation setup
    set_default_calculation_setup = Signal()  # Show the default (first) calculation setup

    calculation_setup_changed = Signal()  # Calculation setup was changed
    calculation_setup_selected = Signal(str)  # This calculation setup was selected (opened) | name of calculation setup

    # LCA Results
    lca_calculation = Signal(dict)  # Generate a calculation setup | dictionary with name, type (simple/scenario) and potentially scenario data

    # Impact Categories & Characterization Factors
    new_method = Signal()  # A new method was added
    method_deleted = Signal()  # A method was deleted
    copy_method = Signal(tuple, str)  # Copy this method | tuple of impact category, level of tree OR the proxy
    delete_method = Signal(tuple, str)  # Delete this method | tuple of impact category, level of tree OR the proxy
    edit_method_cf = Signal(tuple, tuple)  # Edit this CF for this method | tuple of characterization factor, tuple of method
    remove_cf_uncertainties = Signal(list, tuple)  # Remove uncertainty data for these CFs | list of CFs to remove info from, tuple of method
    method_modified = Signal(tuple)  # This method was modified | tuple of method
    method_selected = Signal(tuple)  # This method was selected (opened) | tuple of method
    set_uncertainty = Signal(tuple)  # Set uncertainty of CF | proxy index of the table view of the CF
    add_cf_method = Signal(tuple, tuple)  # Add uncertainty to CF | tuple of CF, tuple impact category
    delete_cf_method = Signal(tuple, tuple)  # Delete this CF from impact category | tuple of CF, tuple of impact category
    cf_changed = Signal()  # A characterization factor was changed

    # Monte Carlo LCA
    monte_carlo_finished = Signal()  # The monte carlo calculations are finished

    # Qt Windows
    update_windows = Signal()  # Update the windows
    new_statusbar_message = Signal(str)  # Update the statusbar this message | message
    restore_cursor = Signal()  # Restore the cursor to normal

    # Tabs
    toggle_show_or_hide_tab = Signal(str)  # Show/Hide the tab with this name | name of tab
    show_tab = Signal(str)  # Show this tab | name of tab
    hide_tab = Signal(str)  # Hide this tab | name of tab
    hide_when_empty = Signal()  # Show/Hide tab when it has/does not have sub-tabs

    # Plugins
    plugin_selected = Signal(str, bool)  # This plugin was/was not selected | name of plugin, selected state
    manage_plugins = Signal()  # Trigger the plugins dialog


signals = ABSignals()

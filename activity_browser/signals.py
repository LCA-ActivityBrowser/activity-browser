# -*- coding: utf-8 -*-
from bw2data import Method, get_activity
from bw2data.parameters import ParameterBase
from qtpy.QtCore import QObject, Qt, QThread, Signal, SignalInstance
from blinker import signal as blinker_signal

from .application import application

from bw2data.backends import Activity, Exchange


class NodeSignals(QObject):
    from bw2data.backends import ActivityDataset

    changed: SignalInstance = Signal(ActivityDataset, ActivityDataset)
    deleted: SignalInstance = Signal(ActivityDataset, ActivityDataset)
    database_change: SignalInstance = Signal(ActivityDataset, ActivityDataset)
    code_change: SignalInstance = Signal(ActivityDataset, ActivityDataset)


class EdgeSignals(QObject):
    from bw2data.backends import ExchangeDataset

    changed: SignalInstance = Signal(ExchangeDataset, ExchangeDataset)
    deleted: SignalInstance = Signal(ExchangeDataset, ExchangeDataset)


class MethodSignals(QObject):
    from bw2data import Method

    changed: SignalInstance = Signal(Method, Method)
    deleted: SignalInstance = Signal(Method, Method)


class DatabaseSignals(QObject):
    from bw2data.backends import SQLiteBackend

    written: SignalInstance = Signal(SQLiteBackend)
    reset: SignalInstance = Signal(SQLiteBackend)
    delete: SignalInstance = Signal(str)


class ProjectSignals(QObject):
    changed: SignalInstance = Signal(dict)
    created: SignalInstance = Signal(dict)


class MetaSignals(QObject):
    from bw2data.serialization import SerializedDict

    databases_changed: SignalInstance = Signal(SerializedDict, SerializedDict)
    methods_changed: SignalInstance = Signal(SerializedDict, SerializedDict)


class ABSignals(QObject):
    """Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible.
    Every signal should have a comment (no matter how descriptive the name of the signal) that describes what a
    signal is used for and after a pipe (|), what variables are sent, if any.
    """
    node = NodeSignals()
    edge = EdgeSignals()
    method = MethodSignals()
    database = DatabaseSignals()
    project = ProjectSignals()
    meta = MetaSignals()

    import_project = Signal()  # Import a project
    export_project = Signal()  # Export the current project
    database_selected = Signal(str)  # This database was selected (opened) | name of database
    database_read_only_changed = Signal(str, bool)  # The read_only state of database changed | name of database, read-only state
    database_tab_open = Signal(str)  # This database tab is being viewed by user | name of database
    add_activity_to_history = Signal(tuple)
    safe_open_activity_tab = Signal(tuple)  # Open activity details tab in read-only mode | key of activity
    unsafe_open_activity_tab = Signal(tuple)  # Open activity details tab in editable mode | key of activity
    close_activity_tab = Signal(tuple)  # Close this activity details tab | key of activity
    open_activity_graph_tab = Signal(tuple)  # Open the graph-view tab | key of activity
    edit_activity = Signal(str)  # An activity in this database may now be edited | name of database
    added_parameter = Signal(str, str, str)  # This parameter has been added | name of the parameter, amount, type (project, database or activity)
    parameters_changed = Signal()  # The parameters have changed
    parameter_scenario_sync = Signal(int, object, bool)  # Synchronize this data for table | index of the table, dataframe with scenario data, include default scenario
    parameter_superstructure_built = Signal(int, object)  # Superstructure built from scenarios | index of the table, dataframe with scenario data
    set_default_calculation_setup = Signal()  # Show the default (first) calculation setup
    calculation_setup_changed = Signal()  # Calculation setup was changed
    calculation_setup_selected = Signal(str)  # This calculation setup was selected (opened) | name of calculation setup
    lca_calculation = Signal(dict)  # Generate a calculation setup | dictionary with name, type (simple/scenario) and potentially scenario data
    delete_method = Signal(tuple, str)  # Delete this method | tuple of impact category, level of tree OR the proxy
    method_selected = Signal(tuple)  # This method was selected (opened) | tuple of method
    monte_carlo_finished = Signal()  # The monte carlo calculations are finished
    new_statusbar_message = Signal(str)  # Update the statusbar this message | message
    restore_cursor = Signal()  # Restore the cursor to normal
    project_updates_available = Signal(str, int)  # Project name and number of updates available
    toggle_show_or_hide_tab = Signal(str)  # Show/Hide the tab with this name | name of tab
    show_tab = Signal(str)  # Show this tab | name of tab
    hide_tab = Signal(str)  # Hide this tab | name of tab
    hide_when_empty = Signal()  # Show/Hide tab when it has/does not have sub-tabs
    plugin_selected = Signal(str, bool)  # This plugin was/was not selected | name of plugin, selected state

    def __init__(self, parent=None):
        super().__init__(parent)

        self._connect_bw_signals()

    def _connect_bw_signals(self):
        from bw2data import signals
        from bw2data.meta import databases, methods

        signals.signaleddataset_on_save.connect(self._on_signaleddataset_on_delete)
        signals.signaleddataset_on_delete.connect(self._on_signaleddataset_on_delete)
        signals.on_activity_database_change.connect(self._on_activity_database_change)
        signals.on_activity_code_change.connect(self._on_activity_code_change)

        signals.on_database_delete.connect(self._on_database_delete)
        signals.on_database_reset.connect(self._on_database_reset)
        signals.on_database_write.connect(self._on_database_write)

        signals.project_changed.connect(self._on_project_changed)
        signals.project_created.connect(self._on_project_created)

        databases._save_signal.connect(self._on_database_metadata_change)
        setattr(methods, "_save_signal", blinker_signal("ab.patched_methods"))
        methods._save_signal.connect(self._on_methods_metadata_change)

    def _on_signaleddataset_on_save(self, sender, old, new):
        from bw2data.backends import ActivityDataset, ExchangeDataset
        if isinstance(new, ActivityDataset):
            self.node.changed.emit(old, new)
        elif isinstance(new, ExchangeDataset):
            self.edge.changed.emit(old, new)
        else:
            print(f"Unknown dataset type changed: {type(new)}")

    def _on_signaleddataset_on_delete(self, sender, old, new):
        from bw2data.backends import ActivityDataset, ExchangeDataset
        if isinstance(new, ActivityDataset):
            self.node.deleted.emit(old, new)
        elif isinstance(new, ExchangeDataset):
            self.edge.deleted.emit(old, new)
        else:
            print(f"Unknown dataset type deleted: {type(new)}")

    def _on_activity_database_change(self, sender, old, new):
        self.node.database_change.emit(old, new)

    def _on_activity_code_change(self, sender, old, new):
        self.node.code_change.emit(old, new)

    def _on_database_delete(self, sender, name):
        self.database.delete.emit(name)

    def _on_database_reset(self, sender, name):
        from bw2data import Database
        self.database.reset.emit(Database(name))

    def _on_database_write(self, sender, name):
        from bw2data import Database
        self.database.written.emit(Database(name))

    def _on_project_changed(self, ds):
        self.project.changed.emit(ds)

    def _on_project_created(self, ds):
        self.project.created.emit(ds)

    def _on_database_metadata_change(self, sender, old, new):
        self.meta.databases_changed.emit(old, new)

    def _on_methods_metadata_change(self, sender, old, new):
        self.meta.methods_changed.emit(old, new)


signals = ABSignals()

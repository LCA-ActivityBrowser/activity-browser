# -*- coding: utf-8 -*-
from bw2data import Method, get_activity
from bw2data.parameters import ParameterBase
from qtpy.QtCore import QObject, Qt, QThread, Signal, SignalInstance
from blinker import signal as blinker_signal

from .application import application

from bw2data.backends import Activity, Exchange


class NodeSignals(QObject):
    changed = blinker_signal("ab.node.changed")
    deleted = blinker_signal("ab.node.deleted")
    database_change = blinker_signal("ab.node.database_change")
    code_change = blinker_signal("ab.node.code_change")


class EdgeSignals(QObject):
    changed = blinker_signal("ab.edge.changed")
    deleted = blinker_signal("ab.edge.deleted")


class MethodSignals(QObject):
    changed = blinker_signal("ab.method.changed")
    deleted = blinker_signal("ab.method.deleted")


class DatabaseSignals(QObject):
    written = blinker_signal("ab.database.written")
    reset = blinker_signal("ab.database.reset")
    delete = blinker_signal("ab.database.delete")


class ProjectSignals(QObject):
    changed: SignalInstance = Signal(dict)
    created: SignalInstance = Signal(dict)


class MetaSignals(QObject):
    databases_changed = blinker_signal("ab.meta.databases_changed")
    methods_changed = blinker_signal("ab.meta.methods_changed")


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
            self.node.changed.send(new, old=old, new=new)
        elif isinstance(new, ExchangeDataset):
            self.edge.changed.send(new,  old=old, new=new)
        else:
            print(f"Unknown dataset type changed: {type(new)}")

    def _on_signaleddataset_on_delete(self, sender, old, new):
        from bw2data.backends import ActivityDataset, ExchangeDataset
        if isinstance(new, ActivityDataset):
            self.node.deleted.send(new, old=old, new=new)
        elif isinstance(new, ExchangeDataset):
            self.edge.deleted.send(new,  old=old, new=new)
        else:
            print(f"Unknown dataset type deleted: {type(new)}")

    def _on_activity_database_change(self, sender, old, new):
        self.node.database_change.send(new, old=old, new=new)

    def _on_activity_code_change(self, sender, old, new):
        self.node.code_change.send(new, old=old, new=new)

    def _on_database_delete(self, sender, name):
        self.database.delete.send(None, database_name=name)

    def _on_database_reset(self, sender, name):
        from bw2data import Database
        self.database.reset.send(Database(name), name=name)

    def _on_database_write(self, sender, name):
        from bw2data import Database
        self.database.written.send(Database(name), name=name)

    def _on_project_changed(self, ds):
        self.project.changed.emit(ds)

    def _on_project_created(self, ds):
        self.project.created.emit(ds)

    def _on_database_metadata_change(self, sender, old, new):
        from bw2data import databases
        self.meta.databases_changed.send(databases, old=old, new=new)

    def _on_methods_metadata_change(self, sender, old, new):
        from bw2data import methods
        self.meta.methods_changed.send(methods, old=old, new=new)


class QUpdater(QObject):
    """
    A QUpdater is the link between Brightway and the widgets. Its purpose is to be the Qt counterpart of any Brightway
    object and instantiate/emit the necessary signals for it. Signals can be emitted through emitLater, which will emit
    the latest registered signals once when either the main event loop wakes, or when the sub-thread in which the
    emit was requested finishes. This keeps the amount of emits to the necessary minimum and keeps the system lean.

    Subclass this to add the signals you want a Brightway object. See for example QDatabases for bw2data.databases or
    QProjects for bw2data.projects

    The signals should be accessible through the patched Brightway object so the developer can connect to the QUpdater
    via the object itself, instead of directly to the QUpdater, like so:

    bw2data.projects.current_changed.connect()

    instead of:

    activity_browser.signals.signals.project.changed.connect()
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cache = {}

    def emitLater(self, signal_name: str, *args):
        """
        Emit this signal with these arguments when the main event loop wakes, or when the thread is finished. For a
        single signal instance only the last registered arguments will be emitted, which should be the most up-to-date
        data.
        """
        # check if the signal_name corresponds with a SignalInstance on this object
        if not isinstance(getattr(self, signal_name), SignalInstance):
            raise ValueError("Signal name not valid on this QObject")

        # cache the emit for later
        self.cache[signal_name] = args

        # if we're running in the main thread, emit cache when the event loop wakes
        if QThread.currentThread() == application.thread():
            application.thread().eventDispatcher().awake.connect(
                self.emit_cache, Qt.UniqueConnection
            )
        # else, emit the cache when the thread has finished work
        else:
            QThread.currentThread().finished.connect(
                self.emit_cache, Qt.UniqueConnection
            )

    def emit_cache(self):
        """
        Emit all currently cached signals and clear the cache. If triggered by an eventdispatcher or thread, this slot
        will try to disconnect to avoid unnecessary calls when the cache is empty.
        """
        # emit all signals in the cache
        for key, value in self.cache.items():
            signal = getattr(self, key)
            signal.emit(*value)

        # clear the cache so they are only emitted once
        self.cache.clear()

        # cleaning up the connections
        if self.sender() == application.thread().eventDispatcher():
            self.sender().awake.disconnect(self.emit_cache)
        elif isinstance(self.sender(), QThread):
            self.sender().finished.disconnect(self.emit_cache)


class QDatastore(QUpdater):
    """
    A QDatastore is a special kind of updater that will only be instantiated when connected to, and that will delete
    itself when fully disconnected from. This is useful for non-persistent bw objects of which there can be very many,
    like databases, activities, exchanged and methods. By instantiating an (expensive) QUpdater for these objects only
    when we need to, we make sure we don't have to deal with enormous load times.

    QDatastores should be initialized by accessing either the .changed or .deleted attribute of the patched Brightway
    class, e.g.: get_activity(key).changed.connect(), or, Database("biosphere3").changed.connect(). This will
    instantiate a QDatastore and connect or connect to an already existing QDatastore.

    QDatastore objects are children of the persistent list-QObjects, which are described below, and can be used to
    iterate over the existing QDatastores. QDatastores are initialized using keyword-arguments that can later be used to
    match them to their corresponding Brightway counterpart. The QDatastore for an Activity will for example be
    initialized using the Activity Model Fields like "id", "database" and "code".
    """

    changed: SignalInstance = Signal(object)
    deleted: SignalInstance = Signal(object)

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.fields = kwargs
        self.connected = 0
        self.cache = {}

    def __getitem__(self, item):
        return self.fields[item]

    def connectNotify(self, signal):
        """
        When a connection is made to "changed" or "deleted", increase connected value by one
        """
        signal_name = signal.name().data().decode()
        if signal_name == "changed" or signal_name == "deleted":
            self.connected += 1

    def disconnectNotify(self, signal):
        """
        When a disconnection is made from "changed" or "deleted", decrease connected value by one. If connected value is
        zero, remove ourselves from the list-QObject and deleteLater.
        """
        signal_name = signal.name().data().decode()
        if signal_name == "changed" or signal_name == "deleted":
            self.connected -= 1

        if self.connected == 0:
            self.setParent(None)
            self.deleteLater()


class QDatabaseList(QObject):
    """
    A QObject that has Database QUpdaters as its children. Iterate and match using the database name.
    """

    def __iter__(self):
        for child in self.findChildren(QDatastore):
            yield child

    def get_or_create(self, database):
        db_name = database if isinstance(database, str) else database.name

        qdatabase = [
            qdatabase for qdatabase in self.children() if qdatabase["name"] == db_name
        ]

        if qdatabase:
            return qdatabase[0]
        else:
            return QDatastore(self, name=db_name)


class QActivityList(QObject):
    """
    A QObject that has Activity QUpdaters as its children. Iterate and match using Activity model fields.
    """

    def __iter__(self):
        for child in self.findChildren(QDatastore):
            yield child

    def get_or_create(self, activity):
        activity = (
            activity if isinstance(activity, Activity) else get_activity(activity)
        )
        doc = activity._document

        qactivity = [
            qactivity for qactivity in self.children() if qactivity["id"] == doc.id
        ]

        if qactivity:
            return qactivity[0]
        else:
            return QDatastore(self, **doc.__data__)


class QExchangeList(QObject):
    """
    A QObject that has Exchange QUpdaters as its children. Iterate and match using Exchange model fields.
    """

    def __iter__(self):
        for child in self.findChildren(QDatastore):
            yield child

    def get_or_create(self, exchange: Exchange):
        doc = exchange._document
        qexchange = [
            qexchange for qexchange in self.children() if qexchange["id"] == doc.id
        ]

        if qexchange:
            return qexchange[0]
        else:
            return QDatastore(self, **doc.__data__)


class QMethodList(QObject):
    """
    A QObject that has Method QUpdaters as its children. Iterate and match using the Method name tuple.
    """

    def __iter__(self):
        for child in self.findChildren(QDatastore):
            yield child

    def get_or_create(self, method: Method):
        qmethod = [
            qmethod for qmethod in self.children() if qmethod["name"] == method.name
        ]

        if qmethod:
            return qmethod[0]
        else:
            return QDatastore(self, name=method.name)


class QParameterList(QObject):
    """
    A QObject that has Parameter QUpdaters as its children. Iterate and match using the Parameter key:
    Tuple(group, param_name).
    """

    def __iter__(self):
        for child in self.findChildren(QDatastore):
            yield child

    def get_or_create(self, parameter: ParameterBase):
        qparam = [
            qparam for qparam in self.children() if qparam["key"] == parameter.key
        ]

        if qparam:
            return qparam[0]
        else:
            return QDatastore(self, key=parameter.key)


class QProjects(QUpdater):
    current_changed: SignalInstance = Signal()
    list_changed: SignalInstance = Signal()


class QDatabases(QUpdater):
    metadata_changed: SignalInstance = Signal()


class QCalculationSetups(QUpdater):
    metadata_changed: SignalInstance = Signal()


class QMethods(QUpdater):
    metadata_changed: SignalInstance = Signal()


class QParameters(QUpdater):
    parameters_changed: SignalInstance = Signal()


signals = ABSignals()

qprojects = QProjects()
qdatabases = QDatabases()
qcalculation_setups = QCalculationSetups()
qmethods = QMethods()
qparameters = QParameters()

qdatabase_list = QDatabaseList()
qactivity_list = QActivityList()
qexchange_list = QExchangeList()
qmethod_list = QMethodList()
qparameter_list = QParameterList()

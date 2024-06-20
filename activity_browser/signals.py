# -*- coding: utf-8 -*-
from bw2data import Method, get_activity
from bw2data.parameters import ParameterBase
from PySide2.QtCore import QObject, Qt, QThread, Signal, SignalInstance

from .application import application

try:
    from bw2data.backends.peewee.proxies import Activity, Exchange
except ModuleNotFoundError:
    # we're running Brightway 25
    from bw2data.backends import Activity, Exchange


class ABSignals(QObject):
    """Signals used for the Activity Browser should be defined here.
    While arguments can be passed to signals, it is good practice not to do this if possible.
    Every signal should have a comment (no matter how descriptive the name of the signal) that describes what a
    signal is used for and after a pipe (|), what variables are sent, if any.
    """

    # General Settings
    # log = Signal(str)  # Write log message to debug window | log message

    # bw2 directory
    # switch_bw2_dir_path = Signal(str)  # Change the path to the BW2 settings | path
    # edit_settings = Signal()  # Change AB settings

    # Project
    # change_project = Signal(str)  # Change the project | project name
    # new_project = Signal()  # Start a new project
    # copy_project = Signal()  # Copy a project
    # delete_project = Signal()  # Delete a project
    # project_selected = Signal()  # A project was selected (opened)
    # projects_changed = Signal()  # The list of projects changed

    # Database
    # add_database = Signal()  # Trigger dialog to start a new database
    # delete_database = Signal(str)  # Delete this database | name of database
    # delete_database_confirmed = Signal(str)  # This database has been deleted | name of database
    # copy_database = Signal(str)  # Copy this database | name of the database to be copied
    # install_default_data = Signal()  # Trigger dialog for user to install default data
    # import_database = Signal()  # Trigger dialog to import a database
    # export_database = Signal()  # Trigger dialog to export a database
    # relink_database = Signal(str)  # Relink this database | name of database
    # update_biosphere = Signal()  # Trigger dialog to update the biosphere
    database_selected = Signal(
        str
    )  # This database was selected (opened) | name of database
    # databases_changed = Signal()  # The list of databases in this project has changed e.g. a database was added
    # database_changed = Signal(str)  # This database has changed e.g. an activity was added to it | name of database
    database_read_only_changed = Signal(
        str, bool
    )  # The read_only state of database changed | name of database, read-only state
    database_tab_open = Signal(
        str
    )  # This database tab is being viewed by user | name of database

    # Activity
    # new_activity = Signal(str)  # Trigger dialog to create a new activity in this database | name of database
    add_activity_to_history = Signal(
        tuple
    )  # Add this activity to history | key of activity
    # duplicate_activity = Signal(tuple)  # Duplicate this activity | key of activity
    # duplicate_activity_new_loc = Signal(tuple)  # Trigger dialog to duplicate this activity to a new location | key of activity
    # duplicate_activities = Signal(list)  # Duplicate these activities | list of activity keys
    # duplicate_activity_to_db = Signal(str, object)  # Duplicate this activity to another database | name of target database, BW2 actiivty object

    # duplicate_to_db_interface = Signal(tuple, str)  # Trigger dialog to duplicate actiivty to another database | key of activity, name of source database
    # duplicate_to_db_interface_multiple = Signal(list, str)  # Trigger dialog to duplicate actiivty to another database | list of activity keys, name of source database
    safe_open_activity_tab = Signal(
        tuple
    )  # Open activity details tab in read-only mode | key of activity
    unsafe_open_activity_tab = Signal(
        tuple
    )  # Open activity details tab in editable mode | key of activity
    close_activity_tab = Signal(
        tuple
    )  # Close this activity details tab | key of activity
    open_activity_graph_tab = Signal(tuple)  # Open the graph-view tab | key of activity
    # delete_activity = Signal(tuple)  # Delete this activity | key of activity
    # delete_activities = Signal(list)  # Delete these activities | list of activity keys

    # Activity editing
    edit_activity = Signal(
        str
    )  # An activity in this database may now be edited | name of database
    # activity_modified = Signal(tuple, str, object)  # This was changed about this activity | key of activity, name of the changed field, new content of the field
    # relink_activity = Signal(tuple)  # Trigger dialog to relink this activity | key of activity

    # Exchanges
    # exchanges_deleted = Signal(list)  # These exchanges should be deleted | list of exchange keys
    # exchanges_add = Signal(list, tuple)  # Add these exchanges to this activity | list of exchange keys to be added, key of target activity
    # exchanges_add_w_values = Signal(list, tuple, dict)  # Add these exchanges to this activity with these values| list of exchange keys to be added, key of target activity, values to add per exchange
    # exchange_modified = Signal(object, str, object)  # This was changed about this exchange | exchange object, name of the changed field, new content of the field
    # Exchange object and uncertainty dictionary
    # exchange_uncertainty_wizard = Signal(object)  # Trigger uncertainty dialog for this exchange | exchange object
    # exchange_uncertainty_modified = Signal(object, dict)  # The uncertainty data for this exchange was modified | exchange object, uncertainty data
    # exchange_pedigree_modified = Signal(object, object)  # The pedigree uncertainty data for this exchange was modified | exchange object, pedigree data

    # Parameters
    # add_parameter = Signal(tuple)  # Trigger dialog to add parameter to this exchange | key of exchange
    # add_activity_parameter = Signal(tuple)  # Add a parameter to this exchange | key of exchange
    # add_activity_parameters = Signal(list)  # Add parameter to these exchanges | list of exchange keys
    added_parameter = Signal(
        str, str, str
    )  # This parameter has been added | name of the parameter, amount, type (project, database or activity)
    parameters_changed = Signal()  # The parameters have changed
    # rename_parameter = Signal(object, str)  # Trigger dialog to rename parameter | parameter object, type (project, database or activity)
    # parameter_renamed = Signal(str, str, str)  # This parameter was renamed | old name, type (project, database or activity), new name
    # exchange_formula_changed = Signal(tuple)  # The formula for an exchange in this activity was changed | key of activity
    # parameter_modified = Signal(object, str, object)  # This parameter was modified | parameter object, name of the changed field, new content of the field
    # parameter_uncertainty_modified = Signal(object, dict)  # The uncertainty data for this parameter was modified | parameter object, uncertainty data
    # parameter_pedigree_modified = Signal(object, object)  # The pedigree uncertainty data for this parameter was modified | parameter object, pedigree data
    # delete_parameter = Signal(object)  # Delete this parameter | proxy index of the table view of the parameter
    parameter_scenario_sync = Signal(
        int, object, bool
    )  # Synchronize this data for table | index of the table, dataframe with scenario data, include default scenario
    parameter_superstructure_built = Signal(
        int, object
    )  # Superstructure built from scenarios | index of the table, dataframe with scenario data
    # clear_activity_parameter = Signal(str, str, str)  # Clear this parameter | name of database, name of code, name of group

    # Calculation Setups
    # new_calculation_setup = Signal()  # Trigger dialog for a new calculation setup
    # copy_calculation_setup = Signal(str)  # Trigger dialog for copying this calculation setup | name of calculation setup
    # delete_calculation_setup = Signal(str)  # Delete this calculation setup | name of calculation setup
    # rename_calculation_setup = Signal(str)  # Trigger dialog to rename this calculation setup | name of calculation setup
    set_default_calculation_setup = (
        Signal()
    )  # Show the default (first) calculation setup
    calculation_setup_changed = Signal()  # Calculation setup was changed
    calculation_setup_selected = Signal(
        str
    )  # This calculation setup was selected (opened) | name of calculation setup

    # LCA Results
    lca_calculation = Signal(
        dict
    )  # Generate a calculation setup | dictionary with name, type (simple/scenario) and potentially scenario data

    # Impact Categories & Characterization Factors
    # new_method = Signal()  # A new method was added
    # method_deleted = Signal()  # A method was deleted
    # copy_method = Signal(tuple, str)  # Copy this method | tuple of impact category, level of tree OR the proxy
    delete_method = Signal(
        tuple, str
    )  # Delete this method | tuple of impact category, level of tree OR the proxy
    # edit_method_cf = Signal(tuple, tuple)  # Edit this CF for this method | tuple of characterization factor, tuple of method
    # remove_cf_uncertainties = Signal(list, tuple)  # Remove uncertainty data for these CFs | list of CFs to remove info from, tuple of method
    # method_modified = Signal(tuple)  # This method was modified | tuple of method
    method_selected = Signal(
        tuple
    )  # This method was selected (opened) | tuple of method
    # set_uncertainty = Signal(tuple)  # Set uncertainty of CF | proxy index of the table view of the CF
    # add_cf_method = Signal(tuple, tuple)  # Add uncertainty to CF | tuple of CF, tuple impact category
    # delete_cf_method = Signal(tuple, tuple)  # Delete this CF from impact category | tuple of CF, tuple of impact category
    # cf_changed = Signal()  # A characterization factor was changed

    # Monte Carlo LCA
    monte_carlo_finished = Signal()  # The monte carlo calculations are finished

    # Qt Windows
    # update_windows = Signal()  # Update the windows
    new_statusbar_message = Signal(str)  # Update the statusbar this message | message
    restore_cursor = Signal()  # Restore the cursor to normal

    # Tabs
    toggle_show_or_hide_tab = Signal(
        str
    )  # Show/Hide the tab with this name | name of tab
    show_tab = Signal(str)  # Show this tab | name of tab
    hide_tab = Signal(str)  # Hide this tab | name of tab
    hide_when_empty = Signal()  # Show/Hide tab when it has/does not have sub-tabs

    # Plugins
    plugin_selected = Signal(
        str, bool
    )  # This plugin was/was not selected | name of plugin, selected state
    # manage_plugins = Signal()  # Trigger the plugins dialog


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

    activity_browser.signals.qprojects.current_changed.connect()
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

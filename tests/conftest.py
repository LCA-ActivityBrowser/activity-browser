from importlib import reload
from loguru import logger

import pandas as pd
import pytest
import os
import time

import bw2data as bd
from PySide6 import QtCore, QtWidgets

from bw2data.tests import bw2test

from fixtures.bw_helpers import (
    register_parameter_setup,
    write_calculation_setup,
    write_functional_database,
    write_method,
)

# Per-test duration TSV / CI log lines (see tests/duration_logging.py).
pytest_plugins = ["duration_logging"]

os.environ["AB_SKIP_SETTINGS_ON_STARTUP"] = "1"
os.environ["AB_NO_SEARCHER"] = "1"
os.environ["AB_NO_FILE_LOG"] = "1"

_MAIN_WINDOW_READY = False


def _wait_for_loader(qapp, loader, timeout: float = 30.0) -> None:
    """Poll metadata loader with short sleeps instead of blocking 1s per iteration."""
    deadline = time.monotonic() + timeout
    while loader.secondary_status != "done" and time.monotonic() < deadline:
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
        time.sleep(0.05)
    if loader.secondary_status != "done":
        raise TimeoutError("Metadata loader did not finish in time.")


def _ensure_main_window() -> None:
    """Create the main window once per process; tests only reset lightweight state."""
    global _MAIN_WINDOW_READY
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    if _MAIN_WINDOW_READY:
        return

    reload(metadata)
    reload(app.main)
    reload(app)
    _MAIN_WINDOW_READY = True


def _delete_orphan_signal_widgets() -> None:
    """Drop top-level widgets that subscribe to ``app.signals`` but are not owned
    by the main window.

    Tests that build parameter / FU sections without ``qtbot.addWidget`` (or that
    leave deferred ``QTimer.singleShot(0)`` syncs pending) otherwise keep walking
    Brightway proxies after ``@bw2test`` tears the project down — UnknownObject on
    Windows, native abort on Linux/CPython 3.11.
    """
    from activity_browser.app.pages.activity_details.parameters_tab import ParametersTab
    from activity_browser.app.pages.calculation_setup.functional_unit_section import (
        FunctionalUnitSection,
    )
    from activity_browser.app.pages.parameters.parameterized_exchanges_section import (
        ParameterizedExchangesSection,
    )
    from activity_browser.app.pages.parameters.parameters_section import ParametersSection
    from activity_browser.ui import core

    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        return

    kinds = (
        ParameterizedExchangesSection,
        ParametersSection,
        ParametersTab,
        FunctionalUnitSection,
    )
    for widget in list(qapp.topLevelWidgets()):
        if isinstance(widget, kinds) and core.qt_is_valid(widget):
            widget.deleteLater()


def _reset_main_window(qtbot=None) -> None:
    """Close extra tabs/docks opened during a test; keep the main window alive."""
    from activity_browser import app
    from activity_browser.app import panes
    from activity_browser.app.pages.activity_details.activity_details import (
        ActivityDetailsPage,
    )
    from activity_browser.ui import core, widgets

    qapp = QtWidgets.QApplication.instance()
    mw = getattr(app, "main_window", None)
    if mw is None or not core.qt_is_valid(mw):
        return

    # Drop leftover Activity Details pages so delete signals cannot hit stale UI.
    for page in list(mw.findChildren(ActivityDetailsPage)):
        if core.qt_is_valid(page):
            page.deleteLater()

    # Products docks hold live Database proxies; leave them and later basic_project
    # / @bw2test swaps crash or raise UnknownObject during project.changed sync.
    for dock in list(mw.findChildren(widgets.ABDockWidget)):
        if not core.qt_is_valid(dock):
            continue
        inner = dock.widget()
        if isinstance(inner, panes.DatabaseProductsPane):
            mw.removeDockWidget(dock)
            dock.close()
            dock.deleteLater()

    central = mw.centralWidget()
    if central is not None and core.qt_is_valid(central):
        while central.count() > 1:
            index = central.count() - 1
            widget = central.widget(index)
            central.removeTab(index)
            if widget is not None and core.qt_is_valid(widget):
                widget.deleteLater()

    _delete_orphan_signal_widgets()

    if qapp is not None:
        qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)


@pytest.fixture(autouse=True)
def _sync_metadata_singleton():
    """Tests that replace MetaDataStore._instance must not desync app.metadata."""
    import sys

    yield

    app_module = sys.modules.get("activity_browser.app")
    if app_module is None:
        return

    from activity_browser.bwutils.metadata.metadata import MetaDataStore

    MetaDataStore._instance = app_module.metadata


@pytest.fixture(autouse=True)
def _cleanup_live_ui_after_bw_tests():
    """When the main window exists, reset UI after every test — not only those
    that requested the ``main_window`` fixture.

    Cheap ``basic_project`` tests still run after slower UI tests; without this,
    leftover docks/widgets sync into the next ``@bw2test`` project.
    """
    yield
    if not _MAIN_WINDOW_READY:
        return
    _reset_main_window()


@pytest.fixture
def no_exception_dialogs(monkeypatch):
    """Monkeypatch QMessageBox.critical to do nothing, to avoid blocking tests."""
    from qtpy import QtWidgets

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args, **kwargs: None)
    yield


@pytest.fixture
def main_window(qtbot, monkeypatch, no_exception_dialogs):
    """Return the main window of the application instance."""
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    _ensure_main_window()
    metadata.dataframe = pd.DataFrame()
    # show() is expensive on Windows offscreen; only raise if not already visible.
    if not app.main_window.isVisible():
        app.main_window.show()

    yield app.main_window

    _reset_main_window(qtbot)


@pytest.fixture
@bw2test
def basic_database(qapp, main_window):
    """``basic`` DB with main window + MetaDataStore loaded.

    Prefer :func:`basic_project` unless the test needs UI pages, metadata rows,
    or a loaded secondary metadata pass. This fixture is much slower per test.
    """
    from activity_browser.app import metadata
    from fixtures.basic import CALCULATION_SETUP, DATABASE, METHOD

    qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)
    if metadata.loader.secondary_status != "done":
        _wait_for_loader(qapp, metadata.loader)

    db = write_functional_database("basic", DATABASE, process=False, mark_dirty=True)
    write_method("basic_method", METHOD, process=False)
    write_calculation_setup("basic_calculation_setup", CALCULATION_SETUP)

    _wait_for_loader(qapp, metadata.loader)
    yield db


@pytest.fixture
@bw2test
def mc_project():
    """
    Minimal functional_sqlite project for Monte Carlo uncertainty tests.

    Yields the calculation setup name. Does not load the Activity Browser UI.
    """
    from fixtures.monte_carlo import (
        CALCULATION_SETUP,
        CALCULATION_SETUP_NAME,
        DATABASE,
        METHOD,
        METHOD_NAME,
    )

    write_functional_database("mc", DATABASE, process=True)
    write_method(METHOD_NAME, METHOD, process=True)
    write_calculation_setup(CALCULATION_SETUP_NAME, CALCULATION_SETUP)
    yield CALCULATION_SETUP_NAME


@pytest.fixture(scope="module")
@bw2test
def lcia_overview_project():
    """LCIA overview DB sized for current consumers (1×1 / 3×3), once per module.

    Full 10×10 fixture data remains available via ``fixtures.lcia_overview`` for
    local/scripts use; CI tests only need the small setups.
    """
    from fixtures.lcia_overview import (
        CALCULATION_SETUPS,
        DATABASE_NAME,
        build_database,
        build_methods,
    )

    write_functional_database(
        DATABASE_NAME, build_database(n_products=3), process=True
    )
    for method_key, cfs in build_methods(n_methods=3).items():
        write_method(method_key, cfs, process=True)
    for cs_name in ("lcia_1x1", "lcia_3x3", "lcia_3x3_neg"):
        write_calculation_setup(cs_name, CALCULATION_SETUPS[cs_name])
    yield DATABASE_NAME


def _write_basic_project_data():
    from fixtures.basic import CALCULATION_SETUP, DATABASE, METHOD

    db = write_functional_database("basic", DATABASE, process=True, mark_dirty=False)
    write_method("basic_method", METHOD, process=True)
    write_calculation_setup("basic_calculation_setup", CALCULATION_SETUP)
    return db


@pytest.fixture
@bw2test
def basic_project():
    """``basic`` DB + method + CS without main_window / metadata load.

    Prefer this over ``basic_database`` for Brightway / action / MLCA tests that
    do not need Qt pages or MetaDataStore rows. Keeps per-test ``@bw2test``
    isolation without the metadata-wait tax.

    Process synchronously and do not mark dirty: once any earlier test has created
    ``main_window``, a dirty write triggers MetaDataStore reload work and defeats
    this fixture.
    """
    yield _write_basic_project_data()


@pytest.fixture(scope="module")
@bw2test
def basic_project_readonly():
    """Module-scoped ``basic`` project for read-only tests only (ADR-0014).

    Do not mutate databases, methods, calculation setups, or parameters in tests
    that use this fixture — use :func:`basic_project` instead.
    """
    yield _write_basic_project_data()


@pytest.fixture
@bw2test
def mc_project_with_parameters():
    """
    Like ``mc_project`` but with uncertain parameter ``bio_amount`` on the main biosphere exchange.
    """
    from fixtures.monte_carlo import (
        CALCULATION_SETUP,
        CALCULATION_SETUP_NAME,
        DATABASE_NAME,
        DATABASE_WITH_PARAMETER_FORMULA,
        METHOD,
        METHOD_NAME,
        PARAMETER_SETUP,
    )

    write_functional_database("mc", DATABASE_WITH_PARAMETER_FORMULA, process=True)
    register_parameter_setup(DATABASE_NAME, PARAMETER_SETUP)
    write_method(METHOD_NAME, METHOD, process=True)
    write_calculation_setup(CALCULATION_SETUP_NAME, CALCULATION_SETUP)
    yield CALCULATION_SETUP_NAME

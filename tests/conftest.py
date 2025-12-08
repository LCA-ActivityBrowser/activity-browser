from copy import deepcopy
from importlib import reload

import pandas as pd
import pytest
import os

import bw2data as bd
from PySide6 import QtCore

import bw_functional as bf
from bw2data.tests import bw2test

os.environ["AB_SKIP_SETTINGS_ON_STARTUP"] = "1"


@pytest.fixture
def no_exception_dialogs(monkeypatch):
    """Monkeypatch QMessageBox.critical to do nothing, to avoid blocking tests."""
    from qtpy import QtWidgets

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args, **kwargs: None)
    yield
    # No need to undo the monkeypatch, pytest does it automatically


@pytest.fixture
def main_window(qtbot, monkeypatch, no_exception_dialogs):
    """Return the main window of the application instance."""
    from activity_browser import app
    from activity_browser.bwutils.metadata import metadata

    # Reload modules to ensure a clean state for each test
    reload(metadata)
    reload(app.main)
    reload(app)
    metadata.df = pd.DataFrame()

    app.main_window.show()

    yield main_window

    app.main_window.deleteLater()

    qtbot.wait(10)

@pytest.fixture
@bw2test
def basic_database(qapp, main_window):
    import time
    from activity_browser.app import metadata
    from fixtures.basic import DATABASE, METHOD, CALCULATION_SETUP

    qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents)

    db = bf.FunctionalSQLiteDatabase("basic")
    db.write(deepcopy(DATABASE), process=False)
    db.metadata["dirty"] = True
    bd.databases.flush()

    mthd = bd.Method(("basic_method",))
    mthd.register(unit="kilogram", num_cfs=1)
    mthd.write(deepcopy(METHOD), process=False)

    bd.calculation_setups["basic_calculation_setup"] = CALCULATION_SETUP
    bd.calculation_setups.flush()

    while metadata.loader.secondary_status != "done":
        time.sleep(1)

    return db


from copy import deepcopy

import pytest

import PySide6
from qtpy import QtCore, QtGui, QtWidgets, QT_API

import bw2data as bd
import bw_functional as bf
from bw2data.tests import bw2test

import activity_browser
from activity_browser import application
from activity_browser.signals import ABSignals
from activity_browser.ui.widgets import MainWindow, CentralTabWidget
from activity_browser.layouts import pages


@pytest.fixture()
def main_window(qtbot):
    """Return the main window of the application instance."""
    main_window = MainWindow()
    central_widget = CentralTabWidget(main_window)

    qtbot.addWidget(main_window)
    setattr(application, "main_window", main_window)

    central_widget.addTab(pages.WelcomePage(), "Welcome")
    central_widget.addTab(pages.ParametersPage(), "Parameters")

    main_window.setCentralWidget(central_widget)
    main_window.show()

    yield main_window

    # main_window.close()
    main_window.deleteLater()
    qtbot.wait(10)

@pytest.fixture
@bw2test
def basic_database(main_window):
    from fixtures.basic import DATABASE, METHOD, CALCULATION_SETUP

    db = bf.FunctionalSQLiteDatabase("basic")
    db.write(deepcopy(DATABASE), process=False)
    db.metadata["dirty"] = True
    bd.databases.flush()

    mthd = bd.Method(("basic_method",))
    mthd.register(unit="kilogram", num_cfs=1)
    mthd.write(deepcopy(METHOD), process=False)

    bd.calculation_setups["basic_calculation_setup"] = CALCULATION_SETUP
    bd.calculation_setups.flush()

    return db


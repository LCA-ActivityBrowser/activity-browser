from copy import deepcopy

import pytest

import bw2data as bd
import bw_functional as bf
from bw2data.tests import bw2test

from activity_browser import application, signals
from activity_browser.ui.widgets import MainWindow, CentralTabWidget
from activity_browser.layouts import pages



@pytest.fixture(scope="session")
def application_instance():
    """Initialize the application and yield it. Cleanup the 'test' project
    after session is complete.
    """
    application.main_window = MainWindow()

    central_widget = CentralTabWidget(application.main_window)
    central_widget.addTab(pages.WelcomePage(), "Welcome")
    central_widget.addTab(pages.ParametersPage(), "Parameters")

    application.main_window.setCentralWidget(central_widget)
    application.show()

    yield application

    application.close()

@pytest.fixture
@bw2test
def clean_project(application_instance):
    return
    # signals.project.changed.emit(bd.projects.dataset, bd.projects.dataset)

@pytest.fixture
def basic_database(clean_project):
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


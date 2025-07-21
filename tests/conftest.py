# -*- coding: utf-8 -*-
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from bw2data import projects, config
import bw2io as bi
import pytest

from activity_browser import application
from activity_browser.ui.widgets import MainWindow


def create_temp_dirs(temp_dir: Optional[Path] = None):
    """
    Create temporary directories for testing
    """
    temp_dir = temp_dir or Path(tempfile.mkdtemp())
    dir_base_data = temp_dir / "data"
    dir_base_data.mkdir(parents=True, exist_ok=True)
    dir_base_logs = temp_dir / "logs"
    dir_base_logs.mkdir(parents=True, exist_ok=True)
    return dir_base_data, dir_base_logs


@pytest.fixture(scope="session")
def ab_app():
    """Initialize the application and yield it. Cleanup the 'test' project
    after session is complete.
    """
    print("check")
    from activity_browser.ui.widgets import MainWindow, CentralTabWidget
    from activity_browser.layouts import panes, pages

    dir_base_data, dir_base_logs = create_temp_dirs()
    projects.change_base_directories(dir_base_data, dir_base_logs)

    bi.restore_project_directory(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "pytest_base.gz"),
        "default",
        overwrite_existing=True,
    )

    application.main_window = MainWindow()
    application.main_window.setPanes([panes.DatabasesPane, panes.ImpactCategoriesPane, panes.CalculationSetupsPane])

    central_widget = CentralTabWidget(application.main_window)
    central_widget.addTab(pages.WelcomePage(), "Welcome")
    central_widget.addTab(pages.ParametersPage(), "Parameters")

    application.main_window.setCentralWidget(central_widget)
    application.main_window.show()

    projects.set_current("default")

    yield application
    application.close()


@pytest.fixture()
def bw2test():
    """Similar to `bw2test` from bw2data.tests, but makes use of pytest
    fixture setup/teardown mechanics.

    Allows tests to be performed in a perfectly clean project instead
    of the test project.
    """
    config.dont_warn = True
    config.is_test = True
    config.cache = {}
    current_data_dir = projects._base_data_dir
    current_log_dir = projects._base_logs_dir
    tempdir = Path(tempfile.mkdtemp())
    dir_base_data, dir_base_logs = create_temp_dirs(tempdir)
    projects.change_base_directories(dir_base_data, dir_base_logs)

    yield tempdir

    projects.change_base_directories(current_data_dir, current_log_dir)
    # Make the jump back to the pytest_project if it exists
    if "pytest_project" in projects:
        projects.set_current("pytest_project", update=False)
    shutil.rmtree(tempdir)

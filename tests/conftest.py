# -*- coding: utf-8 -*-
import shutil
import os

import brightway2 as bw
import bw2io as bi
import pytest

from activity_browser import application, MainWindow, project_controller


@pytest.fixture(scope='session')
def ab_app():
    """ Initialize the application and yield it. Cleanup the 'test' project
    after session is complete.
    """
    bw.projects._use_temp_directory()
    bi.restore_project_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pytest_base.gz"), "default", overwrite_existing=True)

    application.main_window = MainWindow(application)
    application.show()
    project_controller.set_current("default")
    yield application
    application.close()


@pytest.fixture()
def bw2test():
    """ Similar to `bw2test` from bw2data.tests, but makes use of pytest
    fixture setup/teardown mechanics.

    Allows tests to be performed in a perfectly clean project instead
    of the test project.
    """
    bw.config.dont_warn = True
    bw.config.is_test = True
    bw.config.cache = {}
    tempdir = bw.projects._use_temp_directory()
    yield tempdir
    bw.projects._restore_orig_directory()
    # Make the jump back to the pytest_project if it exists
    if "pytest_project" in bw.projects:
        bw.projects.set_current("pytest_project", update=False)
    shutil.rmtree(tempdir)

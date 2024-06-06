# -*- coding: utf-8 -*-
import shutil
import os

import bw2data as bd
import bw2io as bi
import pytest

from activity_browser import application, MainWindow


@pytest.fixture(scope='session')
def ab_app():
    """ Initialize the application and yield it. Cleanup the 'test' project
    after session is complete.
    """
    bd.projects._use_temp_directory()
    bi.restore_project_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pytest_base.gz"), "default", overwrite_existing=True)

    application.main_window = MainWindow(application)
    application.show()
    bd.projects.set_current("default")
    yield application
    application.close()


@pytest.fixture()
def bw2test():
    """ Similar to `bw2test` from bw2data.tests, but makes use of pytest
    fixture setup/teardown mechanics.

    Allows tests to be performed in a perfectly clean project instead
    of the test project.
    """
    bd.config.dont_warn = True
    bd.config.is_test = True
    bd.config.cache = {}
    tempdir = bd.projects._use_temp_directory()
    yield tempdir
    bd.projects._restore_orig_directory()
    # Make the jump back to the pytest_project if it exists
    if "pytest_project" in bd.projects:
        bd.projects.set_current("pytest_project", update=False)
    shutil.rmtree(tempdir)

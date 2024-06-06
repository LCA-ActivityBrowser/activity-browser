# -*- coding: utf-8 -*-
import shutil

from bw2data.project import projects
from bw2data.configuration import config

import pytest

from activity_browser import Application


@pytest.fixture(scope='session')
def ab_application():
    """ Initialize the application and yield it. Cleanup the 'test' project
    after session is complete.
    """
    app = Application()
    yield app
    # Explicitly close the window
    app.close()
    # Explicitly close the connection to all the databases for the pytest_project
    if projects.current == "pytest_project":
        for _, db in config.sqlite3_databases:
            if not db._database.is_closed():
                db._database.close()
    if 'pytest_project' in projects:
        projects.delete_project('pytest_project', delete_dir=True)
    # finally, perform a cleanup of any remnants, mostly for local testing
    projects.purge_deleted_directories()


@pytest.fixture()
def ab_app(qtbot, ab_application):
    """ Function-level fixture which returns the session-level application.
    This is the actual fixture to be used in tests.
    """
    ab_application.show()
    return ab_application


@pytest.fixture()
def bw2test():
    """ Similar to `bw2test` from bw2data.tests, but makes use of pytest
    fixture setup/teardown mechanics.

    Allows tests to be performed in a perfectly clean project instead
    of the test project.
    """
    config.dont_warn = True
    config.is_test = True
    config.cache = {}
    tempdir = projects._use_temp_directory()
    yield tempdir
    projects._restore_orig_directory()
    # Make the jump back to the pytest_project if it exists
    if "pytest_project" in projects:
        projects.set_current("pytest_project", update=False)
    shutil.rmtree(tempdir)

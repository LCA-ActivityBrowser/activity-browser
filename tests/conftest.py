# -*- coding: utf-8 -*-
import pytest

import brightway2 as bw
from activity_browser import Application


@pytest.fixture(scope='session')
def ab_application():
    app = Application()
    yield app
    if 'pytest_project' in bw.projects:
        bw.projects.delete_project('pytest_project', delete_dir=True)


@pytest.fixture()
def ab_app(qtbot, ab_application):
    ab_application.show()
    return ab_application

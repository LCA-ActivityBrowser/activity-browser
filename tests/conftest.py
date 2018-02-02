# -*- coding: utf-8 -*-
import pytest

import brightway2 as bw
from activity_browser import Application


@pytest.fixture(scope='session')
def ab_app():
    if 'pytest_project' in bw.projects:
        bw.projects.delete_project('pytest_project', delete_dir=True)
    application = Application()
    application.show()
    return application

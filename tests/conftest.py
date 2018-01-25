# -*- coding: utf-8 -*-
import time

import pytest

from activity_browser import Application


@pytest.fixture(scope='module')
def ab_app():
    application = Application()
    application.show()
    time.sleep(1)
    return application

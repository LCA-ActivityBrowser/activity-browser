# -*- coding: utf-8 -*-
from .info import __version__

import os

PACKAGE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

from .app import Application, run_activity_browser

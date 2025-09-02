from peewee import *
from peewee import _ConnectionState

import threading

from activity_browser.mod.patching import patch_superclass, patched
from activity_browser.ui.threading import thread_local


@patch_superclass
class _ConnectionLocal(_ConnectionState, threading.local):

    def __init__(self, *args, **kwargs):
        patched[_ConnectionLocal]["__init__"](self, *args, **kwargs)

        if not hasattr(thread_local, 'peewee_connections'):
            thread_local.peewee_connections = []

        thread_local.peewee_connections.append(self)

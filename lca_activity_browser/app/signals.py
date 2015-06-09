# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from eight import *

from PyQt4 import QtCore


class Signals(QtCore.QObject):
    new_activity = QtCore.pyqtSignal(str)
    activity_selected = QtCore.pyqtSignal(tuple)
    # Activity key, field, new value
    activity_modified = QtCore.pyqtSignal(tuple, str, object)
    copy_activity = QtCore.pyqtSignal(tuple)
    open_activity_tab = QtCore.pyqtSignal(str, tuple)

    exchanges_output_modified = QtCore.pyqtSignal(list, tuple)
    exchanges_deleted = QtCore.pyqtSignal(list)

    calculation_setup_changed = QtCore.pyqtSignal()
    calculation_setup_selected = QtCore.pyqtSignal(str)

    database_selected = QtCore.pyqtSignal(str)
    databases_changed = QtCore.pyqtSignal()
    database_changed = QtCore.pyqtSignal(str)

    lca_calculation = QtCore.pyqtSignal(str)

    method_selected = QtCore.pyqtSignal(tuple)

    project_selected = QtCore.pyqtSignal(str)


signals = Signals()

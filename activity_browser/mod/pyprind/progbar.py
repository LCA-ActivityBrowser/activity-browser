from pyprind.progbar import *
from activity_browser.mod.patching import patch_superclass, patched
from activity_browser.ui.threading import thread_local

from qtpy.QtCore import QObject, SignalInstance, Signal

@patch_superclass
class Progbar(ProgBar):

    def _print(self, force_flush=False):
        patched[Progbar]["_print"](self, force_flush)
        try:
            thread_local.progress_slot(int(self._calc_percent()), self.title)
            qt_pyprind.updated.emit(self.title, self._calc_percent())
        except AttributeError:
            pass


class QtPyprind(QObject):
    updated: SignalInstance = Signal(str, float)


qt_pyprind = QtPyprind()


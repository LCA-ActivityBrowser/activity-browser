from pyprind.progbar import *
from activity_browser.mod.patching import patch_superclass, patched
from activity_browser.ui.threading import thread_local


@patch_superclass
class Progbar(ProgBar):

    def _print(self, force_flush=False):
        patched[Progbar]["_print"](self, force_flush)
        try:
            thread_local.progress_slot(int(self._calc_percent()), self.title)
        except AttributeError:
            pass



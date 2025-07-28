from tqdm.std import *
from activity_browser.mod.patching import patch_attribute, patched
from qtpy.QtCore import QObject, SignalInstance, Signal


@patch_attribute(tqdm, "update")
def update(self, n=1):
    patched[tqdm]["update"](self, n)
    try:
        qt_tqdm.updated.emit(int(self.n/self.total * 100), self.desc)
    except (TypeError, ZeroDivisionError):
        # Handle case where total is None or zero
        pass


@patch_attribute(tqdm, "close")
def close(self):
    patched[tqdm]["close"](self)
    qt_tqdm.updated.emit(100, self.desc)


class QtTqdm(QObject):
    updated: SignalInstance = Signal(int, str)


qt_tqdm = QtTqdm()

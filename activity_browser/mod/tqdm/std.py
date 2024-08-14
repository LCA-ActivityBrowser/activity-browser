from tqdm.std import *
from activity_browser.mod.patching import patch_attribute, patched
from PySide2.QtCore import QObject, SignalInstance, Signal


@patch_attribute(tqdm, "update")
def update(self, n=1):
    patched[tqdm]["update"](self, n)

    qt_tqdm.updated.emit(self.desc, self.n/self.total * 100)


class QtTqdm(QObject):
    updated: SignalInstance = Signal(str, float)


qt_tqdm = QtTqdm()

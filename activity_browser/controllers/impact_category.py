from bw2data import methods
from PySide2.QtCore import QObject, Signal, SignalInstance

import activity_browser.bwutils.data as ABData
from activity_browser import application
from .base import VirtualDatapoint


class VirtualMethod(VirtualDatapoint):
    changed: SignalInstance = Signal(ABData.ABMethod)
    deleted: SignalInstance = Signal(ABData.ABMethod)

    data_point: ABData.ABMethod

    @property
    def name(self) -> tuple:
        return self.data_point.name if self.data_point else (None,)


class ICController(QObject):
    metadata_changed: SignalInstance = Signal()

    _dummy: VirtualMethod = VirtualMethod()
    _cache: dict = methods.data.copy()

    # mimicking the iterable behaviour of bw2data.meta.methods
    def __getitem__(self, item) -> dict:
        return methods[item]

    def __iter__(self) -> dict:
        for method in methods:
            yield method

    def __len__(self):
        return len(methods)

    def __delitem__(self, name) -> None:
        ABData.ABMethod(name).deregister()

    def random(self):
        return methods.random()

    def get_virtual(self, method: ABData.ABMethod, create=False) -> VirtualMethod:
        virtual_method = self.findChild(VirtualMethod, str(method.name))

        if virtual_method: return virtual_method
        elif create: return VirtualMethod(method.name, method, self)
        else: return self._dummy

    def changed(self, method: ABData.ABMethod):
        virtual_method = self.findChild(VirtualMethod, str(method.name))
        if not virtual_method: return
        virtual_method.changed.emit(method)

    def deleted(self, method: ABData.ABMethod):
        virtual_method = self.findChild(VirtualMethod, str(method.name))
        if not virtual_method: return
        virtual_method.deleted.emit(method)

    def get(self, ic_tuple: tuple) -> ABData.ABMethod:
        return ABData.ABMethod(ic_tuple)

    def sync(self):
        if self._cache == methods.data: return

        self._cache = methods.data.copy
        self.metadata_changed.emit()


ic_controller = ICController(application)

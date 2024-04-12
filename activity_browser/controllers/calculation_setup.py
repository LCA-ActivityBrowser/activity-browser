from bw2data import calculation_setups
from PySide2.QtCore import QObject, Signal, SignalInstance

import activity_browser.bwutils.data as ABData
from activity_browser import application
from .base import VirtualDatapoint


class VirtualCalculationSetup(VirtualDatapoint):
    changed: SignalInstance = Signal(ABData.ABCalculationSetup)
    deleted: SignalInstance = Signal(ABData.ABCalculationSetup)

    data_point: ABData.ABCalculationSetup


class CSController(QObject):
    _dummy = VirtualCalculationSetup()

    # mimicking the iterable behaviour of bw2data.meta.calculation_setups
    def __getitem__(self, item) -> dict:
        return ABData.ABCalculationSetup(item, **calculation_setups[item])

    def __setitem__(self, key, value):
        calculation_setups[key] = dict(value)

        virtual_cs = self.findChild(VirtualCalculationSetup, key)
        if not virtual_cs: return
        virtual_cs.changed.emit(self[key])

    def __delitem__(self, key):
        cs = self[key]

        del calculation_setups[key]

        virtual_cs = self.findChild(VirtualCalculationSetup, key)
        if not virtual_cs: return
        virtual_cs.changed.emit(cs)
        virtual_cs.deleted.emit(cs)

    def __iter__(self) -> dict:
        for name in calculation_setups:
            yield name

    def keys(self):
        for key in calculation_setups.keys():
            yield key

    def items(self):
        for key in calculation_setups:
            yield key, self[key]

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError as e:
            if default: return default
            raise e

    def get_virtual(self, cs: ABData.ABCalculationSetup, create=False):
        virtual_database = self.findChild(VirtualCalculationSetup, cs.name)

        if virtual_database: return virtual_database
        elif create: return VirtualCalculationSetup(cs.name, cs, self)
        else: return self._dummy


cs_controller = CSController(application)

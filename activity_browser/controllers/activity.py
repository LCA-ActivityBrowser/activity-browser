from bw2data import get_activity
from PySide2.QtCore import QObject, Signal, SignalInstance

import activity_browser.bwutils.data as ABData
from activity_browser import application
from .base import VirtualDatapoint


class VirtualActivity(VirtualDatapoint):
    changed: SignalInstance = Signal(ABData.ABActivity)
    deleted: SignalInstance = Signal(ABData.ABActivity)

    data_point: ABData.ABActivity

    @property
    def key(self):
        return self.data_point.key if self.data_point else (None, None)


class ActivityController(QObject):
    _dummy = VirtualActivity()

    def get_virtual(self, activity: ABData.ABActivity, create=False):
        virtual_activity = self.findChild(VirtualActivity, str(activity.key))

        if virtual_activity: return virtual_activity
        elif create: return VirtualActivity(activity.key, activity, self)
        else: return self._dummy

    def changed(self, activity: ABData.ABActivity):
        virtual_activity = self.findChild(VirtualActivity, str(activity.key))
        if not virtual_activity: return
        virtual_activity.changed.emit(activity)

    def deleted(self, activity: ABData.ABActivity):
        virtual_activity = self.findChild(VirtualActivity, str(activity.key))
        if not virtual_activity: return
        virtual_activity.deleted.emit(activity)

    def get(self, key: tuple) -> ABData.ABActivity:
        activity = get_activity(key)
        return ABData.ABActivity.from_activity(activity)


activity_controller = ActivityController(application)
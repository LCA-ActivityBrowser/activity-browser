from bw2data.backends.peewee import Activity
from bw2data import get_activity
from PySide2.QtCore import QObject, Signal, SignalInstance

from activity_browser import signals, application
from activity_browser.bwutils import AB_metadata


class ABActivity(Activity):
    @classmethod
    def from_activity(cls, activity: Activity) -> "ABActivity":
        return cls(activity._document)

    def save(self) -> None:
        super().save()
        activity_controller.activity_changed.emit(self)

    def delete(self) -> None:
        super().delete()
        activity_controller.activity_deleted.emit(self)

        # legacy
        AB_metadata.update_metadata(self.key)
        signals.database_changed.emit(self["database"])
        signals.databases_changed.emit()
        signals.calculation_setup_changed.emit()

    def copy(self, code=None, **kwargs) -> "ABActivity":
        activity = super().copy(code, **kwargs)
        activity_controller.new_activity.emit(activity)

        # legacy
        AB_metadata.update_metadata(activity.key)
        signals.database_changed.emit(self["database"])
        signals.databases_changed.emit()

        return ABActivity.from_activity(activity)


class ActivityController(QObject):
    activity_changed: SignalInstance = Signal(ABActivity)
    activity_deleted: SignalInstance = Signal(ABActivity)
    new_activity: SignalInstance = Signal(ABActivity)

    def get(self, key: tuple) -> ABActivity:
        activity = get_activity(key)
        return ABActivity.from_activity(activity)


activity_controller = ActivityController(application)

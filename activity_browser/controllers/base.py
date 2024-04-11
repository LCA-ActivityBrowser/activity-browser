
from PySide2.QtCore import QObject, SignalInstance


class VirtualDatapoint(QObject):
    changed: SignalInstance
    deleted: SignalInstance

    def __init__(self, identifier=None, data_point=None, parent=None):
        super().__init__(parent)
        self.setObjectName(str(identifier))

        self.data_point = data_point

        self.connected = 0

    def connectNotify(self, signal):
        signal_name = signal.name().data().decode()
        if signal_name == 'changed' or signal_name == 'deleted': self.connected += 1

    def disconnectNotify(self, signal):
        signal_name = signal.name().data().decode()
        if signal_name == 'changed' or signal_name == 'deleted': self.connected -= 1

        if self.connected == 0:
            self.setParent(None)
            self.deleteLater()

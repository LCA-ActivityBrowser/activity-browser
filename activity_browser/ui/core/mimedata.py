import pickle

from qtpy import QtCore


class ABMimeData(QtCore.QMimeData):

    def setPickleData(self, mimeType, data):
        self.setData(mimeType, pickle.dumps(data))

    def retrievePickleData(self, mimeType):
        data = self.retrieveData(mimeType, bytes)

        if data is None:
            return

        return pickle.loads(data)

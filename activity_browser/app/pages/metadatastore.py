from qtpy import QtWidgets

from activity_browser.ui import widgets, delegates
from activity_browser.app import metadata, signals


class MetaDataStorePage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MetaDataStorePage")

        self.model = MDSModel(self, metadata.dataframe)
        self.view = MDSView(self)
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        signals.metadata.synced.connect(self.sync)

    def sync(self):
        self.model.setDataFrame(metadata.dataframe)

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)


class MDSView(widgets.ABTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(delegates.StringDelegate(self))

class MDSItem(widgets.ABDataItem):
    pass

class MDSModel(widgets.ABItemModel):
    pass

from qtpy import QtWidgets

from activity_browser.ui import widgets
from activity_browser.bwutils import AB_metadata


class MetaDataStorePage(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MetaDataStorePage")

        self.model = MDSModel(self, AB_metadata.dataframe)
        self.view = MDSView(self)
        self.view.setModel(self.model)

        self.build_layout()
        self.connect_signals()

    def connect_signals(self):
        AB_metadata.synced.connect(self.sync)

    def sync(self):
        self.model.setDataFrame(AB_metadata.dataframe)

    def build_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)


class MDSView(widgets.ABTreeView):
    pass


class MDSItem(widgets.ABDataItem):
    pass

class MDSModel(widgets.ABItemModel):
    pass

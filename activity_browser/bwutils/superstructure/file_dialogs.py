from PySide2 import QtWidgets, QtCore
import pandas as pd


from ...ui.icons import qicons
"""
    The basic premise of this module is to contain a series of different popup menus that will allow the user
    to make a choice that can help them to resolve an issue with their use of the AB.
    
    To this end there are two supporting classes (for a table) and the actual Popup.
    
    The first use case is with scenario files (hence the current location of this module in 
    bwutils.superstructure
    
"""


class ProblemDataModel(QtCore.QAbstractTableModel):
    updated = QtCore.Signal()
    def __init__(self):
        super().__init__()
        self.columns = None
        self._dataframe = None

    def rowCount(self, *args, **kwargs):
        return self._dataframe.shape[0]

    def columnCount(self, *args, **kwargs):
        return self._dataframe.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        v = None
        if role == QtCore.Qt.DisplayRole:
            v = self._dataframe.iloc[index.row(), index.column()]
            if isinstance(v, tuple):
                v = str(v)
        return v

    def sync(self, *args, **kwargs) -> None:
        assert('dataframe' in kwargs and 'columns in kwargs')
        self.columns = kwargs['columns']
        data = kwargs['dataframe']
        self._dataframe = pd.DataFrame(data,columns=self.columns)
        self.updated.emit()


class ProblemDataFrame(QtWidgets.QTableView):
    def __init__(self, parent: QtWidgets.QWidget, dataframe: pd.DataFrame, cols: pd.Index):
        super().__init__(parent)
        self.model = ProblemDataModel()
        self.model.updated.connect(self.update_proxy)
        self.model.sync(dataframe=dataframe, columns=cols)
#        self.setSizePolicy(QtWidgets.QSizePolicy(
#            QtWidgets.QSizePolicy.Preferred,
#            QtWidgets.QSizePolicy.Maximum
#        ))

    def update(self, dataframe:pd.DataFrame, cols: pd.Index):
        self.model.sync(dataframe=dataframe, columns=cols)

    def update_proxy(self):
        self.proxy = QtCore.QIdentityProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.setModel(self.proxy)
class ABPopup(QtWidgets.QDialog):
    """
    Holds AB defined message boxes to enable a more consistent popup message structure
    """
    def __init__(self):
        super().__init__()
        self.data_frame = ProblemDataFrame(self, pd.DataFrame({}), pd.Index([]))
        self.data_frame.setVisible(False)
        self._dataframe = None
        self._flags = None
        self.message = None
        self.topic = None
        self.save = None
        self.label = None
        self.buttons = QtWidgets.QHBoxLayout()
        self.button1 = None
        self.button2 = None
        self.layout = QtWidgets.QVBoxLayout()
        self.check_box = QtWidgets.QCheckBox()
        self.check_box.setVisible(False)
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.check_box)
        self.setSizePolicy(QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Maximum
        ))

    def dataframe(self, data: pd.DataFrame, columns: list = None):
        dataframe = data
        cols = pd.Index(columns)
        dataframe = dataframe.loc[:, columns]
        dataframe.index = dataframe.index.astype(str)
        self.data_frame.update(dataframe, cols)
        self.data_frame.setHidden(False)
        self.updateGeometry()

    def save_options(self, msg: str = None):
        self.check_box.setVisible(True)
        self.check_box.setTristate(True)
        self.check_box.setText("Excerpt")
        self.check_box.setToolTip("If left unchecked the entire file is written with an additional column indicating "
                             "the status of the exchange data in the scenario file.<br> Check to save a smaller "
                             "excerpt of the file, containing only those exchanges that failed."
                             )
        self.check_box.setChecked(False)
        self.updateGeometry()


    def dataframe_to_file(self, dataframe: pd.DataFrame, flags: pd.Index=None) -> None:
        self._dataframe = dataframe
        self._flags = flags

    def save_dataframe(self):
        if self.check_box.isChecked():
            self._dataframe = self._dataframe.loc[self._flags]
        elif self._dataframe is not None:
            self._dataframe['Failed'] = [False for i in self._dataframe.index]
            self._dataframe.loc[self._flags, 'Failed'] = True
        # Else we're not actually intending on saving anything
        else:
            return True
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self, caption="Choose the location to save the dataframe",
            filter="All Files (*.*);; CSV (*.csv);; Excel (*.xlsx)",
        )
        if not filepath.strip():
            return False
        if filepath.endswith('.xlsx') or filepath.endswith('.xls'):
            self._dataframe.to_excel(filepath, index=False)
        else:
            self._dataframe.to_csv(filepath, index=False, sep=';')
        return True

    @QtCore.Slot(name='affirmative')
    def affirmative(self):
        if self.save_dataframe():
            self.accept()

    @QtCore.Slot(name='rejection')
    def rejection(self):
        self.reject()
    # TODO switch the buttons to the dialog buttons
    # TODO set a max_width to the windows

    @staticmethod
    def abQuestion(title, message, button1, button2):
        obj = ABPopup()
        obj.layout = QtWidgets.QVBoxLayout()
        obj.setWindowTitle(title)
        obj.label = QtWidgets.QLabel(message)
        obj.label.setWordWrap(True)
        obj.layout.addWidget(obj.label)
        obj.setWindowIcon(qicons.question)
        # add the interactive elements AND table
        obj.button1 = button1
        obj.button2 = button2
        obj.buttons.addWidget(obj.button1)
        obj.buttons.addWidget(obj.button2)
        obj.button_layout.addLayout(obj.buttons)
        obj.layout.addWidget(obj.data_frame)
        obj.layout.addWidget(obj.button_layout)

        obj.data_frame.setHidden(True)
        obj.button1.setDefault(True)
        obj.button1.clicked.connect(obj.affirmative)
        obj.button2.clicked.connect(obj.rejection)
        obj.setLayout(obj.layout)
        obj.updateGeometry()
        return obj

    @staticmethod
    def abWarning(title, message, button1, button2=None, default=1):
        obj = ABPopup()
        obj.layout = QtWidgets.QVBoxLayout()
        obj.setWindowTitle(title)
        obj.label = QtWidgets.QLabel(message)
        obj.label.setWordWrap(True)
        obj.layout.addWidget(obj.label)
        obj.setWindowIcon(qicons.warning)

        # add the interactive elements
        obj.button1 = button1
        obj.button2 = button2
        if button2:
            obj.buttons.addWidget(obj.button1)
            obj.buttons.addWidget(obj.button2)
        else:
            obj.buttons.addWidget(button1)
        if default == 1:
            obj.button1.setDefault(True)
        else:
            obj.button2.setDefault(True)
        obj.button_layout.addLayout(obj.buttons)
        obj.layout.addWidget(obj.data_frame)
        obj.layout.addLayout(obj.button_layout)

        obj.data_frame.setHidden(True)
        obj.button1.clicked.connect(obj.affirmative)
        obj.button2.clicked.connect(obj.rejection)
        obj.setLayout(obj.layout)
        obj.updateGeometry()
        return obj

# TODO try turning off random features
    @staticmethod
    def abCritical(title, message, button1, button2=None, default=1):
        obj = ABPopup()
        obj.layout = QtWidgets.QVBoxLayout()
        obj.setWindowTitle(title)
        obj.label = QtWidgets.QLabel(message)
        obj.label.setWordWrap(True)
        obj.layout.addWidget(obj.label)
#        obj.setWindowIcon(qicons.critical)

        # add the interactive elements
        obj.button1 = button1
        obj.button2 = button2
        if button2:
            obj.buttons.addWidget(button1)
            obj.buttons.addWidget(button2)
        else:
            obj.buttons.addWidget(button1)
        if default == 1:
            obj.button1.setDefault(True)
        else:
            obj.button2.setDefault(True)
        obj.button_layout.addLayout(obj.buttons)
        obj.layout.addWidget(obj.data_frame)
        obj.layout.addLayout(obj.button_layout)

        obj.data_frame.setHidden(True)
        obj.button1.clicked.connect(obj.affirmative)
        if button2 is not None:
            obj.button2.clicked.connect(obj.rejection)
        obj.setLayout(obj.layout)
        obj.updateGeometry()
        return obj

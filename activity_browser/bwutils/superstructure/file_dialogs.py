import pandas as pd
from qtpy import QtCore, QtWidgets

from ...ui.icons import qicons

"""
    The basic premise of this module is to contain a series of different popup menus that will allow the user
    to make a choice that can help them to resolve an issue with their use of the AB.
    
    To this end there are two small supporting classes (for a table) and the actual Popup.
    
    The first use case is with scenario files (hence the current location of this module in 
    bwutils.superstructure
    
"""


class ProblemDataModel(QtCore.QAbstractTableModel):
    """
    A simple table model for use in the ABPopup dialogs for error reporting.

    Intentionally coupled with the ABPopup class and not intended for use externally.

    """

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
            # if the data is a tuple force the conversion to strings
            if isinstance(v, tuple):
                v = str(v)
        return v

    def sync(self, *args, **kwargs) -> None:
        assert "dataframe" in kwargs and "columns in kwargs"
        self.columns = kwargs["columns"]
        data = kwargs["dataframe"]
        self._dataframe = pd.DataFrame(data, columns=self.columns)
        self.updated.emit()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.columns[section]


class ProblemDataFrame(QtWidgets.QTableView):
    """
    A simple view class coupled with the ABPopup class.

    Not intended for external use.
    """

    def __init__(
        self, parent: QtWidgets.QWidget, dataframe: pd.DataFrame, cols: pd.Index
    ):
        super().__init__(parent)
        self.model = ProblemDataModel()
        self.model.updated.connect(self.update_proxy)
        self.model.sync(dataframe=dataframe, columns=cols)

    def update(self, dataframe: pd.DataFrame, cols: pd.Index):
        self.model.sync(dataframe=dataframe, columns=cols)

    def update_proxy(self):
        self.proxy = QtCore.QIdentityProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.setModel(self.proxy)


class ABPopup(QtWidgets.QDialog):
    """
    Holds AB defined message boxes to enable a more consistent popup message structure for errors.

    Primarily concerned with the creation of errors for the purposes of scenario file imports.

    Contains a tightly coupled dataframe that is intended to hold a limited sample set for user guidance.
    Dataframe management is through the dataframe() method that takes the dataframe with the data of interest
    and the columns to be extract for the creation of the internal table

    Contains the option of saving the warning output to a file with the option of printing the data that
    generated the throwing of the popup, or the full file with the error causing entries highlighted



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
        self.setSizePolicy(
            QtWidgets.QSizePolicy(
                QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum
            )
        )

    def dataframe(self, data: pd.DataFrame, columns: list = None):
        """
        Handles the creation of the internal dataframe using just those columns provided

        Arguments
        ---------
        data: a dataframe with the exchanges/rows that generate the error
        columns: a list of columns to provide the dataframe with for the popup message
        """
        dataframe = data
        cols = pd.Index(columns)
        dataframe = dataframe.loc[:, columns]
        if not isinstance(dataframe.index, pd.MultiIndex):
            dataframe.index = dataframe.index.astype(str)
        self.data_frame.update(dataframe, cols)
        self.data_frame.setHidden(False)
        self.updateGeometry()

    def save_options(self):
        """
        Creates a checkbox for determining the format for saved files
        """
        self.check_box.setVisible(True)
        self.check_box.setTristate(False)
        self.check_box.setText("Excerpt")
        self.check_box.setToolTip(
            "If left unchecked the entire file is written with an additional column indicating "
            "the status of the exchange data in the scenario file.<br> Check to save a smaller "
            "excerpt of the file, containing only those exchanges that failed."
        )
        self.check_box.setChecked(False)
        self.updateGeometry()

    def dataframe_to_file(
        self, dataframe: pd.DataFrame, flags: pd.Index = None
    ) -> None:
        """
        Sets the class variables for determining those elements of the dataframe that contain error causing data

        Arguments
        ---------
        dataframe: the pandas dataframe with the full data from importing into the AB
        flags: the pandas row index indicating those rows with the data causing the error
        """
        self._dataframe = dataframe
        self._flags = flags

    def save_dataframe(self):
        """
        Saves the dataframe according to pre-specified conditions with the dataframe_to_file and save_options class
        methods
        """
        if self.check_box.isChecked():
            self._dataframe = self._dataframe.loc[self._flags]
        elif self._dataframe is not None:
            self._dataframe["Failed"] = [False for i in self._dataframe.index]
            self._dataframe.loc[self._flags, "Failed"] = True
        # Else we're not actually intending on saving anything
        else:
            return True
        filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent=self,
            caption="Choose the location to save the dataframe",
            filter="Excel (*.xlsx *.xls);; CSV (*.csv)",
        )
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        if filepath.endswith(".xlsx") or filepath.endswith(".xls"):
            self._dataframe.to_excel(filepath, index=False)
            QtWidgets.QApplication.restoreOverrideCursor()
            return True
        elif not filepath.endswith(".csv"):
            filepath += ".csv"
        self._dataframe.to_csv(filepath, index=False, sep=";")
        QtWidgets.QApplication.restoreOverrideCursor()
        return True

    @QtCore.Slot(name="affirmative")
    def affirmative(self):
        if self.save_dataframe():
            self.accept()

    @QtCore.Slot(name="rejection")
    def rejection(self):
        self.reject()

    # TODO set a max_width to the windows

    @staticmethod
    def abQuestion(title, message, button1, button2):
        """
        Creates an ABPopup object that contains a title message and multiple options

        Arguments
        ---------
        title: The Popup's title, should be relevant for the request to the user
        message: A detailed explanation providing why a response from the user is required, what is done
        according to the type of response and what the user should expect
        button1: a QPushButton instance MUST BE PROVIDED
        button2: a QPushButton instance MUST BE PROVIDED

        Returns
        -------
        An ABPopup instance that provides the basic format and dialog for the popup window.
        Further manipulation of the object and execution (via .exec_()) is performed upon instantiation
        """
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
        """
        Creates an ABPopup object that contains a title message and a user response for a raised warning

        Arguments
        ---------
        title: The Popup's title, should be relevant for the request to the user
        message: A detailed explanation providing why a response from the user is required, what is done
        according to the type of response and what the user should expect
        button1: a QPushButton instance MUST BE PROVIDED
        button2: a QPushButton instance OPTIONAL
        default: the default button to be used (default set to button1)

        Returns
        -------
        An ABPopup instance that provides the basic format and dialog for the popup window to provide a warning.
        Further manipulation of the object and execution (via .exec_()) is performed upon instantiation
        """
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

    @staticmethod
    def abCritical(title, message, button1, button2=None, default=1):
        """
        Creates an ABPopup object that contains a title message and a user response for a critical error

        Arguments
        ---------
        title: The Popup's title, should be relevant for the request to the user
        message: A detailed explanation providing why a response from the user is required, what is done
        according to the type of response and what the user should expect
        button1: a QPushButton instance MUST BE PROVIDED
        button2: a QPushButton instance OPTIONAL
        default: the default button to be used (default set to button1)

        Returns
        -------
        An ABPopup instance that provides the basic format and dialog for the popup window to provide a warning.
        Further manipulation of the object and execution (via .exec_()) is performed upon instantiation
        """
        obj = ABPopup()
        obj.layout = QtWidgets.QVBoxLayout()
        obj.setWindowTitle(title)
        obj.label = QtWidgets.QLabel(message)
        obj.label.setWordWrap(True)
        obj.layout.addWidget(obj.label)
        obj.setWindowIcon(qicons.critical)

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

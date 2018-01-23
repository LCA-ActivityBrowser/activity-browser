# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets

from .line_edit import SignalledLineEdit, SignalledPlainTextEdit


class DetailsGroupBox(QtWidgets.QGroupBox):
    def __init__(self, label, widget):
        super().__init__(label)
        self.widget = widget
        self.setCheckable(True)
        self.toggled.connect(self.showhide)
        self.setChecked(False)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(widget)
        self.setLayout(layout)
        if isinstance(self.widget, QtWidgets.QTableWidget):
            self.widget.itemChanged.connect(self.toggle_empty_table)

    def showhide(self):
        self.widget.setVisible(self.isChecked())

    def toggle_empty_table(self):
        self.setChecked(bool(self.widget.rowCount()))


class ActivityDataGrid(QtWidgets.QWidget):
    def __init__(self, parent=None, activity=None):
        super(ActivityDataGrid, self).__init__(parent)
        self.activity = activity

        self.grid = self.get_grid()
        self.setLayout(self.grid)
        # self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum))

        if activity:
            self.populate()

    def get_grid(self):
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(5)
        right_side = 10

        grid.addWidget(QtWidgets.QLabel('Database'), 1, 1)
        self.database = QtWidgets.QLabel('')
        grid.addWidget(self.database, 1, 2, 1, right_side)

        grid.addWidget(QtWidgets.QLabel('Activity'), 2, 1)
        self.name_box = SignalledLineEdit(
            key=getattr(self.activity, "key", None),
            field="name",
            parent=self,
        )
        self.name_box.setPlaceholderText("Activity name")
        grid.addWidget(self.name_box, 2, 2, 1, right_side)

        grid.addWidget(QtWidgets.QLabel('Location'), 3, 1)
        self.location_box = SignalledLineEdit(
            key=getattr(self.activity, "key", None),
            field="location",
            parent=self,
        )
        self.location_box.setPlaceholderText("ISO 2-letter code or custom name")
        grid.addWidget(self.location_box, 3, 2, 1, right_side)

        # grid.addWidget(QtWidgets.QLabel('Description'), 4, 1, 2, 1)
        self.comment_box = SignalledPlainTextEdit(
            key=getattr(self.activity, "key", None),
            field="comment",
            parent=self,
        )
        self.comment_groupbox = DetailsGroupBox(
            'Description', self.comment_box
        )
        self.comment_groupbox.setChecked(False)

        grid.addWidget(self.comment_groupbox, 4, 1, 2, right_side + 1)
        # grid.addWidget(self.comment_box, 4, 2, 2, right_side)

        # grid.addWidget(QtWidgets.QLabel('Unit'), 5, 1)
        # self.unit_box = SignalledLineEdit(
        #     key=getattr(self.activity, "key", None),
        #     field="unit",
        #     parent=self,
        # )
        # grid.addWidget(self.unit_box, 5, 2, 1, 3)

        grid.setAlignment(QtCore.Qt.AlignTop)

        return grid

    def populate(self, activity=None):
        if activity:
            self.activity = activity
        self.database.setText(self.activity['database'])
        self.name_box.setText(self.activity['name'])
        self.name_box._key = self.activity.key
        self.location_box.setText(self.activity.get('location', ''))
        self.location_box._key = self.activity.key
        self.comment_box.setPlainText(self.activity.get('comment', ''))
        # the <font> html-tag has no effect besides making the tooltip rich text
        # this is required for line breaks of long comments
        self.comment_groupbox.setToolTip(
            '<font>{}</font>'.format(self.comment_box.toPlainText())
        )
        # print("Commentbox Width/Height: {}/{}".format(self.comment_box.width(), self.comment_box.width()))
        self.comment_box._before = self.activity.get('comment', '')
        self.comment_box._key = self.activity.key
        self.comment_box.adjust_size()
        # print("Commentbox Width/Height: {}/{}".format(self.comment_box.width(), self.comment_box.height()))
        # print("Activity Grid Width/Height: {}/{}".format(self.width(), self.height()))
        # self.unit_box.setText(self.activity.get('unit', ''))
        # self.unit_box._key = self.activity.key

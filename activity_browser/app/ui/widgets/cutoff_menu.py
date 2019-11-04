# -*- coding: utf-8 -*-
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QSlider, \
    QLabel, QLineEdit, QPushButton
from PySide2.QtGui import QIntValidator, QDoubleValidator
from math import log10

from activity_browser.app.ui.style import vertical_line

class CutoffMenu(QWidget):
    def __init__(self, parent_widget, cutoff_value=0.01, limit_type="percent"):
        super(CutoffMenu, self).__init__()
        self.parent = parent_widget
        self.cutoff_value = cutoff_value
        self.limit_type = limit_type
        self.make_layout()
        self.connect_signals()

    def connect_signals(self):
        # Cut-off types
        self.cutoff_type_topx.clicked.connect(self.cutoff_type_topx_check)
        self.cutoff_type_relative.clicked.connect(self.cutoff_type_relative_check)
        self.cutoff_slider_lft_btn.clicked.connect(self.cutoff_increment_left_check)
        self.cutoff_slider_rght_btn.clicked.connect(self.cutoff_increment_right_check)

        # Cut-off log slider
        self.cutoff_slider_log_slider.valueChanged.connect(
            lambda: self.cutoff_slider_relative_check("sl"))
        self.cutoff_slider_line.textChanged.connect(
            lambda: self.cutoff_slider_relative_check("le"))
        # Cut-off slider
        self.cutoff_slider_slider.valueChanged.connect(
            lambda: self.cutoff_slider_topx_check("sl"))
        self.cutoff_slider_line.textChanged.connect(
            lambda: self.cutoff_slider_topx_check("le"))

    def update_plot_table(self):
        """Updates tables and plots in parent widget.
        Could also be implemented with signals/slots and
        a check for the specific parent (e.g. isinstance(receiver, self.parent))"""
        if self.parent.plot:
            self.parent.update_plot()
        if self.parent.table:
            self.parent.update_table()

    def cutoff_increment_left_check(self):
        """ Move the slider 1 increment when left button is clicked. """
        if self.cutoff_type_relative.isChecked():
            num = int(self.cutoff_slider_log_slider.value())
            self.cutoff_slider_log_slider.setValue(num + 1)
        else:
            num = int(self.cutoff_slider_slider.value())
            self.cutoff_slider_slider.setValue(num - 1)

    def cutoff_increment_right_check(self):
        """ Move the slider 1 increment when right button is clicked. """
        if self.cutoff_type_relative.isChecked():
            num = int(self.cutoff_slider_log_slider.value())
            self.cutoff_slider_log_slider.setValue(num - 1)
        else:
            num = int(self.cutoff_slider_slider.value())
            self.cutoff_slider_slider.setValue(num + 1)

    def cutoff_type_relative_check(self):
        """ Set cutoff to process that contribute #% or more. """
        self.cutoff_slider_slider.setVisible(False)
        self.cutoff_slider_log_slider.blockSignals(True)
        self.cutoff_slider_slider.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)
        self.cutoff_slider_unit.setText("%  of total")
        self.cutoff_slider_min.setText("100%")
        self.cutoff_slider_max.setText("0.001%")
        self.limit_type = "percent"
        self.cutoff_slider_log_slider.blockSignals(False)
        self.cutoff_slider_slider.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_slider_log_slider.setVisible(True)

    def cutoff_type_topx_check(self):
        """ Set cut-off to the top # of processes. """
        self.cutoff_slider_log_slider.setVisible(False)
        self.cutoff_slider_log_slider.blockSignals(True)
        self.cutoff_slider_slider.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)
        self.cutoff_slider_unit.setText(" top #")
        self.cutoff_slider_min.setText(str(self.cutoff_slider_slider.minimum()))
        self.cutoff_slider_max.setText(str(self.cutoff_slider_slider.maximum()))
        self.limit_type = "number"
        self.cutoff_slider_log_slider.blockSignals(False)
        self.cutoff_slider_slider.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)
        self.cutoff_slider_slider.setVisible(True)

    def cutoff_slider_relative_check(self, editor):
        """ With relative selected, change the values for plots and tables to reflect the slider/line-edit. """
        if self.cutoff_type_relative.isChecked():
            self.cutoff_validator = self.cutoff_validator_float
            self.cutoff_slider_line.setValidator(self.cutoff_validator)
            cutoff = float

            # If called by slider
            if editor == "sl":
                self.cutoff_slider_line.blockSignals(True)
                cutoff = abs(self.cutoff_slider_log_slider.logValue())
                self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_line.blockSignals(False)

            # if called by line edit
            elif editor == "le":
                self.cutoff_slider_log_slider.blockSignals(True)
                if self.cutoff_slider_line.text() == '-':
                    cutoff = 0.001
                    self.cutoff_slider_line.setText("0.001")
                elif self.cutoff_slider_line.text() == '':
                    cutoff = 0.001
                else:
                    cutoff = abs(float(self.cutoff_slider_line.text()))

                if cutoff > 100:
                    cutoff = 100
                    self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_log_slider.setLogValue(float(cutoff))
                self.cutoff_slider_log_slider.blockSignals(False)

            self.cutoff_value = (cutoff/100)
            self.update_plot_table()

    def cutoff_slider_topx_check(self, editor):
        """ With top # selected, change the values for plots and tables to reflect the slider/line-edit. """
        if self.cutoff_type_topx.isChecked():
            self.cutoff_validator = self.cutoff_validator_int
            self.cutoff_slider_line.setValidator(self.cutoff_validator)
            cutoff = int

            # If called by slider
            if editor == "sl":
                self.cutoff_slider_line.blockSignals(True)
                cutoff = abs(int(self.cutoff_slider_slider.value()))
                self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_line.blockSignals(False)

            # if called by line edit
            elif editor == "le":
                self.cutoff_slider_slider.blockSignals(True)
                if self.cutoff_slider_line.text() == '-':
                    cutoff = self.cutoff_slider_slider.minimum()
                    self.cutoff_slider_line.setText(str(self.cutoff_slider_slider.minimum()))
                elif self.cutoff_slider_line.text() == '':
                    cutoff = self.cutoff_slider_slider.minimum()
                else:
                    cutoff = abs(int(self.cutoff_slider_line.text()))

                if cutoff > self.cutoff_slider_slider.maximum():
                    cutoff = self.cutoff_slider_slider.maximum()
                    self.cutoff_slider_line.setText(str(cutoff))
                self.cutoff_slider_slider.setValue(int(cutoff))
                self.cutoff_slider_slider.blockSignals(False)

            self.cutoff_value = int(cutoff)
            self.update_plot_table()

    def make_layout(self):
        """ Add the cut-off menu to the tab. """
        self.cutoff_menu = QHBoxLayout()

        # Cut-off types
        self.cutoff_type = QVBoxLayout()
        self.cutoff_type_label = QLabel("Cut-off type")
        self.cutoff_type_relative = QRadioButton("Relative")
        self.cutoff_type_relative.setChecked(True)
        self.cutoff_type_topx = QRadioButton("Top #")

        # Cut-off slider
        self.cutoff_slider = QVBoxLayout()
        self.cutoff_slider_set = QVBoxLayout()
        self.cutoff_slider_label = QLabel("Cut-off level")
        self.cutoff_slider_slider = QSlider(Qt.Horizontal)
        self.cutoff_slider_log_slider = LogarithmicSlider(self)
        self.cutoff_slider_log_slider.setInvertedAppearance(True)
        self.cutoff_slider_slider.setMinimum(1)
        self.cutoff_slider_slider.setMaximum(50)
        self.cutoff_slider_slider.setValue(self.cutoff_value)
        self.cutoff_slider_log_slider.setLogValue(self.cutoff_value)
        self.cutoff_slider_minmax = QHBoxLayout()
        self.cutoff_slider_min = QLabel("100%")
        self.cutoff_slider_max = QLabel("0.001%")
        self.cutoff_slider_ledit = QHBoxLayout()
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_validator_int = QIntValidator(self.cutoff_slider_line)
        self.cutoff_validator_float = QDoubleValidator(self.cutoff_slider_line)
        self.cutoff_validator = self.cutoff_validator_int
        self.cutoff_slider_line.setValidator(self.cutoff_validator)

        self.cutoff_slider_unit = QLabel("%  of total")

        self.cutoff_slider_lft_btn = QPushButton("<")
        self.cutoff_slider_lft_btn.setMaximumWidth(15)
        self.cutoff_slider_rght_btn = QPushButton(">")
        self.cutoff_slider_rght_btn.setMaximumWidth(15)

        # Assemble types
        self.cutoff_type.addWidget(self.cutoff_type_label)
        self.cutoff_type.addWidget(self.cutoff_type_relative)
        self.cutoff_type.addWidget(self.cutoff_type_topx)

        # Assemble slider set
        self.cutoff_slider_set.addWidget(self.cutoff_slider_label)
        self.cutoff_slider_set.addWidget(self.cutoff_slider_slider)
        self.cutoff_slider_slider.setVisible(False)
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_min)
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_log_slider)
        self.cutoff_slider_minmax.addWidget(self.cutoff_slider_max)
        self.cutoff_slider_set.addLayout(self.cutoff_slider_minmax)

        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_lft_btn)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_rght_btn)
        self.cutoff_slider_ledit.addWidget(self.cutoff_slider_unit)
        self.cutoff_slider_ledit.addStretch(1)

        self.cutoff_slider.addLayout(self.cutoff_slider_set)
        self.cutoff_slider.addLayout(self.cutoff_slider_ledit)

        # Assemble cut-off menu
        self.cutoff_menu.addLayout(self.cutoff_type)
        self.cutoff_menu.addWidget(vertical_line())
        self.cutoff_menu.addLayout(self.cutoff_slider)
        self.cutoff_menu.addStretch()

        self.setLayout(self.cutoff_menu)


# Logarithmic math refresher:
# BOP Base, Outcome Power;
# log(B)(O) = P --> log(2)(64) = 6  ||  log(10)(1000) = 3
#       B^P = O -->        2^6 = 64 ||           10^3 = 1000

class LogarithmicSlider(QSlider):
    """ Makes a QSlider object that behaves logarithmically.

    This slider adds two functions, setLogValue and Logvalue, named after the setValue and Value functions
    of a QSlider.
    """

    def __init__(self, parent):
        super(LogarithmicSlider, self).__init__(parent)

        self.setOrientation(Qt.Horizontal)

        self.setMinimum(1)
        self.setMaximum(100)

    def setLogValue(self, value):
        """ Modify value from 0.001-100 to 1-100 logarithmically and set slider to value. """
        value = int(float(value)*(10**3))
        log_val = round(log10(value), 3)
        set_val = log_val*20
        self.setValue(set_val)

    def logValue(self, value=None):
        """ Read (slider) value and modify it from 1-100 to 0.001-100 logarithmically with relevant rounding. """
        if value == None:
            value = self.value()
        value = float(value)
        log_val = log10(value)
        power = log_val * 2.5 - 3
        ret_val = 10**power

        if log10(ret_val) < -1:
            ret_val = round(ret_val, 3)
        elif log10(ret_val) < -0:
            ret_val = round(ret_val, 2)
        elif log10(ret_val) < 1:
            ret_val = round(ret_val, 1)
        else:
            ret_val = int(round(ret_val, 0))
        return ret_val
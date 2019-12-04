# -*- coding: utf-8 -*-
from collections import namedtuple
from typing import Union

import numpy as np
from PySide2.QtCore import QLocale, Qt, Signal, Slot
from PySide2.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QRadioButton, QSlider, QLabel,
    QLineEdit, QPushButton, QButtonGroup
)
from PySide2.QtGui import QIntValidator, QDoubleValidator

from ..style import vertical_line


Types = namedtuple("types", ("relative", "topx"))
Labels = namedtuple("labels", ("unit", "min", "max"))


class CutoffMenu(QWidget):
    slider_change = Signal()

    def __init__(self, parent=None, cutoff_value=0.01, limit_type="percent"):
        super().__init__(parent)
        self.cutoff_value = cutoff_value
        self.limit_type = limit_type

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        self.validators = Types(
            QDoubleValidator(0.001, 100.0, 1, self), QIntValidator(0, 50, self)
        )
        self.validators.relative.setLocale(locale)
        self.validators.topx.setLocale(locale)
        self.buttons = Types(QRadioButton("Relative"), QRadioButton("Top #"))
        self.buttons.relative.setChecked(True)
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.buttons.relative, 0)
        self.button_group.addButton(self.buttons.topx, 1)
        self.sliders = Types(LogarithmicSlider(self), QSlider(Qt.Horizontal, self))
        self.units = Types("% of total", "top #")
        self.labels = Labels(QLabel(), QLabel(), QLabel())
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_slider_line.setLocale(locale)
        self.cutoff_slider_lft_btn = QPushButton("<")
        self.cutoff_slider_rght_btn = QPushButton(">")

        self.make_layout()
        self.connect_signals()

    def connect_signals(self):
        # Cut-off types
        self.buttons.relative.toggled.connect(self.cutoff_type_check)
        self.cutoff_slider_lft_btn.clicked.connect(self.cutoff_increment_left_check)
        self.cutoff_slider_rght_btn.clicked.connect(self.cutoff_increment_right_check)

        # Cut-off log slider
        self.sliders.relative.valueChanged.connect(
            lambda: self.cutoff_slider_relative_check("sl"))
        self.cutoff_slider_line.textChanged.connect(
            lambda: self.cutoff_slider_relative_check("le"))
        # Cut-off slider
        self.sliders.topx.valueChanged.connect(
            lambda: self.cutoff_slider_topx_check("sl"))
        self.cutoff_slider_line.textChanged.connect(
            lambda: self.cutoff_slider_topx_check("le"))

    @property
    def is_relative(self) -> bool:
        return self.buttons.relative.isChecked()

    @Slot(name="incrementLeftCheck")
    def cutoff_increment_left_check(self):
        """ Move the slider 1 increment when left button is clicked. """
        if self.is_relative:
            num = int(self.sliders.relative.value())
            self.sliders.relative.setValue(num + 1)
        else:
            num = int(self.sliders.topx.value())
            self.sliders.topx.setValue(num - 1)

    @Slot(name="incrementRightCheck")
    def cutoff_increment_right_check(self):
        """ Move the slider 1 increment when right button is clicked. """
        if self.is_relative:
            num = int(self.sliders.relative.value())
            self.sliders.relative.setValue(num - 1)
        else:
            num = int(self.sliders.topx.value())
            self.sliders.topx.setValue(num + 1)

    @Slot(bool, name="isRelativeToggled")
    def cutoff_type_check(self, toggled: bool) -> None:
        """ Slot connected to the relative radiobutton, the state of that
        button determines:
        - which sliders are visible
        - the unit shown
        - minimum and maximum
        - limit_type
        """
        self.sliders.topx.setVisible(not toggled)
        self.sliders.relative.setVisible(toggled)

        self.sliders.relative.blockSignals(True)
        self.sliders.topx.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)
        if toggled:
            self.labels.unit.setText(self.units.relative)
            self.labels.min.setText("100%")
            self.labels.max.setText("0.001%")
            self.limit_type = "percent"
            self.cutoff_slider_line.setValidator(self.validators.relative)
        else:
            self.labels.unit.setText(self.units.topx)
            self.labels.min.setText(str(self.sliders.topx.minimum()))
            self.labels.max.setText(str(self.sliders.topx.maximum()))
            self.limit_type = "number"
            self.cutoff_slider_line.setValidator(self.validators.topx)
        self.sliders.relative.blockSignals(False)
        self.sliders.topx.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)

    @Slot(str, name="sliderRelativeCheck")
    def cutoff_slider_relative_check(self, editor: str):
        """ With relative selected, change the values for plots and tables to reflect the slider/line-edit. """
        if not self.is_relative:
            return
        cutoff = 0.01

        # If called by slider
        if editor == "sl":
            self.cutoff_slider_line.blockSignals(True)
            cutoff = abs(self.sliders.relative.log_value)
            self.cutoff_slider_line.setText(str(cutoff))
            self.cutoff_slider_line.blockSignals(False)

        # if called by line edit
        elif editor == "le":
            self.sliders.relative.blockSignals(True)
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
            self.sliders.relative.log_value = float(cutoff)
            self.sliders.relative.blockSignals(False)

        self.cutoff_value = (cutoff/100)
        self.slider_change.emit()

    @Slot(str, name="sliderTopXCheck")
    def cutoff_slider_topx_check(self, editor: str):
        """ With top # selected, change the values for plots and tables to reflect the slider/line-edit. """
        if self.is_relative:
            return
        cutoff = 2

        # If called by slider
        if editor == "sl":
            self.cutoff_slider_line.blockSignals(True)
            cutoff = abs(int(self.sliders.topx.value()))
            self.cutoff_slider_line.setText(str(cutoff))
            self.cutoff_slider_line.blockSignals(False)

        # if called by line edit
        elif editor == "le":
            self.sliders.topx.blockSignals(True)
            if self.cutoff_slider_line.text() == '-':
                cutoff = self.sliders.topx.minimum()
                self.cutoff_slider_line.setText(str(self.sliders.topx.minimum()))
            elif self.cutoff_slider_line.text() == '':
                cutoff = self.sliders.topx.minimum()
            else:
                cutoff = abs(int(self.cutoff_slider_line.text()))

            if cutoff > self.sliders.topx.maximum():
                cutoff = self.sliders.topx.maximum()
                self.cutoff_slider_line.setText(str(cutoff))
            self.sliders.topx.setValue(int(cutoff))
            self.sliders.topx.blockSignals(False)

        self.cutoff_value = int(cutoff)
        self.slider_change.emit()

    def make_layout(self):
        """ Construct the layout for the cutoff menu widget.

        The initial layout is set to 'relative'.
        """
        layout = QHBoxLayout()

        # Cut-off types
        cutoff_type = QVBoxLayout()
        cutoff_type_label = QLabel("Cut-off type")

        # Cut-off slider
        cutoff_slider = QVBoxLayout()
        cutoff_slider_set = QVBoxLayout()
        cutoff_slider_label = QLabel("Cut-off level")
        self.sliders.relative.setInvertedAppearance(True)
        self.sliders.topx.setMinimum(1)
        self.sliders.topx.setMaximum(50)
        self.sliders.topx.setValue(self.cutoff_value)
        self.sliders.relative.log_value = self.cutoff_value
        cutoff_slider_minmax = QHBoxLayout()
        self.labels.min.setText("100%")
        self.labels.max.setText("0.001%")
        self.labels.unit.setText("%  of total")
        cutoff_slider_ledit = QHBoxLayout()
        self.cutoff_slider_line.setValidator(self.validators.relative)
        self.cutoff_slider_lft_btn.setMaximumWidth(15)
        self.cutoff_slider_rght_btn.setMaximumWidth(15)

        # Assemble types
        cutoff_type.addWidget(cutoff_type_label)
        cutoff_type.addWidget(self.buttons.relative)
        cutoff_type.addWidget(self.buttons.topx)

        # Assemble slider set
        self.sliders.topx.setVisible(False)
        cutoff_slider_set.addWidget(cutoff_slider_label)
        cutoff_slider_minmax.addWidget(self.labels.min)
        cutoff_slider_minmax.addWidget(self.sliders.relative)
        cutoff_slider_minmax.addWidget(self.sliders.topx)
        cutoff_slider_minmax.addWidget(self.labels.max)
        cutoff_slider_set.addLayout(cutoff_slider_minmax)

        cutoff_slider_ledit.addWidget(self.cutoff_slider_line)
        cutoff_slider_ledit.addWidget(self.cutoff_slider_lft_btn)
        cutoff_slider_ledit.addWidget(self.cutoff_slider_rght_btn)
        cutoff_slider_ledit.addWidget(self.labels.unit)
        cutoff_slider_ledit.addStretch(1)

        cutoff_slider.addLayout(cutoff_slider_set)
        cutoff_slider.addLayout(cutoff_slider_ledit)

        # Assemble cut-off menu
        layout.addLayout(cutoff_type)
        layout.addWidget(vertical_line())
        layout.addLayout(cutoff_slider)
        layout.addStretch()

        self.setLayout(layout)


# Logarithmic math refresher:
# BOP Base, Outcome Power;
# log(B)(O) = P --> log(2)(64) = 6  ||  log(10)(1000) = 3
#       B^P = O -->        2^6 = 64 ||           10^3 = 1000

class LogarithmicSlider(QSlider):
    """ Makes a QSlider object that behaves logarithmically.

    This class uses the property `log_value` getter and setter to modify
    the QSlider through the `value` and `setValue` methods.
    """
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMinimum(1)
        self.setMaximum(100)

    @property
    def log_value(self) -> Union[int, float]:
        """ Read (slider) value and modify it from
        1-100 to 0.001-100 logarithmically with relevant rounding.
        """
        value = float(self.value())
        log_val = np.log10(value)
        power = log_val * 2.5 - 3
        ret_val = np.power(10, power)
        test_val = np.log10(ret_val)

        if test_val < -1:
            return ret_val.round(3)
        elif test_val < -0:
            return ret_val.round(2)
        elif test_val < 1:
            return ret_val.round(1)
        else:
            return ret_val.astype(int)

    @log_value.setter
    def log_value(self, value: float) -> None:
        """ Modify value from 0.001-100 to 1-100 logarithmically and set
        slider to value.
        """
        value = int(float(value) * np.power(10, 3))
        log_val = np.log10(value).round(3)
        set_val = log_val * 20
        self.setValue(set_val)

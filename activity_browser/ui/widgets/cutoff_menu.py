# -*- coding: utf-8 -*-
"""Classes related to the cutoff options menu in contributions tabs.

These classes contain all menu items required to modify the cutoffs of the MLCA results. The
CutoffMenu class is responsible for assembling the menu. Each different menu item is contained in
its separate class.
"""

from collections import namedtuple
from typing import Union

import numpy as np
from qtpy import QtCore
from qtpy.QtCore import QLocale, Qt, Signal, Slot
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QRadioButton, QSlider, QVBoxLayout,
                               QWidget)

from activity_browser.ui import widgets


# These tuples are used in referring to the two Types and three Labels used
Types = namedtuple("types", ("percent", "cum_percent", "number"))
Labels = namedtuple("labels", ("unit", "min", "max"))


class CutoffMenu(QWidget):
    """This class assembles the cutoff menu from the other classes in this module."""

    slider_change = Signal()

    def __init__(self, parent=None, cutoff_value=0.05, limit_type="percent"):
        super().__init__(parent)
        self.cutoff_value = cutoff_value
        self.limit_type = limit_type

        locale = QLocale(QLocale.English, QLocale.UnitedStates)
        locale.setNumberOptions(QLocale.RejectGroupSeparator)
        self.validators = Types(
            QDoubleValidator(0.001, 100.0, 1, self),
            QIntValidator(0, 100, self),
            QIntValidator(0, 50, self),
        )
        self.validators.percent.setLocale(locale)
        self.validators.number.setLocale(locale)
        self.buttons = Types(
            QRadioButton("Minimum %"),
            QRadioButton("Cumulative %"),
            QRadioButton("Top #"))
        self.buttons.percent.setChecked(True)
        self.buttons.percent.setToolTip(
            "This cut-off type shows contributions of at least some percentage "
            "(for example contributions of at least 5% of the total impact)"
        )
        self.buttons.cum_percent.setToolTip(
            "This cut-off type shows contributions that together are some percentage "
            "(for example all highest contributors that together count up to 80% of the total impact)"
        )
        self.buttons.number.setToolTip(
            "This cut-off type shows this number of largest contributors "
            "(for example the top 5 largest contributors)"
        )
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.buttons.percent, 0)
        self.button_group.addButton(self.buttons.cum_percent, 1)
        self.button_group.addButton(self.buttons.number, 2)
        self.button_id_limit_type = {
            0: "percent",
            1: "cum_percent",
            2: "number",
        }
        self.button_group.setExclusive(True)
        self.sliders = Types(
            LogarithmicSlider(self),
            QSlider(Qt.Horizontal, self),
            QSlider(Qt.Horizontal, self))
        self.sliders.percent.setToolTip(
            "This slider sets the cut-off percentage to show"
        )
        self.sliders.cum_percent.setToolTip(
            "This slider sets the cumulative cut-off percentage to show"
        )
        self.sliders.number.setToolTip(
            "This slider sets the amount of highest contributors to show"
        )
        self.units = Types("minimum %", "cumulative %", "number")
        self.labels = Labels(QLabel(), QLabel(), QLabel())
        self.cutoff_slider_line = QLineEdit()
        self.cutoff_slider_line.setToolTip(
            "This entry sets the cut-off amount"
        )
        self.cutoff_slider_line.setLocale(locale)
        self.cutoff_slider_lft_btn = QPushButton("<")
        self.cutoff_slider_lft_btn.setToolTip(
            "This button moves the cut-off value one increment"
        )
        self.cutoff_slider_rght_btn = QPushButton(">")
        self.cutoff_slider_rght_btn.setToolTip(
            "This button moves the cut-off value one increment"
        )

        self.debounce_slider = QtCore.QTimer()
        self.debounce_slider.setInterval(300)
        self.debounce_slider.setSingleShot(True)

        self.debounce_text = QtCore.QTimer()
        self.debounce_text.setInterval(300)
        self.debounce_text.setSingleShot(True)

        self.make_layout()
        self.connect_signals()

    def connect_signals(self):
        """Connect the signals of the menu."""
        # Cut-off types
        self.button_group.buttonClicked.connect(self.cutoff_type_check)
        self.cutoff_slider_lft_btn.clicked.connect(self.cutoff_increment_left_check)
        self.cutoff_slider_rght_btn.clicked.connect(self.cutoff_increment_right_check)

        self.debounce_slider.timeout.connect(self.initiate_slider_change)
        self.debounce_text.timeout.connect(self.initiate_text_change)

        self.sliders.percent.valueChanged.connect(self.debounce_slider.start)
        self.sliders.cum_percent.valueChanged.connect(self.debounce_slider.start)
        self.sliders.number.valueChanged.connect(self.debounce_slider.start)
        self.cutoff_slider_line.textChanged.connect(self.debounce_text.start)

    def initiate_slider_change(self):
        if self.limit_type == "percent":
            self.cutoff_slider_percent_check("sl")
        elif self.limit_type == "cum_percent":
            self.cutoff_slider_cum_percent_check("sl")
        elif self.limit_type == "number":
            self.cutoff_slider_number_check("sl")

    def initiate_text_change(self):
        if self.limit_type == "percent":
            self.cutoff_slider_percent_check("le")
        elif self.limit_type == "cum_percent":
            self.cutoff_slider_cum_percent_check("le")
        elif self.limit_type == "number":
            self.cutoff_slider_number_check("le")

    @Slot(name="incrementLeftCheck")
    def cutoff_increment_left_check(self):
        """Move the slider 1 increment to left when left button is clicked."""
        if self.limit_type == "percent":
            num = int(self.sliders.percent.value())
            self.sliders.percent.setValue(num + 1)
        elif self.limit_type == "cum_percent":
            num = int(self.sliders.cum_percent.value())
            self.sliders.cum_percent.setValue(num - 1)
        elif self.limit_type == "number":
            num = int(self.sliders.number.value())
            self.sliders.number.setValue(num - 1)

    @Slot(name="incrementRightCheck")
    def cutoff_increment_right_check(self):
        """Move the slider 1 increment to right when right button is clicked."""
        if self.limit_type == "percent":
            num = int(self.sliders.percent.value())
            self.sliders.percent.setValue(num - 1)
        elif self.limit_type == "cum_percent":
            num = int(self.sliders.cum_percent.value())
            self.sliders.cum_percent.setValue(num + 1)
        elif self.limit_type == "number":
            num = int(self.sliders.number.value())
            self.sliders.number.setValue(num + 1)

    @Slot(name="isClicked")
    def cutoff_type_check(self) -> None:
        """Dependent on cutoff-type, set the right labels.

                Slot connected to the 'Cut-off types', the state of those buttons determines:
                - which sliders are visible
                - the unit shown
                - minimum and maximum
                - limit_type
                """
        # determine which mode is clicked
        clicked_type = self.button_id_limit_type[self.button_group.checkedId()]
        if self.limit_type == clicked_type:
            return  # immediately return if the clicked type was already toggled
        self.limit_type = clicked_type

        # temporarily block signals
        self.sliders.percent.blockSignals(True)
        self.sliders.cum_percent.blockSignals(True)
        self.sliders.number.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)

        if self.limit_type == "percent":
            self.sliders.percent.setVisible(True)
            self.sliders.cum_percent.setVisible(False)
            self.sliders.number.setVisible(False)

            self.labels.unit.setText(self.units.percent)
            self.labels.min.setText("100%")
            self.labels.max.setText("0.001%")
            self.cutoff_slider_line.setValidator(self.validators.percent)
        if self.limit_type == "cum_percent":
            self.sliders.percent.setVisible(False)
            self.sliders.cum_percent.setVisible(True)
            self.sliders.number.setVisible(False)

            self.labels.unit.setText(self.units.cum_percent)
            self.labels.min.setText("1%")
            self.labels.max.setText("100%")
            self.cutoff_slider_line.setValidator(self.validators.cum_percent)
        elif self.limit_type == "number":
            self.sliders.percent.setVisible(False)
            self.sliders.cum_percent.setVisible(False)
            self.sliders.number.setVisible(True)

            self.labels.unit.setText(self.units.number)
            self.labels.min.setText(str(self.sliders.number.minimum()))
            self.labels.max.setText(str(self.sliders.number.maximum()))
            self.cutoff_slider_line.setValidator(self.validators.number)

        # unblock signals
        self.sliders.percent.blockSignals(False)
        self.sliders.cum_percent.blockSignals(False)
        self.sliders.number.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)

    @Slot(str, name="sliderPercentCheck")
    def cutoff_slider_percent_check(self, editor: str):
        """If 'Percent' selected, change the plots and tables to reflect the slider/line-edit."""
        if not self.limit_type == "percent":
            return
        cutoff = 0.05

        # If called by slider
        if editor == "sl":
            self.cutoff_slider_line.blockSignals(True)
            cutoff = abs(self.sliders.percent.log_value)
            self.cutoff_slider_line.setText(str(cutoff))
            self.cutoff_slider_line.blockSignals(False)

        # if called by line edit
        elif editor == "le":
            self.sliders.percent.blockSignals(True)
            if self.cutoff_slider_line.text() == "-":
                cutoff = 0.001
                self.cutoff_slider_line.setText("0.001")
            elif self.cutoff_slider_line.text() == "":
                cutoff = 0.001
            else:
                cutoff = abs(float(self.cutoff_slider_line.text()))

            if cutoff > 100:
                cutoff = 100
                self.cutoff_slider_line.setText(str(cutoff))
            self.sliders.percent.log_value = float(cutoff)
            self.sliders.percent.blockSignals(False)

        self.cutoff_value = cutoff / 100
        self.slider_change.emit()

    @Slot(str, name="sliderCumPercentCheck")
    def cutoff_slider_cum_percent_check(self, editor: str):
        """If 'Percent' selected, change the plots and tables to reflect the slider/line-edit."""
        """If 'Number' selected, change the plots and tables to reflect the slider/line-edit."""
        if not self.limit_type == "cum_percent":
            return
        cutoff = 2

        # If called by slider
        if editor == "sl":
            self.cutoff_slider_line.blockSignals(True)
            cutoff = abs(int(self.sliders.cum_percent.value()))
            self.cutoff_slider_line.setText(str(cutoff))
            self.cutoff_slider_line.blockSignals(False)

        # if called by line edit
        elif editor == "le":
            self.sliders.cum_percent.blockSignals(True)
            if self.cutoff_slider_line.text() == "-":
                cutoff = self.sliders.cum_percent.minimum()
                self.cutoff_slider_line.setText(str(self.sliders.cum_percent.minimum()))
            elif self.cutoff_slider_line.text() == "":
                cutoff = self.sliders.cum_percent.minimum()
            else:
                cutoff = abs(int(self.cutoff_slider_line.text()))

            if cutoff > self.sliders.cum_percent.maximum():
                cutoff = self.sliders.cum_percent.maximum()
                self.cutoff_slider_line.setText(str(cutoff))
            self.sliders.cum_percent.setValue(int(cutoff))
            self.sliders.cum_percent.blockSignals(False)

        self.cutoff_value = cutoff / 100
        self.slider_change.emit()

    @Slot(str, name="sliderNumberCheck")
    def cutoff_slider_number_check(self, editor: str):
        """If 'Number' selected, change the plots and tables to reflect the slider/line-edit."""
        if not self.limit_type == "number":
            return
        cutoff = 2

        # If called by slider
        if editor == "sl":
            self.cutoff_slider_line.blockSignals(True)
            cutoff = abs(int(self.sliders.number.value()))
            self.cutoff_slider_line.setText(str(cutoff))
            self.cutoff_slider_line.blockSignals(False)

        # if called by line edit
        elif editor == "le":
            self.sliders.number.blockSignals(True)
            if self.cutoff_slider_line.text() == "-":
                cutoff = self.sliders.number.minimum()
                self.cutoff_slider_line.setText(str(self.sliders.number.minimum()))
            elif self.cutoff_slider_line.text() == "":
                cutoff = self.sliders.number.minimum()
            else:
                cutoff = abs(int(self.cutoff_slider_line.text()))

            if cutoff > self.sliders.number.maximum():
                cutoff = self.sliders.number.maximum()
                self.cutoff_slider_line.setText(str(cutoff))
            self.sliders.number.setValue(int(cutoff))
            self.sliders.number.blockSignals(False)

        self.cutoff_value = int(cutoff)
        self.slider_change.emit()

    def make_layout(self):
        """Assemble the layout of the cutoff menu.

        Construct the layout for the cutoff menu widget. The initial layout is set to 'Percent'.
        """
        layout = QHBoxLayout()

        # Cut-off types
        cutoff_type = QVBoxLayout()
        cutoff_type_label = QLabel("Cut-off type")

        # Cut-off slider
        cutoff_slider = QVBoxLayout()
        cutoff_slider_set = QVBoxLayout()
        cutoff_slider_label = QLabel("Cut-off level")
        self.sliders.percent.log_value = self.cutoff_value
        self.sliders.percent.setInvertedAppearance(True)
        self.sliders.cum_percent.setValue(self.cutoff_value)
        self.sliders.cum_percent.setMinimum(1)
        self.sliders.cum_percent.setMaximum(100)
        self.sliders.number.setValue(self.cutoff_value)
        self.sliders.number.setMinimum(1)
        self.sliders.number.setMaximum(50)
        cutoff_slider_minmax = QHBoxLayout()
        self.labels.min.setText("100%")
        self.labels.max.setText("0.001%")
        self.labels.unit.setText("minimum %")
        cutoff_slider_ledit = QHBoxLayout()
        self.cutoff_slider_line.setValidator(self.validators.percent)
        self.cutoff_slider_lft_btn.setMaximumWidth(15)
        self.cutoff_slider_rght_btn.setMaximumWidth(15)

        # Assemble types
        cutoff_type.addWidget(cutoff_type_label)
        cutoff_type.addWidget(self.buttons.percent)
        cutoff_type.addWidget(self.buttons.cum_percent)
        cutoff_type.addWidget(self.buttons.number)

        # Assemble slider set
        self.sliders.number.setVisible(False)
        self.sliders.cum_percent.setVisible(False)
        cutoff_slider_set.addWidget(cutoff_slider_label)
        cutoff_slider_minmax.addWidget(self.labels.min)
        cutoff_slider_minmax.addWidget(self.sliders.percent)
        cutoff_slider_minmax.addWidget(self.sliders.cum_percent)
        cutoff_slider_minmax.addWidget(self.sliders.number)
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
        layout.addWidget(widgets.ABVLine(self))
        layout.addLayout(cutoff_slider)
        layout.addStretch()

        self.setLayout(layout)


class LogarithmicSlider(QSlider):
    """Makes a QSlider object that behaves logarithmically.

    Inherits from QSlider. This class uses the property `log_value` getter and setter to modify
    the QSlider through the `value` and `setValue` methods.
    """

    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setMinimum(1)
        self.setMaximum(100)

    @property
    def log_value(self) -> Union[int, float]:
        """Read (slider) and modify from 1-100 to 0.001-100 logarithmically with relevant rounding.

        This function converts the 1-100 values and modifies these to 0.001-100 on a logarithmic
        scale. Rounding is done based on magnitude.
        """

        # Logarithmic math refresher:
        # BOP = Base, Outcome Power;
        # log(B)(O) = P --> log(2)(64) = 6  ||  log(10)(1000) = 3
        #       B^P = O -->        2^6 = 64 ||           10^3 = 1000

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
        """Modify value from 0.001-100 to 1-100 logarithmically and set slider to value."""
        value = int(float(value) * np.power(10, 3))
        log_val = np.log10(value).round(3)
        set_val = log_val * 20
        self.setValue(set_val)

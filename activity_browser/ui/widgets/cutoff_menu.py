# -*- coding: utf-8 -*-
"""Classes related to the cutoff options menu in contributions tabs.

These classes contain all menu items required to modify the cutoffs of the MLCA results. The
CutoffMenu class is responsible for assembling the menu. Each different menu item is contained in
its separate class.
"""

from collections import namedtuple
from typing import Union

from qtpy import QtCore
from qtpy.QtCore import QLocale, Qt, Signal, Slot
from qtpy.QtGui import QDoubleValidator, QIntValidator
from qtpy.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QSizePolicy, QSlider, QWidget

from activity_browser.ui import widgets


# These tuples are used in referring to the two Types and three Labels used
Types = namedtuple("types", ("percent", "cum_percent", "number"))

_SLIDER_MAX_WIDTH = 200
_LINEEDIT_MAX_WIDTH = 50


class CutoffMenu(QWidget):
    """This class assembles the cutoff menu from the other classes in this module."""

    slider_change = Signal()

    _INDEX_TO_LIMIT_TYPE = {
        0: "percent",
        1: "cum_percent",
        2: "number",
    }
    _LIMIT_TYPE_TO_INDEX = {v: k for k, v in _INDEX_TO_LIMIT_TYPE.items()}

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

        self.type_combo = QComboBox(self)
        self.type_combo.addItems(["Minimum %", "Cumulative %", "Top #"])
        self.type_combo.setItemData(
            0,
            "Contributions smaller than the value set here are cut-off",
            Qt.ToolTipRole,
        )
        self.type_combo.setItemData(
            1,
            "Highest contributors that together reach a percentage of the total impact "
            "(e.g. up to 80%).",
            Qt.ToolTipRole,
        )
        self.type_combo.setItemData(
            2,
            "This many largest contributors (e.g. top 5).",
            Qt.ToolTipRole,
        )
        self.type_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.type_combo.setMinimumWidth(110)
        self.type_combo.setMaximumWidth(200)
        self.type_combo.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)

        self.sliders = Types(
            LogarithmicSlider(self),
            QSlider(Qt.Horizontal, self),
            QSlider(Qt.Horizontal, self),
        )
        for s in self.sliders:
            s.setMaximumWidth(_SLIDER_MAX_WIDTH)
        self.sliders.percent.setToolTip(
            "Cut-off percentage (logarithmic scale; right is stricter)."
        )
        self.sliders.cum_percent.setToolTip(
            "Cumulative cut-off percentage (1–100%)."
        )
        self.sliders.number.setToolTip(
            "Number of largest contributors to show (1–50)."
        )

        self.cutoff_slider_line = QLineEdit()
        self.cutoff_slider_line.setLocale(locale)
        self.cutoff_slider_line.setMaximumWidth(_LINEEDIT_MAX_WIDTH)
        self.cutoff_slider_line.setAlignment(Qt.AlignRight)

        self.debounce_slider = QtCore.QTimer()
        self.debounce_slider.setInterval(300)
        self.debounce_slider.setSingleShot(True)

        self.debounce_text = QtCore.QTimer()
        self.debounce_text.setInterval(300)
        self.debounce_text.setSingleShot(True)

        self.make_layout()
        self.connect_signals()

        idx = self._LIMIT_TYPE_TO_INDEX.get(self.limit_type, 0)
        self.type_combo.blockSignals(True)
        self.type_combo.setCurrentIndex(idx)
        self.type_combo.blockSignals(False)
        self._apply_limit_type_changed(force=True)

    def connect_signals(self):
        """Connect the signals of the menu."""
        self.type_combo.currentIndexChanged.connect(self._on_type_combo_changed)
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

    def _on_type_combo_changed(self, _index: int) -> None:
        self._apply_limit_type_changed(force=False)

    def _apply_limit_type_changed(self, force: bool = False) -> None:
        clicked_type = self._INDEX_TO_LIMIT_TYPE[self.type_combo.currentIndex()]
        if not force and self.limit_type == clicked_type:
            return
        self.limit_type = clicked_type

        self.sliders.percent.blockSignals(True)
        self.sliders.cum_percent.blockSignals(True)
        self.sliders.number.blockSignals(True)
        self.cutoff_slider_line.blockSignals(True)

        if self.limit_type == "percent":
            self.sliders.percent.setVisible(True)
            self.sliders.cum_percent.setVisible(False)
            self.sliders.number.setVisible(False)
            self.cutoff_slider_line.setValidator(self.validators.percent)
            self.cutoff_slider_line.setToolTip(
                "Minimum contribution as % of total impact (0.001–100)."
            )
        elif self.limit_type == "cum_percent":
            self.sliders.percent.setVisible(False)
            self.sliders.cum_percent.setVisible(True)
            self.sliders.number.setVisible(False)
            self.cutoff_slider_line.setValidator(self.validators.cum_percent)
            self.cutoff_slider_line.setToolTip(
                "Cumulative share of impact to include, as % (1–100)."
            )
        else:
            self.sliders.percent.setVisible(False)
            self.sliders.cum_percent.setVisible(False)
            self.sliders.number.setVisible(True)
            self.cutoff_slider_line.setValidator(self.validators.number)
            self.cutoff_slider_line.setToolTip(
                "How many of the largest contributors to show (1–50)."
            )

        self.sliders.percent.blockSignals(False)
        self.sliders.cum_percent.blockSignals(False)
        self.sliders.number.blockSignals(False)
        self.cutoff_slider_line.blockSignals(False)

        if self.limit_type == "percent":
            self.cutoff_slider_percent_check("sl")
        elif self.limit_type == "cum_percent":
            self.cutoff_slider_cum_percent_check("sl")
        elif self.limit_type == "number":
            self.cutoff_slider_number_check("sl")

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
        """If 'Cumulative %' selected, change the plots and tables to reflect the slider/line-edit."""
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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sliders.percent.log_value = self.cutoff_value
        self.sliders.percent.setInvertedAppearance(True)
        self.sliders.cum_percent.setValue(self.cutoff_value)
        self.sliders.cum_percent.setMinimum(1)
        self.sliders.cum_percent.setMaximum(100)
        self.sliders.number.setValue(self.cutoff_value)
        self.sliders.number.setMinimum(1)
        self.sliders.number.setMaximum(50)

        self.sliders.number.setVisible(False)
        self.sliders.cum_percent.setVisible(False)
        self.cutoff_slider_line.setValidator(self.validators.percent)

        layout.addWidget(QLabel("Cut-off:"))
        layout.addWidget(self.type_combo)
        layout.addWidget(self.sliders.percent, 0)
        layout.addWidget(self.sliders.cum_percent, 0)
        layout.addWidget(self.sliders.number, 0)
        layout.addWidget(self.cutoff_slider_line, 0)
        layout.addStretch(1)


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
        import numpy as np

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
        import numpy as np

        value = int(float(value) * np.power(10, 3))
        log_val = np.log10(value).round(3)
        set_val = log_val * 20
        self.setValue(set_val)

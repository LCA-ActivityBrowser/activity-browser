# -*- coding: utf-8 -*-
from typing import Union

from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase
from PySide2 import QtCore, QtGui, QtWidgets
import numpy as np
from stats_arrays import LognormalUncertainty, uncertainty_choices as uc

from ..figures import SimpleDistributionPlot
from ..style import style_group_box
from ...bwutils import PedigreeMatrix
from ...signals import signals


class UncertaintyWizard(QtWidgets.QWizard):
    """Using this wizard, guide the user through selecting an 'uncertainty'
    distribution (and related values) for their activity/process exchanges.

    Note that this can also be used for setting uncertainties on parameters
    """
    KEYS = {
        "uncertainty type", "loc", "scale", "shape", "minimum", "maximum",
        "negative"
    }

    TYPE = 0
    PEDIGREE = 1

    def __init__(self, unc_object: Union[ExchangeProxyBase, ParameterBase], parent=None):
        super().__init__(parent)

        self.obj = unc_object

        self.pedigree = PedigreeMatrixPage(self)
        self.type = UncertaintyTypePage(self)
        self.pages = (self.type, self.pedigree)

        for i, p in enumerate(self.pages):
            self.setPage(i, p)
        self.setStartId(self.TYPE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setOption(QtWidgets.QWizard.IndependentPages, True)

        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.update_uncertainty)
        self.extract_uncertainty()

    @property
    def uncertainty_info(self):
        return {
            "uncertainty type": self.field("uncertainty type"),
            "loc": float(self.field("loc")) if self.field("loc") else float("nan"),
            "scale": float(self.field("scale")) if self.field("scale") else float("nan"),
            "shape": float(self.field("shape")) if self.field("shape") else float("nan"),
            "minimum": float(self.field("minimum")) if self.field("minimum") else float("nan"),
            "maximum": float(self.field("maximum")) if self.field("maximum") else float("nan"),
            "negative": bool(self.field("negative")),
        }

    @QtCore.Slot(name="modifyUncertainty")
    def update_uncertainty(self):
        if isinstance(self.obj, ExchangeProxyBase):
            signals.exchange_uncertainty_modified.emit(self.obj, self.uncertainty_info)
        elif isinstance(self.obj, ParameterBase):
            signals.parameter_uncertainty_modified.emit(self.obj, self.uncertainty_info)

    def extract_uncertainty(self) -> None:
        """Used to extract possibly existing uncertainty information from the
        given exchange/parameter
        """
        if self.obj is None:
            return
        # If we start from an exchange, we can use a shortcut.
        if isinstance(self.obj, ExchangeProxyBase):
            for k, v in self.obj.uncertainty.items():
                self.setField(k, v)
        # Otherwise, try and get something from the parameter.
        elif isinstance(self.obj, ParameterBase):
            for key in (k for k in self.KEYS if k in self.obj.data):
                self.setField(key, self.obj.data[key])

        # If no loc/mean value is set yet, convert the amount.
        loc = self.field("loc")
        if (loc is None or loc == "nan") and hasattr(self.obj, "amount"):
            self.setField("loc", str(np.log(self.obj.amount)))


class UncertaintyTypePage(QtWidgets.QWizardPage):
    """Present a list of uncertainty types directly retrieved from the `stats_arrays` package.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.dist = None
        self.complete = False
        self.goto_pedigree = False

        # Selection of uncertainty distribution.
        box1 = QtWidgets.QGroupBox("Select the uncertainty distribution")
        box1.setStyleSheet(style_group_box.border_title)
        self.distribution = QtWidgets.QComboBox(box1)
        self.distribution.addItems([ud.description for ud in uc.choices])
        self.distribution.currentIndexChanged.connect(self.distribution_selection)
        self.registerField("uncertainty type", self.distribution, "currentIndex")
        self.pedigree = QtWidgets.QPushButton("Use pedigree")
        self.pedigree.clicked.connect(self.pedigree_page)
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Distribution:"), 0, 0, 2, 1)
        box_layout.addWidget(self.distribution, 0, 1, 2, 2)
        box_layout.addWidget(self.pedigree, 0, 3, 2, 1)
        box1.setLayout(box_layout)

        # Set values for selected uncertainty distribution.
        box2 = QtWidgets.QGroupBox("Fill out or change required parameters")
        box2.setStyleSheet(style_group_box.border_title)
        self.locale = QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates)
        self.locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        self.validator = QtGui.QDoubleValidator()
        self.validator.setLocale(self.locale)
        self.loc = QtWidgets.QLineEdit()
        self.loc.setValidator(self.validator)
        self.loc.textEdited.connect(self.generate_plot)
        self.loc_label = QtWidgets.QLabel("Mean/loc:")
        self.scale = QtWidgets.QLineEdit()
        self.scale.setValidator(self.validator)
        self.scale.textEdited.connect(self.generate_plot)
        self.scale_label = QtWidgets.QLabel("Sigma/scale:")
        self.shape = QtWidgets.QLineEdit()
        self.shape.setValidator(self.validator)
        self.shape.textEdited.connect(self.generate_plot)
        self.shape_label = QtWidgets.QLabel("Shape:")
        self.minimum = QtWidgets.QLineEdit()
        self.minimum.setValidator(self.validator)
        self.minimum.textEdited.connect(self.generate_plot)
        self.min_label = QtWidgets.QLabel("Minimum:")
        self.maximum = QtWidgets.QLineEdit()
        self.maximum.setValidator(self.validator)
        self.maximum.textEdited.connect(self.generate_plot)
        self.max_label = QtWidgets.QLabel("Maximum:")
        self.negative = QtWidgets.QRadioButton(self)
        self.negative.setChecked(False)
        self.negative.setHidden(True)
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(self.loc_label, 0, 0, 2, 1)
        box_layout.addWidget(self.loc, 0, 1, 2, 2)
        box_layout.addWidget(self.scale_label, 2, 0, 2, 1)
        box_layout.addWidget(self.scale, 2, 1, 2, 2)
        box_layout.addWidget(self.shape_label, 4, 0, 2, 1)
        box_layout.addWidget(self.shape, 4, 1, 2, 2)
        box_layout.addWidget(self.min_label, 6, 0, 2, 1)
        box_layout.addWidget(self.minimum, 6, 1, 2, 2)
        box_layout.addWidget(self.max_label, 8, 0, 2, 1)
        box_layout.addWidget(self.maximum, 8, 1, 2, 2)
        box2.setLayout(box_layout)

        self.registerField("loc", self.loc, "text")
        self.registerField("scale", self.scale, "text")
        self.registerField("shape", self.shape, "text")
        self.registerField("minimum", self.minimum, "text")
        self.registerField("maximum", self.maximum, "text")
        self.registerField("negative", self.negative, "checked")

        self.plot = SimpleDistributionPlot(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box1)
        layout.addWidget(box2)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def hide_param(self, *params, hide: bool = True):
        if "loc" in params:
            self.loc_label.setHidden(hide)
            self.loc.setHidden(hide)
        if "scale" in params:
            self.scale_label.setHidden(hide)
            self.scale.setHidden(hide)
        if "shape" in params:
            self.shape_label.setHidden(hide)
            self.shape.setHidden(hide)
        if "min" in params:
            self.min_label.setHidden(hide)
            self.minimum.setHidden(hide)
        if "max" in params:
            self.max_label.setHidden(hide)
            self.maximum.setHidden(hide)

    @QtCore.Slot(name="changeDistribution")
    def distribution_selection(self):
        """Selected distribution and present the correct uncertainty parameters.

        See https://stats-arrays.readthedocs.io/en/latest/index.html for which
        fields to show and hide.
        """
        self.dist = uc.id_dict[self.distribution.currentIndex()]

        # Huge if/elif tree to ensure the correct fields are shown.
        if self.dist.id in {0, 1}:
            self.hide_param("loc", "scale", "shape", "min", "max")
        elif self.dist.id in {2, 3}:
            self.hide_param("shape", "min", "max")
            self.hide_param("loc", "scale", hide=False)
        elif self.dist.id in {4, 7}:
            self.hide_param("loc", "scale", "shape")
            self.hide_param("min", "max", hide=False)
        elif self.dist.id in {5, 6}:
            self.hide_param("scale", "shape")
            self.hide_param("loc", "min", "max", hide=False)
        elif self.dist.id in {8, 9, 10, 11, 12}:
            self.hide_param("min", "max")
            self.hide_param("loc", "scale", "shape", hide=False)
        self.generate_plot()

    @property
    def active_fields(self) -> tuple:
        """Returns anywhere from 0 to 3 fields"""
        if self.dist.id in {0, 1}:
            return ()
        elif self.dist.id in {2, 3}:
            return self.loc, self.scale
        elif self.dist.id in {4, 7}:
            return self.minimum, self.maximum
        elif self.dist.id in {5, 6}:
            return self.loc, self.minimum, self.maximum
        elif self.dist.id in {8, 9, 10, 11, 12}:
            return self.loc, self.scale, self.shape

    def cleanupPage(self):
        """Remove values from fields and reset the plot."""
        super().cleanupPage()
        self.plot.reset_plot()
        self.plot.canvas.draw()

    def initializePage(self):
        self.distribution_selection()

    def nextId(self):
        if self.goto_pedigree:
            return UncertaintyWizard.PEDIGREE
        return -1

    def isComplete(self):
        return self.complete

    @QtCore.Slot(name="gotoPedigreePage")
    def pedigree_page(self) -> None:
        self.goto_pedigree = True
        self.wizard().next()

    @QtCore.Slot(name="regenPlot")
    def generate_plot(self) -> None:
        """Called whenever a value changes, (re)generate the plot.

        Also tests if all of the visible QLineEdit fields have valid values.
        """
        self.complete = all(
            (field.hasAcceptableInput() and field.text())
            for field in self.active_fields
        )
        if self.complete:
            data = self.dist.random_variables(
                self.dist.from_dicts(self.wizard().uncertainty_info), 1000
            )
            if not np.any(np.isnan(data)):
                self.plot.plot(data)
        self.completeChanged.emit()


class PedigreeMatrixPage(QtWidgets.QWizardPage):
    """Guide the user through filling out a pedigree matrix.

    There are 5 indicators used, each carrying a score from 1 to 5
    with 1 indicating 'less uncertain' and 5 'more uncertain'.

    NOTE: Currently, the pedigree matrix will always default to a lognormal distribution.

    NOTE: using terms and quoting from the paper:
    'Empirically based uncertainty factors for the pedigree matrix in ecoinvent' (2016)
    doi: 10.1007/s11367-013-0670-5
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)

        box = QtWidgets.QGroupBox("Fill out pedigree matrix")
        box.setStyleSheet(style_group_box.border_title)

        self.reliable = QtWidgets.QComboBox(box)
        self.reliable.addItems([
            "1) Verified data based on measurements",
            "2) Verified data partly based on assumptions",
            "3) Non-verified data partly based on qualified measurements",
            "4) Qualified estimate",
            "5) Non-qualified estimate",
        ])
        self.complete = QtWidgets.QComboBox(box)
        self.complete.addItems([
            "1) Representative relevant data from all sites, over an adequate period",
            "2) Representative relevant data from >50% sites, over an adequate period",
            "3) Representative relevant data from <50% sites OR >50%, but over shorter period",
            "4) Representative relevant data from one site OR some sites but over shorter period",
            "5) Representativeness unknown",
        ])
        self.temporal = QtWidgets.QComboBox(box)
        self.temporal.addItems([
            "1) Data less than 3 years old",
            "2) Data less than 6 years old",
            "3) Data less than 10 years old",
            "4) Data less than 15 years old",
            "5) Data age unknown or more than 15 years old",
        ])
        self.geographical = QtWidgets.QComboBox(box)
        self.geographical.addItems([
            "1) Data from area under study",
            "2) Average data from larger area in which area under study is included",
            "3) Data from area with similar production conditions",
            "4) Data from area with slightly similar production conditions",
            "5) Data from unknown OR distinctly different area",
        ])
        self.technological = QtWidgets.QComboBox(box)
        self.technological.addItems([
            "1) Data from enterprises, processes and materials under study",
            "2) Data from processes and materials under study, different enterprise",
            "3) Data from processes and materials under study from different technology",
            "4) Data on related processes and materials",
            "5) Data on related processes on lab scale OR from different technology",
        ])
        self.reliable.currentIndexChanged.connect(self.check_complete)
        self.complete.currentIndexChanged.connect(self.check_complete)
        self.temporal.currentIndexChanged.connect(self.check_complete)
        self.geographical.currentIndexChanged.connect(self.check_complete)
        self.technological.currentIndexChanged.connect(self.check_complete)

        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Reliability"), 0, 0, 2, 2)
        box_layout.addWidget(self.reliable, 0, 2, 2, 3)
        box_layout.addWidget(QtWidgets.QLabel("Completeness"), 2, 0, 2, 2)
        box_layout.addWidget(self.complete, 2, 2, 2, 3)
        box_layout.addWidget(QtWidgets.QLabel("Temporal correlation"), 4, 0, 2, 2)
        box_layout.addWidget(self.temporal, 4, 2, 2, 3)
        box_layout.addWidget(QtWidgets.QLabel("Geographical correlation"), 6, 0, 2, 2)
        box_layout.addWidget(self.geographical, 6, 2, 2, 3)
        box_layout.addWidget(QtWidgets.QLabel("Further technological correlation"), 8, 0, 2, 2)
        box_layout.addWidget(self.technological, 8, 2, 2, 3)
        box.setLayout(box_layout)

        self.plot = SimpleDistributionPlot(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def initializePage(self):
        # if the parent contains an 'obj' with uncertainty, extract data
        self.setField("uncertainty type", 2)
        obj = getattr(self.wizard(), "obj")
        if isinstance(obj, ExchangeProxyBase) and "pedigree" in obj:
            self.pedigree = obj.get("pedigree", {})
        # Otherwise, try and get something from the parameter.
        elif isinstance(obj, ParameterBase) and "pedigree" in obj.data:
            self.pedigree = obj.data.get("pedigree", {})
        self.check_complete()

    def nextId(self):
        """Ensures that 'Next' button does not show."""
        return -1

    @property
    def pedigree(self) -> tuple:
        return (
            self.reliable.currentIndex() + 1,
            self.complete.currentIndex() + 1,
            self.temporal.currentIndex() + 1,
            self.geographical.currentIndex() + 1,
            self.technological.currentIndex() + 1,
        )

    @pedigree.setter
    def pedigree(self, data: dict) -> None:
        self.reliable.setCurrentIndex(data.get("reliability", 1) - 1)
        self.complete.setCurrentIndex(data.get("completeness", 1) - 1)
        self.temporal.setCurrentIndex(data.get("temporal correlation", 1) - 1)
        self.geographical.setCurrentIndex(data.get("geographical correlation", 1) - 1)
        self.technological.setCurrentIndex(data.get("further technological correlation", 1) - 1)

    @QtCore.Slot(name="constructPedigreeMatrix")
    def check_complete(self) -> None:
        matrix = PedigreeMatrix.from_numbers(self.pedigree)
        self.setField("scale", matrix.calculate())
        self.generate_plot()

    @QtCore.Slot(name="regenPlot")
    def generate_plot(self) -> None:
        """Called whenever a value changes, (re)generate the plot.

        Also tests if all of the visible QLineEdit fields have valid values.
        """
        data = LognormalUncertainty.random_variables(
            LognormalUncertainty.from_dicts(self.wizard().uncertainty_info), 1000
        )
        if not np.any(np.isnan(data)):
            self.plot.plot(data)

# -*- coding: utf-8 -*-
from typing import Union

from bw2data.parameters import ParameterBase
from bw2data.proxies import ExchangeProxyBase
from PySide2 import QtCore, QtGui, QtWidgets
import numpy as np
from stats_arrays import uncertainty_choices as uc

from ..figures import SimpleDistributionPlot
from ..style import style_group_box
from ...bwutils import DistributionGenerator, PedigreeMatrix, UncertainValues
from ...signals import signals


class UncertaintyWizard(QtWidgets.QWizard):
    """Using this wizard, guide the user through selecting an 'uncertainty'
    distribution (and related values) for their activity/process exchanges.

    Note that this can also be used for setting uncertainties on parameters
    """
    CHOICE = 0
    PEDIGREE = 1
    TYPE = 2
    VALUES = 3

    def __init__(self, unc_object: Union[ExchangeProxyBase, ParameterBase], parent=None):
        super().__init__(parent)

        self.obj = unc_object

        self.choice = ChoicePage(self)
        self.pedigree = PedigreeMatrixPage(self)
        self.type = UncertaintyTypePage(self)
        self.values = UncertaintyValuesPage(self)
        self.pages = (
            self.choice, self.pedigree, self.type, self.values
        )

        for i, p in enumerate(self.pages):
            self.setPage(i, p)
        self.setStartId(self.CHOICE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(self.update_uncertainty)

    @property
    def uncertainty_info(self):
        return {
            "uncertainty type": self.field("distribution"),
            "loc": self.field("loc"),
            "scale": self.field("scale"),
            "shape": self.field("shape"),
            "minimum": self.field("minimum"),
            "maximum": self.field("maximum"),
            "negative": False,
        }

    @QtCore.Slot(name="modifyUncertainty")
    def update_uncertainty(self):
        if isinstance(self.obj, ExchangeProxyBase):
            signals.exchange_uncertainty_modified.emit(self.obj, self.uncertainty_info)
        elif isinstance(self.obj, ParameterBase):
            signals.parameter_uncertainty_modified.emit(self.obj, self.uncertainty_info)


class ChoicePage(QtWidgets.QWizardPage):
    """Present three choices to the user:

    - No uncertainty
    - Pedigree matrix
    - (Manual) distribution selection and value editing.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.choice = QtWidgets.QComboBox(self)
        # Set three options, the first is the 'No uncertainty' option.
        # Possibly allows users to quick click through, is this good or bad?
        self.choice.addItems(
            ["No uncertainty", "Pedigree matrix", "Manual selection"]
        )
        self.registerField("uncertain_choice", self.choice, "currentIndex")

        # Startup options
        group = QtWidgets.QGroupBox("How to set uncertainty")
        # Explicitly set the stylesheet to avoid parent classes overriding
        group.setStyleSheet(style_group_box.border_title)
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Define by:"), 0, 0, 1, 1)
        box_layout.addWidget(self.choice, 0, 1, 1, 2)
        group.setLayout(box_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(group)
        self.setLayout(layout)

    def nextId(self):
        """Read out the uncertain_choice field and proceed to related page."""
        choice = self.field("uncertain_choice")
        if choice == 0:
            return UncertaintyWizard.VALUES
        if choice == 1:
            return UncertaintyWizard.PEDIGREE
        if choice == 2:
            return UncertaintyWizard.TYPE


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
        self.is_complete = False

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
        self.registerField("reliable", self.reliable, "currentIndex")
        self.registerField("complete", self.complete, "currentIndex")
        self.registerField("temporal", self.temporal, "currentIndex")
        self.registerField("geographical", self.geographical, "currentIndex")
        self.registerField("technological", self.technological, "currentIndex")
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

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
        self.setLayout(layout)

    def initializePage(self):
        self.check_complete()

    @QtCore.Slot(name="constructPedigreeMatrix")
    def check_complete(self) -> None:
        self.setField("distribution", 2)
        matrix = PedigreeMatrix.from_numbers((
            int(self.field("reliable")) + 1,
            int(self.field("complete")) + 1,
            int(self.field("temporal")) + 1,
            int(self.field("geographical")) + 1,
            int(self.field("technological")) + 1,
        ))
        self.setField("loc", 1)
        self.setField("scale", matrix.calculate())
        self.is_complete = True

    def isComplete(self):
        return self.is_complete

    def nextId(self):
        """ Calculate and set values for fields before moving to next page.
        """
        return UncertaintyWizard.VALUES


class UncertaintyTypePage(QtWidgets.QWizardPage):
    """Present a list of uncertainty types directly retrieved from the `stats_arrays` package.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        box = QtWidgets.QGroupBox("Select the uncertainty distribution")
        box.setStyleSheet(style_group_box.border_title)

        self.distribution = QtWidgets.QComboBox(box)
        self.distribution.addItems([ud.description for ud in uc.choices])
        self.registerField("distribution", self.distribution, "currentIndex")
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Distribution:"), 0, 0, 2, 1)
        box_layout.addWidget(self.distribution, 0, 1, 2, 2)
        box.setLayout(box_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
        self.setLayout(layout)

    def nextId(self):
        return UncertaintyWizard.VALUES


class UncertaintyValuesPage(QtWidgets.QWizardPage):
    """Show values for specific fields and allow user to edit.

    Also, possibly show a graph of the distribution that is updated as
    the values change.

    ('loc', np.NaN),
    ('scale', np.NaN),
    ('shape', np.NaN),
    ('minimum', np.NaN),
    ('maximum', np.NaN),
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)

        self.locale = QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates)
        self.locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        self.validator = QtGui.QDoubleValidator()
        self.validator.setLocale(self.locale)

        box = QtWidgets.QGroupBox("Fill out or change required parameters")
        box.setStyleSheet(style_group_box.border_title)

        self.distribution = QtWidgets.QLabel("")
        self.loc = QtWidgets.QLineEdit()
        self.loc.setValidator(self.validator)
        self.loc.textEdited.connect(self.generate_plot)
        self.loc_label = QtWidgets.QLabel("Mean:")
        self.scale = QtWidgets.QLineEdit()
        self.scale.setValidator(self.validator)
        self.scale.textEdited.connect(self.generate_plot)
        self.scale_label = QtWidgets.QLabel("Scale:")
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
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Distribution:"), 0, 0, 2, 1)
        box_layout.addWidget(self.distribution, 0, 1, 2, 2)
        box_layout.addWidget(self.loc_label, 2, 0, 2, 1)
        box_layout.addWidget(self.loc, 2, 1, 2, 2)
        box_layout.addWidget(self.scale_label, 4, 0, 2, 1)
        box_layout.addWidget(self.scale, 4, 1, 2, 2)
        box_layout.addWidget(self.shape_label, 6, 0, 2, 1)
        box_layout.addWidget(self.shape, 6, 1, 2, 2)
        box_layout.addWidget(self.min_label, 8, 0, 2, 1)
        box_layout.addWidget(self.minimum, 8, 1, 2, 2)
        box_layout.addWidget(self.max_label, 10, 0, 2, 1)
        box_layout.addWidget(self.maximum, 10, 1, 2, 2)
        box.setLayout(box_layout)

        self.registerField("loc", self.loc, "text")
        self.registerField("scale", self.scale, "text")
        self.registerField("shape", self.shape, "text")
        self.registerField("minimum", self.minimum, "text")
        self.registerField("maximum", self.maximum, "text")

        self.plot = SimpleDistributionPlot(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box)
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

    def initializePage(self):
        """Take the information from the previous pages and present the correct
        uncertainty parameters.

        See https://stats-arrays.readthedocs.io/en/latest/index.html for which
        fields to show and hide.
        """
        ud = uc.id_dict[self.field("distribution")]
        self.distribution.setText("<strong>{}</strong>".format(ud.description))

        # Huge if/elif tree to ensure the correct fields are shown.
        if ud.id in {0, 1}:
            self.hide_param("loc", "scale", "shape", "min", "max")
        elif ud.id in {2, 3}:
            self.hide_param("shape", "min", "max")
            self.hide_param("loc", "scale", hide=False)
        elif ud.id in {4, 7}:
            self.hide_param("loc", "scale", "shape")
            self.hide_param("min", "max", hide=False)
        elif ud.id in {5, 6}:
            self.hide_param("scale", "shape")
            self.hide_param("loc", "min", "max", hide=False)
        elif ud.id in {8, 9, 10, 11}:
            self.hide_param("min", "max")
            self.hide_param("loc", "scale", "shape", hide=False)

    def extract_values(self) -> UncertainValues:
        """Return a namedtuple containing values for all of the registered
        fields on this page.
        """
        return UncertainValues(
            loc=float(self.field("loc")) if self.field("loc") else np.nan,
            scale=float(self.field("scale")) if self.field("scale") else np.nan,
            shape=float(self.field("shape")) if self.field("shape") else np.nan,
            min=float(self.field("minimum")) if self.field("minimum") else np.nan,
            max=float(self.field("maximum")) if self.field("maximum") else np.nan
        )

    @QtCore.Slot(name="regenPlot")
    def generate_plot(self) -> None:
        """ Called whenever a value changes, regenerate the plot based on """
        # data = DistributionGenerator.generate_distribution(
        #     self.extract_values(), self.field("distribution")
        # )
        data = None
        if data is not None and not any(np.isnan(data)):
            self.plot.plot(data)

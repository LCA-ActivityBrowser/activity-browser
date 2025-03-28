from logging import getLogger

import numpy as np
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, Slot
from stats_arrays import uncertainty_choices as uncertainty
from stats_arrays.distributions import *

from activity_browser import actions
from .. import application

from ...bwutils import PedigreeMatrix, get_uncertainty_interface
from ...bwutils.uncertainty import EMPTY_UNCERTAINTY
from ..figures import SimpleDistributionPlot

log = getLogger(__name__)


class UncertaintyWizard(QtWidgets.QWizard):
    """Using this wizard, guide the user through selecting an 'uncertainty'
    distribution (and related values) for their activity/process exchanges.

    Note that this can also be used for setting uncertainties on parameters
    """

    TYPE = 0
    PEDIGREE = 1

    complete = Signal(tuple, object)  # feed the CF uncertainty back to the origin

    def __init__(self, unc_object: object, parent=None):
        super().__init__(parent)

        self.obj = get_uncertainty_interface(unc_object)
        self.using_pedigree = False

        self.pedigree = PedigreeMatrixPage(self)
        self.type = UncertaintyTypePage(self)
        self.pages = (self.type, self.pedigree)

        for i, p in enumerate(self.pages):
            self.setPage(i, p)
        self.setStartId(self.TYPE)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.button(QtWidgets.QWizard.FinishButton).clicked.connect(
            self.update_uncertainty
        )
        self.pedigree.enable_pedigree.connect(self.used_pedigree)
        self.extract_uncertainty()

    @staticmethod
    def standard_dist_fields(dist_id: int) -> list:
        if dist_id in {2, 3}:
            return ["loc", "scale"]
        elif dist_id in {4, 7}:
            return ["minimum", "maximum"]
        elif dist_id in {5, 6}:
            return ["loc", "minimum", "maximum"]
        elif dist_id in {8, 9, 10, 11, 12}:
            return ["loc", "scale", "shape"]
        else:
            return []

    @property
    def uncertainty_info(self) -> dict:
        data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
        data["uncertainty type"] = self.field("uncertainty type")
        data["negative"] = bool(self.field("negative"))
        for field in self.standard_dist_fields(data["uncertainty type"]):
            data[field] = float(self.field(field))
        return data

    @Slot(bool, name="togglePedigree")
    def used_pedigree(self, toggle: bool) -> None:
        self.using_pedigree = toggle

    @Slot(name="modifyUncertainty")
    def update_uncertainty(self):
        """Update the uncertainty information of the relevant object, optionally
        including a pedigree update.
        """
        self.amount_mean_test()
        if self.obj.data_type == "exchange":
            actions.ExchangeModify.run(self.obj.data, self.uncertainty_info)
            if self.using_pedigree:
                actions.ExchangeModify.run(
                    self.obj.data, {"pedigree": self.pedigree.matrix.factors}
                )
        elif self.obj.data_type == "parameter":
            actions.ParameterModify.run(self.obj.data, "data", self.uncertainty_info)
            if self.using_pedigree:
                actions.ParameterModify.run(
                    self.obj.data, "data", self.pedigree.matrix.factors
                )
        elif self.obj.data_type == "cf":
            self.complete.emit(self.obj.data, self.uncertainty_info)

    def extract_uncertainty(self) -> None:
        """Used to extract possibly existing uncertainty information from the
        given exchange/parameter

        Exchange objects have uncertainty shortcuts built in, other
        objects which sometimes have uncertainty do not.
        """
        for k, v in self.obj.uncertainty.items():
            if k in EMPTY_UNCERTAINTY:
                self.setField(k, v)

        # If no loc/mean value is set yet, convert the amount.
        if not self.field("loc") or self.field("loc") == "nan":
            val = getattr(self.obj, "amount", 1.0)
            if self.field("uncertainty type") == LognormalUncertainty.id:
                val = np.log(val)
            self.setField("loc", str(val))
        # Let the other fields default to 'nan' if no values are set.
        for f in ("scale", "shape", "maximum", "minimum"):
            if not self.field(f):
                self.setField(f, "nan")

    def extract_lognormal_loc(self) -> None:
        """Special handling for looking at the uncertainty['loc'] field

        This should only be used when the 'original' set uncertainty is
        lognormal.
        """
        mean = getattr(self.obj, "amount", 1.0)
        loc = self.obj.uncertainty.get("loc", np.NaN)
        if not np.isnan(loc) and self.obj.uncertainty_type != LognormalUncertainty:
            loc = np.log(loc)
        if np.isnan(loc):
            loc = np.log(mean)
        self.setField("loc", str(loc))

    def amount_mean_test(self) -> None:
        """Asks if the 'amount' of the object should be updated to account for
        the user altering the loc/mean value.
        """
        uc_type = self.field("uncertainty type")
        no_change = {UndefinedUncertainty.id, NoUncertainty.id}
        mean = float(self.field("loc"))
        if uc_type == LognormalUncertainty.id:
            mean = np.exp(mean)
        elif uc_type in self.type.mean_is_calculated:
            mean = self.type.calculate_mean
        if not np.isclose(self.obj.amount, mean) and uc_type not in no_change:
            msg = (
                "Do you want to update the 'amount' field to match mean?"
                "\nAmount: {}\tMean: {}".format(self.obj.amount, mean)
            )
            choice = QtWidgets.QMessageBox.question(
                self,
                "Amount differs from mean",
                msg,
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )
            if choice == QtWidgets.QMessageBox.Yes:
                if self.obj.data_type == "exchange":
                    actions.ExchangeModify.run(self.obj.data, {"amount": mean})

                elif self.obj.data_type == "parameter":
                    try:
                        actions.ParameterModify.run(self.obj.data, "amount", mean)
                    except Exception as e:
                        QtWidgets.QMessageBox.warning(
                            application.main_window,
                            "Could not save changes",
                            str(e),
                            QtWidgets.QMessageBox.Ok,
                            QtWidgets.QMessageBox.Ok,
                        )
                elif self.obj.data_type == "cf":
                    altered = {k: v for k, v in self.obj.uncertainty.items()}
                    altered["amount"] = mean
                    data = [*self.obj.data]
                    data[1] = altered
                    self.obj = get_uncertainty_interface(tuple(data))


class UncertaintyTypePage(QtWidgets.QWizardPage):
    """Present a list of uncertainty types directly retrieved from the `stats_arrays` package."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.dist = None
        self.complete = False
        self.goto_pedigree = False
        self.previous = None
        self.mean_is_calculated = {
            TriangularUncertainty.id,
            UniformUncertainty.id,
            DiscreteUniform.id,
            BetaUncertainty.id,
        }

        # Selection of uncertainty distribution.
        box1 = QtWidgets.QGroupBox("Select the uncertainty distribution")
        self.distribution = QtWidgets.QComboBox(box1)
        self.distribution.addItems([ud.description for ud in uncertainty.choices])
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
        self.field_box = QtWidgets.QGroupBox("Fill out or change required parameters")
        self.locale = QtCore.QLocale(
            QtCore.QLocale.English, QtCore.QLocale.UnitedStates
        )
        self.locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        self.validator = QtGui.QDoubleValidator()
        self.validator.setLocale(self.locale)
        self.loc = QtWidgets.QLineEdit()
        self.loc.setValidator(self.validator)
        self.loc.textEdited.connect(self.balance_mean_with_loc)
        self.loc.textEdited.connect(self.check_negative)
        self.loc.textEdited.connect(self.generate_plot)
        self.loc_label = QtWidgets.QLabel("Loc:")
        self.mean = QtWidgets.QLineEdit()
        self.mean.setValidator(self.validator)
        self.mean.textEdited.connect(self.balance_loc_with_mean)
        self.mean.textEdited.connect(self.check_negative)
        self.mean.textEdited.connect(self.generate_plot)
        self.mean_label = QtWidgets.QLabel("Mean:")
        self.blocked_label = QtWidgets.QLabel("Mean:")
        self.blocked_mean = QtWidgets.QLineEdit("nan")
        self.blocked_mean.setDisabled(True)
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
        box_layout.addWidget(self.blocked_label, 0, 0)
        box_layout.addWidget(self.blocked_mean, 0, 1)
        box_layout.addWidget(self.loc_label, 2, 0)
        box_layout.addWidget(self.loc, 2, 1)
        box_layout.addWidget(self.mean_label, 2, 3)
        box_layout.addWidget(self.mean, 2, 4)
        box_layout.addWidget(self.scale_label, 4, 0)
        box_layout.addWidget(self.scale, 4, 1)
        box_layout.addWidget(self.shape_label, 6, 0)
        box_layout.addWidget(self.shape, 6, 1)
        box_layout.addWidget(self.min_label, 8, 0)
        box_layout.addWidget(self.minimum, 8, 1)
        box_layout.addWidget(self.max_label, 10, 0)
        box_layout.addWidget(self.maximum, 10, 1)
        self.field_box.setLayout(box_layout)

        self.registerField("loc", self.loc, "text")
        self.registerField("scale", self.scale, "text")
        self.registerField("shape", self.shape, "text")
        self.registerField("minimum", self.minimum, "text")
        self.registerField("maximum", self.maximum, "text")
        self.registerField("negative", self.negative, "checked")

        self.plot = SimpleDistributionPlot(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(box1)
        layout.addWidget(self.field_box)
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

    def special_distribution_handling(self):
        """Special kansas city shuffling for this distribution."""
        if self.dist.id == LognormalUncertainty.id:
            self.mean.setHidden(False)
            self.mean_label.setHidden(False)
            # Convert 'mean' to lognormal mean
            if self.previous is not None and self.previous != LognormalUncertainty.id:
                self.wizard().extract_lognormal_loc()
                self.balance_mean_with_loc()
        else:
            self.mean.setHidden(True)
            self.mean_label.setHidden(True)
            # Override the lognormal mean and copy the amount in its place
            if self.previous and self.previous == LognormalUncertainty.id:
                self.loc.setText(str(getattr(self.wizard().obj, "amount", 1)))
        # Hide or show additional untouchable 'mean' field.
        if self.dist.id in self.mean_is_calculated:
            self.blocked_label.setHidden(False)
            self.blocked_mean.setHidden(False)
        else:
            self.blocked_label.setHidden(True)
            self.blocked_mean.setHidden(True)
        self.loc_label.setText(self.distribution_loc_label)
        self.previous = self.dist.id
        self.field_box.updateGeometry()

    @property
    def distribution_loc_label(self) -> str:
        """Many distributions have a special name for the value that is entered
        into the 'loc' field.
        """
        if self.dist.id == LognormalUncertainty.id:
            return "Loc (ln(mean)):"
        elif self.dist.id == TriangularUncertainty.id:
            return "Mode:"
        elif self.dist.id == BetaUncertainty.id:
            return "Loc / alpha:"
        elif self.dist.id in {GammaUncertainty.id, WeibullUncertainty.id}:
            return "Loc / offset:"
        else:
            return "Mean:"

    @property
    def calculate_mean(self) -> float:
        """Some distributions do not specifically use a mean to generate
        their random values, in those cases present a calculated mean.

        If any of the data is missing or the calculation fails, float('nan')
        is returned.
        """
        array = self.dist.from_dicts(self.wizard().uncertainty_info)
        try:
            calc = self.dist.statistics(array).get("mean")
        # Catch exception for DiscreteUniform (https://bitbucket.org/cmutel/stats_arrays/pull-requests/5/)
        except TypeError:
            array = self.dist.fix_nan_minimum(array)
            calc = (array["maximum"] + array["minimum"]) / 2
        calc = calc.mean() if isinstance(calc, np.ndarray) else calc
        return float(calc)

    @Slot(name="changeDistribution")
    def distribution_selection(self):
        """Selected distribution and present the correct uncertainty parameters.

        See https://stats-arrays.readthedocs.io/en/latest/index.html for which
        fields to show and hide.
        """
        self.dist = uncertainty.id_dict[self.distribution.currentIndex()]

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
        self.special_distribution_handling()
        self.generate_plot()

    def completed_active_fields(self) -> bool:
        """Returns a boolean value based on the distribution id.
        If the distribution contains an average, minimum and maximum this forces the
        average to exist exclusively within these bounds"""
        completed = False
        if self.dist.id in {0, 1}:
            completed = True
        elif self.dist.id in {2, 3}:
            completed = all(
                [
                    field.hasAcceptableInput() and field.text()
                    for field in (self.loc, self.scale)
                ]
            )
        elif self.dist.id in {4, 7}:
            completed = all(
                [
                    field.hasAcceptableInput() and field.text()
                    for field in (self.minimum, self.maximum)
                ]
            )
        elif self.dist.id in {5, 6}:
            completed = all(
                [
                    field.hasAcceptableInput() and field.text()
                    for field in (self.minimum, self.maximum, self.loc)
                ]
            ) and (
                float(self.minimum.text())
                < float(self.loc.text())
                < float(self.maximum.text())
            )
        elif self.dist.id in {8, 9, 10, 11, 12}:
            completed = all(
                [
                    field.hasAcceptableInput() and field.text()
                    for field in (self.scale, self.shape, self.loc)
                ]
            )
        return completed

    @Slot(name="locToMean")
    def balance_mean_with_loc(self):
        if self.loc.text():
            self.mean.setText(str(np.exp(float(self.loc.text()))))

    @Slot(name="meanToLoc")
    def balance_loc_with_mean(self):
        if not self.mean.hasAcceptableInput():
            self.loc.setText("nan")
            return
        val = float(self.mean.text() if self.mean.text() else "nan")
        val = -1 * val if val < 0 else val
        self.loc.setText(str(np.log(val) if val != 0 else float("nan")))

    @Slot(name="testValueNegative")
    def check_negative(self) -> None:
        """Determine which QLineEdit to use to set the negative value.

        Another special edge-case for the lognormal distribution.
        """
        if not self.mean.hasAcceptableInput():
            return
        val = float(self.mean.text() if self.mean.text() else "nan")
        if self.dist.id == LognormalUncertainty.id and val < 0:
            self.setField("negative", True)
        else:
            self.setField("negative", False)

    def initializePage(self) -> None:
        self.distribution_selection()
        self.balance_mean_with_loc()

    def nextId(self) -> int:
        if self.goto_pedigree:
            return UncertaintyWizard.PEDIGREE
        return -1

    def isComplete(self) -> bool:
        return self.complete

    @Slot(name="gotoPedigreePage")
    def pedigree_page(self) -> None:
        self.goto_pedigree = True
        self.wizard().next()

    @Slot(name="regenPlot")
    def generate_plot(self) -> None:
        """Called whenever a value changes, (re)generate the plot.

        Also tests if all of the visible QLineEdit fields have valid values.
        """
        self.complete = self.completed_active_fields()
        no_dist = self.dist.id in {UndefinedUncertainty.id, NoUncertainty.id}
        if self.complete or no_dist:
            array = self.dist.from_dicts(self.wizard().uncertainty_info)
            if self.dist.id in self.mean_is_calculated:
                mean = self.calculate_mean
                self.blocked_mean.setText(str(mean))
            if self.dist.id == LognormalUncertainty.id:
                mean = self.dist.statistics(array).get("median")
            elif no_dist:
                mean = self.wizard().obj.amount
            else:
                mean = self.dist.statistics(array).get("mean")
            data = self.dist.random_variables(array, 1000)
            if not np.any(np.isnan(data)):
                self.plot.plot(data, mean)
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

    enable_pedigree = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFinalPage(True)
        self.matrix = None

        self.field_box = QtWidgets.QGroupBox("Fill out or change required parameters")
        self.locale = QtCore.QLocale(
            QtCore.QLocale.English, QtCore.QLocale.UnitedStates
        )
        self.locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
        self.validator = QtGui.QDoubleValidator()
        self.validator.setLocale(self.locale)
        self.loc = QtWidgets.QLineEdit()
        self.loc.setValidator(self.validator)
        self.loc.textEdited.connect(self.balance_mean_with_loc)
        self.loc.textEdited.connect(self.check_negative)
        self.loc.textEdited.connect(self.check_complete)
        self.mean = QtWidgets.QLineEdit()
        self.mean.setValidator(self.validator)
        self.mean.textEdited.connect(self.balance_loc_with_mean)
        self.mean.textEdited.connect(self.check_negative)
        self.mean.textEdited.connect(self.check_complete)
        box_layout = QtWidgets.QGridLayout()
        box_layout.addWidget(QtWidgets.QLabel("Loc (ln(mean)):"), 0, 0)
        box_layout.addWidget(self.loc, 0, 1)
        box_layout.addWidget(QtWidgets.QLabel("Mean:"), 0, 3)
        box_layout.addWidget(self.mean, 0, 4)
        self.field_box.setLayout(box_layout)

        box = QtWidgets.QGroupBox("Select pedigree values")

        self.reliable = QtWidgets.QComboBox(box)
        self.reliable.addItems(
            [
                "1) Verified data based on measurements",
                "2) Verified data partly based on assumptions",
                "3) Non-verified data partly based on qualified measurements",
                "4) Qualified estimate",
                "5) Non-qualified estimate",
            ]
        )
        self.complete = QtWidgets.QComboBox(box)
        self.complete.addItems(
            [
                "1) Representative relevant data from all sites, over an adequate period",
                "2) Representative relevant data from >50% sites, over an adequate period",
                "3) Representative relevant data from <50% sites OR >50%, but over shorter period",
                "4) Representative relevant data from one site OR some sites but over shorter period",
                "5) Representativeness unknown",
            ]
        )
        self.temporal = QtWidgets.QComboBox(box)
        self.temporal.addItems(
            [
                "1) Data less than 3 years old",
                "2) Data less than 6 years old",
                "3) Data less than 10 years old",
                "4) Data less than 15 years old",
                "5) Data age unknown or more than 15 years old",
            ]
        )
        self.geographical = QtWidgets.QComboBox(box)
        self.geographical.addItems(
            [
                "1) Data from area under study",
                "2) Average data from larger area in which area under study is included",
                "3) Data from area with similar production conditions",
                "4) Data from area with slightly similar production conditions",
                "5) Data from unknown OR distinctly different area",
            ]
        )
        self.technological = QtWidgets.QComboBox(box)
        self.technological.addItems(
            [
                "1) Data from enterprises, processes and materials under study",
                "2) Data from processes and materials under study, different enterprise",
                "3) Data from processes and materials under study from different technology",
                "4) Data on related processes and materials",
                "5) Data on related processes on lab scale OR from different technology",
            ]
        )
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
        box_layout.addWidget(
            QtWidgets.QLabel("Further technological correlation"), 8, 0, 2, 2
        )
        box_layout.addWidget(self.technological, 8, 2, 2, 3)
        box.setLayout(box_layout)

        self.plot = SimpleDistributionPlot(self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.field_box)
        layout.addWidget(box)
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def cleanupPage(self):
        self.enable_pedigree.emit(False)

    def initializePage(self):
        # if the parent contains an 'obj' with uncertainty, extract data
        self.setField("uncertainty type", 2)
        self.loc.setText(self.field("loc"))
        self.balance_mean_with_loc()
        obj = getattr(self.wizard(), "obj")
        try:
            matrix = PedigreeMatrix.from_dict(obj.uncertainty.get("pedigree", {}))
            self.pedigree = matrix.factors
        except AssertionError as e:
            log.info("Could not extract pedigree data: {}".format(str(e)))
            self.pedigree = {}
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
        self.technological.setCurrentIndex(
            data.get("further technological correlation", 1) - 1
        )

    @Slot(name="locToMean")
    def balance_mean_with_loc(self):
        self.setField("loc", self.loc.text())
        if self.loc.text():
            self.mean.setText(str(np.exp(float(self.loc.text()))))

    @Slot(name="meanToLoc")
    def balance_loc_with_mean(self):
        if not self.mean.hasAcceptableInput():
            self.loc.setText("nan")
            return
        val = float(self.mean.text() if self.mean.text() else "nan")
        val = -1 * val if val < 0 else val
        loc_val = str(np.log(val)) if val != 0 else "nan"
        self.loc.setText(loc_val)
        self.setField("loc", loc_val)

    @Slot(name="testValueNegative")
    def check_negative(self) -> None:
        """Determine which QLineEdit to use to set the negative value.

        Another special edge-case for the lognormal distribution.
        """
        if not self.mean.hasAcceptableInput():
            return
        val = float(self.mean.text() if self.mean.text() else "nan")
        if val < 0:
            self.setField("negative", True)
        else:
            self.setField("negative", False)

    @Slot(name="constructPedigreeMatrix")
    def check_complete(self) -> None:
        self.matrix = PedigreeMatrix.from_numbers(self.pedigree)
        self.setField("scale", self.matrix.calculate())
        self.generate_plot()

    @Slot(name="regenPlot")
    def generate_plot(self) -> None:
        """Called whenever a value changes, (re)generate the plot.

        Also tests if all of the visible QLineEdit fields have valid values.
        """
        array = LognormalUncertainty.from_dicts(self.wizard().uncertainty_info)
        median = LognormalUncertainty.statistics(array).get("median")
        data = LognormalUncertainty.random_variables(array, 1000)
        if not np.any(np.isnan(data)):
            self.plot.plot(data, median)
        self.enable_pedigree.emit(True)

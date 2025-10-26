from __future__ import annotations

from logging import getLogger
from typing import Optional, Tuple

import numpy as np
import seaborn as sns

from qtpy import QtCore, QtGui, QtWidgets
from stats_arrays import uncertainty_choices as uncertainty
from stats_arrays.distributions import *  # noqa: F401,F403 - mirror wizard usage

from ...ui.widgets.plot import ABPlot
from ...bwutils.uncertainty import EMPTY_UNCERTAINTY

log = getLogger(__name__)


class UncertaintyDialog(QtWidgets.QDialog):
	"""Single-step dialog for defining a stats_arrays uncertainty.

	Mirrors the behavior of the UncertaintyWizard type page but returns a
	stats_arrays structured array on accept.

	Usage:
		ok, array = UncertaintyDialog.get_uncertainty(parent, initial=dict(...))
		if ok:
			# array is a numpy structured array compatible with stats_arrays
	"""

	def __init__(self, parent=None, initial: Optional[dict] = None):
		super().__init__(parent)
		self.setWindowTitle("Set Uncertainty")
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

		# State
		self.dist = None
		self.result_array = None  # Filled on accept
		self.previous_dist_id: Optional[int] = None
		self.mean_is_calculated = {
			TriangularUncertainty.id,
			UniformUncertainty.id,
			DiscreteUniform.id,
			BetaUncertainty.id,
		}

		# Top: distribution selection
		box1 = QtWidgets.QGroupBox("Select the uncertainty distribution")
		self.distribution = QtWidgets.QComboBox(box1)
		self.distribution.addItems([ud.description for ud in uncertainty.choices])
		self.distribution.currentIndexChanged.connect(self._on_distribution_changed)

		header_layout = QtWidgets.QGridLayout()
		header_layout.addWidget(QtWidgets.QLabel("Distribution:"), 0, 0)
		header_layout.addWidget(self.distribution, 0, 1)
		box1.setLayout(header_layout)

		# Middle: parameters
		self.fields_box = QtWidgets.QGroupBox("Fill out required parameters")
		self.locale = QtCore.QLocale(
			QtCore.QLocale.English, QtCore.QLocale.UnitedStates
		)
		self.locale.setNumberOptions(QtCore.QLocale.RejectGroupSeparator)
		self.validator = QtGui.QDoubleValidator()
		self.validator.setLocale(self.locale)

		# loc/mean
		self.loc_label = QtWidgets.QLabel("Loc:")
		self.loc = QtWidgets.QLineEdit()
		self.loc.setValidator(self.validator)
		self.loc.textEdited.connect(self._sync_mean_from_loc)
		self.loc.textEdited.connect(self._check_negative)
		self.loc.textEdited.connect(self._generate_plot)

		self.mean_label = QtWidgets.QLabel("Mean:")
		self.mean = QtWidgets.QLineEdit()
		self.mean.setValidator(self.validator)
		self.mean.textEdited.connect(self._sync_loc_from_mean)
		self.mean.textEdited.connect(self._check_negative)
		self.mean.textEdited.connect(self._generate_plot)

		# Calculated mean (read-only) for some dists
		self.calc_mean_label = QtWidgets.QLabel("Mean:")
		self.calc_mean = QtWidgets.QLineEdit("nan")
		self.calc_mean.setDisabled(True)

		# Other parameters
		self.scale_label = QtWidgets.QLabel("Sigma/scale:")
		self.scale = QtWidgets.QLineEdit()
		self.scale.setValidator(self.validator)
		self.scale.textEdited.connect(self._generate_plot)

		self.shape_label = QtWidgets.QLabel("Shape:")
		self.shape = QtWidgets.QLineEdit()
		self.shape.setValidator(self.validator)
		self.shape.textEdited.connect(self._generate_plot)

		self.min_label = QtWidgets.QLabel("Minimum:")
		self.minimum = QtWidgets.QLineEdit()
		self.minimum.setValidator(self.validator)
		self.minimum.textEdited.connect(self._generate_plot)

		self.max_label = QtWidgets.QLabel("Maximum:")
		self.maximum = QtWidgets.QLineEdit()
		self.maximum.setValidator(self.validator)
		self.maximum.textEdited.connect(self._generate_plot)

		# Hidden flag for negative mean on lognormal
		self.negative = QtWidgets.QRadioButton(self)
		self.negative.setChecked(False)
		self.negative.setHidden(True)

		params_layout = QtWidgets.QGridLayout()
		# row 0: read-only calculated mean (will be hidden for most dists)
		params_layout.addWidget(self.calc_mean_label, 0, 0)
		params_layout.addWidget(self.calc_mean, 0, 1)
		# row 1: loc/mean pair
		params_layout.addWidget(self.loc_label, 1, 0)
		params_layout.addWidget(self.loc, 1, 1)
		params_layout.addWidget(self.mean_label, 1, 3)
		params_layout.addWidget(self.mean, 1, 4)
		# row 2+: other params
		params_layout.addWidget(self.scale_label, 2, 0)
		params_layout.addWidget(self.scale, 2, 1)
		params_layout.addWidget(self.shape_label, 3, 0)
		params_layout.addWidget(self.shape, 3, 1)
		params_layout.addWidget(self.min_label, 4, 0)
		params_layout.addWidget(self.minimum, 4, 1)
		params_layout.addWidget(self.max_label, 5, 0)
		params_layout.addWidget(self.maximum, 5, 1)
		self.fields_box.setLayout(params_layout)

		# Bottom: plot
		self.plot = SimpleDistributionPlot(self)

		# Buttons
		self.buttons = QtWidgets.QDialogButtonBox(
			QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
		)
		self.buttons.accepted.connect(self._on_accept)
		self.buttons.rejected.connect(self.reject)

		# Layout
		layout = QtWidgets.QVBoxLayout()
		layout.addWidget(box1)
		layout.addWidget(self.fields_box)
		layout.addWidget(self.plot)
		layout.addWidget(self.buttons)
		self.setLayout(layout)

		# Initialize values (defaults or provided initial)
		self._apply_initial(initial or {})
		self._on_distribution_changed(self.distribution.currentIndex())
		self._sync_mean_from_loc()
		self._generate_plot()

	# ---------- Public API ----------
	@staticmethod
	def get_uncertainty(
		parent=None, initial: Optional[dict] = None
	) -> Tuple[bool, Optional[np.ndarray]]:
		dlg = UncertaintyDialog(parent, initial=initial)
		ok = dlg.exec_() == QtWidgets.QDialog.Accepted
		return ok, dlg.result_array if ok else None

	# ---------- Internal helpers ----------
	def _apply_initial(self, initial: dict) -> None:
		# Use EMPTY_UNCERTAINTY defaults, overridden by initial
		data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
		data.update(initial or {})
		# Distribution
		try:
			uc_type = int(data.get("uncertainty type", 0))
		except Exception:
			uc_type = 0
		self.distribution.setCurrentIndex(uc_type)
		# Fields (string form for QLineEdit)
		def to_str(val):
			return "nan" if val is None or (isinstance(val, float) and np.isnan(val)) else str(val)

		self.loc.setText(to_str(data.get("loc", np.nan)))
		self.scale.setText(to_str(data.get("scale", np.nan)))
		self.shape.setText(to_str(data.get("shape", np.nan)))
		self.minimum.setText(to_str(data.get("minimum", np.nan)))
		self.maximum.setText(to_str(data.get("maximum", np.nan)))
		self._check_negative()

	@property
	def _distribution_loc_label(self) -> str:
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

	def _hide_params(self, *params, hide: bool = True) -> None:
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

	def _on_distribution_changed(self, index: int) -> None:
		self.dist = uncertainty.id_dict[index]

		# Show/hide fields per distribution (mirror wizard)
		if self.dist.id in {0, 1}:  # Undefined / NoUncertainty
			self._hide_params("loc", "scale", "shape", "min", "max")
		elif self.dist.id in {2, 3}:  # Normal / Lognormal
			self._hide_params("shape", "min", "max")
			self._hide_params("loc", "scale", hide=False)
		elif self.dist.id in {4, 7}:  # Uniform / DiscreteUniform
			self._hide_params("loc", "scale", "shape")
			self._hide_params("min", "max", hide=False)
		elif self.dist.id in {5, 6}:  # Triangular / Bernoulli-like (min/max/loc)
			self._hide_params("scale", "shape")
			self._hide_params("loc", "min", "max", hide=False)
		elif self.dist.id in {8, 9, 10, 11, 12}:  # Other 3-param
			self._hide_params("min", "max")
			self._hide_params("loc", "scale", "shape", hide=False)

		# Special handling (lognormal and calculated mean label)
		if self.dist.id == LognormalUncertainty.id:
			self.mean.setHidden(False)
			self.mean_label.setHidden(False)
			# Convert existing loc to log-space if coming from non-lognormal
			if self.previous_dist_id is not None and self.previous_dist_id != LognormalUncertainty.id:
				self._extract_lognormal_loc_from_mean()
				self._sync_mean_from_loc()
		else:
			self.mean.setHidden(True)
			self.mean_label.setHidden(True)
			# If switching away from lognormal, set loc to linear amount if mean present
			if self.previous_dist_id == LognormalUncertainty.id:
				try:
					mean_val = float(self.mean.text()) if self.mean.text() else np.nan
					if not np.isnan(mean_val):
						self.loc.setText(str(mean_val))
				except Exception:
					pass

		# Calculated mean visibility
		show_calc = self.dist.id in self.mean_is_calculated
		self.calc_mean_label.setHidden(not show_calc)
		self.calc_mean.setHidden(not show_calc)

		# Update labels
		self.loc_label.setText(self._distribution_loc_label)
		self.previous_dist_id = self.dist.id
		self.fields_box.updateGeometry()

		# Update plot and OK state
		self._generate_plot()
		self._update_ok_state()

	def _extract_lognormal_loc_from_mean(self) -> None:
		"""Set loc to ln(mean) when switching to lognormal, if mean is known."""
		try:
			mtxt = self.mean.text().strip()
			if not mtxt:
				return
			val = float(mtxt)
			if val == 0:
				self.loc.setText("nan")
			else:
				val = -1 * val if val < 0 else val
				self.loc.setText(str(np.log(val)))
		except Exception:
			self.loc.setText("nan")

	def _sync_mean_from_loc(self) -> None:
		if not self.loc.text():
			return
		try:
			self.mean.setText(str(np.exp(float(self.loc.text()))))
		except Exception:
			self.mean.setText("nan")
		self._update_ok_state()

	def _sync_loc_from_mean(self) -> None:
		if not self.mean.hasAcceptableInput():
			self.loc.setText("nan")
			self._update_ok_state()
			return
		try:
			val = float(self.mean.text()) if self.mean.text() else float("nan")
		except Exception:
			val = float("nan")
		if np.isnan(val) or val == 0:
			self.loc.setText("nan")
		else:
			val = -1 * val if val < 0 else val
			self.loc.setText(str(np.log(val)))
		self._update_ok_state()

	def _check_negative(self) -> None:
		# Special case for lognormal negative mean
		try:
			if not self.mean.hasAcceptableInput():
				return
			val = float(self.mean.text()) if self.mean.text() else float("nan")
		except Exception:
			val = float("nan")
		self.negative.setChecked(bool(not np.isnan(val) and val < 0))

	def _standard_dist_fields(self, dist_id: int) -> list:
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
	def _uncertainty_info(self) -> dict:
		data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
		data["uncertainty type"] = self.distribution.currentIndex()
		data["negative"] = bool(self.negative.isChecked())
		# Pull values from widgets
		def as_float(txt: str) -> float:
			try:
				val = float(txt)
				return val
			except Exception:
				return float("nan")

		for field in self._standard_dist_fields(data["uncertainty type"]):
			widget = {
				"loc": self.loc,
				"scale": self.scale,
				"shape": self.shape,
				"minimum": self.minimum,
				"maximum": self.maximum,
			}[field]
			data[field] = as_float(widget.text())
		return data

	def _completed_active_fields(self) -> bool:
		# Mirror wizard validations
		dist_id = self.dist.id
		def ok_lineedit(le: QtWidgets.QLineEdit) -> bool:
			return bool(le.hasAcceptableInput() and le.text())

		if dist_id in {0, 1}:
			return True
		elif dist_id in {2, 3}:
			return ok_lineedit(self.loc) and ok_lineedit(self.scale)
		elif dist_id in {4, 7}:
			return ok_lineedit(self.minimum) and ok_lineedit(self.maximum)
		elif dist_id in {5, 6}:
			if not (ok_lineedit(self.minimum) and ok_lineedit(self.maximum) and ok_lineedit(self.loc)):
				return False
			try:
				return float(self.minimum.text()) < float(self.loc.text()) < float(self.maximum.text())
			except Exception:
				return False
		elif dist_id in {8, 9, 10, 11, 12}:
			return ok_lineedit(self.scale) and ok_lineedit(self.shape) and ok_lineedit(self.loc)
		return False

	def _update_ok_state(self) -> None:
		ok_btn = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
		ok_btn.setEnabled(self._completed_active_fields())

	def _generate_plot(self) -> None:
		# Update calculated mean if applicable and render sample
		if self.dist is None:
			return
		complete = self._completed_active_fields() or self.dist.id in {UndefinedUncertainty.id, NoUncertainty.id}
		if not complete:
			self._update_ok_state()
			return
		array = self.dist.from_dicts(self._uncertainty_info)
		# Calculated mean display for specific distributions
		if self.dist.id in self.mean_is_calculated:
			try:
				calc = self.dist.statistics(array).get("mean")
			except TypeError:
				# DiscreteUniform workaround
				array = self.dist.fix_nan_minimum(array)
				calc = (array["maximum"] + array["minimum"]) / 2
			calc = calc.mean() if isinstance(calc, np.ndarray) else calc
			self.calc_mean.setText(str(float(calc)))
		# Vertical line value
		if self.dist.id == LognormalUncertainty.id:
			vline = self.dist.statistics(array).get("median")
		elif self.dist.id in {UndefinedUncertainty.id, NoUncertainty.id}:
			# Best effort: use loc as "mean" placeholder
			try:
				vline = float(self.loc.text()) if self.loc.text() else np.nan
			except Exception:
				vline = np.nan
		else:
			vline = self.dist.statistics(array).get("mean")
		# Sample data
		data = self.dist.random_variables(array, 1000)
		if not np.any(np.isnan(data)):
			try:
				self.plot.plot(data, vline)
			except RuntimeError as e:
				log.error("%s: plotting failed, retry without KDE", e)
				try:
					sns.histplot(data.T, kde=False, stat="density", ax=self.plot.ax, edgecolor="none")
					self.plot.ax.axvline(vline, label="Mean / amount", c="r", ymax=0.98)
					self.plot.ax.legend(loc="upper right")
					self.plot.canvas.draw()
				except Exception:
					pass
		self._update_ok_state()

	def _on_accept(self) -> None:
		try:
			self.result_array = self.dist.from_dicts(self._uncertainty_info)
		except Exception as e:
			QtWidgets.QMessageBox.warning(
				self,
				"Invalid uncertainty",
				str(e),
				QtWidgets.QMessageBox.Ok,
				QtWidgets.QMessageBox.Ok,
			)
			return
		self.accept()


class SimpleDistributionPlot(ABPlot):
	def plot(self, data: np.ndarray, mean: float, label: str = "Value"):
		self.reset_plot()
		try:
			sns.histplot(data.T, kde=True, stat="density", ax=self.ax, edgecolor="none")
		except RuntimeError as e:
			log.error("%s: Plotting without KDE.", e)
			sns.histplot(data.T, kde=False, stat="density", ax=self.ax, edgecolor="none")
		self.ax.set_xlabel(label)
		self.ax.set_ylabel("Probability density")
		# Add vertical line at given mean of x-axis
		self.ax.axvline(mean, label="Mean / amount", c="r", ymax=0.98)
		self.ax.legend(loc="upper right")
		_, height = self.canvas.get_width_height()
		self.setMinimumHeight(height / 2)
		self.canvas.draw()


__all__ = ["UncertaintyDialog"]


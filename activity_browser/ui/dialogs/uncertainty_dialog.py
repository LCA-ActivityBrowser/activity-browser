from __future__ import annotations

from loguru import logger
from typing import Optional, Tuple

import numpy as np
import seaborn as sns

from qtpy import QtCore, QtGui, QtWidgets
import stats_arrays as sa

from activity_browser.ui.widgets import ABPlot

# ``stats_arrays`` validation uses a short random draw (same cost as preview path).
_UNCERTAINTY_VALIDATION_N = 24
# Histogram preview: keep N modest; ``sns.histplot(..., kde=True)`` can be very slow on
# extreme scales / near-degenerate data even though ``random_variables`` is only O(n).
_UNCERTAINTY_PREVIEW_DRAW_N = 500
# Linear-axis preview: cap bin count so wide-range (e.g. lognormal with large σ) stays cheaper to draw.
_UNCERTAINTY_PREVIEW_HIST_BINS = 36


def _try_build_validate_sample(
	dist,
	info: dict,
	n: int,
) -> Tuple[Optional[np.ndarray], Optional[str]]:
	"""Build params via ``from_dicts``, run ``stats_arrays`` :meth:`validate`, then a short draw.

	Returns ``(array, None)`` on success, or ``(None, message)`` where *message* is the
	exception string from ``stats_arrays`` (e.g. :class:`InvalidParamsError`) or NumPy.
	"""
	try:
		array = dist.from_dicts(info)
		dist.validate(array)
		dist.random_variables(array, n)
		return array, None
	except Exception as e:
		msg = str(e).strip() or e.__class__.__name__
		return None, msg


EMPTY_UNCERTAINTY = {
    "uncertainty type": sa.UndefinedUncertainty.id,
    "loc": np.NaN,
    "scale": np.NaN,
    "shape": np.NaN,
    "minimum": np.NaN,
    "maximum": np.NaN,
    "negative": False,
}


def _uncertainty_dict_is_sampleable(data: dict) -> bool:
	"""True if ``stats_arrays`` accepts parameters (``validate``) and a short sample works."""
	try:
		uc_type = int(data.get("uncertainty type", 0))
	except Exception:
		return False
	if uc_type < 0 or uc_type >= len(sa.uncertainty_choices):
		return False
	dist = sa.uncertainty_choices[uc_type]
	if dist.id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
		return True
	arr, err = _try_build_validate_sample(dist, data, _UNCERTAINTY_VALIDATION_N)
	return arr is not None


_MSG_PREVIEW_INCOMPLETE = (
	"Some required parameters are missing or not accepted by the validator. "
	"Complete them to preview the distribution and enable OK."
)
_MSG_PREVIEW_NONFINITE = "Sampling produced non-finite values; adjust the parameters."


def _scalar_stats_value(x) -> float:
	"""Single float from ``statistics()`` / similar (may be scalar or 0-d / 1-element array)."""
	if x is None:
		return float("nan")
	arr = np.asarray(x, dtype=float).ravel()
	if arr.size == 0:
		return float("nan")
	return float(arr[0])


class UncertaintyDialog(QtWidgets.QDialog):
	"""Single-step dialog for defining a stats_arrays uncertainty.

	Mirrors the behavior of the UncertaintyWizard type page but returns a
	stats_arrays structured array on accept.

	Usage:
		ok, array = UncertaintyDialog.get_uncertainty(parent, initial=dict(...))
		if ok:
			# array is a numpy structured array compatible with stats_arrays
	"""

	def __init__(self, parent=None, initial: Optional[dict] = None, *, read_only: bool = False):
		super().__init__(parent)
		self._read_only = read_only
		self.setWindowTitle("Set Uncertainty")
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

		# State
		self.dist = None
		self.result_array = None  # Filled on accept
		self.result_dict = None  # Filled on accept
		self.previous_dist_id: Optional[int] = None
		self.mean_is_calculated = {
			sa.TriangularUncertainty.id,
			sa.UniformUncertainty.id,
			sa.DiscreteUniform.id,
			sa.BetaUncertainty.id,
		}

		# Top: distribution selection
		box1 = QtWidgets.QGroupBox("Select the uncertainty distribution")
		self.distribution = QtWidgets.QComboBox(box1)
		self.distribution.addItems([ud.description for ud in sa.uncertainty_choices])
		self.distribution.currentIndexChanged.connect(self._on_distribution_changed)

		header_layout = QtWidgets.QGridLayout()
		header_layout.setContentsMargins(4, 4, 4, 4)
		header_layout.setHorizontalSpacing(8)
		header_layout.setVerticalSpacing(4)
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
		self.loc.textEdited.connect(self._schedule_plot_refresh)

		self.mean_label = QtWidgets.QLabel("Mean:")
		self.mean = QtWidgets.QLineEdit()
		self.mean.setValidator(self.validator)
		self.mean.textEdited.connect(self._sync_loc_from_mean)
		self.mean.textEdited.connect(self._check_negative)
		self.mean.textEdited.connect(self._schedule_plot_refresh)

		# Calculated mean (read-only) for some dists
		self.calc_mean_label = QtWidgets.QLabel("Mean:")
		self.calc_mean = QtWidgets.QLineEdit("nan")
		self.calc_mean.setDisabled(True)

		# Other parameters
		self.scale_label = QtWidgets.QLabel("Sigma/scale:")
		self.scale = QtWidgets.QLineEdit()
		self.scale.setValidator(self.validator)
		self.scale.textEdited.connect(self._schedule_plot_refresh)

		self.shape_label = QtWidgets.QLabel("Shape:")
		self.shape = QtWidgets.QLineEdit()
		self.shape.setValidator(self.validator)
		self.shape.textEdited.connect(self._schedule_plot_refresh)

		self.min_label = QtWidgets.QLabel("Minimum:")
		self.minimum = QtWidgets.QLineEdit()
		self.minimum.setValidator(self.validator)
		self.minimum.textEdited.connect(self._schedule_plot_refresh)

		self.max_label = QtWidgets.QLabel("Maximum:")
		self.maximum = QtWidgets.QLineEdit()
		self.maximum.setValidator(self.validator)
		self.maximum.textEdited.connect(self._schedule_plot_refresh)

		# Hidden flag for negative mean on lognormal
		self.negative = QtWidgets.QRadioButton(self)
		self.negative.setChecked(False)
		self.negative.setHidden(True)

		# Optional sign flip for Gamma / Weibull (stats_arrays ``negative`` row flag)
		self.neg_samples_cb = QtWidgets.QCheckBox("Negative samples (mirror sign)")
		self.neg_samples_cb.setChecked(False)
		self.neg_samples_cb.setHidden(True)
		self.neg_samples_cb.stateChanged.connect(lambda *_: self._schedule_plot_refresh())

		# One label + one field per row (harmonized layout; lognormal mean stacks under loc).
		params_layout = QtWidgets.QGridLayout()
		params_layout.setContentsMargins(8, 6, 8, 6)
		params_layout.setHorizontalSpacing(10)
		params_layout.setVerticalSpacing(6)
		params_layout.setColumnStretch(1, 1)
		row = 0
		params_layout.addWidget(self.calc_mean_label, row, 0)
		params_layout.addWidget(self.calc_mean, row, 1)
		row += 1
		params_layout.addWidget(self.loc_label, row, 0)
		params_layout.addWidget(self.loc, row, 1)
		row += 1
		params_layout.addWidget(self.mean_label, row, 0)
		params_layout.addWidget(self.mean, row, 1)
		row += 1
		params_layout.addWidget(self.scale_label, row, 0)
		params_layout.addWidget(self.scale, row, 1)
		row += 1
		params_layout.addWidget(self.shape_label, row, 0)
		params_layout.addWidget(self.shape, row, 1)
		row += 1
		params_layout.addWidget(self.min_label, row, 0)
		params_layout.addWidget(self.minimum, row, 1)
		row += 1
		params_layout.addWidget(self.max_label, row, 0)
		params_layout.addWidget(self.maximum, row, 1)
		row += 1
		params_layout.addWidget(self.neg_samples_cb, row, 0, 1, 2)
		self.fields_box.setLayout(params_layout)

		# Bottom: plot + status when preview is unavailable
		self.plot = SimpleDistributionPlot(self)
		self._plot_message = QtWidgets.QLabel()
		self._plot_message.setWordWrap(True)
		self._plot_message.setAlignment(
			QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop
		)
		self._plot_message.setObjectName("uncertaintyPlotMessage")
		self._plot_message.setStyleSheet(
			"#uncertaintyPlotMessage { color: palette(mid); padding: 2px 0; }"
		)
		self._plot_message.hide()

		# Buttons
		self.buttons = QtWidgets.QDialogButtonBox(
			QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
		)
		self.buttons.accepted.connect(self._on_accept)
		self.buttons.rejected.connect(self.reject)

		# Layout
		layout = QtWidgets.QVBoxLayout()
		layout.setSpacing(6)
		layout.setContentsMargins(12, 10, 12, 10)
		layout.addWidget(box1)
		layout.addWidget(self.fields_box)
		layout.addWidget(self.plot)
		layout.addWidget(self._plot_message)
		layout.addWidget(self.buttons)
		self.setLayout(layout)

		self._plot_refresh_timer = QtCore.QTimer(self)
		self._plot_refresh_timer.setSingleShot(True)
		self._plot_refresh_timer.setInterval(90)
		self._plot_refresh_timer.timeout.connect(self._generate_plot)

		# Initialize values (defaults or provided initial)
		self._apply_initial(initial or {})
		self._on_distribution_changed(self.distribution.currentIndex())
		self._sync_mean_from_loc()
		self._generate_plot()
		if read_only:
			self._apply_read_only_mode()

	# ---------- Public API ----------
	@staticmethod
	def get_uncertainty_array(
		parent=None, initial: Optional[dict] = None, *, read_only: bool = False
	) -> Tuple[bool, Optional[np.ndarray]]:
		dlg = UncertaintyDialog(parent, initial=initial, read_only=read_only)
		ok = dlg.exec_() == QtWidgets.QDialog.Accepted
		return ok, dlg.result_array if ok else None
	
	@staticmethod
	def get_uncertainty_dict(
		parent=None, initial: Optional[dict] = None, *, read_only: bool = False
	) -> Tuple[bool, Optional[dict]]:
		dlg = UncertaintyDialog(parent, initial=initial, read_only=read_only)
		ok = dlg.exec_() == QtWidgets.QDialog.Accepted
		return ok, dlg.result_dict if ok else None

	# ---------- Internal helpers ----------
	def _apply_initial(self, initial: dict) -> None:
		# Use EMPTY_UNCERTAINTY defaults, overridden by initial
		data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
		data.update(initial or {})
		# Do not load numerics that cannot be sampled (e.g. Student's T with df <= 0).
		if not _uncertainty_dict_is_sampleable(data):
			try:
				uc_type = int(data.get("uncertainty type", 0))
			except Exception:
				uc_type = 0
			if uc_type < 0 or uc_type >= len(sa.uncertainty_choices):
				uc_type = 0
			data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
			data["uncertainty type"] = uc_type
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

	def _apply_read_only_mode(self) -> None:
		self.setWindowTitle("View uncertainty")
		self.distribution.setEnabled(False)
		self.fields_box.setEnabled(False)
		ok_btn = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
		ok_btn.setVisible(False)
		ok_btn.setEnabled(False)
		cancel_btn = self.buttons.button(QtWidgets.QDialogButtonBox.Cancel)
		cancel_btn.setText("Close")
		cancel_btn.setDefault(True)

	@property
	def _distribution_loc_label(self) -> str:
		if self.dist is None:
			return "Mean / location:"
		if self.dist.id == sa.BernoulliUncertainty.id:
			return "Probability (0 ≤ p ≤ 1):"
		if self.dist.id == sa.LognormalUncertainty.id:
			return "Loc (ln(mean)):"
		elif self.dist.id == sa.TriangularUncertainty.id:
			return "Mode:"
		elif self.dist.id == sa.BetaUncertainty.id:
			return "Alpha (α):"
		elif self.dist.id in {sa.GammaUncertainty.id, sa.WeibullUncertainty.id}:
			return "Loc / offset:"
		else:
			return "Mean / location:"

	def _refresh_axis_labels(self) -> None:
		"""Scale/shape captions aligned with stats_arrays parameter names."""
		if self.dist is None:
			return
		d = self.dist.id
		if d in (
			sa.NormalUncertainty.id,
			sa.LognormalUncertainty.id,
			sa.StudentsTUncertainty.id,
			sa.GeneralizedExtremeValueUncertainty.id,
		):
			self.scale_label.setText("Scale (σ):")
		elif d == sa.GammaUncertainty.id:
			self.scale_label.setText("Scale (θ):")
		elif d == sa.WeibullUncertainty.id:
			self.scale_label.setText("Scale (λ):")
		else:
			self.scale_label.setText("Sigma/scale:")
		if d == sa.BetaUncertainty.id:
			self.shape_label.setText("Beta (β):")
		elif d == sa.StudentsTUncertainty.id:
			self.shape_label.setText("Degrees of freedom (ν):")
		elif d == sa.GammaUncertainty.id:
			self.shape_label.setText("Shape (k):")
		elif d == sa.WeibullUncertainty.id:
			self.shape_label.setText("Shape (k):")
		else:
			self.shape_label.setText("Shape:")

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
		self.dist = sa.uncertainty_choices[index]

		# Show/hide fields per stats_arrays parameter usage
		if self.dist.id in {0, 1}:  # Undefined / NoUncertainty
			self._hide_params("loc", "scale", "shape", "min", "max")
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id in {2, 3}:  # Lognormal / Normal
			self._hide_params("shape", "min", "max")
			self._hide_params("loc", "scale", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id in {4, 7}:  # Uniform / Discrete uniform
			self._hide_params("loc", "scale", "shape")
			self._hide_params("min", "max", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id == sa.TriangularUncertainty.id:  # Triangular
			self._hide_params("scale", "shape")
			self._hide_params("loc", "min", "max", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id == sa.BernoulliUncertainty.id:  # Bernoulli — loc only (probability)
			self._hide_params("scale", "shape", "min", "max")
			self._hide_params("loc", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id == sa.BetaUncertainty.id:  # Beta — loc (α), shape (β), optional bounds; no ``scale``
			self._hide_params("scale")
			self._hide_params("loc", "shape", "min", "max", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id == sa.GeneralizedExtremeValueUncertainty.id:  # GEV — μ, σ only (ξ must be 0)
			self._hide_params("shape", "min", "max")
			self._hide_params("loc", "scale", hide=False)
			self.neg_samples_cb.setHidden(True)
		elif self.dist.id in (
			sa.WeibullUncertainty.id,
			sa.GammaUncertainty.id,
			sa.StudentsTUncertainty.id,
		):
			self._hide_params("min", "max")
			self._hide_params("loc", "scale", "shape", hide=False)
			self.neg_samples_cb.setHidden(
				self.dist.id not in (sa.WeibullUncertainty.id, sa.GammaUncertainty.id)
			)

		# Special handling (lognormal and calculated mean label)
		if self.dist.id == sa.LognormalUncertainty.id:
			self.mean.setHidden(False)
			self.mean_label.setHidden(False)
			# Convert existing loc to log-space if coming from non-lognormal
			if self.previous_dist_id is not None and self.previous_dist_id != sa.LognormalUncertainty.id:
				self._extract_lognormal_loc_from_mean()
				self._sync_mean_from_loc()
		else:
			self.mean.setHidden(True)
			self.mean_label.setHidden(True)
			# If switching away from lognormal, set loc to linear amount if mean present
			if self.previous_dist_id == sa.LognormalUncertainty.id:
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

		# No parameter inputs for undefined / no uncertainty — hide entire group
		self.fields_box.setVisible(
			self.dist.id
			not in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id)
		)

		# Update labels
		self.loc_label.setText(self._distribution_loc_label)
		self._refresh_axis_labels()
		self.previous_dist_id = self.dist.id
		self._generate_plot()

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
		"""Widget fields written into the uncertainty dict for each ``stats_arrays`` type."""
		if dist_id in (sa.LognormalUncertainty.id, sa.NormalUncertainty.id):
			return ["loc", "scale"]
		if dist_id == sa.UniformUncertainty.id:
			return ["minimum", "maximum"]
		if dist_id == sa.DiscreteUniform.id:
			return ["minimum", "maximum"]
		if dist_id == sa.TriangularUncertainty.id:
			return ["loc", "minimum", "maximum"]
		if dist_id == sa.BernoulliUncertainty.id:
			return ["loc"]
		if dist_id in (
			sa.WeibullUncertainty.id,
			sa.GammaUncertainty.id,
			sa.StudentsTUncertainty.id,
		):
			return ["loc", "scale", "shape"]
		if dist_id == sa.BetaUncertainty.id:
			return ["loc", "shape", "minimum", "maximum"]
		if dist_id == sa.GeneralizedExtremeValueUncertainty.id:
			return ["loc", "scale"]
		return []

	def _completed_active_fields(self) -> bool:
		dist_id = self.dist.id

		def ok_lineedit(le: QtWidgets.QLineEdit) -> bool:
			return bool(le.hasAcceptableInput() and le.text())

		if dist_id in (0, 1):
			return True
		if dist_id in (sa.LognormalUncertainty.id, sa.NormalUncertainty.id):
			return ok_lineedit(self.loc) and ok_lineedit(self.scale)
		if dist_id == sa.UniformUncertainty.id:
			return ok_lineedit(self.minimum) and ok_lineedit(self.maximum)
		if dist_id == sa.DiscreteUniform.id:
			if not ok_lineedit(self.maximum):
				return False
			if not self.minimum.text().strip():
				return True
			return ok_lineedit(self.minimum)
		if dist_id == sa.TriangularUncertainty.id:
			if not (
				ok_lineedit(self.minimum)
				and ok_lineedit(self.maximum)
				and ok_lineedit(self.loc)
			):
				return False
			try:
				return (
					float(self.minimum.text())
					< float(self.loc.text())
					< float(self.maximum.text())
				)
			except Exception:
				return False
		if dist_id == sa.BernoulliUncertainty.id:
			if not ok_lineedit(self.loc):
				return False
			try:
				p = float(self.loc.text())
				return 0.0 <= p <= 1.0
			except Exception:
				return False
		if dist_id in (
			sa.WeibullUncertainty.id,
			sa.GammaUncertainty.id,
			sa.StudentsTUncertainty.id,
		):
			return (
				ok_lineedit(self.loc)
				and ok_lineedit(self.scale)
				and ok_lineedit(self.shape)
			)
		if dist_id == sa.BetaUncertainty.id:
			if not (ok_lineedit(self.loc) and ok_lineedit(self.shape)):
				return False
			try:
				if float(self.loc.text()) <= 0 or float(self.shape.text()) <= 0:
					return False
			except Exception:
				return False
			if not self.minimum.text().strip() and not self.maximum.text().strip():
				return True
			if not (ok_lineedit(self.minimum) and ok_lineedit(self.maximum)):
				return False
			try:
				return float(self.minimum.text()) < float(self.maximum.text())
			except Exception:
				return False
		if dist_id == sa.GeneralizedExtremeValueUncertainty.id:
			return ok_lineedit(self.loc) and ok_lineedit(self.scale)
		return False

	@property
	def _uncertainty_info(self) -> dict:
		data = {k: v for k, v in EMPTY_UNCERTAINTY.items()}
		data["uncertainty type"] = self.distribution.currentIndex()
		if self.dist is None:
			return data
		if self.dist.id == sa.LognormalUncertainty.id:
			data["negative"] = bool(self.negative.isChecked())
		elif self.dist.id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id):
			data["negative"] = self.neg_samples_cb.isChecked()
		else:
			data["negative"] = False

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
		# stats_arrays GEV implementation only supports xi (shape) == 0
		if self.dist.id == sa.GeneralizedExtremeValueUncertainty.id:
			data["shape"] = 0.0
		return data

	def _structured_array_if_sampleable(self) -> Tuple[Optional[np.ndarray], Optional[str]]:
		"""Build params, ``stats_arrays`` validation, and a short random draw."""
		return _try_build_validate_sample(self.dist, self._uncertainty_info, _UNCERTAINTY_VALIDATION_N)

	def _ok_enabled(self) -> bool:
		if self.dist is None:
			return False
		if self.dist.id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
			return True
		if not self._completed_active_fields():
			return False
		arr, _ = self._structured_array_if_sampleable()
		return arr is not None

	def _update_ok_state(self, structured: Optional[np.ndarray] = None) -> None:
		if self._read_only:
			return
		ok_btn = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
		if self.dist is None:
			ok_btn.setEnabled(False)
			return
		if self.dist.id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
			ok_btn.setEnabled(True)
			return
		if not self._completed_active_fields():
			ok_btn.setEnabled(False)
			return
		if structured is not None:
			ok_btn.setEnabled(True)
			return
		arr, _ = self._structured_array_if_sampleable()
		ok_btn.setEnabled(arr is not None)

	def _schedule_plot_refresh(self) -> None:
		"""Refresh OK state immediately; defer heavy matplotlib work to avoid UI stalls."""
		self._update_ok_state()
		self._plot_refresh_timer.stop()
		self._plot_refresh_timer.start()

	def _relayout_dialog_compact(self) -> None:
		self.fields_box.updateGeometry()
		self.updateGeometry()
		main_lay = self.layout()
		if main_lay is not None:
			main_lay.activate()
		self.adjustSize()

	def _hide_plot_preview(self, message: Optional[str]) -> None:
		"""Hide the matplotlib preview, collapse its layout height, optional status text."""
		try:
			self.plot.reset_plot()
			# Do not draw here: canvas may be 0×0 during collapse → constrained_layout warnings / churn.
		except Exception:
			pass
		self.plot.setMinimumHeight(0)
		self.plot.setMaximumHeight(0)
		self.plot.setVisible(False)
		if message:
			self._plot_message.setText(message)
			self._plot_message.show()
		else:
			self._plot_message.hide()
			self._plot_message.clear()

	def _generate_plot(self) -> None:
		try:
			if self.dist is None:
				return

			# No distribution shape to visualize
			if self.dist.id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
				self._hide_plot_preview(None)
				self._update_ok_state()
				return

			if not self._completed_active_fields():
				self._hide_plot_preview(_MSG_PREVIEW_INCOMPLETE)
				self._update_ok_state()
				return

			array, sample_err = self._structured_array_if_sampleable()
			if array is None:
				self._hide_plot_preview(
					sample_err or "Invalid parameters for this distribution."
				)
				self._update_ok_state()
				return

			if self.dist.id in self.mean_is_calculated:
				try:
					try:
						calc = self.dist.statistics(array).get("mean")
					except TypeError:
						array = self.dist.fix_nan_minimum(array)
						calc = (array["maximum"] + array["minimum"]) / 2
					calc = calc.mean() if isinstance(calc, np.ndarray) else calc
					self.calc_mean.setText(str(float(calc)))
				except Exception:
					self.calc_mean.setText("nan")

			try:
				if self.dist.id == sa.LognormalUncertainty.id:
					ref_lin = _scalar_stats_value(
						self.dist.statistics(array).get("median")
					)
				else:
					ref_lin = _scalar_stats_value(
						self.dist.statistics(array).get("mean")
					)
				data = self.dist.random_variables(array, _UNCERTAINTY_PREVIEW_DRAW_N)
			except Exception as e:
				logger.debug(
					"Uncertainty preview skipped (invalid or unsampled parameters): {}",
					e,
				)
				self._hide_plot_preview(str(e).strip() or e.__class__.__name__)
				self._update_ok_state()
				return

			if np.any(np.isnan(data)):
				self._hide_plot_preview(_MSG_PREVIEW_NONFINITE)
				self._update_ok_state()
				return

			# Linear scale on the axis (physical values). Speed: fewer hist bins + KDE off when spread is huge.
			plot_vals = np.asarray(data, dtype=float)
			xlabel = "Value"
			vline_legend = (
				"Median"
				if self.dist.id == sa.LognormalUncertainty.id
				else "Mean / amount"
			)
			ref_plot = ref_lin

			try:
				# Bernoulli samples are discrete {0,1}; Gaussian KDE is always singular here.
				use_kde = self.dist.id != sa.BernoulliUncertainty.id
				if use_kde:
					flat = np.asarray(plot_vals, dtype=float).ravel()
					flat = flat[np.isfinite(flat)]
					if flat.size < 2:
						use_kde = False
					else:
						spread = float(np.ptp(flat))
						std = float(np.std(flat))
						# Very wide or near-constant samples: KDE bandwidth/grid work is costly and unstable.
						spread_cap = (
							5e5 if self.dist.id == sa.LognormalUncertainty.id else 1e7
						)
						if (
							spread == 0
							or not np.isfinite(spread)
							or spread > spread_cap
							or std
							<= 1e-12 * max(float(np.max(np.abs(flat))), 1.0)
						):
							use_kde = False
				self._plot_message.hide()
				self._plot_message.clear()
				self.plot.plot(
					plot_vals, ref_plot, kde=use_kde, label=xlabel, vline_legend=vline_legend
				)
			except Exception as e:
				logger.warning("Uncertainty preview could not be drawn: {}", e)
				self._hide_plot_preview(str(e).strip() or e.__class__.__name__)
				self._update_ok_state()
				return
			self._update_ok_state(structured=array)
		finally:
			self._relayout_dialog_compact()

	def _on_accept(self) -> None:
		if self._read_only:
			return
		if not self._ok_enabled():
			return
		try:
			self.result_dict = self._uncertainty_info
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
	_kde_plot_errors = (RuntimeError, np.linalg.LinAlgError, ValueError)

	def __init__(self, parent=None):
		super().__init__(parent)
		# Embedded in a dialog with changing height: constrained_layout fights 0-size passes and spams warnings.
		if hasattr(self.figure, "set_constrained_layout"):
			self.figure.set_constrained_layout(False)
		# Fixed floor for the preview strip (logical px). Do not derive from MPL buffer.
		self.setMinimumHeight(320)

	def plot(
		self,
		data: np.ndarray,
		mean: float,
		label: str = "Value",
		*,
		kde: bool = True,
		vline_legend: str = "Mean / amount",
	) -> None:
		# Restore layout height after _hide_plot_preview collapsed this widget.
		self.setMinimumHeight(320)
		self.setMaximumHeight(16777215)
		self.setSizePolicy(
			QtWidgets.QSizePolicy.Policy.Ignored,
			QtWidgets.QSizePolicy.Policy.Expanding,
		)
		self.reset_plot()
		# Match figure size to widget before plotting so axes bbox is non-zero for seaborn/matplotlib.
		self.sync_figure_to_widget()

		x = np.asarray(data, dtype=float).ravel()
		x = x[np.isfinite(x)]
		if x.size == 0:
			self.ax.text(
				0.5,
				0.5,
				"No finite samples",
				transform=self.ax.transAxes,
				ha="center",
				va="center",
			)
			self.ax.set_xlabel(label)
			self._set_plot_chrome_white()
			self.sync_figure_to_widget()
			self.canvas.draw_idle()
			self.setVisible(True)
			return

		if kde:
			try:
				sns.histplot(
					x=x,
					kde=True,
					stat="density",
					ax=self.ax,
					edgecolor="none",
					bins=_UNCERTAINTY_PREVIEW_HIST_BINS,
				)
			except self._kde_plot_errors as e:
				logger.warning("Uncertainty histogram KDE unavailable ({}), plotting without KDE", e)
				sns.histplot(
					x=x,
					kde=False,
					stat="density",
					ax=self.ax,
					edgecolor="none",
					bins=_UNCERTAINTY_PREVIEW_HIST_BINS,
				)
		else:
			sns.histplot(
				x=x,
				kde=False,
				stat="density",
				ax=self.ax,
				edgecolor="none",
				bins=_UNCERTAINTY_PREVIEW_HIST_BINS,
			)
		self.ax.set_xlabel(label)
		self.ax.set_ylabel("Probability density")
		try:
			if np.isfinite(mean):
				self.ax.axvline(mean, label=vline_legend, c="r", ymax=0.98)
			self.ax.legend(loc="upper right")
		except np.linalg.LinAlgError:
			logger.warning("Uncertainty preview: could not draw mean line (singular transform)")
			self.ax.legend(loc="upper right")
		self._set_plot_chrome_white()
		self.sync_figure_to_widget()
		self.canvas.draw_idle()
		self.setVisible(True)


__all__ = ["UncertaintyDialog"]


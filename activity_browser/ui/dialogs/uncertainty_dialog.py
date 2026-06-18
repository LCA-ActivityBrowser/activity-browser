from __future__ import annotations

from loguru import logger
from typing import Optional, Tuple

import numpy as np

from qtpy import QtCore, QtGui, QtWidgets
import stats_arrays as sa

from activity_browser.bwutils.uncertainty import (
	DISTRIBUTIONS_WITH_CALCULATED_MEAN,
	EMPTY_UNCERTAINTY,
	OPTIONAL_UNCERTAINTY_FIELDS,
	UNCERTAINTY_VALIDATION_N,
	prepare_uncertainty_dict,
	uncertainty_dict_is_sampleable,
	uncertainty_field_name,
	uncertainty_reference_value,
	uncertainty_statistics_scalar,
	standard_uncertainty_fields,
	validate_uncertainty_dict,
)
from stats_arrays import UncertaintyBase
from activity_browser.ui.widgets import ABPlot

from .uncertainty_pdf_preview import PreviewDensity, preview_density

_MSG_PREVIEW_INCOMPLETE = (
	"Some required parameters are missing or not accepted by the validator. "
	"Complete them to preview the distribution and enable OK."
)


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
		# Stretch so the preview absorbs all extra height when the dialog is resized.
		layout.addWidget(self.plot, 1)
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
		if not uncertainty_dict_is_sampleable(data):
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
			if val is None or (isinstance(val, float) and np.isnan(val)):
				return ""
			return str(val)

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
	def _field_widgets(self) -> dict[str, tuple[QtWidgets.QWidget, QtWidgets.QLineEdit]]:
		return {
			"loc": (self.loc_label, self.loc),
			"scale": (self.scale_label, self.scale),
			"shape": (self.shape_label, self.shape),
			"minimum": (self.min_label, self.minimum),
			"maximum": (self.max_label, self.maximum),
		}

	def _sync_parameter_fields(self) -> None:
		"""Show/hide inputs and captions from ``standard_uncertainty_fields``."""
		dist_id = self.dist.id
		active = set(standard_uncertainty_fields(dist_id))
		for key, (label, widget) in self._field_widgets.items():
			visible = key in active
			label.setVisible(visible)
			widget.setVisible(visible)
			if visible:
				label.setText(f"{uncertainty_field_name(dist_id, key)}:")
				if widget.text().strip().lower() == "nan":
					widget.clear()
		self.neg_samples_cb.setVisible(
			dist_id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id)
		)

	def _on_distribution_changed(self, index: int) -> None:
		self._plot_refresh_timer.stop()
		self.dist = sa.uncertainty_choices[index]
		self._sync_parameter_fields()

		if self.dist.id == sa.LognormalUncertainty.id:
			self.mean.setHidden(False)
			self.mean_label.setHidden(False)
			if self.previous_dist_id is not None and self.previous_dist_id != sa.LognormalUncertainty.id:
				self._extract_lognormal_loc_from_mean()
				self._sync_mean_from_loc()
		else:
			self.mean.setHidden(True)
			self.mean_label.setHidden(True)
			if self.previous_dist_id == sa.LognormalUncertainty.id:
				try:
					mean_val = float(self.mean.text()) if self.mean.text() else np.nan
					if not np.isnan(mean_val):
						self.loc.setText(str(mean_val))
				except Exception:
					pass

		show_calc = self.dist.id in DISTRIBUTIONS_WITH_CALCULATED_MEAN
		self.calc_mean_label.setHidden(not show_calc)
		self.calc_mean.setHidden(not show_calc)
		self.fields_box.setVisible(
			self.dist.id not in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id)
		)
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

	def _field_has_value(self, text: str) -> bool:
		"""False for blank fields and the ``nan`` placeholder shown in line edits."""
		t = text.strip().lower()
		return bool(t and t != "nan")

	def _any_parameter_text(self) -> bool:
		"""True if the user has entered any value for the active distribution."""
		optional = OPTIONAL_UNCERTAINTY_FIELDS.get(self.dist.id, frozenset())
		for field in standard_uncertainty_fields(self.dist.id):
			if field in optional:
				continue
			_, widget = self._field_widgets[field]
			if widget.isVisible() and self._field_has_value(widget.text()):
				return True
		return False

	def _parse_field(self, text: str) -> float:
		if not self._field_has_value(text):
			return float("nan")
		try:
			return float(text)
		except (TypeError, ValueError):
			return float("nan")

	@property
	def _uncertainty_info(self) -> dict:
		if self.dist is None:
			return {**EMPTY_UNCERTAINTY}
		data = {**EMPTY_UNCERTAINTY, "uncertainty type": self.dist.id}
		if self.dist.id == sa.LognormalUncertainty.id:
			data["negative"] = bool(self.negative.isChecked())
		elif self.dist.id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id):
			data["negative"] = self.neg_samples_cb.isChecked()
		else:
			data["negative"] = False

		for field in standard_uncertainty_fields(self.dist.id):
			_, widget = self._field_widgets[field]
			data[field] = self._parse_field(widget.text())
		return prepare_uncertainty_dict(data, self.dist)

	def _structured_array_if_sampleable(self) -> Tuple[Optional[np.ndarray], Optional[str]]:
		return validate_uncertainty_dict(self._uncertainty_info, self.dist, UNCERTAINTY_VALIDATION_N)

	def _ok_enabled(self) -> bool:
		if self.dist is None:
			return False
		if self.dist.id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
			return True
		array, _ = self._structured_array_if_sampleable()
		return array is not None

	def _update_ok_state(self, structured: Optional[np.ndarray] = None) -> None:
		if self._read_only:
			return
		ok_btn = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
		ok_btn.setEnabled(
			structured is not None if structured is not None else self._ok_enabled()
		)

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
		# ``adjustSize`` collapses the dialog to minimum hints and defeats vertical stretch
		# on the plot; only compact when the matplotlib preview is hidden.
		plot = getattr(self, "plot", None)
		if plot is None or plot.maximumHeight() <= 0 or not plot.isVisible():
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

			array, sample_err = self._structured_array_if_sampleable()
			if array is None:
				msg = (
					_MSG_PREVIEW_INCOMPLETE
					if not self._any_parameter_text()
					else (sample_err or "Invalid parameters for this distribution.")
				)
				self._hide_plot_preview(msg)
				self._update_ok_state()
				return

			if self.dist.id in DISTRIBUTIONS_WITH_CALCULATED_MEAN:
				calc = uncertainty_statistics_scalar(self.dist, array, "mean")
				self.calc_mean.setText(str(calc) if np.isfinite(calc) else "nan")

			ref_lin = uncertainty_reference_value(self.dist, array)
			if not np.isfinite(ref_lin):
				self._hide_plot_preview("Could not compute distribution statistics for preview.")
				self._update_ok_state()
				return

			curve = preview_density(self.dist, array)
			if curve is None:
				self._hide_plot_preview(
					"Preview is not available for this uncertainty type or parameters."
				)
				self._update_ok_state()
				return

			try:
				self._plot_message.hide()
				self._plot_message.clear()
				self.plot.plot_analytical(curve, ref_lin, title=self.dist.description)
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
			self.result_array = UncertaintyBase.from_dicts(self._uncertainty_info)
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
	def __init__(self, parent=None):
		super().__init__(parent)
		# Embedded in a dialog with changing height: constrained_layout fights 0-size passes and spams warnings.
		if hasattr(self.figure, "set_constrained_layout"):
			self.figure.set_constrained_layout(False)
		# Fixed floor for the preview strip (logical px); extra height helps x-axis label fit.
		self.setMinimumHeight(348)
		exp = QtWidgets.QSizePolicy.Policy.Expanding
		self.setSizePolicy(exp, exp)
		self.canvas.setSizePolicy(exp, exp)
		lay = self.layout()
		if isinstance(lay, QtWidgets.QVBoxLayout):
			m = lay.contentsMargins()
			lay.setContentsMargins(m.left(), m.top(), m.right(), 6)

	def plot_analytical(
		self, curve: PreviewDensity, vline_x: float, *, title: str = ""
	) -> None:
		"""Plot ``stats_arrays`` / SciPy PDF or PMF (no random sampling)."""
		self.setMinimumHeight(348)
		self.setMaximumHeight(16777215)
		self.setVisible(True)
		self.reset_plot()
		if title:
			self.ax.set_title(title, fontsize=10, pad=6)

		if curve.kind == "bar":
			self.ax.set_ylabel("PMF", labelpad=6)
			w = 0.35 if curve.x.size <= 2 else min(0.45, 0.85 / max(int(curve.x.size), 1))
			self.ax.bar(
				curve.x,
				curve.y,
				width=w,
				align="center",
				edgecolor="none",
				color="steelblue",
			)
		else:
			self.ax.set_ylabel("Probability density", labelpad=6)
			self.ax.plot(curve.x, curve.y, color="steelblue", linewidth=1.8)
			self.ax.fill_between(
				curve.x,
				0.0,
				curve.y,
				alpha=0.22,
				color="steelblue",
				linewidth=0.0,
			)

		self.ax.set_xlabel(curve.xlabel, labelpad=7)
		self._sync_plot_to_theme()
		try:
			if np.isfinite(vline_x):
				self.ax.axvline(vline_x, label=curve.vline_legend, c="r", ymax=0.98)
			handles, labels = self.ax.get_legend_handles_labels()
			if handles:
				self.ax.legend(loc="upper right", fontsize=9, ncol=1, frameon=False)
		except np.linalg.LinAlgError:
			logger.warning("Uncertainty preview: could not draw reference line")
			handles, labels = self.ax.get_legend_handles_labels()
			if handles:
				self.ax.legend(loc="upper right", fontsize=9, ncol=1, frameon=False)

		self.ax.tick_params(axis="both", which="major", labelsize=9)
		self.ax.tick_params(axis="x", which="major", pad=4)
		# Layout after Qt assigns the restored height (first show is often still 0×0).
		QtCore.QTimer.singleShot(0, self._fit_preview_to_widget)

	def _fit_preview_to_widget(self, _attempt: int = 0) -> None:
		self.sync_figure_to_widget()
		if not self._canvas_has_size():
			if _attempt < 8:
				QtCore.QTimer.singleShot(0, lambda: self._fit_preview_to_widget(_attempt + 1))
			else:
				self.canvas.draw_idle()
			return
		try:
			self.figure.tight_layout(pad=0.28, h_pad=0.55, w_pad=0.35)
		except Exception:
			self.figure.subplots_adjust(left=0.09, right=0.99, top=0.96, bottom=0.18)
		else:
			p = self.figure.subplotpars
			h_in = float(self.figure.get_figheight())
			bottom_floor = max(0.14, min(0.24, 1.05 / max(h_in, 0.25)))
			self.figure.subplots_adjust(
				left=max(p.left, 0.07),
				right=min(p.right, 0.995),
				top=min(p.top, 0.97),
				bottom=max(p.bottom, bottom_floor),
			)
		self.canvas.draw_idle()


__all__ = ["UncertaintyDialog"]


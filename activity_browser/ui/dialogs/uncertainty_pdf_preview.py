# -*- coding: utf-8 -*-
"""PDF/PMF preview: ``stats_arrays`` :meth:`pdf` first, SciPy only where missing."""
from __future__ import annotations

from typing import NamedTuple, Optional

import numpy as np
import scipy.stats as st
import stats_arrays as sa

from activity_browser.bwutils.uncertainty import as_scalar


class PreviewDensity(NamedTuple):
	x: np.ndarray
	y: np.ndarray
	kind: str = "line"
	xlabel: str = "Value"
	vline_legend: str = "Mean / amount"


def _linspace_ppf(rv: st.rv_continuous, n: int) -> np.ndarray:
	a, b = rv.ppf(0.001), rv.ppf(0.999)
	if not np.isfinite(a):
		a = rv.ppf(0.02)
	if not np.isfinite(b):
		b = rv.ppf(0.98)
	if not np.isfinite(a) or not np.isfinite(b) or a >= b:
		a, b = -5.0, 5.0
	return np.linspace(a, b, n)


def _mirror_negative(xp: np.ndarray, yp: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
	xn, yn = -xp[::-1], yp[::-1]
	return np.concatenate([xn[:-1], xp]), np.concatenate([yn[:-1], yp])


def _scipy_preview(dist_id: int, row: np.void, n: int) -> Optional[PreviewDensity]:
	"""SciPy curves for distributions without a working ``stats_arrays`` ``pdf()``."""
	if dist_id == sa.LognormalUncertainty.id:
		mu, sig = as_scalar(row["loc"]), as_scalar(row["scale"])
		neg = bool(row["negative"])
		rv = st.lognorm(s=sig, scale=np.exp(mu))
		xp = _linspace_ppf(rv, max(n // 2, 50) if neg else n)
		yp = rv.pdf(xp)
		if neg:
			xp, yp = _mirror_negative(xp, yp)
		return PreviewDensity(x=xp, y=yp, kind="line", vline_legend="Median")

	if dist_id in (sa.GammaUncertainty.id, sa.WeibullUncertainty.id):
		loc = as_scalar(row["loc"])
		if not np.isfinite(loc):
			loc = 0.0
		scale, shape = as_scalar(row["scale"]), as_scalar(row["shape"])
		if dist_id == sa.GammaUncertainty.id:
			rv = st.gamma(a=shape, loc=loc, scale=scale)
		else:
			rv = st.weibull_min(c=shape, loc=loc, scale=scale)
		xp = _linspace_ppf(rv, max(n // 2, 50))
		yp = rv.pdf(xp)
		if bool(row["negative"]):
			xp, yp = _mirror_negative(xp, yp)
		return PreviewDensity(x=xp, y=yp, kind="line")

	if dist_id == sa.StudentsTUncertainty.id:
		loc = as_scalar(row["loc"])
		if not np.isfinite(loc):
			loc = 0.0
		sc = as_scalar(row["scale"])
		if not np.isfinite(sc) or sc <= 0:
			sc = 1.0
		rv = st.t(df=as_scalar(row["shape"]), loc=loc, scale=sc)
		xs = _linspace_ppf(rv, n)
		return PreviewDensity(x=xs, y=rv.pdf(xs), kind="line")

	if dist_id == sa.GeneralizedExtremeValueUncertainty.id:
		rv = st.gumbel_r(loc=as_scalar(row["loc"]), scale=as_scalar(row["scale"]))
		xs = _linspace_ppf(rv, n)
		return PreviewDensity(x=xs, y=rv.pdf(xs), kind="line")

	if dist_id == sa.BernoulliUncertainty.id:
		p = min(max(as_scalar(row["loc"]), 0.0), 1.0)
		return PreviewDensity(
			x=np.array([0.0, 1.0]),
			y=np.array([1.0 - p, p]),
			kind="bar",
			vline_legend="Probability",
		)

	if dist_id == sa.DiscreteUniform.id:
		lo = int(round(as_scalar(row["minimum"])))
		hi = int(round(as_scalar(row["maximum"])))
		if hi < lo:
			lo, hi = hi, lo
		x = np.arange(lo, hi, dtype=float)
		if x.size == 0:
			return PreviewDensity(
				x=np.array([float(lo)]),
				y=np.array([0.0]),
				kind="bar",
				vline_legend="Expected value",
			)
		return PreviewDensity(
			x=x,
			y=np.full(x.shape, 1.0 / x.size),
			kind="bar",
			vline_legend="Expected value",
		)
	return None


def preview_density(dist, structured_array: np.ndarray, n_points: int = 400) -> Optional[PreviewDensity]:
	"""Density or PMF for *dist* (authoritative type) and the first parameter row."""
	if dist is None or structured_array is None or len(structured_array) == 0:
		return None
	dist_id = dist.id
	if dist_id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
		return None

	row = structured_array[0]

	try:
		x, y = dist.pdf(structured_array, None)
		x = np.asarray(x, dtype=float).ravel()
		y = np.asarray(y, dtype=float).ravel()
		if x.size and x.size == y.size and np.isfinite(y).any() and np.nanmax(y) > 1e-30:
			ok = np.isfinite(x) & np.isfinite(y)
			vleg = "Median" if dist_id == sa.LognormalUncertainty.id else "Mean / amount"
			return PreviewDensity(x=x[ok], y=y[ok], kind="line", vline_legend=vleg)
	except (NotImplementedError, TypeError, ValueError):
		pass

	return _scipy_preview(dist_id, row, n_points)


__all__ = ["PreviewDensity", "preview_density"]

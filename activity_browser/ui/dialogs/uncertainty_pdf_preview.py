# -*- coding: utf-8 -*-
"""Analytical PDF/PMF curves for uncertainty dialog preview (no Monte Carlo histogram)."""
from __future__ import annotations

from typing import NamedTuple, Optional

import numpy as np
import scipy.stats as st
import stats_arrays as sa


class PreviewDensity(NamedTuple):
	"""Curve data for :class:`SimpleDistributionPlot`."""

	x: np.ndarray
	y: np.ndarray
	# "line" = continuous density; "bar" = PMF at discrete support
	kind: str = "line"
	xlabel: str = "Value"
	vline_legend: str = "Mean / amount"


def _row(arr: np.ndarray) -> np.void:
	return arr[0]


def _f(row: np.void, key: str, default: float = np.nan) -> float:
	v = row[key]
	if isinstance(v, np.ndarray):
		v = v.flat[0]
	try:
		return float(v)
	except (TypeError, ValueError):
		return float("nan")


def _bool(row: np.void, key: str) -> bool:
	return bool(row[key])


def _try_stats_arrays_pdf(dist, arr: np.ndarray, xs: Optional[np.ndarray]) -> Optional[tuple[np.ndarray, np.ndarray]]:
	try:
		x, y = dist.pdf(arr, xs)
	except (NotImplementedError, TypeError, ValueError):
		return None
	x = np.asarray(x, dtype=float).ravel()
	y = np.asarray(y, dtype=float).ravel()
	if x.size == 0 or y.size == 0 or x.size != y.size:
		return None
	m = np.nanmax(y)
	if not np.isfinite(m) or m <= 1e-30:
		return None
	ok = np.isfinite(x) & np.isfinite(y)
	if not ok.any():
		return None
	return x[ok], y[ok]


def _linspace_ppf(rv: st.rv_continuous, n: int, lo: float = 0.001, hi: float = 0.999) -> np.ndarray:
	a, b = rv.ppf(lo), rv.ppf(hi)
	if not np.isfinite(a):
		a = rv.ppf(0.02)
	if not np.isfinite(b):
		b = rv.ppf(0.98)
	if not np.isfinite(a) or not np.isfinite(b) or a >= b:
		a, b = -5.0, 5.0
	return np.linspace(a, b, n)


def _lognormal_positive_curve(row: np.void, n: int) -> PreviewDensity:
	"""SciPy log-normal PDF (stats_arrays ``pdf`` can return zeros for some ``loc`` values)."""
	mu = _f(row, "loc")
	sig = _f(row, "scale")
	rv = st.lognorm(s=sig, scale=np.exp(mu))
	xp = _linspace_ppf(rv, n)
	yp = rv.pdf(xp)
	return PreviewDensity(x=xp, y=yp, kind="line", xlabel="Value", vline_legend="Median")


def _lognormal_negative_curve(row: np.void, n: int) -> PreviewDensity:
	mu = _f(row, "loc")
	sig = _f(row, "scale")
	rv = st.lognorm(s=sig, scale=np.exp(mu))
	xp = _linspace_ppf(rv, max(n // 2, 50))
	yp = rv.pdf(xp)
	xn = -xp[::-1]
	yn = yp[::-1]
	x = np.concatenate([xn[:-1], xp])
	y = np.concatenate([yn[:-1], yp])
	return PreviewDensity(x=x, y=y, kind="line", xlabel="Value", vline_legend="Median")


def _gamma_weibull_scipy_pdf(dist_id: int, row: np.void, n: int) -> PreviewDensity:
	loc = _f(row, "loc")
	if not np.isfinite(loc):
		loc = 0.0
	scale = _f(row, "scale")
	shape = _f(row, "shape")
	neg = _bool(row, "negative")
	if dist_id == sa.GammaUncertainty.id:
		rv = st.gamma(a=shape, loc=loc, scale=scale)
	else:
		rv = st.weibull_min(c=shape, loc=loc, scale=scale)
	xp = _linspace_ppf(rv, max(n // 2, 50))
	yp = rv.pdf(xp)
	if neg:
		xn = -xp[::-1]
		yn = yp[::-1]
		x = np.concatenate([xn[:-1], xp])
		y = np.concatenate([yn[:-1], yp])
	else:
		x, y = xp, yp
	vleg = "Mean / amount"
	return PreviewDensity(x=x, y=y, kind="line", xlabel="Value", vline_legend=vleg)


def _students_t_curve(row: np.void, n: int) -> PreviewDensity:
	df = _f(row, "shape")
	loc = _f(row, "loc")
	if not np.isfinite(loc):
		loc = 0.0
	sc = _f(row, "scale")
	if not np.isfinite(sc) or sc <= 0:
		sc = 1.0
	rv = st.t(df=df, loc=loc, scale=sc)
	xs = _linspace_ppf(rv, n)
	ys = rv.pdf(xs)
	return PreviewDensity(x=xs, y=ys, kind="line", xlabel="Value", vline_legend="Mean / amount")


def _gumbel_curve(row: np.void, n: int) -> PreviewDensity:
	# stats_arrays GEV only supports xi=0 and draws from gumbel(loc, scale)
	loc = _f(row, "loc")
	sc = _f(row, "scale")
	rv = st.gumbel_r(loc=loc, scale=sc)
	xs = _linspace_ppf(rv, n)
	ys = rv.pdf(xs)
	return PreviewDensity(x=xs, y=ys, kind="line", xlabel="Value", vline_legend="Mean / amount")


def _bernoulli_pmf(row: np.void) -> PreviewDensity:
	p = _f(row, "loc")
	p = min(max(p, 0.0), 1.0)
	x = np.array([0.0, 1.0], dtype=float)
	y = np.array([1.0 - p, p], dtype=float)
	return PreviewDensity(x=x, y=y, kind="bar", xlabel="Value", vline_legend="Probability")


def _discrete_uniform_pmf(row: np.void) -> PreviewDensity:
	"""PMF on integers ``minimum, minimum+1, …, maximum - 1`` (``maximum`` is exclusive).

	Matches :class:`stats_arrays.DiscreteUniform` / ``numpy.random.randint(low, high)``.
	"""
	lo = int(round(_f(row, "minimum")))
	hi = int(round(_f(row, "maximum")))
	if hi < lo:
		lo, hi = hi, lo
	x = np.arange(lo, hi, dtype=float)
	if x.size == 0:
		return PreviewDensity(
			x=np.array([float(lo)]),
			y=np.array([0.0]),
			kind="bar",
			xlabel="Value",
			vline_legend="Expected value",
		)
	p = 1.0 / float(x.size)
	y = np.full_like(x, p)
	return PreviewDensity(x=x, y=y, kind="bar", xlabel="Value", vline_legend="Expected value")


def preview_density(dist, structured_array: np.ndarray, n_points: int = 400) -> Optional[PreviewDensity]:
	"""Return density/PMF for the first row of *structured_array*, or None if not drawable."""
	if structured_array is None or len(structured_array) == 0:
		return None
	row = _row(structured_array)
	dist_id = int(row["uncertainty_type"])

	if dist_id in (sa.UndefinedUncertainty.id, sa.NoUncertainty.id):
		return None

	# Lognormal + negative: stats_arrays pdf() is not usable; mirror positive lognormal.
	if dist_id == sa.LognormalUncertainty.id and _bool(row, "negative"):
		return _lognormal_negative_curve(row, n_points)

	# Discrete laws: ``stats_arrays`` :meth:`pdf` may return a sampled continuous curve;
	# always show the exact PMF as bars.
	if dist_id == sa.BernoulliUncertainty.id:
		return _bernoulli_pmf(row)
	if dist_id == sa.DiscreteUniform.id:
		return _discrete_uniform_pmf(row)

	res = _try_stats_arrays_pdf(dist, structured_array, None)
	if dist_id == sa.LognormalUncertainty.id and not _bool(row, "negative"):
		if res is None or float(np.nanmax(res[1])) <= 1e-30:
			return _lognormal_positive_curve(row, n_points)
	if res is not None:
		x, y = res
		vleg = "Median" if dist_id == sa.LognormalUncertainty.id else "Mean / amount"
		return PreviewDensity(x=x, y=y, kind="line", xlabel="Value", vline_legend=vleg)

	if dist_id == sa.WeibullUncertainty.id:
		return _gamma_weibull_scipy_pdf(dist_id, row, n_points)
	if dist_id == sa.GammaUncertainty.id:
		return _gamma_weibull_scipy_pdf(dist_id, row, n_points)
	if dist_id == sa.StudentsTUncertainty.id:
		return _students_t_curve(row, n_points)
	if dist_id == sa.GeneralizedExtremeValueUncertainty.id:
		return _gumbel_curve(row, n_points)

	return None


__all__ = ["PreviewDensity", "preview_density"]

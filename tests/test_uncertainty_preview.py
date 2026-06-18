"""Regression tests for AB uncertainty preview helpers (not stats_arrays itself)."""
import numpy as np
import stats_arrays as sa

from activity_browser.bwutils.uncertainty import (
    standard_uncertainty_fields,
    uncertainty_reference_value,
    uncertainty_statistics_scalar,
)
from activity_browser.ui.dialogs.uncertainty_pdf_preview import preview_density


def _lognormal_array(loc=0.0, scale=0.5, negative=False):
    info = {
        "uncertainty type": sa.LognormalUncertainty.id,
        "loc": loc,
        "scale": scale,
        "shape": np.nan,
        "minimum": np.nan,
        "maximum": np.nan,
        "negative": negative,
    }
    arr = sa.LognormalUncertainty.from_dicts(info)
    sa.LognormalUncertainty.validate(arr)
    return arr


def test_lognormal_preview_reference_avoids_statistics_bug():
    arr = _lognormal_array(loc=0.0, scale=0.5)
    ref = uncertainty_reference_value(sa.LognormalUncertainty, arr)
    assert ref == 1.0
    curve = preview_density(sa.LognormalUncertainty, arr)
    assert curve is not None
    assert curve.y.size > 0
    assert np.nanmax(curve.y) > 0


def test_beta_pert_fields_and_preview():
    info = {
        "uncertainty type": sa.BetaPERTUncertainty.id,
        "minimum": 1.0,
        "loc": 5.0,
        "maximum": 10.0,
        "scale": np.nan,
        "shape": np.nan,
        "negative": False,
    }
    assert standard_uncertainty_fields(sa.BetaPERTUncertainty.id) == [
        "minimum",
        "loc",
        "maximum",
        "scale",
    ]
    arr = sa.BetaPERTUncertainty.from_dicts(info)
    sa.BetaPERTUncertainty.validate(arr)
    mean = uncertainty_statistics_scalar(sa.BetaPERTUncertainty, arr, "mean")
    assert abs(mean - 5.166666666666667) < 1e-9
    ref = uncertainty_reference_value(sa.BetaPERTUncertainty, arr)
    assert abs(ref - mean) < 1e-9
    curve = preview_density(sa.BetaPERTUncertainty, arr)
    assert curve is not None
    assert np.nanmax(curve.y) > 0

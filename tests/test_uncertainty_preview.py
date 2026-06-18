"""Uncertainty dialog preview helpers (lognormal / Beta PERT / Student's t)."""
import numpy as np
import stats_arrays as sa

from activity_browser.bwutils.uncertainty import (
    standard_uncertainty_fields,
    uncertainty_reference_value,
    uncertainty_statistics_scalar,
    validate_uncertainty_dict,
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


def test_students_t_preview_with_optional_loc_scale():
    info = {
        "uncertainty type": sa.StudentsTUncertainty.id,
        "loc": np.nan,
        "scale": np.nan,
        "shape": 5.0,
        "minimum": np.nan,
        "maximum": np.nan,
        "negative": False,
    }
    arr, err = validate_uncertainty_dict(info)
    assert arr is not None
    assert err is None
    curve = preview_density(sa.StudentsTUncertainty, arr)
    assert curve is not None
    assert np.nanmax(curve.y) > 0


def test_gev_preview_with_defaults_and_shape_zero():
    info = {
        "uncertainty type": sa.GeneralizedExtremeValueUncertainty.id,
        "loc": np.nan,
        "scale": np.nan,
        "shape": np.nan,
        "minimum": np.nan,
        "maximum": np.nan,
        "negative": False,
    }
    arr, err = validate_uncertainty_dict(info)
    assert arr is not None
    assert err is None
    assert float(arr[0]["shape"]) == 0.0
    assert float(arr[0]["loc"]) == 0.0
    assert float(arr[0]["scale"]) == 1.0
    curve = preview_density(sa.GeneralizedExtremeValueUncertainty, arr)
    assert curve is not None
    assert np.nanmax(curve.y) > 0


def test_gamma_and_weibull_previews_differ():
    base = dict(
        loc=0.0,
        scale=2.0,
        shape=3.0,
        minimum=np.nan,
        maximum=np.nan,
        negative=False,
    )
    curves = {}
    for dist in (sa.GammaUncertainty, sa.WeibullUncertainty):
        info = {**base, "uncertainty type": dist.id}
        arr, err = validate_uncertainty_dict(info, dist)
        assert err is None
        assert int(arr[0]["uncertainty_type"]) == dist.id
        curve = preview_density(dist, arr)
        assert curve is not None
        curves[dist.id] = float(curve.x[np.argmax(curve.y)])

    assert curves[sa.GammaUncertainty.id] != curves[sa.WeibullUncertainty.id]


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

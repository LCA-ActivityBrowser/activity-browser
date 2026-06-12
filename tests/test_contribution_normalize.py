"""Contribution normalization with mixed-sign values."""

import numpy as np
import pytest

from activity_browser.bwutils.multilca import Contributions


@pytest.fixture
def contributions():
    return Contributions.__new__(Contributions)


def test_normalize_score_mode_uses_net_total(contributions):
    arr = np.array([[10.0, -5.0]])
    out = contributions.normalize(arr, total_range=False)
    np.testing.assert_allclose(out, [[200.0, -100.0]])


def test_normalize_score_mode_zero_net_falls_back_to_range(contributions):
    arr = np.array([[10.0, -10.0]])
    out = contributions.normalize(arr, total_range=False)
    np.testing.assert_allclose(out, [[50.0, -50.0]])
    assert np.isfinite(out).all()


def test_normalize_score_mode_all_zero(contributions):
    arr = np.array([[0.0, 0.0]])
    out = contributions.normalize(arr, total_range=False)
    np.testing.assert_allclose(out, [[0.0, 0.0]])


def test_normalize_range_mode(contributions):
    arr = np.array([[10.0, -2.0]])
    out = contributions.normalize(arr, total_range=True)
    np.testing.assert_allclose(out, 100.0 * arr / 12.0)

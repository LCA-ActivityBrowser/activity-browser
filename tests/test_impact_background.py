"""Tests for log-scaled impact tint intensity (no widget needed)."""

from __future__ import annotations

import pytest

from activity_browser.ui.delegates.impact_background import impact_intensity_fraction


def test_log_scale_separates_one_ten_fifty_hundred():
    """1 / 10 / 50 / 100 must spread clearly under max=100 (floor at 1%)."""
    one = impact_intensity_fraction(1.0, 100.0)
    ten = impact_intensity_fraction(10.0, 100.0)
    fifty = impact_intensity_fraction(50.0, 100.0)
    hundred = impact_intensity_fraction(100.0, 100.0)
    assert one == pytest.approx(0.0)
    assert hundred == pytest.approx(1.0)
    assert ten == pytest.approx(0.5)
    assert 0.8 < fifty < 0.95
    assert ten - one > 0.4
    assert hundred - fifty > 0.05
    assert fifty - ten > 0.2


def test_log_scale_zero_and_invalid_max():
    assert impact_intensity_fraction(0.0, 100.0) == 0.0
    assert impact_intensity_fraction(10.0, 0.0) == 0.0


def test_log_scale_clamps_above_max():
    assert impact_intensity_fraction(200.0, 100.0) == pytest.approx(1.0)

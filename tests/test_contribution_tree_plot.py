"""Tests for Contribution Tree plot label helpers (no Qt)."""

import numpy as np
import pytest

from activity_browser.app.pages.lca_results.contribution_tree_plot import (
    ContributionTreePlot,
    direct_impact_rgba,
)


def test_fit_label_shorten_at_word_boundary():
    text = "aluminium, primary, ingot"
    out = ContributionTreePlot._fit_label(text, max_chars=12, max_lines=1)
    assert out.endswith("…")
    assert not out.endswith(", c…")
    assert out.startswith("aluminium,")


def test_fit_label_unchanged_when_short():
    text = "electricity"
    assert ContributionTreePlot._fit_label(text, max_chars=20) == text


def test_fit_label_wraps_to_two_lines():
    text = "electricity, medium voltage, aluminium industry"
    out = ContributionTreePlot._fit_label(text, max_chars=18, max_lines=2)
    lines = out.splitlines()
    assert len(lines) <= 2
    assert lines[0].startswith("electricity,")
    assert "medium" not in lines[0] or len(lines[0]) <= 20


def test_fit_label_empty():
    assert ContributionTreePlot._fit_label("", max_chars=10) == ""


def test_label_worth_showing():
    assert ContributionTreePlot._label_worth_showing("aluminium, …") is True
    assert ContributionTreePlot._label_worth_showing("…") is False
    assert ContributionTreePlot._label_worth_showing("...") is False


def test_sunburst_tangent_rotation_readable():
    assert ContributionTreePlot._sunburst_tangent_rotation(0) == 0
    assert ContributionTreePlot._sunburst_tangent_rotation(np.pi) == 0


def test_sunburst_radial_rotation_readable():
    # East: horizontal outward
    assert ContributionTreePlot._sunburst_radial_rotation(np.pi / 2) == 0
    # North: vertical outward
    assert ContributionTreePlot._sunburst_radial_rotation(0) == 270


def test_lines_for_row_height():
    assert ContributionTreePlot._lines_for_row_height(0.22, 6.0) == 2
    assert ContributionTreePlot._lines_for_row_height(0.08, 6.0) == 1
    assert ContributionTreePlot._lines_for_row_height(0.65, 5.0) == 6


def test_fit_label_chars_breaks_mid_word():
    text = "aluminium, primary, ingot"
    out = ContributionTreePlot._fit_label_chars(text, max_chars=8, max_lines=3)
    lines = out.splitlines()
    assert len(lines) == 3
    assert all(len(line) <= 8 for line in lines[:-1])


def test_icicle_column_fontsize():
    assert ContributionTreePlot._icicle_column_fontsize(0.25, 6.0) == 6.0
    assert ContributionTreePlot._icicle_column_fontsize(0.1, 6.0) == 5.0


def test_direct_impact_rgba_burden_and_credit():
    r, g, b, a = direct_impact_rgba(50.0, 100.0)
    assert r == pytest.approx(70 / 255)
    assert a > 0.5
    cr, cg, cb, ca = direct_impact_rgba(-50.0, 100.0)
    assert cg > cr
    assert ca > 0.5

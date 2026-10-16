"""Aggregating contributions must keep every contribution, also rows whose grouping field is empty."""

import bw2data as bd
import numpy as np
import pytest

from activity_browser import app  # noqa: F401  # NOTE: create the AB application before pytest-qt does
from activity_browser.bwutils.multilca import MLCA, Contributions


@pytest.mark.parametrize("field", ["product", "location", "unit"])
def test_process_aggregation_keeps_total(basic_database, field):
    bd.Method(("basic_method",)).process()
    mlca = MLCA("basic_calculation_setup")
    mlca.calculate()
    contributions = Contributions(mlca)

    raw = contributions.get_contributions(contributions.ACT, functional_unit="0")
    aggregated, _, _ = contributions.aggregate_by_parameters(raw, contributions.TECH, field)

    np.testing.assert_allclose(aggregated.sum(), raw.sum())
    assert raw.sum() != 0


@pytest.mark.parametrize("field", ["name", "categories", "unit"])
def test_elementary_flow_aggregation_keeps_total(basic_database, field):
    bd.Method(("basic_method",)).process()
    mlca = MLCA("basic_calculation_setup")
    mlca.calculate()
    contributions = Contributions(mlca)

    raw = contributions.get_contributions(contributions.EF, functional_unit="0")
    aggregated, _, _ = contributions.aggregate_by_parameters(raw, contributions.BIOS, field)

    np.testing.assert_allclose(aggregated.sum(), raw.sum())
    assert raw.sum() != 0


def test_process_table_aggregated_by_empty_field_keeps_score(basic_database):
    bd.Method(("basic_method",)).process()
    mlca = MLCA("basic_calculation_setup")
    mlca.calculate()
    df = Contributions(mlca).top_process_contributions(functional_unit="0", aggregator="product")

    assert df.iloc[0, -1] == pytest.approx(mlca.lca_scores[0, 0])

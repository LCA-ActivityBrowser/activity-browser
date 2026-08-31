"""SHRECC create service unit tests."""
from types import SimpleNamespace

import pandas as pd

from ab_shrecc.create_service import build_inspect_artifacts, run_create


class _FakeNewDatabase:
    years = [2021]

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.created = False
        self.sources = {2021: "energy_charts"}
        self.background_databases = {2021: "bg-db"}
        self.database_names = {2021: "out-db"}
        self.mapping_gap_reports = {2021: pd.DataFrame({"DE": [0.01]}, index=[("DE", "wind")])}

    def create(self):
        self.created = True

    def mapping_report(self, year):
        return self.mapping_gap_reports[year]

    def table(self, year):
        return pd.DataFrame({"DE": [0.6, 0.4], "FR": [0.5, 0.5]}, index=["a1", "a2"])


def test_run_create_builds_artifacts_with_mock_factory():
    def factory(**kwargs):
        return _FakeNewDatabase(**kwargs)

    ndb, result = run_create({"years": [2021]}, new_database_factory=factory)
    assert ndb.created
    assert result.artifacts["summary"][0]["background_db"] == "bg-db"
    assert 2021 in result.artifacts["table_previews"]
    assert result.artifacts["column_sums"][2021]["DE"] == 1.0


def test_build_inspect_artifacts_skips_mapping_for_tyndp_year():
    ndb = SimpleNamespace(
        years=[2035],
        sources={2035: "tyndp"},
        background_databases={2035: "bg"},
        database_names={2035: "out"},
        mapping_gap_reports={},
    )
    ndb.mapping_report = lambda year: pd.DataFrame()
    ndb.table = lambda year: pd.DataFrame({"DE": [1.0]}, index=["x"])

    artifacts = build_inspect_artifacts(ndb, warnings=["done"])
    assert artifacts["mapping_reports"][2035] is None
    assert artifacts["warnings"] == ["done"]

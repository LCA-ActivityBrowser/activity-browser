"""Scenario files may include flow type = substitution."""

from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA
from activity_browser.bwutils.utils import Index, Key


def test_substitution_scenario_rows_map_to_technosphere_matrix():
    assert SuperstructureMLCA.matrices["substitution"] == "technosphere_matrix"
    idx = Index(
        input=Key("db", "from"),
        output=Key("db", "to"),
        flow_type="substitution",
    )
    assert idx.flip is False

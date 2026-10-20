"""Datapackage Scenario LCA matches a scenario difference file on the same exchanges."""

from __future__ import annotations

import inspect
import time
from pathlib import Path

import bw2data as bd
import numpy as np
import pytest
from bw2data.tests import bw2test

from activity_browser.bwutils.scenario_datapackage import ABMultiLCA
from activity_browser.bwutils.superstructure.manager import SuperstructureManager
from activity_browser.bwutils.superstructure.mlca import SuperstructureMLCA
from activity_browser.bwutils.utils import Index
from fixtures.bw_helpers import (
    write_calculation_setup,
    write_functional_database,
    write_method,
)
from fixtures.lcia_overview import (
    CALCULATION_SETUPS,
    DATABASE,
    DATABASE_NAME,
    METHODS,
    build_scenario_dataframe,
)

_SCORE_RTOL = 1e-8
_SCORE_ATOL = 1e-10


def _multilca_supports_arrays() -> bool:
    import bw2calc as bc

    return "use_arrays" in inspect.signature(bc.MultiLCA.__init__).parameters


pytestmark = pytest.mark.skipif(
    not _multilca_supports_arrays(),
    reason="MultiLCA on this stack has no use_arrays/next() scenario path",
)


def _wait_for_metadata(qapp, database_name: str, timeout: float = 30.0) -> None:
    from activity_browser.bwutils.metadata.metadata import MetaDataStore

    store = MetaDataStore()
    store.loader.load_project()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        qapp.processEvents()
        frame = store.dataframe
        if not frame.empty and database_name in set(frame.index.get_level_values(0)):
            return
        time.sleep(0.05)
    raise TimeoutError(f"Metadata for {database_name} did not load")


def _node_id(key: tuple) -> int:
    from activity_browser.bwutils.metadata.metadata import MetaDataStore

    frame = MetaDataStore().dataframe
    if key in frame.index:
        return int(frame.loc[key, "id"])
    return int(bd.get_activity(key).id)


def _write_scenario_datapackage(df, path: Path) -> None:
    """Dual-emit ``df`` (input, output, flow index) as a sequential scenario datapackage."""
    import bw_processing as bwp

    labels = [str(name) for name in df.columns]
    grouped: dict[str, list] = {}
    for key, series in df.iterrows():
        input_key, output_key, flow = key
        matrix = SuperstructureMLCA.matrices[flow]
        flip = Index.build_from_dict(
            {"input": input_key, "output": output_key, "flow type": flow}
        ).flip
        grouped.setdefault(matrix, []).append(
            (
                _node_id(input_key),
                _node_id(output_key),
                bool(flip),
                series.to_numpy(dtype=float),
            )
        )

    if path.exists():
        path.unlink()
    filesystem = bwp.generic_zipfile_filesystem(
        dirpath=path.parent, filename=path.name
    )
    package = bwp.create_datapackage(
        fs=filesystem,
        name="scenarios",
        sequential=True,
        metadata={"scenario_labels": labels, "scenario_count": len(labels)},
    )
    for matrix, rows in grouped.items():
        package.add_persistent_array(
            matrix=matrix,
            name=matrix,
            indices_array=np.array(
                [(row_id, col_id) for row_id, col_id, _flip, _amounts in rows],
                dtype=bwp.INDICES_DTYPE,
            ),
            data_array=np.vstack([amounts for _r, _c, _f, amounts in rows]),
            flip_array=np.array([flip for _r, _c, flip, _a in rows]),
        )
    package.finalize_serialization()


@pytest.fixture
@bw2test
def shared_scenario_exchanges(qapp, tmp_path):
    """One product system, one scenario difference table, and the same exchanges as a datapackage."""
    write_functional_database(DATABASE_NAME, DATABASE, process=True)
    write_method("lcia_method_0", METHODS["lcia_method_0"], process=True)
    write_calculation_setup("lcia_1x1", CALCULATION_SETUPS["lcia_1x1"])
    _wait_for_metadata(qapp, DATABASE_NAME)

    frame = SuperstructureManager(build_scenario_dataframe()).combined_data()
    frame = frame.copy()
    frame["excluded"] = 4.0
    package_path = tmp_path / "scenarios.zip"
    _write_scenario_datapackage(frame, package_path)
    return frame, package_path


def test_datapackage_matches_scenario_difference_file(shared_scenario_exchanges):
    frame, package_path = shared_scenario_exchanges
    included = ["low_demand", "baseline"]
    before = package_path.read_bytes()

    difference = SuperstructureMLCA("lcia_1x1", frame)
    difference.calculate()
    datapackage = ABMultiLCA("lcia_1x1", package_path, included)
    datapackage.calculate()

    assert list(datapackage.scenario_names) == ["baseline", "low_demand"]
    assert "excluded" not in datapackage.scenario_names
    assert "high_demand" not in datapackage.scenario_names

    for name in datapackage.scenario_names:
        difference_index = list(difference.scenario_names).index(name)
        datapackage_index = list(datapackage.scenario_names).index(name)
        scores_match = np.allclose(
            difference.lca_scores[:, :, difference_index],
            datapackage.lca_scores[:, :, datapackage_index],
            rtol=_SCORE_RTOL,
            atol=_SCORE_ATOL,
        )
        assert scores_match, name

    for name in datapackage.scenario_names:
        difference_index = list(difference.scenario_names).index(name)
        datapackage_index = list(datapackage.scenario_names).index(name)
        assert np.allclose(
            difference.elementary_flow_contributions[:, :, difference_index, :],
            datapackage.elementary_flow_contributions[:, :, datapackage_index, :],
            rtol=_SCORE_RTOL,
            atol=_SCORE_ATOL,
        ), name
        assert np.allclose(
            difference.process_contributions[:, :, difference_index, :],
            datapackage.process_contributions[:, :, datapackage_index, :],
            rtol=_SCORE_RTOL,
            atol=_SCORE_ATOL,
        ), name
        for fu_key in difference.fu_keys:
            assert np.allclose(
                difference.inventory[(fu_key, difference_index)],
                datapackage.inventory[(fu_key, datapackage_index)],
                rtol=_SCORE_RTOL,
                atol=_SCORE_ATOL,
            ), name

    scenario_index = datapackage.scenario_names.index("low_demand")
    demand = {bd.get_activity(next(iter(datapackage.func_units[0]))).id: 1.0}
    singular = datapackage.singular_lca(demand, datapackage.methods[0], scenario_index)
    again = datapackage.singular_lca(demand, datapackage.methods[0], scenario_index)
    assert again is singular

    supplier_id = _node_id((DATABASE_NAME, "supplier_product"))
    product_id = _node_id((DATABASE_NAME, "prod_0"))
    amount = float(
        singular.technosphere_matrix[
            singular.product_dict[supplier_id],
            singular.activity_dict[product_id],
        ]
    )
    assert amount == pytest.approx(-0.5)

    assert package_path.read_bytes() == before
    assert not isinstance(datapackage, SuperstructureMLCA)

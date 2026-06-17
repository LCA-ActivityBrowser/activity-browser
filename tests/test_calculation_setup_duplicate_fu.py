"""Calculation setups may list the same reference flow more than once."""

import bw2data as bd

from activity_browser.app.pages.calculation_setup.functional_unit_section import FunctionalUnitSection
from activity_browser.bwutils.multilca import MLCA, Contributions


def test_duplicate_reference_flow_in_cs_build_df(basic_database):
    cs_name = "basic_calculation_setup"
    key = ("basic", "product_1")
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{key: 1.0}, {key: 2.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    section = FunctionalUnitSection(cs_name)
    df = section.build_df()

    assert len(df) == 2
    assert list(df["amount"]) == [1.0, 2.0]
    assert df["process"].notna().all()


def test_duplicate_reference_flow_in_cs_calculate(basic_database):
    cs_name = "basic_calculation_setup"
    key = ("basic", "product_1")
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{key: 1.0}, {key: 2.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    bd.Method(("basic_method",)).process()

    mlca = MLCA(cs_name)
    assert mlca.fu_keys == ("0", "1")
    assert mlca.fu_demands == {"0": {key: 1.0}, "1": {key: 2.0}}

    mlca.calculate()
    scores = mlca.lca_scores_to_dataframe()

    assert scores.shape[0] == 2
    assert scores.iloc[0, 0] != scores.iloc[1, 0]

    overview = Contributions(mlca).lca_scores_df()
    assert len(overview) == 2
    assert overview["amount"].tolist() == [1.0, 2.0]


def test_duplicate_reference_flow_same_amount_inventory(basic_database):
    """Same activity and amount twice must not collapse inventory columns."""
    cs_name = "basic_calculation_setup"
    key = ("basic", "product_1")
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{key: 1.0}, {key: 1.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    bd.Method(("basic_method",)).process()

    mlca = MLCA(cs_name)
    mlca.calculate()
    contributions = Contributions(mlca)

    assert len(mlca.inventory) == 2
    assert set(mlca.inventory) == {"0", "1"}
    contributions.inventory_df(inventory_type="biosphere")
    contributions.inventory_df(inventory_type="technosphere")


def test_setup_fu_labels_exclude_amount(basic_database):
    from activity_browser.bwutils.multilca import _load_cs

    key = ("basic", "product_1")
    obj = type("Obj", (), {})()
    _load_cs(obj, [{key: 1.0}, {key: 2.0}], [])
    assert len(obj.fu_labels) == 2
    assert obj.fu_labels[0] == obj.fu_labels[1]
    assert "1.0" not in obj.fu_labels[0]


def test_duplicate_reference_flow_contribution_columns(basic_database):
    """Compare-by-method must keep one column per inv row, not collapse on label."""
    cs_name = "basic_calculation_setup"
    key = ("basic", "product_1")
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{key: 1.0}, {key: 2.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    bd.Method(("basic_method",)).process()

    mlca = MLCA(cs_name)
    mlca.calculate()
    contributions = Contributions(mlca)
    method = mlca.methods[0]

    matrix = contributions.get_contributions("process", method=method)
    assert matrix.shape[0] == 2

    df = contributions.top_process_contributions(method=method, limit=5)
    numeric_cols = df.select_dtypes(include="number").columns
    assert set(numeric_cols) == {0, 1}


def test_superstructure_build_inventory_keeps_duplicate_reference_flows(basic_database):
    """Scenario inventory table must have one column per inv row."""
    from activity_browser.bwutils.multilca import MLCA
    from activity_browser.bwutils.superstructure.mlca import (
        SuperstructureContributions,
        SuperstructureMLCA,
    )

    cs_name = "basic_calculation_setup"
    key = ("basic", "product_1")
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{key: 1.0}, {key: 1.0}, {key: 2.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    bd.Method(("basic_method",)).process()

    mlca = MLCA(cs_name)
    mlca.calculate()

    fake = object.__new__(SuperstructureMLCA)
    fake.__dict__.update(mlca.__dict__)
    fake.total = 1
    fake._current_index = 0
    fake.inventory = {(fu_key, 0): mlca.inventory[fu_key] for fu_key in mlca.fu_keys}
    fake.technosphere_flows = {
        (fu_key, 0): mlca.technosphere_flows[fu_key] for fu_key in mlca.fu_keys
    }

    contributions = SuperstructureContributions(fake)
    contributions.inventory_df(inventory_type="biosphere")
    contributions.inventory_df(inventory_type="technosphere")



def test_build_df_handles_missing_reference_flow(basic_database):
    cs_name = "basic_calculation_setup"
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{("basic", "ghost_product"): 1.0}]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    section = FunctionalUnitSection(cs_name)
    df = section.build_df()

    assert len(df) == 1
    assert df.iloc[0]["product"] == "(missing reference flow)"


def test_sync_prunes_missing_functional_units(basic_database):
    cs_name = "basic_calculation_setup"
    cs = bd.calculation_setups[cs_name]
    cs["inv"] = [{("basic", "ghost_product"): 1.0}]
    cs["inv_active"] = [True]
    bd.calculation_setups[cs_name] = cs
    bd.calculation_setups.serialize()

    section = FunctionalUnitSection(cs_name)
    section.sync()

    assert bd.calculation_setups[cs_name]["inv"] == []
    assert section.model.df.empty

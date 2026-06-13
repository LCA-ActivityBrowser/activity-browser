from activity_browser.bwutils.export_names import (
    activity_export_fields,
    contribution_compare_export_slug,
    contribution_tab_slug,
    export_name_slug,
    flip_export_slug,
    lcia_compare_export_slug,
    lca_export_basename,
    relativity_export_slug,
)
from activity_browser.bwutils.lcia_overview import LCIACompareMode
from activity_browser.ui.widgets.comparison_switch import Switches


def test_lcia_compare_modes_produce_distinct_basenames():
    cs = "my_cs"
    base_ref = lca_export_basename(
        cs, "LCA scores", lcia_compare_export_slug(LCIACompareMode.REFERENCE_FLOWS), "abs"
    )
    base_methods = lca_export_basename(
        cs,
        "LCA scores",
        lcia_compare_export_slug(LCIACompareMode.FLOWS_X_METHODS),
        "abs",
    )
    assert base_ref != base_methods
    assert "ref_flows" in base_ref
    assert "ref_flows_x_impacts" in base_methods


def test_relativity_and_flip_suffixes():
    name = lca_export_basename(
        "cs",
        "LCA scores",
        lcia_compare_export_slug(LCIACompareMode.FLOWS_X_METHODS),
        relativity_export_slug(relative=True),
        flip_export_slug(flipped=True),
    )
    assert "_rel" in name
    assert name.endswith("_f") or "_f_" in name


def test_method_tuple_is_slugged():
    method = ("IPCC 2021", "climate change", "GWP100")
    name = lca_export_basename("cs", "LCA scores", export_name_slug(method))
    assert "IPCC_2021" in name
    assert "," not in name


def test_contribution_compare_and_tab_slugs():
    indexes = Switches(0, 1, 2)
    assert contribution_compare_export_slug(0, indexes) == "ref_flows"
    assert contribution_compare_export_slug(1, indexes) == "impacts"
    assert contribution_tab_slug("EF contributions") == "EF"
    assert contribution_tab_slug("Process contributions") == "process"


def test_activity_export_fields_from_dict():
    act = {
        "name": "steel production",
        "reference product": "steel",
        "location": "GLO",
        "database": "test_db",
        "type": "process",
    }
    parts = activity_export_fields(act)
    assert parts == ["steel", "steel_production", "GLO", "test_db"]

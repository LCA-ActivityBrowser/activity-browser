"""Fast AB impact-category Excel interchange tests (bwutils seam)."""
from pathlib import Path

import bw2data as bd
import pytest
from bw2data.tests import bw2test
from stats_arrays import LognormalUncertainty

from activity_browser.bwutils.impact_categories import (
    ConflictMode,
    apply_name_conflicts,
    export_methods_ab_xlsx,
    import_ab_methods,
    join_tuple_path,
    load_ab_xlsx,
    split_tuple_path,
)
from fixtures.basic import DATABASE
from fixtures.bw_helpers import write_functional_database


def test_join_split_tuple_path():
    assert join_tuple_path(("My", "climate", "GWP")) == "My::climate::GWP"
    assert split_tuple_path("My::climate::GWP") == ("My", "climate", "GWP")
    assert split_tuple_path("single") == ("single",)


def test_apply_name_conflicts_rename_prefix():
    data = [
        {"name": ("IPCC", "GWP"), "unit": "kg", "description": "", "exchanges": []},
        {"name": ("new",), "unit": "kg", "description": "", "exchanges": []},
    ]
    out = apply_name_conflicts(
        data,
        {("IPCC", "GWP")},
        mode=ConflictMode.RENAME_PREFIX,
        prefix="Import",
    )
    names = {ds["name"] for ds in out}
    assert ("Import", "IPCC", "GWP") in names
    assert ("new",) in names


def test_apply_name_conflicts_skip():
    data = [
        {"name": ("IPCC", "GWP"), "unit": "kg", "description": "", "exchanges": []},
        {"name": ("new",), "unit": "kg", "description": "", "exchanges": []},
    ]
    out = apply_name_conflicts(data, {("IPCC", "GWP")}, mode=ConflictMode.SKIP)
    assert [ds["name"] for ds in out] == [("new",)]


def test_apply_name_conflicts_per_row_renames():
    data = [
        {"name": ("IPCC", "GWP"), "unit": "kg", "description": "", "exchanges": []},
        {"name": ("kept",), "unit": "kg", "description": "", "exchanges": []},
    ]
    out = apply_name_conflicts(
        data,
        {("IPCC", "GWP")},
        mode=ConflictMode.SKIP,
        renames={("IPCC", "GWP"): ("IPCC", "GWP", "imported")},
    )
    assert [ds["name"] for ds in out] == [("IPCC", "GWP", "imported"), ("kept",)]


def test_ab_csv_sibling_resolution(tmp_path: Path):
    from activity_browser.bwutils.impact_categories import (
        ab_csv_sibling_path,
        resolve_ab_csv_pair,
    )

    cfs = tmp_path / "demo.cfs.csv"
    ics = tmp_path / "demo.metadata.csv"
    cfs.write_text("method,flow,amount\n", encoding="utf-8")
    ics.write_text("method,unit,description\n", encoding="utf-8")
    assert ab_csv_sibling_path(cfs) == ics
    assert resolve_ab_csv_pair(cfs) == (cfs, ics)
    assert resolve_ab_csv_pair(ics) == (cfs, ics)


def test_bw2io_metadata_csv_filename_match(tmp_path: Path):
    from activity_browser.bwutils.impact_categories.bw2io_lcia_file import (
        read_bw2io_metadata_csv,
    )

    meta = tmp_path / "metadata.csv"
    meta.write_text(
        "filename,method,unit,description\n"
        "a.csv,Method::A,kg,desc A\n"
        "b.csv,Method::B,t,desc B\n",
        encoding="utf-8",
    )
    row = read_bw2io_metadata_csv(meta, cf_filename="b.csv")
    assert row["method"] == "Method::B"
    assert row["unit"] == "t"
    assert read_bw2io_metadata_csv(meta, cf_filename="missing.csv") is None


def test_bw2io_metadata_csv_single_row_fallback(tmp_path: Path):
    from activity_browser.bwutils.impact_categories.bw2io_lcia_file import (
        read_bw2io_metadata_csv,
    )

    meta = tmp_path / "metadata.csv"
    meta.write_text(
        "method,unit,description\none::method,kg,only\n",
        encoding="utf-8",
    )
    row = read_bw2io_metadata_csv(meta, cf_filename="anything.csv")
    assert row["method"] == "one::method"


def test_method_name_to_filename_stem_is_cross_platform():
    from activity_browser.bwutils.impact_categories import method_name_to_filename_stem

    stem = method_name_to_filename_stem(("IPCC", "climate change", "GWP100"))
    assert stem == "IPCC__climate change__GWP100"
    assert ":" not in stem
    assert "/" not in stem
    assert "\\" not in stem
    dirty = method_name_to_filename_stem(("a:b", "c/d", "e|f"))
    assert ":" not in dirty
    assert "/" not in dirty
    assert "|" not in dirty


@bw2test
def test_ab_csv_round_trip(tmp_path: Path):
    from activity_browser.bwutils.impact_categories import (
        export_methods_ab_csv_pair,
        load_ab_csv_pair,
    )

    write_functional_database("basic", DATABASE, process=True)
    name = ("climate", "gwp")
    method = bd.Method(name)
    method.register(unit="kg", description="GWP demo")
    method.write([(("basic", "elementary"), 1.5)], process=True)
    bd.methods.flush()

    export_methods_ab_csv_pair([name], tmp_path / "demo")
    loaded = load_ab_csv_pair(tmp_path / "demo.cfs.csv")
    assert len(loaded) == 1
    assert loaded[0]["name"] == name
    assert loaded[0]["exchanges"][0]["amount"] == 1.5


@bw2test
def test_bw2io_xlsx_round_trip(tmp_path: Path):
    from activity_browser.bwutils.impact_categories.bw2io_lcia_file import (
        export_method_bw2io_xlsx,
        load_bw2io_lcia_file,
        read_bw2io_metadata_xlsx,
    )

    write_functional_database("basic", DATABASE, process=True)
    name = ("climate", "gwp")
    method = bd.Method(name)
    method.register(unit="kg", description="GWP demo")
    method.write([(("basic", "elementary"), 3.0)], process=True)
    bd.methods.flush()

    out = tmp_path / "one.xlsx"
    export_method_bw2io_xlsx(name, out)
    meta = read_bw2io_metadata_xlsx(out)
    assert meta["method"] == "climate::gwp"
    assert meta["filename"] == "one.xlsx"
    data = load_bw2io_lcia_file(
        out, name=name, unit=meta["unit"], description=meta["description"]
    )
    assert data[0]["exchanges"][0]["amount"] == 3.0
    assert data[0]["exchanges"][0]["categories"] == ("air",)


@bw2test
def test_ab_xlsx_round_trip_preserves_uncertainty(tmp_path: Path):
    write_functional_database("basic", DATABASE, process=True)
    cfs = [
        (
            ("basic", "elementary"),
            {
                "amount": 2.5,
                "uncertainty type": LognormalUncertainty.id,
                "loc": 0.9,
                "scale": 0.2,
                "negative": False,
            },
        )
    ]
    name = ("climate", "gwp")
    method = bd.Method(name)
    method.register(unit="kg", description="GWP demo")
    method.write(cfs, process=True)
    bd.methods.flush()

    out = tmp_path / "ab-lcia.xlsx"
    export_methods_ab_xlsx([name], out)

    loaded = load_ab_xlsx(out)
    assert len(loaded) == 1
    ds = loaded[0]
    assert ds["name"] == name
    assert ds["unit"] == "kg"
    assert ds["description"] == "GWP demo"
    assert len(ds["exchanges"]) == 1
    exc = ds["exchanges"][0]
    assert exc["name"] == "elementary"
    assert exc["categories"] == ("air",)
    assert exc["amount"] == 2.5
    assert exc["uncertainty type"] == LognormalUncertainty.id
    assert exc["loc"] == pytest.approx(0.9)
    assert exc["scale"] == pytest.approx(0.2)

    del bd.methods[name]
    bd.methods.flush()
    stats = import_ab_methods(
        loaded,
        biosphere_name="basic",
        conflict_mode=ConflictMode.OVERWRITE,
    )
    assert stats.written == 1
    assert stats.unlinked == 0
    written = list(bd.Method(name).load())
    assert len(written) == 1
    payload = written[0][1]
    assert isinstance(payload, dict)
    assert payload["amount"] == 2.5
    assert payload["uncertainty type"] == LognormalUncertainty.id
    assert bd.methods[name].get("description") == "GWP demo"


@bw2test
def test_import_ab_methods_blocks_on_unlinked():
    write_functional_database("basic", DATABASE, process=True)
    data = [
        {
            "name": ("climate", "gwp"),
            "unit": "kg",
            "description": "",
            "filename": "test.xlsx",
            "exchanges": [
                {
                    "name": "does-not-exist",
                    "categories": ("air",),
                    "amount": 1.0,
                }
            ],
        }
    ]
    stats = import_ab_methods(data, biosphere_name="basic")
    assert stats.written == 0
    assert stats.unlinked == 1
    assert ("climate", "gwp") not in bd.methods


@bw2test
def test_import_ab_methods_drop_unlinked_writes_linked_only():
    write_functional_database("basic", DATABASE, process=True)
    data = [
        {
            "name": ("climate", "gwp"),
            "unit": "kg",
            "description": "",
            "filename": "test.xlsx",
            "exchanges": [
                {
                    "name": "elementary",
                    "categories": ("air",),
                    "amount": 2.0,
                },
                {
                    "name": "does-not-exist",
                    "categories": ("air",),
                    "amount": 9.0,
                },
            ],
        }
    ]
    stats = import_ab_methods(
        data, biosphere_name="basic", drop_unlinked=True
    )
    assert stats.written == 1
    assert stats.unlinked == 0
    cfs = list(bd.Method(("climate", "gwp")).load())
    assert len(cfs) == 1
    assert cfs[0][1] == 2.0 or (
        isinstance(cfs[0][1], dict) and cfs[0][1]["amount"] == 2.0
    )

"""Calculation-setup scenario input: datapackage side, reload, and Calculate refusal."""

from __future__ import annotations

from pathlib import Path

import bw2data as bd
import numpy as np
import pytest
from bw2data.tests import bw2test
from qtpy import QtCore, QtWidgets

from activity_browser import app
from activity_browser.app.pages.calculation_setup.calculation_setup import (
    CalculationSetupPage,
)
from activity_browser.bwutils import calculation_setup as cs_helpers
from activity_browser.bwutils.superstructure.inclusion import MODE_PRODUCT


def _write_package(path: Path, labels: list[str] | None, *, sequential: bool = True) -> None:
    import bw_processing as bwp

    if path.exists():
        path.unlink()
    metadata = {}
    width = 2
    if labels is not None:
        metadata = {"scenario_labels": list(labels), "scenario_count": len(labels)}
        width = len(labels)
    filesystem = bwp.generic_zipfile_filesystem(
        dirpath=path.parent, filename=path.name
    )
    package = bwp.create_datapackage(
        fs=filesystem,
        name="scenarios",
        sequential=sequential,
        metadata=metadata or None,
    )
    package.add_persistent_array(
        matrix="technosphere_matrix",
        name="flows",
        indices_array=np.array([(1, 2)], dtype=bwp.INDICES_DTYPE),
        data_array=np.array([[float(i + 1) for i in range(width)]]),
        flip_array=np.array([True]),
    )
    package.finalize_serialization()


def _patch_warnings(monkeypatch):
    seen: list[str] = []

    def warning(*args, **kwargs):
        seen.append(args[1] if len(args) > 1 else "")
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", warning)
    return seen


@bw2test
def test_datapackage_fields_stay_when_the_other_side_is_cleared():
    bd.calculation_setups["cs"] = {"inv": [], "ia": []}
    cs_helpers.set_scenario_persistence(
        "cs",
        paths=["/tmp/scenarios.xlsx"],
        combine=MODE_PRODUCT,
        included=["A | X"],
        axes=[["A"], ["X"]],
    )
    cs_helpers.set_scenario_datapackage_persistence("cs", "/tmp/scenarios.zip", ["baseline"])
    cs_helpers.set_scenario_input("cs", cs_helpers.INPUT_DATAPACKAGE)

    stored = bd.calculation_setups["cs"]
    assert cs_helpers.scenario_input_kind(stored) == cs_helpers.INPUT_DATAPACKAGE
    assert cs_helpers.get_scenario_datapackage(stored)[cs_helpers.SCENARIO_DATAPACKAGE_PATH] == (
        "/tmp/scenarios.zip"
    )
    assert cs_helpers.get_scenario_datapackage(stored)[
        cs_helpers.SCENARIO_DATAPACKAGE_INCLUDED
    ] == ["baseline"]
    assert cs_helpers.scenario_input_kind({}) == cs_helpers.INPUT_SDF

    cs_helpers.clear_scenario_datapackage_persistence("cs")
    stored = bd.calculation_setups["cs"]
    assert cs_helpers.get_scenario_datapackage(stored) is None
    assert cs_helpers.get_scenario_persistence(stored)[cs_helpers.SCENARIO_PATHS] == [
        "/tmp/scenarios.xlsx"
    ]
    assert cs_helpers.scenario_input_kind(stored) == cs_helpers.INPUT_DATAPACKAGE

    cs_helpers.set_scenario_datapackage_persistence("cs", "/tmp/scenarios.zip", ["baseline"])
    cs_helpers.clear_scenario_persistence("cs")
    stored = bd.calculation_setups["cs"]
    assert cs_helpers.get_scenario_persistence(stored) is None
    assert cs_helpers.get_scenario_datapackage(stored)[
        cs_helpers.SCENARIO_DATAPACKAGE_INCLUDED
    ] == ["baseline"]


def test_reconcile_datapackage_inclusion_selects_all_when_names_disagree():
    assert cs_helpers.reconcile_datapackage_inclusion(None, ["baseline", "high"]) == (
        ["baseline", "high"],
        False,
    )
    assert cs_helpers.reconcile_datapackage_inclusion([], ["baseline", "high"]) == (
        [],
        False,
    )
    assert cs_helpers.reconcile_datapackage_inclusion(
        ["high", "baseline"], ["baseline", "high", "low"]
    ) == (["baseline", "high"], False)
    assert cs_helpers.reconcile_datapackage_inclusion(
        ["baseline", "retired"], ["baseline", "high"]
    ) == (["baseline", "high"], True)


@pytest.fixture
@bw2test
def scenario_page(qapp, qtbot, main_window, monkeypatch):
    warnings = _patch_warnings(monkeypatch)
    bd.calculation_setups["cs"] = {"inv": [], "ia": []}
    bd.calculation_setups.flush()
    page = CalculationSetupPage("cs")
    qtbot.addWidget(page)
    return page, warnings


def test_scenario_mode_loads_only_the_active_side(scenario_page, tmp_path, qtbot):
    page, warnings = scenario_page
    package = tmp_path / "scenarios.zip"
    _write_package(package, ["baseline", "high"])
    missing_sdf = tmp_path / "missing.xlsx"
    cs_helpers.set_scenario_persistence(
        "cs",
        paths=[str(missing_sdf)],
        combine=MODE_PRODUCT,
        included=["baseline"],
        axes=[["baseline"]],
    )
    cs_helpers.set_scenario_datapackage_persistence(
        "cs", str(package), ["baseline"]
    )
    cs_helpers.set_scenario_input("cs", cs_helpers.INPUT_DATAPACKAGE)

    assert page.type_dropdown.currentText() == "Standard"
    assert page.scenario_section.isHidden()
    assert warnings == []

    page.show()
    page.type_dropdown.setCurrentText("Scenario")
    assert page.scenario_section.uses_datapackage()
    assert page.scenario_section.sdf_panel.isHidden()
    assert not page.scenario_section.datapackage_panel.isHidden()
    assert page.scenario_section.datapackage_panel.included_names() == ["baseline"]
    assert page.scenario_section.tables == []
    assert "Scenario files not found" not in warnings

    page.type_dropdown.setCurrentText("Standard")
    page.type_dropdown.setCurrentText("Scenario")
    assert "Scenario files not found" not in warnings
    assert page.scenario_section.datapackage_panel.included_names() == ["baseline"]

    page.show()
    qtbot.mouseClick(
        page.scenario_section.sdf_choice, QtCore.Qt.MouseButton.LeftButton
    )
    assert "Scenario files not found" in warnings
    assert cs_helpers.get_scenario_persistence(bd.calculation_setups["cs"]) is None
    assert cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"])[
        cs_helpers.SCENARIO_DATAPACKAGE_PATH
    ] == str(package)
    assert page.scenario_section.sdf_choice.isChecked()


def test_datapackage_names_fallback_and_stale_inclusion(scenario_page, tmp_path):
    page, warnings = scenario_page
    package = tmp_path / "unlabeled.zip"
    _write_package(package, None)
    cs_helpers.set_scenario_datapackage_persistence("cs", str(package), ["retired"])
    cs_helpers.set_scenario_input("cs", cs_helpers.INPUT_DATAPACKAGE)

    page.type_dropdown.setCurrentText("Scenario")
    assert "Scenario names" in warnings
    assert "Scenario selection reset" in warnings
    assert page.scenario_section.datapackage_panel.included_names() == [
        "Scenario 0",
        "Scenario 1",
    ]
    stored = cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"])
    assert stored[cs_helpers.SCENARIO_DATAPACKAGE_INCLUDED] == ["Scenario 0", "Scenario 1"]
    assert "Selected scenarios:" in page.scenario_section.datapackage_panel.count_label.text()


def test_invalid_datapackage_clears_only_that_side(scenario_page, tmp_path):
    page, warnings = scenario_page
    bad = tmp_path / "notes.txt"
    bad.write_text("not a datapackage", encoding="utf-8")
    cs_helpers.set_scenario_persistence(
        "cs",
        paths=[str(tmp_path / "kept.xlsx")],
        combine=MODE_PRODUCT,
        included=["A"],
        axes=[["A"]],
    )
    cs_helpers.set_scenario_datapackage_persistence("cs", str(bad), ["A"])
    cs_helpers.set_scenario_input("cs", cs_helpers.INPUT_DATAPACKAGE)

    page.type_dropdown.setCurrentText("Scenario")
    assert "Scenario datapackage" in warnings
    assert page.scenario_section.datapackage_choice.isChecked()
    assert cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"]) is None
    assert cs_helpers.get_scenario_persistence(bd.calculation_setups["cs"])[
        cs_helpers.SCENARIO_PATHS
    ] == [str(tmp_path / "kept.xlsx")]
    assert cs_helpers.scenario_input_kind(bd.calculation_setups["cs"]) == (
        cs_helpers.INPUT_DATAPACKAGE
    )


def test_calculate_refuses_datapackage_without_clearing_either_side(
    scenario_page, tmp_path, monkeypatch
):
    from activity_browser.app.actions.calculation_setup.cs_calculate import CSCalculate

    page, warnings = scenario_page
    method = bd.Method(("method",))
    method.register(unit="kg", num_cfs=0)
    stored = bd.calculation_setups["cs"]
    stored["inv"] = [{("db", "prod"): 1.0}]
    stored["ia"] = [("method",)]
    bd.calculation_setups["cs"] = stored
    package = tmp_path / "scenarios.zip"
    _write_package(package, ["baseline", "high"])
    bad = tmp_path / "bad.txt"
    bad.write_text("nope", encoding="utf-8")
    sdf_path = str(tmp_path / "kept.xlsx")
    cs_helpers.set_scenario_persistence(
        "cs",
        paths=[sdf_path],
        combine=MODE_PRODUCT,
        included=["A"],
        axes=[["A"]],
    )
    cs_helpers.set_scenario_input("cs", cs_helpers.INPUT_DATAPACKAGE)

    def refuse(path, included):
        warnings.clear()
        CSCalculate.run(
            "cs",
            scenario_datapackage={"path": path, "included": included},
        )
        stored = bd.calculation_setups["cs"]
        assert cs_helpers.get_scenario_persistence(stored)[cs_helpers.SCENARIO_PATHS] == [
            sdf_path
        ]
        assert cs_helpers.scenario_input_kind(stored) == cs_helpers.INPUT_DATAPACKAGE

    cs_helpers.set_scenario_datapackage_persistence("cs", str(package), ["baseline"])
    refuse("", ["baseline"])
    assert warnings == ["Scenario datapackage"]
    assert cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"])[
        cs_helpers.SCENARIO_DATAPACKAGE_PATH
    ] == str(package)

    refuse(str(tmp_path / "missing.zip"), ["baseline"])
    assert warnings == ["Scenario datapackage"]

    cs_helpers.set_scenario_datapackage_persistence("cs", str(bad), ["baseline"])
    refuse(str(bad), ["baseline"])
    assert warnings == ["Scenario datapackage"]
    assert cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"])[
        cs_helpers.SCENARIO_DATAPACKAGE_PATH
    ] == str(bad)

    cs_helpers.set_scenario_datapackage_persistence("cs", str(package), [])
    refuse(str(package), [])
    assert warnings == ["No scenarios selected"]
    assert cs_helpers.get_scenario_datapackage(bd.calculation_setups["cs"])[
        cs_helpers.SCENARIO_DATAPACKAGE_INCLUDED
    ] == []

    captured = {}

    def fake_run(cs_name, scenario_data=None, scenario_datapackage=None):
        captured["cs_name"] = cs_name
        captured["scenario_data"] = scenario_data
        captured["scenario_datapackage"] = scenario_datapackage

    monkeypatch.setattr(app.actions.CSCalculate, "run", staticmethod(fake_run))
    page.run_calculation()
    assert captured["scenario_data"] is None
    assert captured["scenario_datapackage"] is None

    page.type_dropdown.setCurrentText("Scenario")
    page.scenario_section.datapackage_choice.setChecked(True)
    page.scenario_section.use_datapackage_path(str(package))
    page.run_calculation()
    assert captured["scenario_datapackage"]["path"] == str(package)
    assert captured["scenario_datapackage"]["included"] == ["baseline", "high"]
    assert "scenario_data" not in captured or captured["scenario_data"] is None

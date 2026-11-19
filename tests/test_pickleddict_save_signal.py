"""PickledDict/SerializedDict ``_save_signal`` must reach AB on unsourced projects."""

from blinker import signal as blinker_signal
import bw2data as bd

from activity_browser.mod.bw2data import serialized_save_compat  # noqa: F401


def test_calculation_setups_serialize_emits_save_signal_when_unsourced():
    """Drag/add into a CS refreshes via calculation_setups_changed ← _save_signal.

    bw2data 4.8 gates PickledDict._save_signal on is_sourced (revision-only).
    AB restores emit on unsourced projects so CS tables sync after drop/add.
    """
    assert not bd.projects.dataset.is_sourced

    setattr(
        bd.calculation_setups,
        "_save_signal",
        blinker_signal("ab.test_patched_calculation_setups"),
    )

    cs_name = "__ab_test_cs_save_signal__"
    bd.calculation_setups[cs_name] = {"inv": [{("db", "a"): 1.0}], "ia": []}
    seen = []

    def _capture(sender, old=None, new=None, **_kwargs):
        seen.append(new)

    bd.calculation_setups._save_signal.connect(_capture)
    try:
        seen.clear()
        cs = bd.calculation_setups[cs_name]
        cs["inv"] += [{("db", "b"): 1.0}]
        bd.calculation_setups[cs_name] = cs
        bd.calculation_setups.serialize()
        assert len(bd.calculation_setups[cs_name]["inv"]) == 2
        assert seen, "PickledDict.serialize must emit _save_signal on unsourced projects"
    finally:
        bd.calculation_setups._save_signal.disconnect(_capture)
        if cs_name in bd.calculation_setups:
            del bd.calculation_setups[cs_name]
            bd.calculation_setups.serialize(signal=False)


def test_databases_flush_emits_save_signal_when_unsourced():
    """databases._save_signal is the same #299 gate (SerializedDict)."""
    assert not bd.projects.dataset.is_sourced
    assert hasattr(bd.databases, "_save_signal")

    seen = []

    def _capture(sender, old=None, new=None, **_kwargs):
        seen.append(True)

    bd.databases._save_signal.connect(_capture)
    try:
        bd.databases.flush()
        assert seen, "SerializedDict.serialize must emit _save_signal on unsourced projects"
    finally:
        bd.databases._save_signal.disconnect(_capture)

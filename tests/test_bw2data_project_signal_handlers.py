"""Project blinker → Qt / MDS: treat Brightway payload as a trigger only."""

from activity_browser import app  # noqa: F401  — ABApplication before pytest-qt's QApplication


def test_ab_signals_project_handlers_ignore_blinker_payload(qtbot):
    signals = app.signals
    _ = signals.project  # connect Brightway bridges

    with qtbot.waitSignal(signals.project.created, timeout=1000):
        signals._on_project_created(object(), dataset=object())
    with qtbot.waitSignal(signals.project.changed, timeout=1000):
        signals._on_project_changed(object(), dataset=object())

    # bw2data 4.7: first positional arg is the dataset
    with qtbot.waitSignal(signals.project.created, timeout=1000):
        signals._on_project_created(object())
    with qtbot.waitSignal(signals.project.changed, timeout=1000):
        signals._on_project_changed(object())


def test_mds_loader_on_project_changed_ignores_payload(monkeypatch):
    from activity_browser.bwutils.metadata.metadata import MetaDataStore

    loader = MetaDataStore().loader
    called = []
    monkeypatch.setattr(loader, "load_project", lambda: called.append(True))

    loader.on_project_changed(object(), dataset=object())
    loader.on_project_changed(object())
    assert called == [True, True]


def test_signaleddataset_save_emits_on_unsourced_project(qtbot, basic_database):
    """bw2data 4.8 skips signaleddataset_on_save unless is_sourced; AB restores it."""
    import bw2data as bd
    from bw2data.signals import signaleddataset_on_save

    from activity_browser.mod.bw2data import signaled_save_compat  # noqa: F401

    assert not bd.projects.dataset.is_sourced

    seen = []

    def _capture(sender, old=None, new=None, **_kwargs):
        seen.append(new)

    signaleddataset_on_save.connect(_capture)
    try:
        node = basic_database.new_activity(code="signal-compat", name="signal-compat", type="process")
        node.save()
    finally:
        signaleddataset_on_save.disconnect(_capture)

    assert any(getattr(n, "code", None) == "signal-compat" for n in seen)
    assert ("basic", "signal-compat") in app.metadata.keys

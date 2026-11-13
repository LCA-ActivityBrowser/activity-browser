"""Adapt receivers to bw2data 4.8 project signals (send(manager, dataset=...))."""

from activity_browser import app  # noqa: F401  — ABApplication before pytest-qt's QApplication


def test_ab_signals_project_handlers_accept_both_emit_styles(qtbot):
    signals = app.signals
    _ = signals.project  # connect Brightway bridges
    previous = signals._project_dataset

    try:
        manager = object()
        dataset = object()

        signals._on_project_created(manager, dataset=dataset)
        signals._on_project_changed(manager, dataset=dataset)
        assert signals._project_dataset is dataset

        # bw2data 4.7: first positional arg is the dataset
        older = object()
        signals._on_project_created(older)
        signals._on_project_changed(older)
        assert signals._project_dataset is older
    finally:
        signals._project_dataset = previous


def test_mds_loader_on_project_changed_accepts_dataset_kwarg(monkeypatch):
    from activity_browser.bwutils.metadata.loader import MDSLoader
    from activity_browser.bwutils.metadata.metadata import MetaDataStore

    mds = MetaDataStore()
    loader = mds.loader
    called = []
    monkeypatch.setattr(loader, "load_project", lambda: called.append(True))

    loader.on_project_changed(object(), dataset=object())
    loader.on_project_changed(object())
    assert called == [True, True]


def test_signaleddataset_save_emits_on_unsourced_project(qtbot, basic_database):
    """bw2data 4.8 skips signaleddataset_on_save unless is_sourced; AB restores it."""
    import bw2data as bd
    from bw2data.signals import signaleddataset_on_save

    from activity_browser.bwutils.metadata import signaled_save_compat  # noqa: F401

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

"""bw2data 4.8 sends project signals as send(manager, dataset=...); 4.7 used send(dataset)."""

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


def test_bw_functional_project_changed_accepts_bw2data_48_kwargs():
    """Regression for CI: bw_functional._check_and_update vs project_changed kwargs."""
    import bw_functional as bf

    from activity_browser.mod.bw_functional import patch_project_changed_handler

    patch_project_changed_handler()

    class _Dataset:
        name = "compat-test"
        data = {}

        def save(self):
            return None

    ds = _Dataset()
    # Call the patched receiver the way blinker does under bw2data 4.8 / 4.7.
    # Avoid project_changed.send so other receivers (e.g. older multifunctional)
    # are not exercised here.
    bf._check_and_update(object(), dataset=ds)
    bf._check_and_update(ds)

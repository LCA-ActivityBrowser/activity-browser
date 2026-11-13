"""Restore SignaledDataset save notifications for unsourced projects.

bw2data 4.8 (brightway2-data#299) gates ``signaleddataset_on_save`` on
``projects.dataset.is_sourced`` so revision generation can skip a prior-row
query. Activity Browser's MetaDataStore and ``ABSignals`` still need those
notifications for normal (unsourced) projects.

Revision ``signal_dispatcher`` already no-ops when not sourced
(``ProjectDataset.add_revision``), so re-emitting is safe. We still skip the
old-row query unless the project is sourced.

Lives under ``bwutils/metadata`` (not ``mod/``) so MetaDataStore can apply it
during app init without importing the heavy ``activity_browser.mod`` package.
"""
from __future__ import annotations

_patched = False


def patch_signaleddataset_save() -> None:
    global _patched
    if _patched:
        return

    from bw2data.signals import SignaledDataset, signaleddataset_on_save
    from peewee import Model

    _original_save = SignaledDataset.save

    def save(self, signal: bool = True, *args, **kwargs) -> None:
        from bw2data import projects

        emit = bool(signal)
        fetch_old = emit and bool(getattr(projects.dataset, "is_sourced", False))
        old = type(self).get_or_none(type(self).id == self.id) if fetch_old else None
        # Call peewee Model.save directly — upstream SignaledDataset.save would
        # re-apply the is_sourced gate.
        Model.save(self, *args, **kwargs)
        if emit:
            signaleddataset_on_save.send(self, old=old, new=self)

    SignaledDataset.save = save
    patch_signaleddataset_save._original_save = _original_save  # type: ignore[attr-defined]
    _patched = True


patch_signaleddataset_save()

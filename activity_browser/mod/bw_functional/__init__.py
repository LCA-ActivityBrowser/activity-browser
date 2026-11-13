"""Patches for bw_functional.

bw2data 4.8+ emits ``project_changed.send(manager, dataset=...)``. bw_functional
still connects ``_check_and_update(dataset)`` for the 4.7 positional form, which
raises ``TypeError: got multiple values for argument 'dataset'``. Remove this
when upstream bw_functional accepts the 4.8 signature.
"""
from __future__ import annotations

_patched = False


def patch_project_changed_handler() -> None:
    global _patched
    if _patched:
        return

    import bw_functional as bf
    from bw2data.signals import project_changed

    original = bf._check_and_update

    def _check_and_update(sender, dataset=None, **_kwargs):
        ds = dataset if dataset is not None else sender
        return original(ds)

    try:
        project_changed.disconnect(original)
    except Exception:
        pass
    project_changed.connect(_check_and_update)
    bf._check_and_update = _check_and_update
    _patched = True


patch_project_changed_handler()

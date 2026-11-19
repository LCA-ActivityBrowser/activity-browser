"""Restore SerializedDict/PickledDict ``_save_signal`` for unsourced projects.

bw2data 4.8 (brightway2-data#299) gates ``SerializedDict._send_save_signal`` on
``projects.dataset.is_sourced`` so revision generation can skip re-reading and
deep-copying metadata on ``flush``/``serialize``. Activity Browser attaches
``_save_signal`` on ``databases``, ``methods``, and ``calculation_setups`` and
bridges those blinker events to Qt (``meta.*_changed``). Without a notify on
unsourced projects, calculation-setup drag/add and method/database metadata
panes stay stale after a successful write.

``ProjectDataset.add_revision`` already no-ops when not sourced, but
``signal_dispatcher`` still calls ``generate_delta(old, new)`` first — so we
restore the full upstream serialize path (real ``old``/``new`` snapshots) rather
than emitting ``old=None``.
"""
from __future__ import annotations

_patched = False


def patch_serialized_dict_save() -> None:
    global _patched
    if _patched:
        return

    from bw2data.serialization import SerializedDict

    _original = SerializedDict._send_save_signal

    def _send_save_signal(self, signal: bool) -> bool:
        # Ignore is_sourced: AB (and any other _save_signal listener) needs the
        # notify. Revision add_revision still no-ops when unsourced.
        return bool(signal and hasattr(self, "_save_signal"))

    SerializedDict._send_save_signal = _send_save_signal
    patch_serialized_dict_save._original = _original  # type: ignore[attr-defined]
    _patched = True


patch_serialized_dict_save()

from typing import List

from qtpy import QtWidgets

from bw2data.errors import UnknownObject

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.characterization_factors import (
    elementary_flow_activity_id,
    remove_orphaned_characterization_factors,
    valid_characterization_factor_rows,
)
from activity_browser.mod import bw2data as bd
from activity_browser.ui.icons import qicons


class CFNew(ABAction):
    """Add characterization factors for elementary flows to an LCIA method."""

    icon = qicons.add
    text = "New characterization factor"

    @staticmethod
    @exception_dialogs
    def run(method_name: tuple, keys: List[tuple]):
        method = bd.Method(method_name)
        remove_orphaned_characterization_factors(method)

        data, existing_ids, _ = valid_characterization_factor_rows(list(method.load()))
        new_ids: list[int] = []
        unknown_keys: list = []

        for key in keys:
            try:
                flow_id = elementary_flow_activity_id(key)
            except UnknownObject:
                unknown_keys.append(key)
                continue

            if flow_id in existing_ids:
                continue

            existing_ids.add(flow_id)
            new_ids.append(flow_id)
            data.append((flow_id, 0.0))

        if unknown_keys:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Unknown elementary flow",
                "One or more elementary flows could not be found in the database and were not added.",
            )

        if len(new_ids) < len(keys) - len(unknown_keys):
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Duplicate characterization factors",
                "One or more of these elementary flows already exist within this method. Duplicate flows will not be "
                "added",
            )

        if not new_ids:
            return

        method.write(data)

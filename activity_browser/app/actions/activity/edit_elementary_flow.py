from typing import List

from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.activity.new_elementary_flow import ElementaryFlowDialog
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.commontasks import (
    get_writable_databases,
    is_node_biosphere,
    refresh_node,
)
from activity_browser.bwutils.elementary_flows import update_elementary_flow
from activity_browser.ui.icons import qicons


class EditElementaryFlow(ABAction):
    """Edit metadata for an existing elementary flow (biosphere node)."""

    icon = qicons.edit
    text = "Edit elementary flow"

    @staticmethod
    @exception_dialogs
    def run(flow_keys: List[tuple]):
        """Prompt for updated flow metadata and save changes."""
        flows = [refresh_node(key) for key in flow_keys]
        flows = [flow for flow in flows if is_node_biosphere(flow)]
        if not flows:
            return
        if len(flows) > 1:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Edit elementary flow",
                "Select a single elementary flow to edit.",
            )
            return

        flow = flows[0]
        writable = set(get_writable_databases())
        if flow["database"] not in writable:
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Database is read-only",
                f"Cannot edit elementary flows in read-only or locked database: {flow['database']}",
            )
            return

        dialog = ElementaryFlowDialog(app.main_window, flow=flow)
        if dialog.exec_() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        name, unit, flow_type, categories = dialog.get_data()
        if not name:
            return

        update_elementary_flow(
            flow,
            name=name,
            unit=unit,
            flow_type=flow_type,
            categories=categories,
        )

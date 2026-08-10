from typing import List

from loguru import logger
from qtpy import QtCore, QtWidgets

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.characterization_factors import (
    impact_methods_with_flows,
    remove_characterization_factors_for_flows,
)
from activity_browser.bwutils.commontasks import (
    get_writable_databases,
    is_node_biosphere,
    refresh_node,
)
from activity_browser.bwutils.elementary_flows import (
    count_biosphere_exchanges_for_flow,
    delete_biosphere_exchanges_for_flow,
)
from activity_browser.ui.icons import qicons


class DeleteElementaryFlow(ABAction):
    """Delete elementary flow(s) and clean up biosphere exchanges and LCIA CFs."""

    icon = qicons.delete
    text = "Delete elementary flow"

    @staticmethod
    @exception_dialogs
    def run(flow_keys: List[tuple]):
        """Delete biosphere nodes and remove related exchanges and CFs.

        Brightway ``Activity.delete()`` does not remove biosphere exchanges on
        technosphere activities nor characterization factors on LCIA methods.
        """
        flows = [refresh_node(key) for key in flow_keys]
        flows = [flow for flow in flows if is_node_biosphere(flow)]
        if not flows:
            return

        writable = set(get_writable_databases())
        locked = [flow for flow in flows if flow["database"] not in writable]
        if locked:
            names = ", ".join(sorted({flow["database"] for flow in locked}))
            QtWidgets.QMessageBox.warning(
                app.main_window,
                "Database is read-only",
                f"Cannot delete elementary flows from read-only or locked database(s): {names}",
            )
            return

        warnings = []
        if len(flows) == 1:
            warnings.append(f"Delete elementary flow <b>{flows[0]['name']}</b>?")
        else:
            warnings.append(f"Delete {len(flows)} elementary flows?")

        warnings.append("")

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            total_consumers = sum(count_biosphere_exchanges_for_flow(flow) for flow in flows)
            flow_ids = {flow.id for flow in flows}
            method_count = len(impact_methods_with_flows(flow_ids))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if total_consumers:
            warnings.append(
                f"This will remove {total_consumers} exchange(s) from process(es) that use "
                f"{'this flow' if len(flows) == 1 else 'these flows'}."
            )

        if method_count:
            warnings.append(
                f"Characterization factors will be removed from {method_count} impact "
                f"method{'s' if method_count != 1 else ''}."
            )

        choice = QtWidgets.QMessageBox.warning(
            app.main_window,
            "Delete elementary flow" if len(flows) == 1 else "Delete elementary flows",
            "<br>".join(warnings),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if choice == QtWidgets.QMessageBox.No:
            return

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            remove_characterization_factors_for_flows(flow_ids)
            for flow in flows:
                removed = delete_biosphere_exchanges_for_flow(flow)
                if removed:
                    logger.info(
                        f"Removed {removed} exchange(s) referencing elementary flow {flow.key}"
                    )
                flow.delete()
                logger.info(f"Deleted elementary flow {flow.key}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

"""Copy impact-category spreadsheet templates for the user."""
from pathlib import Path

from qtpy import QtWidgets

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.impact_categories.templates import (
    TEMPLATE_LABELS,
    copy_impact_category_template,
)
from activity_browser.ui.icons import qicons


class MethodGetTemplate(ABAction):
    icon = qicons.import_db
    text = "Get template…"
    tool_tip = "Save an impact-category import/export starter template"

    @classmethod
    @exception_dialogs
    def run(cls):
        kind, ok = QtWidgets.QInputDialog.getItem(
            app.main_window,
            "Get impact-category template",
            "Choose a format:\n\n"
            "AB impact-category file = multi–impact-category (recommended default).\n"
            "bw2io impact-category file = one impact category per CF file.",
            list(TEMPLATE_LABELS.values()),
            0,
            False,
        )
        if not ok or not kind:
            return
        # map label back to key
        label_to_kind = {v: k for k, v in TEMPLATE_LABELS.items()}
        key = label_to_kind[kind]

        if key.endswith("csv"):
            path = QtWidgets.QFileDialog.getExistingDirectory(
                app.main_window,
                "Select folder for CSV template files",
            )
            if not path:
                return
            stem = "ab-lcia" if key.startswith("ab") else "bw2io-lcia"
            written = copy_impact_category_template(key, Path(path) / stem)
        else:
            suggested = "ab-lcia.xlsx" if key.startswith("ab") else "bw2io-lcia.xlsx"
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                app.main_window,
                "Save impact-category template",
                suggested,
                "Excel spreadsheet (*.xlsx);; All files (*.*)",
            )
            if not path:
                return
            written = copy_impact_category_template(key, Path(path))

        names = "\n".join(str(p) for p in written)
        QtWidgets.QMessageBox.information(
            app.main_window,
            "Template saved",
            f"Wrote template file(s):\n{names}",
        )

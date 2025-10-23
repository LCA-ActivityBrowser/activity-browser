from logging import getLogger
from typing import List

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import widgets, threading
from activity_browser.bwutils import exporters


log = getLogger(__name__)


class DatabaseExportExcel(ABAction):
    """
    ABAction to export database(s) to Excel format (.xlsx).
    """

    icon = application.style().standardIcon(QtWidgets.QStyle.SP_DriveHDIcon)
    text = "Export to Excel (.xlsx)"
    tool_tip = "Export database(s) to Excel format"

    @classmethod
    @exception_dialogs
    def run(cls, db_names: List[str] = None):
        if db_names is None:
            import bw2data as bd
            dialog = widgets.ABDatabaseSelectionDialog(
                parent=application.main_window,
                databases=sorted(bd.databases),
                title="Select databases to export to Excel"
            )
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                db_names = dialog.get_selected_databases()
            else:
                return

        # Get export directory or file from user
        if len(db_names) == 1:
            # Single database - suggest a filename
            suggested_name = f"lci-{db_names[0]}.xlsx"
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=application.main_window,
                caption=f'Export database "{db_names[0]}" to Excel',
                directory=suggested_name,
                filter='Excel spreadsheet (*.xlsx);; All files (*.*)'
            )
        else:
            # Multiple databases - ask for directory
            path = QtWidgets.QFileDialog.getExistingDirectory(
                parent=application.main_window,
                caption=f'Select directory to export {len(db_names)} databases',
            )
        
        if not path:
            return

        # Show export dialog
        context = {
            "db_names": db_names,
            "path": path,
        }
        export_dialog = ExportExcelSetup(
            parent=application.main_window,
            title="Export to Excel",
            context=context
        )
        export_dialog.exec_()


class ExportExcelSetup(widgets.ABWizard):
    """Wizard for exporting databases to Excel format."""

    class ExportPage(widgets.ABThreadedWizardPage):
        """Wizard page to export the selected database(s) to Excel."""
        title = "Exporting Database(s)"
        subtitle = "Exporting database(s) to Excel file(s)"

        class Thread(threading.ABThread):
            """Thread to handle the export process."""
            
            def run_safely(self, db_names: List[str], path: str):
                """Export the database(s) to Excel."""
                for db_name in db_names:
                    try:
                        exporters.write_lci_excel(db_name, path)
                        log.info(f"Successfully exported database '{db_name}' to Excel")
                    except Exception as e:
                        log.error(f"Failed to export database '{db_name}': {e}")
                        raise

        def initializePage(self, context: dict):
            """Start the export thread."""
            self.thread.start(context["db_names"], context["path"])

    pages = [ExportPage]

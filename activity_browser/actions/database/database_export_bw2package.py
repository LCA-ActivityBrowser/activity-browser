from logging import getLogger
from typing import List

from qtpy import QtWidgets

from activity_browser import application
from activity_browser.actions.base import ABAction, exception_dialogs
from activity_browser.ui import widgets
from activity_browser.bwutils import exporters
from activity_browser.ui.core import threading

log = getLogger(__name__)


class DatabaseExportBW2Package(ABAction):
    """
    ABAction to export database(s) to BW2Package format (.bw2package).
    """

    # icon = icons.qicons.export_db
    text = "Export to .bw2package"
    tool_tip = "Export database(s) to BW2Package format"

    @classmethod
    @exception_dialogs
    def run(cls, db_names: List[str] = None):
        if db_names is None:
            import bw2data as bd
            dialog = widgets.ABDatabaseSelectionDialog(
                parent=application.main_window,
                databases=sorted(bd.databases),
                title="Select databases to export to BW2Package"
            )
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                db_names = dialog.get_selected_databases()
            else:
                return

        # Get export directory or file from user
        if len(db_names) == 1:
            # Single database - suggest a filename
            suggested_name = f"{db_names[0]}.bw2package"
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=application.main_window,
                caption=f'Export database "{db_names[0]}" to BW2Package',
                directory=suggested_name,
                filter='Brightway2 Database Package (*.bw2package);; All files (*.*)'
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
        export_dialog = ExportBW2PackageSetup(
            parent=application.main_window,
            title="Export to BW2Package",
            context=context
        )
        export_dialog.show()


class ExportBW2PackageSetup(widgets.ABWizard):
    """Wizard for exporting databases to BW2Package format."""

    class ExportPage(widgets.ABThreadedWizardPage):
        """Wizard page to export the selected database(s) to BW2Package."""
        title = "Exporting Database(s)"
        subtitle = "Exporting database(s) to .bw2package file(s)"

        class Thread(threading.ABThread):
            """Thread to handle the export process."""
            
            def run_safely(self, db_names: List[str], path: str):
                """Export the database(s) to BW2Package."""
                for db_name in db_names:
                    try:
                        success = exporters.store_database_as_package(db_name, path)
                        if success:
                            log.info(f"Successfully exported database '{db_name}' to BW2Package")
                        else:
                            log.error(f"Failed to export database '{db_name}'")
                            raise RuntimeError(f"Database '{db_name}' not found")
                    except Exception as e:
                        log.error(f"Failed to export database '{db_name}': {e}")
                        raise

        def initializePage(self, context: dict):
            """Start the export thread."""
            self.thread.start(context["db_names"], context["path"])

    pages = [ExportPage]

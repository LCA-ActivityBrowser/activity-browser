from activity_browser.actions.base import ABAction, exception_dialogs

from activity_browser.ui.icons import qicons

from activity_browser.mod.bw2io.migrations import ab_create_core_migrations


class ToolsBW2IOCreateMigrations(ABAction):
    """
    ABAction to install default migrations from bw2io
    """

    icon = qicons.import_db
    text = "Install default bw2io migrations"

    @staticmethod
    @exception_dialogs
    def run():
        ab_create_core_migrations()

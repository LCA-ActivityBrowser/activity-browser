from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.ui.icons import qicons

import bw2data as bd

from .project.project_switch import ProjectSwitch


class MetaDataStoreCacheClear(ABAction):

    icon = qicons.right
    text = "Clear Metadata Store Cache"
    tool_tip = "Clear the Metadata Store cache and reload the current project"

    @staticmethod
    @exception_dialogs
    def run():
        app.metadata.clear_cache()
        ProjectSwitch.run(bd.projects.current, reload=True)

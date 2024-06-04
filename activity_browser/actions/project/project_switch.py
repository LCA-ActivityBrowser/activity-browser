from activity_browser import log
from activity_browser.mod import bw2data as bd
from activity_browser.actions.base import ABAction, exception_dialogs


class ProjectSwitch(ABAction):
    """
    ABAction to switch to another project.
    """
    text = "Switch project"
    tool_tip = "Switch the project"

    @staticmethod
    @exception_dialogs
    def run(project_name: str):
        bd.projects.set_current(project_name)
        log.info(f"Brightway2 current project: {project_name}")

"""SHRECC plugin page shell (pytest-qt smoke)."""
import pytest
from importlib.metadata import entry_points

from activity_browser import app  # noqa: F401 — ABApplication before pytest-qt's QApplication


def _shrecc_installed():
    return any(
        ep.name == "ab_shrecc"
        for ep in entry_points(group="activity_browser.plugins")
    )


pytestmark = pytest.mark.skipif(
    not _shrecc_installed(),
    reason="Install with: pip install -e ./plugins/ab-plugin-shrecc",
)


def test_shrecc_page_starts_with_one_workflow_tab(qtbot):
    from ab_shrecc.page import ShreccPluginPage

    page = ShreccPluginPage()
    qtbot.addWidget(page)
    page.show()

    assert page.workflow_tabs.count() == 1
    assert page.controller.workflows[0].label == "Workflow 1"

    panel = page.workflow_tabs.currentWidget()
    assert panel is not None
    assert not panel.create_btn.isEnabled()

    page.close_btn.click()
    assert page.workflow_tabs.count() == 1

    page.new_btn.click()
    assert page.workflow_tabs.count() == 2


def test_shrecc_page_has_three_stage_tabs(qtbot):
    from ab_shrecc.page import ShreccPluginPage

    page = ShreccPluginPage()
    qtbot.addWidget(page)
    panel = page.workflow_tabs.currentWidget()
    assert panel.stage_tabs.count() == 3

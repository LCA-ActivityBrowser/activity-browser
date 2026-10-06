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
    from ab_shrecc.page import EXPLORER_TAB_TITLE, ShreccPluginPage

    page = ShreccPluginPage()
    qtbot.addWidget(page)
    page.show()

    assert page.workflow_tabs.count() == 2
    assert page.workflow_tabs.tabText(0) == EXPLORER_TAB_TITLE
    assert page.controller.workflows[0].label == "Workflow 1"

    page.workflow_tabs.setCurrentIndex(1)
    panel = page.workflow_tabs.currentWidget()
    assert panel is not None
    assert not panel.create_btn.isEnabled()

    page.close_btn.click()
    assert page.workflow_tabs.count() == 2

    page.new_btn.click()
    assert page.workflow_tabs.count() == 3


def test_shrecc_page_has_three_stage_tabs(qtbot):
    from ab_shrecc import ids
    from ab_shrecc.page import ShreccPluginPage

    page = ShreccPluginPage()
    qtbot.addWidget(page)
    page.show()
    page.workflow_tabs.setCurrentIndex(1)
    panel = page.workflow_tabs.currentWidget()
    assert panel is not None
    assert panel.stage_tabs.count() == 3
    assert panel.stage_tabs.tabText(0) == ids.STAGE_LABELS[ids.STAGE_CONFIGURE]
    assert panel.stage_tabs.tabText(1) == ids.STAGE_LABELS[ids.STAGE_INSPECT]
    assert panel.stage_tabs.tabText(2) == ids.STAGE_LABELS[ids.STAGE_WRITE]
    assert not panel.stage_tabs.isTabEnabled(panel._inspect_index)
    assert not panel.stage_tabs.isTabEnabled(panel._write_index)
    assert panel.create_btn is panel.configure_form.create_btn
    assert panel.create_btn.text() == "Create"
    assert not hasattr(panel.configure_form, "my_db_name_edit")
    assert "summary" not in panel.inspect_panel._sections
    assert hasattr(panel.write_panel, "output_name_edit")

    workflow = page.controller.workflows[0]
    page.controller.complete_create(
        workflow,
        object(),
        {"years": [2021], "summary": [{"year": 2021}]},
    )
    page.controller.update_config(workflow, {"countries": ["FR"]})
    panel.refresh()
    assert panel.create_btn.text() == "Create again"
    assert panel.stage_tabs.isTabEnabled(panel._inspect_index)
    assert not panel.stage_tabs.isTabEnabled(panel._write_index)


def test_inspect_panel_keeps_artifacts_on_configuration_mismatch(qtbot):
    from ab_shrecc.inspect_panel import InspectPanel

    panel = InspectPanel()
    qtbot.addWidget(panel)
    panel.show()
    artifacts = {
        "years": [2021],
        "summary": [
            {
                "year": 2021,
                "source": "energy_charts",
                "background_db": "bg",
                "output_db": "out",
            }
        ],
        "log": ["created"],
        "mapping_reports": {},
        "table_previews": {},
        "column_sums": {},
    }
    panel.set_artifacts(artifacts)
    assert "created" in panel.log_view.toPlainText()
    assert not panel._sections["log"].toggle_btn.isChecked()
    assert "summary" not in panel._sections

    panel.show_configuration_mismatch()
    assert panel.mismatch_banner.isVisible()
    assert "Create again before Write" in panel.mismatch_banner.text()
    assert "created" in panel.log_view.toPlainText()
    assert panel.log_view.isEnabled()

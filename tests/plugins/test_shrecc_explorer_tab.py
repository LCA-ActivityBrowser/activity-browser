"""SHRECC Explorer tab chrome (pytest-qt, faked session)."""
from pathlib import Path

import pytest
from importlib.metadata import entry_points

from activity_browser import app  # noqa: F401


def _shrecc_installed():
    return any(
        ep.name == "ab_shrecc"
        for ep in entry_points(group="activity_browser.plugins")
    )


pytestmark = pytest.mark.skipif(
    not _shrecc_installed(),
    reason="Install with: pip install -e ./plugins/ab-plugin-shrecc",
)


class FakeSession:
    def __init__(self, tmp_path: Path, *, can_embed=False, can_prepare=False):
        self.data_dir = tmp_path
        self._can_embed = can_embed
        self._can_prepare = can_prepare
        self.ensure_calls = 0
        self.stopped = False
        self._url = "http://127.0.0.1:9"

    def status(self):
        from ab_shrecc.explorer_session import ExplorerStatus

        return ExplorerStatus(
            data_dir=self.data_dir,
            data_dir_ok=True,
            has_cache=self._can_prepare,
            ready_exports=[self.data_dir / "x.nc"] if self._can_embed else [],
            can_prepare=self._can_prepare,
            can_embed=self._can_embed,
            message="ready" if self._can_embed else "Nothing to explore yet.",
        )

    def ensure_server(self):
        self.ensure_calls += 1
        if not self._can_embed:
            raise RuntimeError("not ready")
        return self._url

    def stop_server(self):
        self.stopped = True

    def run_prepare(self):
        self._can_embed = True
        self._can_prepare = True
        return [self.data_dir / "x.nc"]


def test_page_has_explorer_sibling_tab(qtbot, tmp_path):
    from ab_shrecc.page import EXPLORER_TAB_TITLE, ShreccPluginPage

    session = FakeSession(tmp_path)
    page = ShreccPluginPage(explorer_session=session)
    qtbot.addWidget(page)
    page.show()

    assert page.workflow_tabs.tabText(0) == EXPLORER_TAB_TITLE
    assert page.workflow_tabs.count() == 2  # Explorer + Workflow 1
    assert page.workflow_tabs.widget(0) is page.explorer_panel
    assert not page.explorer_panel.prepare_btn.isEnabled()
    assert not page.explorer_panel.open_browser_btn.isEnabled()


def test_explorer_chrome_enables_prepare_when_cache_ready(qtbot, tmp_path):
    from ab_shrecc.page import ShreccPluginPage

    session = FakeSession(tmp_path, can_prepare=True)
    page = ShreccPluginPage(explorer_session=session)
    qtbot.addWidget(page)
    page.show()
    page.explorer_panel.refresh()
    assert page.explorer_panel.prepare_btn.isEnabled()


def test_page_shell_still_has_workflow_stages(qtbot, tmp_path):
    from ab_shrecc import ids
    from ab_shrecc.page import ShreccPluginPage

    page = ShreccPluginPage(explorer_session=FakeSession(tmp_path))
    qtbot.addWidget(page)
    page.show()
    # Select workflow tab (index 1)
    page.workflow_tabs.setCurrentIndex(1)
    panel = page.workflow_tabs.currentWidget()
    assert panel is not None
    assert panel.stage_tabs.count() == 3
    assert panel.stage_tabs.tabText(0) == ids.STAGE_LABELS[ids.STAGE_CONFIGURE]

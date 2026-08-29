# -*- coding: utf-8 -*-
"""Host UI helpers for plugins (public; no MainWindow import required of authors)."""


def reveal_page(contribution_id: str) -> None:
    """Show/focus a registered base page by contribution id."""
    from activity_browser import app
    from activity_browser.app import pages

    page_class = pages.base_pages.get(contribution_id)
    if page_class is None:
        return
    central = app.main_window.central_widget
    page = app.main_window.findChild(page_class)
    if page is None:
        page = page_class(parent=central)
    if central.indexOf(page) >= 0:
        central.setCurrentWidget(page)
    else:
        page.toggle_view_action.setChecked(True)
        central.addPage(page)


def reveal_pane(contribution_id: str) -> None:
    """Show/raise a registered base pane by contribution id."""
    from activity_browser import app
    from activity_browser.app import panes

    pane_class = panes.base_panes.get(contribution_id)
    if pane_class is None:
        return
    pane = app.main_window.findChild(pane_class)
    if pane is None:
        return
    dock = pane.getDockWidget()
    dock.show()
    dock.raise_()

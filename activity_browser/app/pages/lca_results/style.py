"""Shared Qt layout and chrome for LCA Results sub-tabs.

Provides consistent margins, control rows, headers, run buttons, and compact
combo boxes used across matplotlib tabs and web navigators (Sankey/Tree).
"""

import json

from qtpy import QtWidgets, QtGui, QtCore

from activity_browser.ui.icons import qicons

from .combobox_utils import SmallComboBox, apply_lca_combo_width

LCA_TAB_LAYOUT_SPACING = 6
LCA_TAB_CONTENT_MARGINS = (10, 10, 10, 10)
LCA_HEADER_ROW_MIN_HEIGHT = 32
LCA_RUN_BUTTON_STYLE = "background-color: #57965C;"

def configure_lca_tab_layout(layout: QtWidgets.QVBoxLayout) -> None:
    """Shared vertical spacing and edge padding for LCA Results sub-tabs."""
    layout.setSpacing(LCA_TAB_LAYOUT_SPACING)
    layout.setContentsMargins(*LCA_TAB_CONTENT_MARGINS)


def lca_tab_control_row() -> QtWidgets.QHBoxLayout:
    """Single control row with standard horizontal spacing."""
    row = QtWidgets.QHBoxLayout()
    row.setSpacing(LCA_TAB_LAYOUT_SPACING)
    row.setContentsMargins(0, 0, 0, 0)
    return row


def lca_tab_controls_section(
    *rows: QtWidgets.QHBoxLayout,
) -> QtWidgets.QVBoxLayout:
    """Stack control rows with the same spacing as the main tab layout."""
    section = QtWidgets.QVBoxLayout()
    section.setSpacing(LCA_TAB_LAYOUT_SPACING)
    section.setContentsMargins(0, 0, 0, 0)
    for row in rows:
        section.addLayout(row)
    return section


def lca_run_button(
    parent: QtWidgets.QWidget | None = None,
    *,
    text: str = "Run",
) -> QtWidgets.QPushButton:
    """Action button styled like the calculation setup Run button."""
    button = QtWidgets.QPushButton(text, parent)
    button.setIcon(qicons.forward)
    button.setStyleSheet(LCA_RUN_BUTTON_STYLE)
    return button


def vertical_line():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.VLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def header(text):
    label = QtWidgets.QLabel(text)

    bold_font = QtGui.QFont()
    bold_font.setBold(True)
    bold_font.setPointSize(12)

    label.setFont(bold_font)
    return label


def lca_help_tool_button(
    parent: QtWidgets.QWidget,
    tooltip: str,
    on_click,
) -> QtWidgets.QToolButton:
    """Compact help control for tab headers (matches plain header height)."""
    button = QtWidgets.QToolButton(parent)
    button.setIcon(qicons.question)
    button.setAutoRaise(True)
    button.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    button.setToolTip(tooltip)
    button.clicked.connect(on_click)
    return button


def lca_header_layout(
    header_text: str,
    help_widget: QtWidgets.QWidget | None = None,
) -> QtWidgets.QVBoxLayout:
    """Title row with consistent height across tabs (with or without help)."""
    bar = QtWidgets.QWidget()
    bar.setMinimumHeight(LCA_HEADER_ROW_MIN_HEIGHT)
    row = lca_tab_control_row()
    row.addWidget(header(header_text))
    if help_widget is not None:
        row.addWidget(help_widget)
    else:
        row.addStretch(1)
    row.setStretch(0, 1)
    bar.setLayout(row)

    section = QtWidgets.QVBoxLayout()
    section.setSpacing(0)
    section.setContentsMargins(0, 0, 0, 0)
    section.addWidget(bar)
    return section


def qt_ui_font_css() -> str:
    """Match WebEngine chrome (Layout row) to the Qt application font."""
    instance = QtWidgets.QApplication.instance()
    font = instance.font() if instance is not None else QtGui.QFont()
    family = font.family() or "sans-serif"
    if font.pointSizeF() > 0:
        size = f"{font.pointSizeF():g}pt"
    elif font.pixelSize() > 0:
        size = f"{font.pixelSize()}px"
    else:
        size = "9pt"
    family_css = family.replace("\\", "\\\\").replace("'", "\\'")
    return (
        ".ab-sankey-controls,#graph-controls{"
        f"font-family:'{family_css}',sans-serif;"
        f"font-size:{size};"
        "}"
    )


def app_is_dark() -> bool:
    """Whether the Qt application color scheme is dark."""
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        return False
    try:
        scheme = instance.styleHints().colorScheme()
        if scheme == QtCore.Qt.ColorScheme.Dark:
            return True
        if scheme == QtCore.Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    bg = instance.palette().color(QtGui.QPalette.ColorRole.Window)
    lum = 0.299 * bg.redF() + 0.587 * bg.greenF() + 0.114 * bg.blueF()
    return lum < 0.45


def inject_qt_ui_font(page) -> None:
    """Apply :func:`qt_ui_font_css` to a WebEngine page."""
    if page is None:
        return
    css = json.dumps(qt_ui_font_css())
    page.runJavaScript(
        "(function(){var s=document.getElementById('ab-ui-font');"
        "if(!s){s=document.createElement('style');s.id='ab-ui-font';"
        "document.head.appendChild(s);}"
        "s.textContent=" + css + ";})();"
    )


def show_open_process_menu(parent, activities, global_pos=None) -> None:
    """One-item Open process menu. Greyed out when there is no single process."""
    from activity_browser import app

    menu = QtWidgets.QMenu(parent)
    n = len(activities or [])
    menu.addAction(
        app.actions.ActivityOpen.get_QAction(
            activities,
            parent=menu,
            text="Open process" if n <= 1 else "Open processes",
            enabled=bool(activities),
        )
    )
    pos = global_pos if global_pos is not None else QtGui.QCursor.pos()
    menu.exec_(pos)

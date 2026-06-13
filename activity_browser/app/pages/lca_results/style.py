from qtpy import QtWidgets, QtGui, QtCore

from activity_browser.ui.icons import qicons

LCA_TAB_LAYOUT_SPACING = 6
LCA_TAB_CONTENT_MARGINS = (10, 10, 10, 10)
LCA_HEADER_ROW_MIN_HEIGHT = 32
LCA_RUN_BUTTON_STYLE = "background-color: #57965C;"


def configure_lca_tab_layout(layout: QtWidgets.QVBoxLayout) -> None:
    """Shared vertical spacing and edge padding for LCA Results sub-tabs."""
    layout.setSpacing(LCA_TAB_LAYOUT_SPACING)
    layout.setContentsMargins(*LCA_TAB_CONTENT_MARGINS)
    layout.setAlignment(QtCore.Qt.AlignTop)


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


class SmallComboBox(QtWidgets.QComboBox):
    """Compact combo box that does not expand to fill available space."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        self.setMinimumWidth(100)
        self.setMaximumWidth(200)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)


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
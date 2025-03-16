from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt


class HideMode:
    Close = 1
    Hide = 2


class ABDockWidget(QtWidgets.QDockWidget):
    HideMode = HideMode

    def __init__(self, title: str, parent: QtWidgets.QMainWindow, mode=HideMode.Close) -> None:
        super().__init__(title, parent)
        self._hide_mode = mode

        if mode == HideMode.Close:
            self.button = CloseButton(self)
            self.title_bar = TitleBar(title, self.button, self)
            self.button.clicked.connect(self.close)
        else:
            self.button = MinimizeButton(self)
            self.title_bar = TitleBar(title, self.button, self)
            self.button.clicked.connect(self.hide)

        self.setTitleBarWidget(QtWidgets.QWidget())
        self.visibilityChanged.connect(self.on_visibility_changed)
        self.dockLocationChanged.connect(self.on_dock_location_changed)

    def on_visibility_changed(self, is_visible: bool) -> None:
        # this visibility monitor is really only needed to detect merges of
        # tabbed, floating windows with existing docked windows
        if not is_visible and isinstance(self.parent(), QtWidgets.QMainWindow):
            main_window: QtWidgets.QMainWindow = self.parent()
            all_dockwidgets: list[QtWidgets.QDockWidget] = main_window.findChildren(QtWidgets.QDockWidget)
            for dockwidget in all_dockwidgets:
                if hasattr(dockwidget, 'on_dock_location_changed'):
                    dockwidget.on_dock_location_changed(main_window.dockWidgetArea(dockwidget), False)

    def on_dock_location_changed(self, area: Qt.DockWidgetArea, update_others: bool = True) -> None:
        main_window = self.parent()
        if not isinstance(main_window, QtWidgets.QMainWindow):
            # mysterious parents call for a title
            self.setTitleBarWidget(self.title_bar)
            return

        if not main_window.tabifiedDockWidgets(self):
            # if there's no siblings we ain't a tab!
            self.setTitleBarWidget(self.title_bar)

            if not update_others:
                # prevent infinite recursion
                return

            # force an update to all other docks that may now no longer be tabs
            all_dockwidgets: list[QtWidgets.QDockWidget] = main_window.findChildren(QtWidgets.QDockWidget)
            for dockwidget in all_dockwidgets:
                if dockwidget != self and hasattr(dockwidget, 'on_dock_location_changed'):
                    dockwidget.on_dock_location_changed(main_window.dockWidgetArea(dockwidget), False)
            return

        # at this point the dockwidget is either a resting tab or a tab
        # that is being dragged and hasn't been dropped yet (siblings are updated post-drop)
        # collect all siblings of this dockwidget...
        tab_siblings: list[QtWidgets.QDockWidget] = main_window.tabifiedDockWidgets(self)
        # and filter for non-floating siblings in the same area
        tab_siblings = [x for x in tab_siblings if main_window.dockWidgetArea(x) == area and not x.isFloating()]

        if tab_siblings:
            if not isinstance(self.titleBarWidget(), TitleBar):
                # no changes needed, prevent infinite recursion
                return

            # show a title if we're not floating (this tab is settled),
            # hide it otherwise (this tab just became floating but wasn't dropped)
            self.setTitleBarWidget(QtWidgets.QWidget() if not self.isFloating() else self.title_bar)

            # in this case it's also a good idea to tell to reconsider their situation
            # since Qt won't notify them separately
            for sibling in tab_siblings:
                if hasattr(sibling, 'on_dock_location_changed'):
                    sibling.on_dock_location_changed(main_window.dockWidgetArea(sibling), True)
        else:
            self.setTitleBarWidget(self.title_bar)


class TitleBar(QtWidgets.QWidget):
    def __init__(self, title: str, button, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel(title, self)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(button)
        self.setLayout(layout)


class CloseButton(QtWidgets.QLabel):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("×", parent)
        self.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(16, 16)

        self.mousePressEvent = lambda event: self.clicked.emit()

        # Default style
        self.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(255, 0, 0, 0.5);
            }
        """)


class MinimizeButton(QtWidgets.QLabel):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("-", parent)
        self.setFont(QtGui.QFont("Arial", 15, QtGui.QFont.Bold))
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(16, 16)

        self.mousePressEvent = lambda event: self.clicked.emit()

        # Default style
        self.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(42, 157, 244, 0.5);
            }
        """)


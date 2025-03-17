from qtpy import QtWidgets, QtCore, QtGui, shiboken
from qtpy.QtCore import Qt


class HideMode:
    Close = 1
    Hide = 2


class ABDockWidget(QtWidgets.QDockWidget):
    HideMode = HideMode

    def __init__(self, title: str, parent: QtWidgets.QMainWindow, mode=HideMode.Close) -> None:
        super().__init__(title, parent)
        self._hide_mode = mode
        if self._hide_mode == HideMode.Close:
            self.setAttribute(Qt.WA_DeleteOnClose)

        self.title_bar = TitleBar(title, self.button(), self)
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.visibilityChanged.connect(self.updateOthers)
        self.dockLocationChanged.connect(self.updateTitlebar)

    def button(self):
        if self._hide_mode == HideMode.Close:
            button = CloseButton(self)
            button.clicked.connect(self.close)
        else:
            button = MinimizeButton(self)
            button.clicked.connect(self.hide)
        return button

    def updateTitlebar(self, area: Qt.DockWidgetArea, update_others: bool = True) -> None:
        main_window = self.parent()
        if not isinstance(main_window, QtWidgets.QMainWindow):
            # mysterious parents call for a title
            self.showTitlebar()
            return

        if not main_window.tabifiedDockWidgets(self):
            # if there's no siblings we ain't a tab!
            self.showTitlebar()
            self.updateOthers() if update_others else None
            return

        # at this point the dockwidget is either a resting tab or a tab
        # that is being dragged and hasn't been dropped yet (siblings are updated post-drop)
        # collect all siblings of this dockwidget...
        tab_siblings: list[QtWidgets.QDockWidget] = main_window.tabifiedDockWidgets(self)
        # and filter for non-floating siblings in the same area
        tab_siblings = [x for x in tab_siblings
                        if main_window.dockWidgetArea(x) == area
                        and not x.isFloating()
                        and not x.isHidden()]

        if tab_siblings:
            # show a title if we're not floating (this tab is settled),
            # hide it otherwise (this tab just became floating but wasn't dropped)
            self.showTitlebar(self.isFloating())
        else:
            self.showTitlebar()

        self.updateOthers() if update_others else None

    def updateOthers(self):
        all_dockwidgets: list[ABDockWidget] = self.parent().findChildren(ABDockWidget)
        for dockwidget in all_dockwidgets:
            if dockwidget != self:
                dockwidget.updateTitlebar(self.parent().dockWidgetArea(dockwidget), False)

    def showTitlebar(self, show: bool = True) -> None:
        if not show:
            return self.hideTitlebar()
        self.title_bar.set_button(self.button())
        self.setTitleBarWidget(self.title_bar)

    def hideTitlebar(self, hide: bool = True) -> None:
        if not hide:
            return self.showTitlebar()
        self.setTitleBarWidget(QtWidgets.QWidget())

        pointer_id = shiboken.getCppPointer(self)[0]

        tab_bars = self.parent().findChildren(QtWidgets.QTabBar, options=Qt.FindDirectChildrenOnly)
        for tab_bar in tab_bars:
            ids = [tab_bar.tabData(i) for i in range(tab_bar.count())]

            if pointer_id not in ids:
                continue

            index = ids.index(pointer_id)
            tab_bar.setTabButton(index, QtWidgets.QTabBar.RightSide, self.button())
            return


class TitleBar(QtWidgets.QWidget):
    def __init__(self, title: str, button, parent=None):
        super().__init__(parent)
        self.label = QtWidgets.QLabel(title, self)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(button)
        self.setLayout(layout)

    def set_button(self, button):
        layout = self.layout()
        w = layout.itemAt(2).widget()
        layout.replaceWidget(w, button)
        layout.update()
        w.deleteLater()


class CloseButton(QtWidgets.QWidget):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel("×", self)

        self.label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(16, 16)
        self.label.mousePressEvent = lambda event: self.clicked.emit()

        self.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(255, 0, 0, 0.5);
            }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)


class MinimizeButton(QtWidgets.QWidget):
    """Custom close button with hover effect."""
    clicked: QtCore.SignalInstance = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = QtWidgets.QLabel("-", self)

        self.label.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setFixedSize(16, 16)
        self.label.mousePressEvent = lambda event: self.clicked.emit()

        self.setStyleSheet("""
            QLabel {
                border-radius: 8px;
                background-color: transparent;
            }
            QLabel:hover {
                background-color: rgba(42, 157, 244, 0.5);
            }
        """)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(5, 0, 0, 0)
        layout.addWidget(self.label)
        self.setLayout(layout)

import gc

def objects_by_id(id_):
    for obj in gc.get_objects():
        if id(obj) == id_:
            return obj
    raise Exception("No found")

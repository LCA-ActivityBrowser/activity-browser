from qtpy import QtWidgets

from .buttons import ABCloseButton, ABMinimizeButton


class ABTabWidget(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        """
        Initialize the GroupTabWidget.

        Args:
            name (str): The name of the group, used as the object name for the widget.
            *args: Additional positional arguments passed to the parent QTabWidget.
        """
        super().__init__(*args, **kwargs)
        self.setMovable(True)  # Allow tabs to be rearranged.
        self.setTabsClosable(True)  # Allow tabs to be closed.
        self.tabBar().setExpanding(False)
        
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Force the tab bar to always fill the full width
        self.tabBar().setMinimumWidth(self.width())

    def addTab(self, widget, label, show_minimize=False):
        """Override addTab to add custom buttons to each tab.
        
        Args:
            widget: The widget to add as a tab
            label: The label for the tab
            show_minimize: If True, show minimize button; if False, show close button
        """
        index = super().addTab(widget, label)
        self._set_buttons(index, widget, show_minimize)
        return index
    
    def insertTab(self, index, widget, label, show_minimize=False):
        """Override insertTab to add custom buttons to each tab.
        
        Args:
            index: The index at which to insert the tab
            widget: The widget to add as a tab
            label: The label for the tab
            show_minimize: If True, show minimize button; if False, show close button
        """
        index = super().insertTab(index, widget, label)
        self._set_buttons(index, widget, show_minimize)
        return index
    
    def _set_buttons(self, index, widget, show_minimize=False):
        tab_bar = self.tabBar()
        button = ABMinimizeButton() if show_minimize else ABCloseButton()
        tab_bar.setTabButton(index, QtWidgets.QTabBar.ButtonPosition.RightSide, button)
        button.clicked.connect(lambda w=widget: self.closeTabByWidget(w))
    
    def closeTabByWidget(self, widget):
        """Handle close button click using the widget reference."""
        index = self.indexOf(widget)
        if index >= 0:
            self.tabCloseRequested.emit(index)

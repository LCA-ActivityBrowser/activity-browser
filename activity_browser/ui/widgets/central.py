from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .tab_widget import ABTabWidget
from .abstract_page import ABAbstractPage


class ABCentralPagesWidget(ABTabWidget):
    """
    A custom QTabWidget that manages groups of tabs and their associated pages.

    This widget allows for organizing tabs into groups, dynamically adding pages to groups,
    and ensuring that each page has a unique object name.
    """
    def __init__(self, *args, **kwargs):
        """
        Initialize the CentralTabWidget.

        Args:
            *args: Additional positional arguments passed to the parent QTabWidget.
            **kwargs: Additional keyword arguments passed to the parent QTabWidget.
        """
        super().__init__(*args, **kwargs)
        self.setTabsClosable(True)

        self.tabCloseRequested.connect(self.closeTab)

    @property
    def groups(self):
        """
        Retrieve all group widgets within the CentralTabWidget.

        Groups are identified as instances of GroupTabWidget.

        Returns:
            dict: A dictionary where keys are group object names and values are GroupTabWidget instances.
        """
        widgets = [self.widget(i) for i in range(self.count())]
        group_widgets = [widget for widget in widgets if isinstance(widget, GroupedPagesWidget)]
        return {widget.objectName(): widget for widget in group_widgets}

    def addPage(self, page):
        """
        Add a page to the central tab widget.

        Args:
            page (ABAbstractPage): The page to add to the central tab widget.

        Raises:
            ValueError: If the page does not have an object name.
        """
        if not page.objectName():
            raise ValueError("Page must have an object name")

        # Check if the page already exists
        page_names = [self.widget(i).objectName() for i in range(self.count())]

        if page.objectName() not in page_names:
            self.addTab(page, page.title, show_minimize=page.basePage)
            self.setCurrentWidget(page)
            page.toggle_view_action.setChecked(True)

            page.windowTitleChanged.connect(self.onPageWindowTitleChanged, Qt.ConnectionType.UniqueConnection)
            page.visibilityChanged.connect(self.onPageVisibilityChanged, Qt.ConnectionType.UniqueConnection)

        else:
            # Set the existing page as the current tab
            index = page_names.index(page.objectName())
            self.setCurrentIndex(index)
            page.deleteLater()  # Clean up the newly created page since it already exists

    def addToGroup(self, group: str, page: ABAbstractPage):
        """
        Add a page to a specified group. If the group does not exist, it is created.

        Args:
            group (str): The name of the group to which the page will be added.
            page (QtWidgets.QWidget): The page to add to the group.

        Raises:
            ValueError: If the page does not have an object name.
        """
        if not page.objectName():
            raise ValueError("Page must have an object name")
        if group not in self.groups:
            # Create a new group if it does not exist
            self.addTab(GroupedPagesWidget(group, self), group)

        group = self.groups[group]
        self.setCurrentWidget(group)

        # Check if the page already exists in the group
        page_names = [group.widget(i).objectName() for i in range(group.count())]
        if page.objectName() not in page_names:
            # Add the page to the group if it does not exist
            name = page.windowTitle() or page.objectName()  # Use windowTitle if available
            page.setWindowTitle(name)  # make sure the page has a title
            page.setParent(group)
            group.addTab(page, name)
            group.setCurrentWidget(page)

            page.windowTitleChanged.connect(lambda title: group.setTabText(group.indexOf(page), title))
        else:
            # Set the existing page as the current tab
            index = page_names.index(page.objectName())
            group.setCurrentIndex(index)
            page.deleteLater()  # Clean up the newly created page since it already exists

    def closeTab(self, index):
        """
        Handle the closing of a tab.

        Deletes the widget associated with the tab and removes the tab from the widget.

        Args:
            index (int): The index of the tab to be closed.
        """
        w = self.widget(index)
        if isinstance(w, ABAbstractPage) and w.basePage:
            w.toggle_view_action.setChecked(False)
            self.removeTab(index)
            return
        self.removeTab(index)
        w.deleteLater()

    def onPageVisibilityChanged(self, visible: bool):
        """
        Handle changes in page visibility.

        Args:
            page (ABAbstractPage): The page whose visibility has changed.
            visible (bool): True if the page is now visible, False otherwise.
        """
        page = self.sender()

        if visible:
            self.addPage(page)
        else:
            index = self.indexOf(page)
            if index >= 0:
                self.removeTab(index)

    def onPageWindowTitleChanged(self, title: str):
        """
        Handle changes in page window title.

        Args:
            title (str): The new title of the page.
        """
        page = self.sender()
        index = self.indexOf(page)
        if index >= 0:
            self.setTabText(index, title)


class GroupedPagesWidget(ABTabWidget):
    """
    A custom QTabWidget that represents a group of tabs.

    This widget allows for managing tabs within a group, including making tabs movable,
    closable, and handling their lifecycle when the project changes or tabs are closed.
    """

    def __init__(self, name: str, *args):
        """
        Initialize the GroupTabWidget.

        Args:
            name (str): The name of the group, used as the object name for the widget.
            *args: Additional positional arguments passed to the parent QTabWidget.
        """
        super().__init__(*args)

        self.setObjectName(name)  # Set the object name for the widget.

        self.connect_signals()  # Connect necessary signals.

    def connect_signals(self):
        """
        Connect signals to their respective handlers.

        - Connects the `tabCloseRequested` signal to the `tabClosed` method.
        - Connects the `project.changed` signal to the `deleteLater` method to clean up the widget.
        """
        self.tabCloseRequested.connect(self.tabClosed)

    def addTab(self, widget, *args, **kwargs):
        super().addTab(widget, *args, **kwargs)
        widget.destroyed.connect(self.checkEmpty)

    def checkEmpty(self):
        """
        Check if the GroupTabWidget is empty (i.e., has no tabs).

        If it is empty, delete the widget.
        """
        if self.count() == 1:
            self.deleteLater()

    def tabClosed(self, index):
        """
        Handle the closing of a tab.

        Deletes the widget associated with the tab and removes the tab from the widget.
        If no tabs remain, the entire GroupTabWidget is deleted.

        Args:
            index (int): The index of the tab to be closed.
        """
        self.widget(index).deleteLater()  # Delete the widget associated with the tab.


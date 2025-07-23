from logging import getLogger

from qtpy import QtWidgets

from activity_browser import signals


log = getLogger(__name__)


class CentralTabWidget(QtWidgets.QTabWidget):
    """
    A custom QTabWidget that manages groups of tabs and their associated pages.

    This widget allows for organizing tabs into groups, dynamically adding pages to groups,
    and ensuring that each page has a unique object name.
    """

    def __init__(self, *args):
        """
        Initialize the CentralTabWidget.

        Args:
            *args: Positional arguments passed to the parent QTabWidget.
        """
        super().__init__(*args)
        # Connect to the project changed signal to reset the current index to 0
        signals.project.changed.connect(self.reset)

    @property
    def groups(self):
        """
        Retrieve all group widgets within the CentralTabWidget.

        Groups are identified as instances of GroupTabWidget.

        Returns:
            dict: A dictionary where keys are group object names and values are GroupTabWidget instances.
        """
        widgets = [self.widget(i) for i in range(self.count())]
        group_widgets = [widget for widget in widgets if isinstance(widget, GroupTabWidget)]
        return {widget.objectName(): widget for widget in group_widgets}

    def addToGroup(self, group: str, page: QtWidgets.QWidget):
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
            self.addTab(GroupTabWidget(group, self), group)

        group = self.groups[group]

        # Check if the page already exists in the group
        page_names = [group.widget(i).objectName() for i in range(group.count())]
        if page.objectName() not in page_names:
            # Add the page to the group if it does not exist
            name = page.windowTitle() or page.objectName()  # Use windowTitle if available
            page.setWindowTitle(name)  # make sure the page has a title
            page.setParent(group)
            group.addTab(page, name)

            page.windowTitleChanged.connect(lambda title: group.setTabText(group.indexOf(page), title))
        else:
            # Set the existing page as the current tab
            index = page_names.index(page.objectName())
            group.setCurrentIndex(index)

        # Set the group and page as the current widgets
        self.setCurrentWidget(group)
        group.setCurrentWidget(page)

    def reset(self):
        self.setCurrentIndex(0)


class GroupTabWidget(QtWidgets.QTabWidget):
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
        self.setMovable(True)  # Allow tabs to be rearranged.
        self.setTabsClosable(True)  # Allow tabs to be closed.
        self.setDocumentMode(True)  # Enable document mode for a more modern appearance.

        self.setObjectName(name)  # Set the object name for the widget.

        self.connect_signals()  # Connect necessary signals.

    def connect_signals(self):
        """
        Connect signals to their respective handlers.

        - Connects the `tabCloseRequested` signal to the `tabClosed` method.
        - Connects the `project.changed` signal to the `deleteLater` method to clean up the widget.
        """
        self.tabCloseRequested.connect(self.tabClosed)
        signals.project.changed.connect(self.deleteLater)

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


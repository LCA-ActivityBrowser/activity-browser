from pathlib import Path
from logging import getLogger

from qtpy import QtWidgets


log = getLogger(__name__)


class CentralTabWidget(QtWidgets.QTabWidget):

    @property
    def groups(self):
        widgets = [self.widget(i) for i in range(self.count())]
        group_widgets = [widget for widget in widgets if isinstance(widget, GroupTabWidget)]
        return {widget.objectName(): widget for widget in group_widgets}

    def addToGroup(self, group: str, page: QtWidgets.QWidget):
        if not page.objectName():
            raise ValueError("Page must have an object name")
        if group not in self.groups:
            self.addTab(GroupTabWidget(group, self), group)

        group = self.groups[group]

        page_names = [group.tabText(i) for i in range(group.count())]
        if page.objectName() not in page_names:
            group.addTab(page, page.objectName())

        self.setCurrentWidget(group)
        group.setCurrentWidget(page)


class GroupTabWidget(QtWidgets.QTabWidget):
    def __init__(self, name: str, *args):
        super().__init__(*args)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setDocumentMode(True)

        self.setObjectName(name)

        self.tabCloseRequested.connect(self.tabClosed)

    def tabClosed(self, index):
        self.widget(index).deleteLater()
        self.removeTab(index)

        if self.count() == 0:
            self.deleteLater()

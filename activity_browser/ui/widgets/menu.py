from qtpy import QtWidgets


class ABMenuItem:
    action: "ABAction" = None

    def __init__(self,
                 action: "ABAction",
                 action_args: tuple = None,
                 action_kwargs: dict = None,
                 enabled=lambda: True,
                 text: str = None,
                 ):
        self.action = action
        self.enabled = enabled
        self.text = text or action.text
        self.args = action_args or ()
        self.kwargs = action_kwargs or {}


class ABMenu(QtWidgets.QMenu):
    menuItems = []
    title: str = None

    def __init__(self, parent=None):
        super().__init__(parent)

        if self.title:
            self.setTitle(self.title)

        self.setupMenu()

    def setupMenu(self):
        for item in self.menuItems:
            if isinstance(item, QtWidgets.QAction):
                self.addAction(item)
            elif isinstance(item, QtWidgets.QMenu):
                self.addMenu(item)
            elif isinstance(item, ABMenuItem):
                self.addMenuItem(item)
            else:
                raise TypeError(f"Invalid menu item type: {type(item)}")

    def addMenuItem(self, item: ABMenuItem):
        action = item.action.get_QAction(*item.args, **item.kwargs)
        action.setEnabled(item.enabled())
        action.setText(item.text)
        self.addAction(action)


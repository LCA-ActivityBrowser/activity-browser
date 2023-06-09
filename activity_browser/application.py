# -*- coding: utf-8 -*-
from .controllers import controllers
from .layouts import MainWindow


class Application(object):
    def __init__(self):
        self.main_window = MainWindow(self)

        # Instantiate all the controllers.
        # -> Ensure all controller instances have access to the MainWindow
        # object, this propagates the 'AB' icon to all controller-handled
        # dialogs and wizards.
        for attr, controller in controllers.items():
            setattr(self, attr, controller(self.main_window))

    def show(self):
        self.main_window.showMaximized()

    def close(self):
        self.plugin_controller.close_plugins()
        self.main_window.close()

    def deleteLater(self):
        self.main_window.deleteLater()

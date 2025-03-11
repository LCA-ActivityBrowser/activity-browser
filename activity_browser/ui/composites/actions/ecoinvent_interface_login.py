from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import Signal, SignalInstance

import requests
import ecoinvent_interface as ei

from activity_browser import application
from activity_browser.ui.composites import LoginComposite, HorizontalButtonsComposite
from activity_browser.mod.ecoinvent_interface import ABEcoinventRelease


class EcoinventInterfaceLoginComposite(LoginComposite):
    rejected: SignalInstance = Signal()
    accepted: SignalInstance = Signal()

    def __init__(self, dialog):
        self.dialog = dialog
        self.settings = ei.Settings()

        # initialize with a special focus on ecoinvent credentials
        super().__init__(
            label="Provide your ecoinvent credentials",
            username_placeholder="ecoinvent username",
            password_placeholder="ecoinvent password",
            username_preset=self.settings.username,
            password_preset=self.settings.password,
        )

        # set up the buttons and connect
        self.buttons = HorizontalButtonsComposite("Cancel", "~Login")
        self.buttons["Login"].setEnabled(self.validate())
        self.valid.connect(self.buttons["Login"].setEnabled)

        self.buttons["Cancel"].clicked.connect(self.rejected.emit)
        self.buttons["Login"].clicked.connect(self.credential_check)

        # add buttons to self
        self.layout().addWidget(self.buttons)

    def credential_check(self):
        """
        Check whether the supplied credentials are valid by instantiating an EcoinventInterface.Release
        and seeing if we can request a list of available versions from it.
        """
        # set waitcursor because we're making http requests which take long
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        # set the provided settings and check if we can get a version list (i.e. logon was succesful)
        try:
            self.settings = ei.Settings(
                username=self.username.text(),
                password=self.password.text()
            )
            self.dialog.ei_release = ABEcoinventRelease(self.settings)
            self.dialog.ei_release.list_versions()

        # logon was unsuccesful
        except requests.exceptions.HTTPError as e:
            QtWidgets.QApplication.restoreOverrideCursor()

            # in case of 401: Unauthorized, we prompt for a retry of logon
            if e.response.status_code == 401:
                self.warning.setText("Invalid username and/or password, please try again.")
                self.warning.setVisible(True)
                return False
            # else, other HTTPError, try again later maybe? Raise exception for logging
            else:
                self.warning.setText("Unknown connection error, try again later.")
                self.warning.setVisible(True)
                raise e

        # in case of success, set the settings for permanent use
        ei.permanent_setting("username", self.username.text())
        ei.permanent_setting("password", self.password.text())

        # emit accepted signal
        self.accepted.emit()
        QtWidgets.QApplication.restoreOverrideCursor()


if __name__ == '__main__':
    import sys
    from activity_browser import application

    # this will fail without a dialog to link to
    comp = EcoinventInterfaceLoginComposite(None)
    comp.show()

    sys.exit(application.exec_())

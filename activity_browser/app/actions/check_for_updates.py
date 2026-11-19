"""Help / startup update check and New version available dialog."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Signal, SignalInstance

from activity_browser import app
from activity_browser.app.actions.base import ABAction, exception_dialogs
from activity_browser.bwutils.updates import (
    UpdateCheckResult,
    check_for_updates,
    format_terminal_notice,
    should_show_auto_prompt,
)
from activity_browser.ui import icons

_remind_later_this_session = False


def _current_version() -> str:
    try:
        return version("activity_browser")
    except PackageNotFoundError:
        return "0.0.0"


def _skipped_version() -> str | None:
    return app.settings["updates"].get("skipped_version") or None


def _set_skipped_version(base: str) -> None:
    if "updates" not in app.settings.global_config:
        app.settings.global_config["updates"] = {}
    app.settings.global_config["updates"]["skipped_version"] = base
    app.settings.save()


class UpdateCheckThread(QtCore.QThread):
    finished_result: SignalInstance = Signal(object)

    def run(self):
        self.finished_result.emit(check_for_updates(current_version=_current_version()))


class UpdateAvailableDialog(QtWidgets.QDialog):
    def __init__(self, result: UpdateCheckResult, parent=None):
        super().__init__(parent)
        self.result = result
        self.setWindowTitle("New version available")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(
            QtWidgets.QLabel(
                f"A newer Activity Browser version is available.\n\n"
                f"Your version: {result.current_display}\n"
                f"Latest version: {result.latest_display}"
            )
        )

        buttons = QtWidgets.QHBoxLayout()
        if result.channel == "stand-alone":
            primary = QtWidgets.QPushButton("Open download page")
            primary.clicked.connect(self._open_release_page)
        else:
            primary = QtWidgets.QPushButton("Copy update command")
            primary.clicked.connect(self._copy_command)
        primary.setDefault(True)
        buttons.addWidget(primary)

        skip = QtWidgets.QPushButton("Skip this version")
        skip.clicked.connect(self._skip)
        buttons.addWidget(skip)

        later = QtWidgets.QPushButton("Remind me later")
        later.clicked.connect(self._remind_later)
        buttons.addWidget(later)
        layout.addLayout(buttons)

    def _copy_command(self):
        cmd = self.result.upgrade_command or ""
        QtWidgets.QApplication.clipboard().setText(cmd)
        QtWidgets.QMessageBox.information(
            self, "Copied", f"Update command copied to the clipboard:\n\n{cmd}"
        )
        self.accept()

    def _open_release_page(self):
        if self.result.release_page_url:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.result.release_page_url))
        self.accept()

    def _skip(self):
        if self.result.latest_base:
            _set_skipped_version(self.result.latest_base)
        self.accept()

    def _remind_later(self):
        global _remind_later_this_session
        _remind_later_this_session = True
        self.reject()


class CheckForUpdates(ABAction):
    icon = icons.qicons.ab
    text = "&Check for updates..."
    tooltip = "Check whether a newer Activity Browser version is available"

    @classmethod
    @exception_dialogs
    def run(cls, *, manual: bool = True):
        thread = UpdateCheckThread(app.application)
        if manual:
            progress = QtWidgets.QProgressDialog(
                "Checking for updates…", None, 0, 0, app.main_window
            )
            progress.setWindowTitle("Check for updates")
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.show()

            def on_result(result: UpdateCheckResult):
                progress.close()
                cls._show_manual_result(result)

            thread.finished_result.connect(on_result)
        else:
            thread.finished_result.connect(cls._on_startup_result)
        thread.start()

    @classmethod
    def schedule_startup_check(cls):
        QtCore.QTimer.singleShot(0, lambda: cls.run(manual=False))

    @classmethod
    def _print_terminal_notice(cls, result: UpdateCheckResult) -> None:
        """Terminal notice is not gated by skipped version (CONTEXT.md)."""
        notice = format_terminal_notice(result)
        if notice:
            print(notice, flush=True)
        elif result.error:
            print(
                f"Could not fetch latest Activity Browser version: {result.error}",
                flush=True,
            )

    @classmethod
    def _on_startup_result(cls, result: UpdateCheckResult):
        cls._print_terminal_notice(result)
        if should_show_auto_prompt(
            result,
            skipped_version=_skipped_version(),
            snoozed=_remind_later_this_session,
        ):
            UpdateAvailableDialog(result, parent=app.main_window).exec_()

    @classmethod
    def _show_manual_result(cls, result: UpdateCheckResult):
        parent = app.main_window
        if result.error and not result.update_available:
            QtWidgets.QMessageBox.warning(
                parent,
                "Check for updates",
                f"Could not check for updates.\n\n{result.error}",
            )
        elif not result.update_available:
            QtWidgets.QMessageBox.information(
                parent,
                "Check for updates",
                f"You’re up to date.\n\nCurrent version: {result.current_display}",
            )
        else:
            UpdateAvailableDialog(result, parent=parent).exec_()

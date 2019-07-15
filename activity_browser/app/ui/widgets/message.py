# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QMessageBox


def parameter_save_errorbox(error) -> QMessageBox:
    """ Construct a messagebox using the given error

    Can take either the Exception itself or a string
    """
    msgbox = QMessageBox()
    msgbox.setText("An error occured while saving parameters")
    msgbox.setInformativeText(
        "Discard changes or cancel and continue editing?"
    )
    msgbox.setDetailedText(str(error))
    msgbox.setStandardButtons(QMessageBox.Discard | QMessageBox.Cancel)
    msgbox.setDefaultButton(QMessageBox.Cancel)
    return msgbox


def simple_warning_box(title: str, message: str) -> QMessageBox:
    """ Build and return a simple warning message box

    The box can have any given title and message.
    """
    box = QMessageBox()
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.Ok)
    box.setDefaultButton(QMessageBox.Ok)
    return box

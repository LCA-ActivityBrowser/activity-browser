# -*- coding: utf-8 -*-
from PySide2.QtCore import Qt
from PySide2.QtWidgets import QMessageBox


def parameter_save_errorbox(parent, error) -> int:
    """ Construct a messagebox using the given error
     Can take either the Exception itself or a string
    """
    msgbox = QMessageBox(
        QMessageBox.Warning,
        "Cannot save parameters",
        ("An error occurred while saving parameters."
         "\nDiscard changes or cancel and continue editing?"),
        QMessageBox.Discard | QMessageBox.Cancel,
        parent
    )
    msgbox.setWindowModality(Qt.ApplicationModal)
    msgbox.setDetailedText(str(error))
    msgbox.setDefaultButton(QMessageBox.Cancel)
    result = msgbox.exec()
    return result


def simple_warning_box(parent, title: str, message: str) -> int:
    """ Build and return a simple warning message box
     The box can have any given title and message.
    """
    return QMessageBox.warning(
        parent, title, message, QMessageBox.Ok, QMessageBox.Ok
    )

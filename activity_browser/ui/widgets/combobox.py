from PySide2 import QtWidgets


class ABComboBox(QtWidgets.QComboBox):

    @classmethod
    def get_database_combobox(cls, parent=None):
        from activity_browser.mod import bw2data

        combobox = cls(parent)
        combobox.addItems(bw2data.databases)
        return combobox

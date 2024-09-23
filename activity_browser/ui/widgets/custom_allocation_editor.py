from typing import Optional, Union
from PySide2 import QtGui
from PySide2.QtCore import Qt
from PySide2.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QSizePolicy, QSplitter,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from multifunctional import (add_custom_property_allocation_to_project,
                             allocation_strategies, check_property_for_allocation,
                             list_available_properties, check_property_for_process_allocation)
from multifunctional.custom_allocation import MessageType

from activity_browser.logger import log
from activity_browser.ui.style import style_item
from bw2data.backends import Node

class CustomAllocationEditor(QDialog):

    def __init__(self, old_property: str, target: Union[str, Node],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Define custom allocation")
        if isinstance(target, Node):
            self._database_label = target.get("database", "")
            self._target_node = target
            dialog_label = target.get("name")
        else:
            self._database_label = target
            self._target_node = None
            dialog_label = target
        self._selected_property = old_property
        title = QLabel(f"Define custom allocation for {dialog_label}")
        self._property_table = QTableWidget()
        self._property_table.setSortingEnabled(True)
        self._property_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._property_table.setColumnCount(2)
        self._property_table.setHorizontalHeaderLabels(["Property", "Eligibility"])
        self._property_table.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._property_table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._property_table.setWordWrap(True)
        self._property_table.setAlternatingRowColors(True)
        self._property_table.horizontalHeader().setHighlightSections(False)
        self._property_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self._property_table.horizontalHeader().setStretchLastSection(True)
        self._property_table.verticalHeader().setVisible(False)
        self._property_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._property_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._property_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._property_table.itemSelectionChanged.connect(
            self._handle_table_selection_changed
        )
        self._property_table.doubleClicked.connect(
            self._handle_table_double_clicked
        )

        self._status_text = QPlainTextEdit()
        self._status_text.setReadOnly(True)
        if self._property_table.rowCount() == 0:
            self._status_text.setPlainText(
                "Define properties on multifunctional processes to define the custom"
                " allocation based on them.")
        else:
            self._status_text.setPlaceholderText(
                "Select a property to see a detailed analysis of eligibility")

        self._save_button = QPushButton("Select")
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._handle_select_clicked)
        self._cancel_button = QPushButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(title)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._property_table)
        splitter.addWidget(self._status_text)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        layout.addWidget(splitter)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self._save_button)
        button_layout.addWidget(self._cancel_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setStyleSheet("QTableView:!active {selection-background-color: lightgray;}")
        # Default width is too small, default height is too big
        self.resize(400, 400)
        # The QPlainTextEdit is too tall, this (together with the stretch factor)
        # is a way to setting it to fixed height when the dialog is resized.
        # The user can still make it bigger using the splitter.
        # These sizes are adjusted by the splitter, so they only set the
        # proportions.
        splitter.setSizes([300, 100])
        self._fill_table()
        self._select_old()

    @staticmethod
    def brush_for_message_type(type: MessageType) -> QtGui.QBrush:
            if type == MessageType.ALL_VALID:
                return style_item.brushes["good"]
            elif type == MessageType.NONNUMERIC_PROPERTY:
                return style_item.brushes["critical"]
            else:
                return style_item.brushes["warning"]

    def _fill_table(self):
        """
        Add the list of of available properties and their status to the table
        (calculated using list_available_properties) and color them
        according to the status.
        """
        property_list = list_available_properties(self._database_label, self._target_node)
        self._property_table.clearContents()
        # Disable sorting while filling the table, otherwise the
        # inserted items will move between setting the property name
        # and status.
        self._property_table.setSortingEnabled(False)

        self._property_table.setRowCount(len(property_list))
        row = 0
        for property, type in property_list:
            self._property_table.setItem(row, 0, QTableWidgetItem(property))
            self._property_table.setItem(row, 1, QTableWidgetItem(type.value))
            self._property_table.item(row, 0).setForeground(
                self.brush_for_message_type(type)
            )
            row += 1
        self._property_table.setSortingEnabled(True)

    def _get_property_for_row(self, row: int) -> str:
        property_item = self._property_table.item(row, 0)
        return property_item.data(Qt.ItemDataRole.DisplayRole)

    def _get_current_property(self) -> str:
        selection = self._property_table.selectedIndexes()
        if selection:
            row = selection[0].row()
            return self._get_property_for_row(row)
        return ""

    def _select_old(self):
        """
        Selects the property the current allocation is based on.
        This allows the user the reopen the dialog and easily verify the
        state of the current property, then dismiss the dialog with Escape.
        """
        for i in range(self._property_table.rowCount()):
            if self._get_property_for_row(i) == self._selected_property:
                self._property_table.selectRow(i)
                break

    def _handle_table_selection_changed(self):
        """
        Execute check_property_for_allocation for the selected property
        and display its output in the status text.
        """
        if property := self._get_current_property():
            self._save_button.setEnabled(True)
            if self._target_node is None:
                messages = check_property_for_allocation(self._database_label, property)
            else:
                messages = check_property_for_process_allocation(
                    self._target_node,
                    property
                )
            if isinstance(messages, bool):
                if messages == True:
                    self._status_text.setPlainText("All good!")
                else:
                    self._status_text.setPlainText("")
                    log.error("Unexpected return from check_property_for_allocation.")
            else:
                text = f"Found {len(messages)} issues:\n\n"
                for message in messages:
                    text += message.message
                self._status_text.setPlainText(text)
        else:
            self._save_button.setEnabled(False)

    def _handle_table_double_clicked(self):
        """Shortcut for selecting a property and clicking select"""
        self._handle_select_clicked()

    def _handle_select_clicked(self):
        """
        Create a custom allocation based on the selected property using
        add_custom_property_allocation_to_project.
        """
        if selected_property := self._get_current_property():
            self._selected_property = selected_property
            if not self._selected_property in allocation_strategies:
                add_custom_property_allocation_to_project(self._selected_property)
            self.accept()

    def selected_property(self) -> str:
        """
        Return the property the user selected, or the old one if the user
        cancelled the dialog.
        """
        return self._selected_property

    @staticmethod
    def define_custom_allocation(old_property: str, target: Union[str, Node], parent: Optional[QWidget] = None) -> str:
        """
        Open the custom allocation editor and return the new property, if the user
        selected one, or the old one if the user cancelled the dialog.
        """
        result = old_property
        try:
            editor = CustomAllocationEditor(old_property, target, parent)
            if editor.exec_() == QDialog.DialogCode.Accepted:
                result = editor.selected_property()
        except Exception as e:
            log.error(f"Exception in CustomAllocationEditor: {e}")
            QMessageBox.warning(parent, "An error occured", str(e))
        finally:
            return result

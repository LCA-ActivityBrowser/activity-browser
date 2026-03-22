from qtpy import QtCore, QtGui, QtWidgets
from activity_browser.ui.icons import qicons


class DragHandleDelegate(QtWidgets.QStyledItemDelegate):
    """Custom delegate that paints a drag handle icon on the left of each row.
    
    This delegate adds a visual affordance (grip icon) to indicate that rows
    can be reordered via drag-and-drop. The icon is painted in the left margin
    of each list item.
    """
    
    def paint(self, painter, option, index):
        """Paint the item with a drag handle icon on the left side.
        
        Parameters
        ----------
        painter : QtGui.QPainter
            The painter to use for rendering.
        option : QtWidgets.QStyleOptionViewItem
            Style options for the item.
        index : QtCore.QModelIndex
            The model index of the item to paint.
        """
        super().paint(painter, option, index)
        
        # Draw drag handle icon on the left
        icon_size = 16
        icon_margin = 4
        icon_rect = QtCore.QRect(
            option.rect.left() + icon_margin,
            option.rect.top() + (option.rect.height() - icon_size) // 2,
            icon_size,
            icon_size
        )
        
        # Use a grip icon if available, otherwise use a simple visual indicator
        if hasattr(qicons, 'drag_indicator'):
            qicons.drag_indicator.paint(painter, icon_rect)
        else:
            # Fallback: draw three horizontal lines as a grip indicator
            painter.save()
            painter.setPen(QtGui.QPen(option.palette.mid().color(), 2))
            y_center = icon_rect.center().y()
            x_left = icon_rect.left() + 2
            x_right = icon_rect.right() - 2
            for offset in [-4, 0, 4]:
                y = y_center + offset
                painter.drawLine(x_left, y, x_right, y)
            painter.restore()


class ABListEditDialog(QtWidgets.QDialog):
    """
    A dialog for editing a list or tuple of strings with drag-and-drop reordering.
        
    Parameters
    ----------
    data : iterable of str
        Initial values to populate the list.
    title : str, optional
        Window title for the dialog. Default is "Edit List/Tuple".
    parent : QtWidgets.QWidget, optional
        Parent widget for the dialog.
    
    Examples
    --------
    >>> dialog = ABListEditDialog(["item1", "item2"], title="Edit Items")
    >>> if dialog.exec_() == QtWidgets.QDialog.Accepted:
    ...     updated_items = dialog.get_data()
    """

    def __init__(self, data, title="Edit List/Tuple", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 320)

        layout = QtWidgets.QVBoxLayout(self)

        # List widget
        self.list = QtWidgets.QListWidget(self)
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
        )
        # Enable intuitive drag-and-drop reordering
        self.list.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.list.setAlternatingRowColors(True)
        self.list.setStyleSheet(
            """
            QListWidget { alternate-background-color: palette(alternate-base); }
            QListWidget::item { padding: 6px 28px 6px 28px; }
            QListWidget::item:selected { background: palette(highlight); color: palette(highlighted-text); }
            """
        )
        # Set custom delegate to draw drag handles
        self.list.setItemDelegate(DragHandleDelegate(self.list))

        # OK/Cancel
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )

        # Assemble layout
        layout.addWidget(self.list)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        # Signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.list.itemChanged.connect(self.on_item_changed)
        self.list.itemSelectionChanged.connect(self._on_selection_changed)
        # Reposition inline buttons on scroll/resize/content changes
        self.list.verticalScrollBar().valueChanged.connect(self._position_inline_buttons)
        self.list.horizontalScrollBar().valueChanged.connect(self._position_inline_buttons)
        self.list.viewport().installEventFilter(self)

        # Populate from provided data
        self.load_data(data)
        self._create_inline_buttons()
        self._position_inline_buttons()

    # ---------- Data ----------
    def load_data(self, data):
        """Load data into the list widget.
        
        Populates the list with the provided values. If no data is provided,
        adds a single empty row to guide the user.
        
        Parameters
        ----------
        data : iterable of str
            Values to populate the list with.
        """
        has_any = False
        for value in data:
            self._append_item(str(value))
            has_any = True
        if not has_any:
            # Provide a single empty row to guide the user
            self._append_item("")

    def get_data(self, as_tuple=False):
        """Retrieve the current list data, excluding empty rows.
        
        Parameters
        ----------
        as_tuple : bool, optional
            If True, return data as a tuple instead of a list. Default is False.
        
        Returns
        -------
        list or tuple of str
            Non-empty string values from the list, in current display order.
        """
        values = []
        for row in range(self.list.count()):
            item = self.list.item(row)
            if item:
                text = item.text().strip()
                if text:
                    values.append(text)
        return tuple(values) if as_tuple else values

    # ---------- Item helpers ----------
    def _append_item(self, text=""):
        """Create and append a new editable, draggable item to the list.
        
        Parameters
        ----------
        text : str, optional
            Initial text content for the item. Default is empty string.
        """
        item = QtWidgets.QListWidgetItem(text)
        # editable + enabled + selectable + draggable
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsDragEnabled)
        self.list.addItem(item)

    def add_item(self):
        """Add a new empty item and immediately start editing it.
        
        This method is connected to the inline add button. It creates a new row,
        selects it, and opens it for editing, then repositions the floating buttons.
        """
        self._append_item("")
        # Select and start editing the newly added row
        item = self.list.item(self.list.count() - 1)
        self.list.setCurrentItem(item)
        self.list.editItem(item)
        self._position_inline_buttons()

    def remove_selected(self):
        """Remove the currently selected item from the list.
        
        This method is connected to the inline remove button. After removal,
        it ensures at least one empty row remains and adjusts the selection
        to the next appropriate row.
        """
        row = self._current_row()
        if row is None:
            return
        self.list.takeItem(row)
        # keep at least one empty row for guidance
        if self.list.count() == 0:
            self._append_item("")
        # adjust selection
        new_row = min(row, self.list.count() - 1)
        if new_row >= 0:
            self.list.setCurrentRow(new_row)
        self._position_inline_buttons()

    # Drag-and-drop handles reordering; no explicit move buttons

    def on_item_changed(self, item: QtWidgets.QListWidgetItem):
        """Handle item text changes by normalizing whitespace.
        
        Connected to the list widget's itemChanged signal. Collapses multiple
        consecutive spaces into a single space to maintain clean data.
        
        Parameters
        ----------
        item : QtWidgets.QListWidgetItem
            The item that was changed.
        """
        # No placeholder logic. Just normalize whitespace.
        if item is None:
            return
        text = item.text()
        if text is None:
            return
        # Collapse accidental multiple spaces
        norm = " ".join(text.split())
        if norm != text:
            # block signals to avoid recursion
            self.list.blockSignals(True)
            item.setText(norm)
            self.list.blockSignals(False)

    # ---------- UI helpers ----------
    def _current_row(self):
        """Get the index of the currently selected row.
        
        Returns
        -------
        int or None
            Row index (0-based) of the selected item, or None if nothing is selected.
        """
        indexes = self.list.selectedIndexes()
        if not indexes:
            return None
        return indexes[0].row()

    # ---------- Inline buttons ----------
    def _create_inline_buttons(self):
        """Create floating icon buttons for add and remove operations.
        
        Creates two QToolButton instances:
        - Add button: positioned at bottom-right corner of the list viewport
        - Remove button: positioned inline with the currently selected row
        
        Both buttons use absolute positioning and are parented to the viewport
        to float over the list content.
        """
        # Add button at bottom-right
        self.inline_add_btn = QtWidgets.QToolButton(self.list.viewport())
        self.inline_add_btn.setIcon(qicons.add)
        self.inline_add_btn.setAutoRaise(True)
        self.inline_add_btn.setToolTip("Add row")
        self.inline_add_btn.clicked.connect(self.add_item)
        
        # Remove button aligned with selected row
        self.inline_remove_btn = QtWidgets.QToolButton(self.list.viewport())
        self.inline_remove_btn.setIcon(qicons.delete)
        self.inline_remove_btn.setAutoRaise(True)
        self.inline_remove_btn.setToolTip("Remove selected row")
        self.inline_remove_btn.clicked.connect(self.remove_selected)
        self.inline_remove_btn.hide()

    def _on_selection_changed(self):
        """Handle selection changes by repositioning inline buttons.
        
        Connected to the list widget's itemSelectionChanged signal. Ensures
        the remove button follows the selected row.
        """
        self._position_inline_buttons()

    def eventFilter(self, obj, event):
        """Monitor viewport events to reposition floating buttons when needed.
        
        Watches for resize, update, and paint events on the list viewport,
        deferring button repositioning until after layout updates complete.
        
        Parameters
        ----------
        obj : QtCore.QObject
            The object being monitored (should be self.list.viewport()).
        event : QtCore.QEvent
            The event that occurred.
        
        Returns
        -------
        bool
            Result from the parent event filter.
        """
        if obj is self.list.viewport():
            if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.UpdateRequest, QtCore.QEvent.Paint):
                # Defer reposition slightly to after layout updates
                QtCore.QTimer.singleShot(0, self._position_inline_buttons)
        return super().eventFilter(obj, event)

    def _position_inline_buttons(self):
        """Calculate and apply absolute positions for floating buttons.
        
        Positions the add button at the bottom-right corner of the viewport,
        and the remove button inline with the currently selected row (if any).
        The remove button is only shown if it would be visible within the viewport.
        
        This method is called on:
        - Selection changes
        - Scroll events
        - Viewport resize/paint/update events
        - After adding or removing items
        """
        if not hasattr(self, "inline_add_btn") or not hasattr(self, "inline_remove_btn"):
            return
        
        # Position add button at bottom-right corner
        viewport_rect = self.list.viewport().rect()
        add_w = self.inline_add_btn.sizeHint().width()
        add_h = self.inline_add_btn.sizeHint().height()
        add_x = viewport_rect.right() - add_w - 6
        add_y = viewport_rect.bottom() - add_h - 6
        self.inline_add_btn.move(add_x, add_y)
        self.inline_add_btn.show()
        
        # Position remove button aligned with selected row
        row = self._current_row()
        if row is None:
            self.inline_remove_btn.hide()
            return
        item = self.list.item(row)
        if item is None:
            self.inline_remove_btn.hide()
            return
        rect = self.list.visualItemRect(item)
        if not rect.isValid() or rect.height() <= 0:
            self.inline_remove_btn.hide()
            return
        # Position inside the item's rect at right side with small margin
        btn_w = self.inline_remove_btn.sizeHint().width()
        btn_h = self.inline_remove_btn.sizeHint().height()
        x = rect.right() - btn_w - 6
        y = rect.top() + (rect.height() - btn_h) // 2
        self.inline_remove_btn.move(x, y)
        # Only show if fully or partially visible within viewport
        if viewport_rect.intersects(QtCore.QRect(x, y, btn_w, btn_h)):
            self.inline_remove_btn.show()
        else:
            self.inline_remove_btn.hide()



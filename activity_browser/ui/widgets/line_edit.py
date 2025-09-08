from qtpy import QtWidgets
from qtpy.QtCore import QTimer, Slot, Signal, SignalInstance, QStringListModel, Qt
from qtpy.QtGui import QTextFormat
from qtpy.QtWidgets import QCompleter

from activity_browser.bwutils import AB_metadata


class ABLineEdit(QtWidgets.QLineEdit):
    textChangedDebounce: SignalInstance = Signal(str)
    _debounce_ms = 250

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._debounce_timer = QTimer(self, singleShot=True)

        self.textChanged.connect(self._set_debounce)
        self._debounce_timer.timeout.connect(self._emit_debounce)

    def _set_debounce(self):
        self._debounce_timer.setInterval(self._debounce_ms)
        self._debounce_timer.start()

    def _emit_debounce(self):
        self.textChangedDebounce.emit(self.text())

    def debounce(self):
        return self._debounce_ms

    def setDebounce(self, ms: int):
        self._debounce_ms = ms


class SignalledLineEdit(QtWidgets.QLineEdit):
    """Adapted from http://stackoverflow.com/questions/12182133/PyQt5-combine-textchanged-and-editingfinished-for-qlineedit"""

    def __init__(self, key, field, contents="", parent=None):
        super(SignalledLineEdit, self).__init__(contents, parent)
        self.editingFinished.connect(self._editing_finished)
        self.textChanged.connect(self._text_changed)
        self._before = contents
        self._key = key
        self._field = field

    @Slot(str, name="customTextChanged")
    def _text_changed(self, text: str) -> None:
        """Reset 'before' value when changing via Python"""
        if not self.hasFocus():
            self._before = text

    @Slot(name="customEditFinish")
    def _editing_finished(self) -> None:
        from activity_browser import actions

        after = self.text()
        if self._before != after:
            self._before = after
            actions.ActivityModify.run(self._key, self._field, after)


class SignalledPlainTextEdit(QtWidgets.QPlainTextEdit):
    """Adapted from https://john.nachtimwald.com/2009/08/19/better-qplaintextedit-with-line-numbers/"""

    def __init__(self, key: tuple, field: str, contents: str = "", parent=None):
        super().__init__(contents, parent)
        self.highlight()
        self.cursorPositionChanged.connect(self.highlight)
        self._before = contents
        self._key = key
        self._field = field

    @Slot(name="highlight")
    def highlight(self):
        selection = QtWidgets.QTextEdit.ExtraSelection()
        selection.format.setBackground(self.palette().alternateBase())
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    def focusOutEvent(self, event):
        from activity_browser import actions

        after = self.toPlainText()
        if self._before != after:
            actions.ActivityModify.run(self._key, self._field, after)
        super().focusOutEvent(event)

    def refresh_text(self, text: str) -> None:
        self._before = text
        self.setPlainText(text)


class SignalledComboEdit(QtWidgets.QComboBox):
    """Based on SignalledPlainTextEdit.

    Could be moved to new file. Or better: this file renamed to be more inclusive
    needed to effectively implement the location dropdown list
    """

    def __init__(self, key, field, contents="", parent=None):
        super().__init__(parent)
        self._before = contents
        self._key = key
        self._field = field

    def focusOutEvent(self, event):
        from activity_browser import actions

        after = self.currentText()
        if self._before != after:
            self._before = after
            actions.ActivityModify.run(self._key, self._field, after)
        super(SignalledComboEdit, self).focusOutEvent(event)


class AutoCompleteLineEdit(QtWidgets.QLineEdit):
    """Line Edit with a completer attached"""

    def __init__(self, items: list[str], parent=None):
        super().__init__(parent=parent)
        completer = QCompleter(items, self)
        self.setCompleter(completer)


class MetaDataAutoCompleteLineEdit(ABLineEdit):
    """Line Edit with MetaDataStore completer attached"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.database_name = ""

        # autocompleter settings
        self.model = QStringListModel()
        self.completer = QCompleter(self.model)
        self.popup = self.completer.popup()
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.completer.setPopup(self.popup)
        # allow all items in popup list
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect textEdited, this only triggers on user input, not Completer input
        self.textEdited.connect(self._set_items)

    def _set_items(self, text=None):
        if text is None:
            text = self.text()

        # find the start and end of the word under the cursor
        cursor_pos = self.cursorPosition()
        start = cursor_pos
        while start > 0 and text[start - 1] != " ":
            start -= 1
        end = cursor_pos
        while end < len(text) and text[end] != " ":
            end += 1
        current_word = text[start:end]
        if not current_word:
            self.model.setStringList([])
            return
        context = set((text[:start] + text[end:]).split(" "))

        # get suggestions for the current word
        alternatives = AB_metadata.auto_complete(current_word, context=context, database=self.database_name)
        alternatives = alternatives[:6]  # at most 6, though we should get ~3 usually
        # replace the current word with each alternative
        items = []
        for alt in alternatives:
            new_text = text[:start] + alt + text[end:]
            items.append(new_text)
        print(text, items)

        self.model.setStringList(items)
        # set correct height now that we have data
        max_height = max(
            20,
            self.popup.sizeHintForRow(0) * 3 + 2 * self.popup.frameWidth()
                         )
        self.popup.setMaximumHeight(max_height)

class ABTextEdit(QtWidgets.QTextEdit):
    textChangedDebounce: SignalInstance = Signal(str)
    _debounce_ms = 250

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._debounce_timer = QTimer(self, singleShot=True)

        self.textChanged.connect(self._set_debounce)
        self._debounce_timer.timeout.connect(self._emit_debounce)

    def _set_debounce(self):
        self._debounce_timer.setInterval(self._debounce_ms)
        self._debounce_timer.start()

    def _emit_debounce(self):
        self.textChangedDebounce.emit(self.toPlainText())

    def debounce(self):
        return self._debounce_ms

    def setDebounce(self, ms: int):
        self._debounce_ms = ms


class MetaDataAutoCompleteLineEdit(ABTextEdit):
    """Line Edit with MetaDataStore completer attached"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.database_name = ""

        # autocompleter settings
        self.model = QStringListModel()
        self.completer = QCompleter(self.model)
        self.completer.setWidget(self)
        self.popup = self.completer.popup()
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.completer.setPopup(self.popup)
        # allow all items in popup list
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.completer.activated.connect(self._insert_auto_complete)

        self.textChanged.connect(self.sanitize_input)

    def sanitize_input(self):
        text = self.toPlainText()
        text = AB_metadata.search_engine.ONE_SPACE_PATTERN.sub(" ", text)
        self.blockSignals(True)
        self.clear()
        self.insertPlainText(text)
        self.blockSignals(False)
        if len(text) == 0:
            self.popup.close()

    def _insert_auto_complete(self, completion):
        self.clear()
        self.insertPlainText(completion)
        self.popup.close()
        self._set_items()

    def _set_items(self):
        text = self.toPlainText()

        # find the start and end of the word under the cursor
        cursor_pos = self.textCursor().position()
        start = cursor_pos
        while start > 0 and text[start - 1] != " ":
            start -= 1
        end = cursor_pos
        while end < len(text) and text[end] != " ":
            end += 1
        current_word = text[start:end]
        if not current_word:
            self.model.setStringList([])
            return
        context = set((text[:start] + text[end:]).split(" "))

        # get suggestions for the current word
        alternatives = AB_metadata.auto_complete(current_word, context=context, database=self.database_name)
        alternatives = alternatives[:6]  # at most 6, though we should get ~3 usually
        # replace the current word with each alternative
        items = []
        for alt in alternatives:
            new_text = text[:start] + alt + text[end:]
            items.append(new_text)
        print(text, items)
        if len(items) == 0:
            return

        self.model.setStringList(items)
        # set correct height now that we have data
        max_height = max(
            20,
            self.popup.sizeHintForRow(0) * 3 + 2 * self.popup.frameWidth()
                         )
        self.popup.setMaximumHeight(max_height)
        self.completer.complete()

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
            # insert an autocomplete item
            # capture enter/return/tab key
            index = self.popup.currentIndex()
            selected_text = index.data(Qt.DisplayRole)
            self.completer.activated.emit(selected_text + " ")
            return
        elif key in (Qt.Key_Space,):
            self.popup.close()

        super().keyPressEvent(event)

        # trigger on text input keys
        if event.text():  # filters out non-text keys like arrows, shift, etc.
            self._set_items()

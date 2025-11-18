from qtpy import QtWidgets
from qtpy.QtCore import QTimer, Signal, SignalInstance, QStringListModel, Qt
from qtpy.QtGui import QSyntaxHighlighter, QTextCharFormat, QTextDocument, QFont
from qtpy.QtWidgets import QCompleter, QStyledItemDelegate, QStyle

from activity_browser.bwutils import AB_metadata


class UnknownWordHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument, known_words: set):
        super().__init__(parent)
        self.known_words = known_words

        # define the format for unknown words
        self.unknown_format = QTextCharFormat()
        self.unknown_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.unknown_format.setUnderlineColor(Qt.red)

    def highlightBlock(self, text: str):
        if text.startswith("="):
            return
        words = text.split()
        index = 0
        for word in words:
            word_len = len(word)
            if word and word not in self.known_words:
                self.setFormat(index, word_len, self.unknown_format)
            index += word_len + 1  # +1 for the space


class AutoCompleteDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_word_index = -1

    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)

        painter.save()

        # Draw selection background if selected
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())

        # Split text into words and draw each with appropriate font
        words = text.split(" ")
        x = option.rect.x()
        y = option.rect.y()
        spacing = 4  # space between words
        font = option.font
        metrics = painter.fontMetrics()

        for i, word in enumerate(words):
            word_font = QFont(font)
            if i+1 == self.current_word_index:
                word_font.setBold(True)
            painter.setFont(word_font)

            word_width = metrics.horizontalAdvance(word)
            painter.drawText(x, y + metrics.ascent() + (option.rect.height() - metrics.height()) // 2, word)
            x += word_width + spacing
        painter.restore()


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


class ABAutoCompleTextEdit(ABTextEdit):
    def __init__(self, parent=None, highlight_unknown=False):
        super().__init__(parent=parent)
        self.auto_complete_word = ""

        # autocompleter settings
        self.model = QStringListModel()
        self.completer = QCompleter(self.model)
        self.completer.setWidget(self)
        self.popup = self.completer.popup()
        self.delegate = AutoCompleteDelegate(self.popup) # set custom delegate to bold the current word
        self.popup.setItemDelegate(self.delegate)
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.completer.setPopup(self.popup)
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion) # allow all items in popup list
        self.completer.activated.connect(self._insert_auto_complete)

        self.textChanged.connect(self._sanitize_input)
        if highlight_unknown:
            self.highlighter = UnknownWordHighlighter(self.document(), set())
        self.cursorPositionChanged.connect(self._set_autocomplete_items)

    def keyPressEvent(self, event):
        key = event.key()

        if key in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab):
            # insert an autocomplete item
            # capture enter/return/tab key
            index = self.popup.currentIndex()
            completion_text = index.data(Qt.DisplayRole)
            self.completer.activated.emit(completion_text)
            return
        elif key in (Qt.Key_Space,):
            self.popup.close()

        super().keyPressEvent(event)

        # trigger on text input keys
        if event.text() or key in (Qt.LeftArrow, Qt.RightArrow):  # filters out non-text keys except l/r arrows
            self._set_autocomplete_items()

    def _sanitize_input(self):
        raise NotImplementedError

    def _set_autocomplete_items(self):
        raise NotImplementedError

    def _insert_auto_complete(self, completion):
        cursor = self.textCursor()
        position = cursor.position()
        completion = completion + " "  # add space to end of new text

        # find where to put cursor back
        new_position = position
        while new_position < len(completion) and completion[new_position] != " ":
            new_position += 1
        new_position += 1  # add one char for space

        # set new text from completion
        self.blockSignals(True)
        self.clear()
        self.setText(completion)
        # set the cursor location
        cursor.setPosition(min(new_position, len(completion)))
        self.setTextCursor(cursor)
        self.blockSignals(False)

        # house keeping
        self._emit_debounce()
        self.popup.close()
        self.auto_complete_word = ""
        self.model.setStringList([])


class MetaDataAutoCompleteTextEdit(ABAutoCompleTextEdit):
    """TextEdit with MetaDataStore completer attached."""
    def __init__(self, parent=None):
        super().__init__(parent=parent, highlight_unknown=True)
        self.database_name = ""

    def _sanitize_input(self):
        self._debounce_timer.stop()
        text = self.toPlainText()
        clean_text = AB_metadata.search_engine.ONE_SPACE_PATTERN.sub(" ", text)

        if clean_text != text:
            cursor = self.textCursor()
            position = cursor.position()
            self.blockSignals(True)
            self.clear()
            self.insertPlainText(clean_text)
            self.blockSignals(False)
            cursor.setPosition(min(position, len(clean_text)))
            self.setTextCursor(cursor)

        known_words = set()
        for identifier in AB_metadata.search_engine.database_id_manager(self.database_name):
            known_words.update(AB_metadata.search_engine.identifier_to_word[identifier].keys())
        self.highlighter.known_words = known_words

        if len(text) == 0:
            self.popup.close()
        self._set_debounce()

    def _set_autocomplete_items(self):
        text = self.toPlainText()
        if text.startswith("="):
            self.model.setStringList([])
            self.auto_complete_word = ""
            self.popup.close()
            return

        # find the start and end of the word under the cursor
        cursor = self.textCursor()
        position = cursor.position()
        start = position
        while start > 0 and text[start - 1] != " ":
            start -= 1
        end = position
        while end < len(text) and text[end] != " ":
            end += 1
        current_word = text[start:end]
        if not current_word:
            self.model.setStringList([])
            self.popup.close()
            self.auto_complete_word = ""
            return
        if self.auto_complete_word == current_word:
            # avoid unnecessary auto_complete calls if the current word didnt change
            return
        self.auto_complete_word = current_word

        context = set((text[:start] + text[end:]).split(" "))
        self.delegate.current_word_index = len(text[:start].split(" "))  # current word index for bolding
        # get suggestions for the current word
        suggestions = AB_metadata.auto_complete(current_word, context=context, database=self.database_name)
        suggestions = suggestions[:6]  # at most 6, though we should get ~3 usually
        # replace the current word with each alternative
        items = []
        for alt in suggestions:
            new_text = text[:start] + alt + text[end:]
            items.append(new_text)
        if len(items) == 0:
            self.popup.close()
            return

        self.model.setStringList(items)
        # set correct height now that we have data
        max_height = max(
            20,
            self.popup.sizeHintForRow(0) * 3 + 2 * self.popup.frameWidth()
                         )
        self.popup.setMaximumHeight(max_height)
        self.completer.complete()

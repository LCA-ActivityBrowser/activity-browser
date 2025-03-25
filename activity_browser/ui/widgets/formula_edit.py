import re
from collections import namedtuple

import pandas as pd

from asteval import make_symbol_table, Interpreter

from qtpy.QtWidgets import QApplication, QWidget, QCompleter, QTableView, QSizePolicy
from qtpy.QtGui import QPainter, QColor, QFontMetrics, QFontDatabase, QPainterPath, QPen, QFont
from qtpy.QtCore import QTimer, Qt, QAbstractTableModel, QModelIndex

from activity_browser.static import fonts

QFontDatabase.addApplicationFont(fonts.__path__[0] + "/mono.ttf")

operators = r"+\-*/%=<>!&|^~"
pattern = r"\b[a-zA-Z_]\w*\b|[\d.]+|[\"'{}:,+\-*/^()\[\]]| +"


TOKEN_REGEX = r'''
(?P<COMMENT>\#.*)                              # Comments
| (?P<SQSTRING>'(?:\\.|[^\\])*?')              # Single-quoted string
| (?P<DQSTRING>"(?:\\.|[^\\])*?")             # Double-quoted string
| (?P<NUMBER>\b\d+(\.\d*)?([eE][-+]?\d+)?\b)  # Integer or decimal number
| (?P<KEYWORD>\b(?:def|class|if|else|elif|return|for|while|import|from|try|except|with|as|True|False|None|break|continue|pass|and|or|not|is|in|lambda|yield|global|nonlocal|assert|raise|del|async|await)\b)
| (?P<OPERATOR>[+\-*/%=<>!&|^~]+)             # Operators
| (?P<PUNCTUATION>[(),.:;\[\]{}])            # Punctuation
| (?P<IDENTIFIER>\b[a-zA-Z_][a-zA-Z0-9_]*\b)  # Identifiers
| (?P<WHITESPACE>\s+)                         # Whitespace
| (?P<MISMATCH>.)                             # Any other character
'''


def tokenize(expression: str):
    regex = re.compile(TOKEN_REGEX, re.VERBOSE)
    tokens = []
    for match in regex.finditer(expression):
        kind = match.lastgroup
        value = match.group()
        tokens.append(namedtuple("Token", ["kind", "value"])(kind, value))
    return tokens

table = make_symbol_table()

parameters = {
    "db_parameter_1": None,
    "activity_parameter_1": None,
}


class Colors:
    builtin = QColor("#a626a4")
    number = QColor("#986801")
    variable = QColor("#4078f2")
    string = QColor("#50a14f")


class ABFormulaEdit(QWidget):
    def __init__(self, parent=None, scope=None, text=None):
        super().__init__(parent)
        self.scope = scope or {}
        self.error = False
        self.cursor_pos = 0  # Cursor position in the text
        self.selection_start = None  # Selection start index
        self.selection_end = None  # Selection end index
        self.cursor_visible = False  # Blinking cursor state
        self.scroll_offset = 0  # Scroll position for long text
        self.padding = 5  # Left padding for text inside the box
        self.dragging = False  # Track if mouse is dragging

        font = self.font()
        font.setFamily("JetBrains Mono")
        font.setPointSize(9)
        self.setFont(font)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.toggle_cursor)
        self.timer.start(500)  # Blink cursor every 500ms

        self.interpreter = Interpreter({k: v.amount for k, v in scope.items()})
        self.completer = QCompleter()
        self.completer.setPopup(CompleterView())
        self.completer_model = CompleterModel(self.scope, self.font())

        self.completer.setWidget(self)
        self.completer.setModel(self.completer_model)
        self.completer.setCompletionColumn(0)
        self.completer.activated.connect(self.insert_completion)

        self.text = text or ""  # Stores user input

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = str(value)
        try:
            self.error = None
            self.interpreter.eval(self.text, show_errors=False, raise_errors=True)
        except (SyntaxError, TypeError) as e:
            self.error = e
        except:
            pass

    def pos_to_token_index(self, pos: int) -> int:
        tokens = tokenize(self.text)

        result = -1
        char_index = 0
        for i, (kind, token) in enumerate(tokens):
            char_index += len(token)
            if pos <= char_index:
                result = i
                break

        return result

    def token_at_cursor(self):
        index = self.pos_to_token_index(self.cursor_pos)
        tokens = re.findall(pattern, self.text)

        return tokens[index] if len(tokens) > 0 else ""

    def update_completer(self):
        tokens = tokenize(self.text)
        index = self.pos_to_token_index(self.cursor_pos)

        if len(tokens) == 0 or tokens[index].kind in ["OPERATOR", "PUNCTUATION", "WHITESPACE"]:
            self.completer.setCompletionPrefix("")
        else:
            self.completer.setCompletionPrefix(tokens[index].value)

        self.completer.complete(self.rect())

    def insert_completion(self, completion):
        tokens = tokenize(self.text)
        index = self.pos_to_token_index(self.cursor_pos)

        # if the line is empty, just replace the line with the completion
        if len(tokens) == 0:
            self.text = completion
            self.move_cursor(len(completion))
            return

        text_list = [token.value for token in tokens]

        if tokens[index].kind in ["OPERATOR", "PUNCTUATION", "WHITESPACE"]:
            shift = len(completion)
            text_list.insert(index + 1, completion)
        else:
            shift = len(completion) - len(text_list[index])
            text_list[index] = completion

        self.text = "".join(text_list)
        self.move_cursor(shift)

    def toggle_cursor(self):
        """Toggles cursor visibility for blinking effect."""
        self.cursor_visible = not self.cursor_visible
        self.update()

    def keyPressEvent(self, event):
        """Handles key press events for text input, cursor movement, and selection."""
        key = event.key()
        ctrl_pressed = event.modifiers() & Qt.ControlModifier
        shift_pressed = event.modifiers() & Qt.ShiftModifier

        if ctrl_pressed and key == Qt.Key_C:  # Copy
            self.copy_to_clipboard()
        elif ctrl_pressed and key == Qt.Key_V:  # Paste
            self.paste_from_clipboard()
        elif ctrl_pressed and key == Qt.Key_X:  # Paste
            self.copy_to_clipboard()
            self.delete_selected_text()
        elif ctrl_pressed and key == Qt.Key_A:  # Select All
            self.select_all()
        elif key == Qt.Key_Backspace:
            if self.selection_start is not None:
                self.delete_selected_text()
            elif self.cursor_pos > 0:
                self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                self.move_cursor(-1)
        elif key == Qt.Key_Delete:
            if self.selection_start is not None:
                self.delete_selected_text()
            elif self.cursor_pos < len(self.text):
                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
        elif key == Qt.Key_Left:
            if shift_pressed:
                self.adjust_selection(-1)
            else:
                self.move_cursor(-1)
        elif key == Qt.Key_Right:
            if shift_pressed:
                self.adjust_selection(1)
            else:
                self.move_cursor(1)
        elif key == Qt.Key_Home:
            self.move_cursor(-self.cursor_pos)
        elif key == Qt.Key_End:
            self.move_cursor(len(self.text) - self.cursor_pos)
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.completer.popup().event(event)
        elif event.text():
            if self.selection_start is not None:
                self.delete_selected_text()
            new_text = "".join(re.findall(pattern, event.text()))
            new_text = self.text[:self.cursor_pos] + new_text + self.text[self.cursor_pos:]
            if re.findall(pattern, self.text) == re.findall(pattern, new_text):
                return
            self.text = new_text
            self.move_cursor(1)

        self.adjust_scroll()
        self.update()

    def copy_to_clipboard(self):
        """Copies selected text to the clipboard."""
        if self.selection_start is not None and self.selection_end is not None:
            start, end = sorted([self.selection_start, self.selection_end])
            clipboard = QApplication.clipboard()
            clipboard.setText(self.text[start:end])

    def paste_from_clipboard(self):
        """Pastes text from the clipboard at the cursor position."""
        clipboard = QApplication.clipboard()
        pasted_text = "".join(re.findall(pattern, clipboard.text()))

        if self.selection_start is not None:
            self.delete_selected_text()

        self.text = self.text[:self.cursor_pos] + pasted_text + self.text[self.cursor_pos:]
        self.cursor_pos += len(pasted_text)
        self.adjust_scroll()
        self.update()

    def select_all(self):
        """Selects all text."""
        self.selection_start = 0
        self.selection_end = len(self.text)
        self.cursor_pos = len(self.text)
        self.update()

    def move_cursor(self, step):
        """Moves the cursor without selection."""
        self.cursor_pos = max(0, min(len(self.text), self.cursor_pos + step))
        self.selection_start = None  # Clear selection
        self.adjust_scroll()
        self.update_completer()

    def adjust_selection(self, step):
        """Adjusts selection range while moving the cursor."""
        if self.selection_start is None:
            self.selection_start = self.cursor_pos

        self.cursor_pos = max(0, min(len(self.text), self.cursor_pos + step))
        self.selection_end = self.cursor_pos if self.selection_start != self.cursor_pos else None
        self.adjust_scroll()

    def delete_selected_text(self):
        """Deletes selected text."""
        if self.selection_start is None or self.selection_end is None:
            return
        start, end = sorted([self.selection_start, self.selection_end])
        self.text = self.text[:start] + self.text[end:]
        self.cursor_pos = start
        self.selection_start = self.selection_end = None
        self.adjust_scroll()

    def adjust_scroll(self):
        """Adjusts the scroll position to keep the cursor visible."""
        font_metrics = self.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.text[:self.cursor_pos])

        if text_width - self.scroll_offset > self.width() - self.padding:
            self.scroll_offset = text_width - self.width() + self.padding
        elif self.scroll_offset and text_width - self.scroll_offset < self.width() - self.padding:
            self.scroll_offset = text_width - self.width() + self.padding
        elif text_width < self.scroll_offset:
            self.scroll_offset = text_width

        if self.scroll_offset < 0:
            self.scroll_offset = 0

    def get_cursor_position_from_x(self, x):
        """Gets the cursor index based on the mouse click position."""
        font_metrics = self.fontMetrics()
        x_offset = x - self.padding + self.scroll_offset
        cursor_pos = len(self.text)

        for i in range(len(self.text)):
            if font_metrics.horizontalAdvance(self.text[:i]) > x_offset:
                cursor_pos = i
                break

        return cursor_pos

    def mousePressEvent(self, event):
        """Handles mouse click events to set cursor position and start selection."""
        if 10 <= event.x() <= 390 and 10 <= event.y() <= 40:
            self.cursor_pos = self.get_cursor_position_from_x(event.x())
            self.selection_start = self.cursor_pos  # Start selection
            self.selection_end = None  # Reset end position
            self.dragging = True  # Start dragging
            self.adjust_scroll()
            self.update()

    def mouseMoveEvent(self, event):
        """Handles mouse dragging for text selection."""
        if self.dragging:
            self.selection_end = self.get_cursor_position_from_x(event.x())
            self.cursor_pos = self.selection_end
            self.adjust_scroll()
            self.update()

    def mouseReleaseEvent(self, event):
        """Stops selection when the mouse is released."""
        self.dragging = False
        if self.selection_end is None or self.selection_end == self.selection_start:
            self.selection_end = self.selection_start = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_scroll()

    def paintEvent(self, event):
        """Handles drawing the text input field, cursor, and selection."""
        background_color = self.palette().color(self.backgroundRole())

        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.fillRect(self.rect(), background_color)
        self.paint_text(painter)

    def paint_text(self, painter: QPainter):
        painter.setFont(self.font())

        # Calculate text width and alignment
        font_metrics = painter.fontMetrics()
        text_x = self.padding - self.scroll_offset
        text_y = font_metrics.height() - 2
        cursor_y1 = 0
        cursor_y2 = self.height()
        foreground_color = self.palette().color(self.foregroundRole())

        # Draw selection background if any
        if self.selection_start is not None and self.selection_end is not None:
            start, end = sorted([self.selection_start, self.selection_end])
            start_x = text_x + font_metrics.horizontalAdvance(self.text[:start])
            end_x = text_x + font_metrics.horizontalAdvance(self.text[:end])
            painter.fillRect(start_x, cursor_y1, end_x - start_x, cursor_y2 - cursor_y1,
                             QColor(173, 216, 230))  # Light blue

        # Draw text
        for token_type, token in tokenize(self.text):
            painter.save()

            if not painter.pen() == Qt.NoPen:
                pass

            if token_type == "NUMBER":
                painter.setPen(Colors.number)
            elif token_type in ["SQSTRING", "DQSTRING"]:
                painter.setPen(Colors.string)
            elif token_type == "IDENTIFIER":
                if token in self.scope:
                    painter.setPen(Colors.variable)
                elif token in table:
                    painter.setPen(Colors.builtin)
                else:
                    painter.setPen(foreground_color)
                    draw_error_line(painter, text_x, text_y + 2, font_metrics.horizontalAdvance(token))
            else:
                painter.setPen(foreground_color)

            painter.drawText(text_x, text_y, token)

            text_x += font_metrics.horizontalAdvance(token)
            painter.restore()

        if self.error:
            draw_error_line(painter, self.padding - self.scroll_offset, text_y + 2, text_x)

        # Draw cursor
        if self.cursor_visible and self.selection_start is None:
            cursor_x = self.padding - self.scroll_offset + text_index_to_x(self.text, self.cursor_pos, font_metrics)
            painter.setPen(foreground_color)
            painter.drawLine(cursor_x, cursor_y1, cursor_x, cursor_y2)


class CompleterModel(QAbstractTableModel):
    def __init__(self, data: dict, font: QFont, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame.from_dict(data, orient="index")

        self._headers = ["Name", "Amount", "Type"]
        self.font = font

    def rowCount(self, parent=QModelIndex()):
        return len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self.df.iloc[index.row(), index.column()]
            if index.column() == 1:
                return f"= {self.df.iloc[index.row()]['amount']}"
            if index.column() == 2:
                if self.df.iloc[index.row()]['param_type'] == "project":
                    return "Project Parameter"
                if self.df.iloc[index.row()]['param_type'] == "database":
                    return "Database Parameter"
                if self.df.iloc[index.row()]['param_type'] == "activity":
                    return "Activity Parameter"


        if role == Qt.EditRole:
            return self.df.iloc[index.row(), index.column()]

        if role == Qt.FontRole:
            if index.column() == 0:
                return self.font
            if index.column() == 1:
                font = QFont()
                font.setItalic(True)
                return font
            if index.column() == 2:
                font = QFont()
                font.setPointSize(font.pointSize() - 2)
                return font

        if role == Qt.ForegroundRole and index.column() == 0:
            return Colors.variable

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        return None


class CompleterView(QTableView):
    def __init__(self):
        super().__init__(showGrid=False)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setSizeAdjustPolicy(self.SizeAdjustPolicy.AdjustToContents)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def setModel(self, model):
        super().setModel(model)
        self.resize_on_reset()
        model.modelReset.connect(self.resize_on_reset)

    def resize_on_reset(self):
        self.resizeColumnsToContents()
        for i in range(self.model().rowCount()):
            self.setRowHeight(i, 20)
        self.setFixedWidth(self.sizeHint().width())

def draw_error_line(painter, x, y, w):
    painter.save()
    path = QPainterPath()

    # Define squiggly wave parameters
    amplitude = 2  # Height of the wave
    frequency = 4  # Number of waves across the width

    path.moveTo(x, y)

    for i in range(w // frequency):
        path.lineTo(x + frequency // 2, y - amplitude)
        path.lineTo(x + frequency, y)
        x += frequency

    # Set the error line pen (red squiggly line)
    pen = QPen(Qt.red)
    pen.setWidth(1)
    painter.setPen(pen)

    # Draw the squiggly line
    painter.drawPath(path)
    painter.restore()


def text_index_to_x(text, index, fm: QFontMetrics):
    x = 0
    for token in re.findall(pattern, text):
        if index > len(token):
            x += fm.horizontalAdvance(token)
            index -= len(token)
            continue
        x += fm.horizontalAdvance(token[:index])
        break
    return x


def is_valid_number(string):
    try:
        float(string)  # float will work for both integers and floats
        return True
    except ValueError:
        return False

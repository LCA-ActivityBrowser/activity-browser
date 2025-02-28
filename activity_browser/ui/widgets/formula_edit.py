import sys
import re

from asteval import make_symbol_table

from qtpy.QtWidgets import QApplication, QWidget
from qtpy.QtGui import QPainter, QColor, QFontMetrics, QFontDatabase, QPainterPath, QPen
from qtpy.QtCore import QTimer, Qt

from activity_browser.static import fonts

QFontDatabase.addApplicationFont(fonts.__path__[0] + "/mono.ttf")

accepted_chars = ["+", "-", "*", "/", "^", "(", ")", "[", "]", " "]
pattern = r"\b[a-zA-Z_]\w*\b|[\d.]+|[+\-*/^()\[\]]| +"
table = make_symbol_table()

parameters = {
    "db_parameter_1": None,
    "activity_parameter_1": None,
}


class Colors:
    builtin = QColor("#a626a4")
    number = QColor("#986801")
    variable = QColor("#4078f2")


class ABFormulaEdit(QWidget):
    def __init__(self, parent=None, scope=None, text=None):
        super().__init__(parent)
        self.scope = scope or {}
        self.text = text or ""  # Stores user input
        self.cursor_pos = 0  # Cursor position in the text
        self.selection_start = None  # Selection start index
        self.selection_end = None  # Selection end index
        self.cursor_visible = False  # Blinking cursor state
        self.scroll_offset = 0  # Scroll position for long text
        self.padding = 5  # Left padding for text inside the box
        self.dragging = False  # Track if mouse is dragging

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.toggle_cursor)
        self.timer.start(500)  # Blink cursor every 500ms

        # self.setFixedHeight(2 * self.fontMetrics().height())

        font = self.font()
        font.setFamily("JetBrains Mono")
        font.setPointSize(10)
        self.setFont(font)

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
                self.cursor_pos -= 1
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
        elif event.text():
            if self.selection_start is not None:
                self.delete_selected_text()
            new_text = "".join(re.findall(pattern, event.text()))
            new_text = self.text[:self.cursor_pos] + new_text + self.text[self.cursor_pos:]
            if re.findall(pattern, self.text) == re.findall(pattern, new_text):
                return
            self.text = new_text
            self.cursor_pos += 1

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
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.fillRect(self.rect(), QColor("White"))
        self.paint_text(painter)

    def paint_text(self, painter: QPainter):
        painter.setFont(self.font())

        # Calculate text width and alignment
        font_metrics = painter.fontMetrics()
        text_x = self.padding - self.scroll_offset
        text_y = font_metrics.height()
        cursor_y1 = 0
        cursor_y2 = self.height()

        # Draw selection background if any
        if self.selection_start is not None and self.selection_end is not None:
            start, end = sorted([self.selection_start, self.selection_end])
            start_x = text_x + font_metrics.horizontalAdvance(self.text[:start])
            end_x = text_x + font_metrics.horizontalAdvance(self.text[:end])
            painter.fillRect(start_x, cursor_y1, end_x - start_x, cursor_y2 - cursor_y1, QColor(173, 216, 230))  # Light blue

        # Draw text
        for token in re.findall(pattern, self.text):
            painter.save()

            if not painter.pen() == Qt.NoPen:
                pass
            elif is_valid_number(token):
                painter.setPen(Colors.number)
            elif token in table:
                painter.setPen(Colors.builtin)
            elif token in self.scope:
                painter.setPen(Colors.variable)
            elif token in accepted_chars:
                painter.setPen(QColor("Black"))
            else:
                painter.setPen(QColor("Black"))
                draw_error_line(painter, text_x, text_y + 2, font_metrics.horizontalAdvance(token))

            painter.drawText(text_x, text_y, token)

            text_x += font_metrics.horizontalAdvance(token)
            painter.restore()

        # Draw cursor
        if self.cursor_visible and self.selection_start is None:
            cursor_x = self.padding - self.scroll_offset + text_index_to_x(self.text, self.cursor_pos, font_metrics)
            painter.setPen(QColor("Black"))
            painter.drawLine(cursor_x, cursor_y1, cursor_x, cursor_y2)


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


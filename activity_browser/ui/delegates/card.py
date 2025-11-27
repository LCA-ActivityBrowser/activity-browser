from typing import TypedDict

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import Qt


class CardData(TypedDict):
    title: str
    subtitle: str | None
    categories: list[str] | None
    icon: QtGui.QIcon | None


class CardDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate for rendering card-like items with title, subtitle, categories and background icon."""

    PADDING = 8
    MARGIN = 2
    TITLE_LINES = 2
    ICON_OPACITY = 0.1

    def sizeHint(self, option, index):
        if index.data() is None:
            return super().sizeHint(option, index)

        card_data = index.data()

        # Calculate text heights
        fm = option.fontMetrics
        line_height = fm.height()

        # Title (2 lines, larger font)
        title_height = int(line_height * 1.3 * self.TITLE_LINES) + 5  # 1.3x for larger font

        # Subtitle
        subtitle_height = int(line_height * 0.9)  # 0.9x for smaller font

        # Categories
        categories_height = 7 + int(line_height * 0.8)

        # Total height with padding
        total_height = (self.PADDING * 2 + self.MARGIN * 2 +
                       title_height + subtitle_height + categories_height)

        return QtCore.QSize(option.rect.width(), max(total_height, 40))

    def paint(self, painter, option: QtWidgets.QStyleOptionViewItem, index):
        if index.data() is None:
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        card_data = index.data()
        is_selected = option.state & QtWidgets.QStyle.StateFlag.State_Selected

        # Draw background and border
        rect = option.rect.adjusted(self.MARGIN, self.MARGIN, -self.MARGIN, -self.MARGIN)

        # Background
        painter.fillRect(rect, option.palette.base())

        # Border
        border_color = option.palette.highlight() if is_selected else option.palette.mid()
        painter.setPen(QtGui.QPen(border_color, 1))
        painter.drawRoundedRect(rect, 3, 3)

        # Draw background icon
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        icon_size = 0
        if icon and not icon.isNull():
            painter.setOpacity(self.ICON_OPACITY)
            icon_size = int(rect.height() * 0.8)
            icon_x = rect.right() - icon_size - 10
            icon_y = rect.top() + (rect.height() - icon_size) // 2
            icon.paint(painter, icon_x, icon_y, icon_size, icon_size)
            painter.setOpacity(1.0)

        # Setup text area
        text_rect = rect.adjusted(self.PADDING, self.PADDING, -self.PADDING, -self.PADDING)
        y = text_rect.top()

        # Draw title (bold, larger, 2 lines)
        title = card_data.get('title', '')
        title_font = option.font
        title_font.setPointSize(int(option.font.pointSize() * 1.3))
        title_font.setWeight(QtGui.QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(option.palette.text().color())

        title_fm = QtGui.QFontMetrics(title_font)
        title_height = 5 + title_fm.height() * self.TITLE_LINES
        title_rect = QtCore.QRect(text_rect.left(), y, text_rect.width(), title_height)

        # Elide title text if it's too long for 2 lines
        title_text = str(title)
        max_width = title_rect.width()

        # Split into words and fit within 2 lines with eliding
        words = title_text.split()
        line1_words = []
        line2_words = []
        current_line = line1_words

        for word in words:
            test_text = " ".join(current_line + [word])
            if title_fm.horizontalAdvance(test_text) <= max_width:
                current_line.append(word)
            elif current_line is line1_words and len(line2_words) == 0:
                # Move to second line
                current_line = line2_words
                current_line.append(word)
            else:
                # Need to elide
                break

        line1_text = " ".join(line1_words)
        line2_text = " ".join(line2_words)

        # If there are remaining words, elide the second line
        if len(line1_words) + len(line2_words) < len(words):
            line2_text = title_fm.elidedText(title_text if not line1_text else " ".join(words[len(line1_words):]),
                                            Qt.TextElideMode.ElideRight, max_width)

        # Draw title lines
        painter.drawText(title_rect.left(), title_rect.top() + title_fm.ascent(), line1_text)
        if line2_text:
            painter.drawText(title_rect.left(), title_rect.top() + title_fm.ascent() + title_fm.height(), line2_text)

        y += title_height

        # Draw subtitle (smaller)
        subtitle = card_data.get('subtitle', '')
        if subtitle:
            subtitle_font: QtGui.QFont = option.font
            subtitle_font.setPointSize(int(option.font.pointSize() * 0.9))
            subtitle_font.setWeight(QtGui.QFont.Weight.Light)
            painter.setFont(subtitle_font)

            subtitle_fm = QtGui.QFontMetrics(subtitle_font)
            subtitle_height = subtitle_fm.height()
            subtitle_rect = QtCore.QRect(text_rect.left(), y, text_rect.width(), subtitle_height)

            # Elide subtitle if too long
            subtitle_text = subtitle_fm.elidedText(str(subtitle), Qt.TextElideMode.ElideRight, subtitle_rect.width())
            painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, subtitle_text)
            y += subtitle_height

        # Draw categories (pipe separated, bottom right)
        categories = card_data.get('categories', [])
        if categories and isinstance(categories, (list, tuple)):
            categories_text = "  |  ".join(str(cat) for cat in categories)
            categories_font = option.font
            categories_font.setPointSize(int(option.font.pointSize() * 0.8))
            painter.setFont(categories_font)

            categories_fm = QtGui.QFontMetrics(categories_font)
            categories_height = categories_fm.height()
            categories_rect = QtCore.QRect(text_rect.left(), text_rect.bottom() - categories_height,
                                          text_rect.width(), categories_height)

            # Elide categories if too long
            categories_text_elided = categories_fm.elidedText(categories_text, Qt.TextElideMode.ElideRight, categories_rect.width())
            painter.drawText(categories_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, categories_text_elided)

        painter.restore()



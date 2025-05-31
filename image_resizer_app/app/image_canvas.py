from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QWidget, QHBoxLayout
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPen, QMouseEvent, QFont
from PyQt6.QtCore import Qt, QRect, QPoint
import os
import random

class InlineEdit(QWidget):
    def __init__(self, axis, original, on_submit, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.axis = axis
        self.original = original
        self.on_submit = on_submit
        self.setStyleSheet("background-color: rgba(0, 0, 0, 180); border: 1px solid #555; border-radius: 5px;")
        self.input = QLineEdit(str(original))
        self.input.setStyleSheet("color: black; background-color: white; padding: 2px;")
        self.input.setFixedWidth(60)
        self.input.setFont(QFont("Arial", 9))

        self.confirm = QPushButton("✔")
        self.confirm.setFixedWidth(26)
        self.confirm.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.cancel = QPushButton("✖")
        self.cancel.setFixedWidth(26)
        self.cancel.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(6)
        layout.addWidget(self.input)
        layout.addWidget(self.confirm)
        layout.addWidget(self.cancel)

        self.confirm.clicked.connect(self.submit)
        self.cancel.clicked.connect(self.close)

    def submit(self):
        try:
            value = int(self.input.text())
        except ValueError:
            return
        self.on_submit(value, self.axis, self.original)
        self.close()

class ImageCanvas(QLabel):
    def __init__(self, parent=None, on_image_loaded=None, on_error=None, on_guides_updated=None):
        super().__init__(parent)
        self.setAcceptDrops(False)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setStyleSheet("border: 1px solid gray; background-color: white;")
        self.on_image_loaded = on_image_loaded
        self.on_error = on_error
        self.on_guides_updated = on_guides_updated
        self.pixmap_loaded = None
        self.scaled_pixmap = None
        self.vertical_lines = []
        self.horizontal_lines = []
        self.grid_includes = []
        self.show_grid = False
        self.ruler_width = 30
        self.ruler_height = 30
        self.inline_editor = None
        self.delete_button_size = 14
        self.label_hitbox_size = 30

    def pixmap(self):
        return self.scaled_pixmap

    def is_valid_image(self, path):
        return os.path.splitext(path)[1].lower() in [".jpg", ".jpeg", ".png"]

    def load_image(self, file_path):
        self.pixmap_loaded = QPixmap(file_path)
        self.update_scaled_pixmap()
        self.vertical_lines.clear()
        self.horizontal_lines.clear()
        self.grid_includes.clear()
        if self.on_image_loaded:
            self.on_image_loaded(file_path)
        self.update()

    def update_scaled_pixmap(self):
        if self.pixmap_loaded:
            available_width = self.width() - self.ruler_width
            available_height = self.height() - self.ruler_height
            self.scaled_pixmap = self.pixmap_loaded.scaled(
                available_width,
                available_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

    def resizeEvent(self, event):
        self.update_scaled_pixmap()
        super().resizeEvent(event)

    def get_vertical_guides(self):
        return self.vertical_lines

    def get_horizontal_guides(self):
        return self.horizontal_lines

    def get_active_crop_flags(self):
        return self.grid_includes

    def toggle_grid(self, show):
        self.show_grid = show
        self.update()

    def is_line_valid(self, value, lines):
        if len(lines) >= 24:
            return False
        return all(abs(value - l) >= 24 for l in lines)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.scaled_pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Arial", 7))

        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, self.ruler_height, QColor("#f0f0f0"))
        painter.fillRect(0, 0, self.ruler_width, height, QColor("#f0f0f0"))

        painter.drawPixmap(self.ruler_width, self.ruler_height, self.scaled_pixmap)

        # ruler ticks
        for x in range(self.ruler_width, width, 50):
            painter.setPen(QColor("gray"))
            painter.drawLine(x, 0, x, 10)
            painter.drawText(x + 2, 20, str(x - self.ruler_width))
        for y in range(self.ruler_height, height, 50):
            painter.setPen(QColor("gray"))
            painter.drawLine(0, y, 10, y)
            painter.drawText(12, y + 2, str(y - self.ruler_height))

        painter.setPen(QPen(QColor("green"), 1))
        for x in self.vertical_lines:
            px = x + self.ruler_width
            painter.drawLine(px, self.ruler_height, px, height)
            painter.drawText(px + 2, self.ruler_height + 12, str(x))
            self.draw_delete_button(painter, px - 7, self.ruler_height)

        painter.setPen(QPen(QColor("blue"), 1))
        for y in self.horizontal_lines:
            py = y + self.ruler_height
            painter.drawLine(self.ruler_width, py, width, py)
            painter.drawText(self.ruler_width + 2, py - 2, str(y))
            self.draw_delete_button(painter, self.ruler_width, py - 7)

        if self.show_grid:
            painter.setPen(Qt.PenStyle.NoPen)
            pw, ph = self.scaled_pixmap.width(), self.scaled_pixmap.height()
            x_lines = [0] + sorted(self.vertical_lines) + [pw]
            y_lines = [0] + sorted(self.horizontal_lines) + [ph]
            total = (len(x_lines) - 1) * (len(y_lines) - 1)
            while len(self.grid_includes) < total:
                self.grid_includes.append(True)

            idx = 0
            for i in range(len(x_lines) - 1):
                for j in range(len(y_lines) - 1):
                    x1 = x_lines[i] + self.ruler_width
                    x2 = x_lines[i + 1] + self.ruler_width
                    y1 = y_lines[j] + self.ruler_height
                    y2 = y_lines[j + 1] + self.ruler_height
                    color = QColor(120, 120, 120, 100) if not self.grid_includes[idx] else QColor(50, 200, 100, 120)
                    painter.setBrush(color)
                    painter.drawRect(QRect(x1, y1, x2 - x1, y2 - y1))

                    box = QRect(x2 - 16, y2 - 16, 12, 12)
                    painter.setPen(QColor("black"))
                    painter.setBrush(QColor("white"))
                    painter.drawRect(box)
                    if self.grid_includes[idx]:
                        painter.drawLine(box.topLeft() + QPoint(3, 6), box.bottomRight() - QPoint(3, 3))
                        painter.drawLine(box.bottomLeft() + QPoint(3, -3), box.topRight() - QPoint(3, -6))
                    idx += 1

    def draw_delete_button(self, painter, x, y):
        rect = QRect(x, y, self.delete_button_size, self.delete_button_size)
        painter.setBrush(QColor("red"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)
        painter.setPen(QColor("white"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "×")

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if not self.scaled_pixmap:
            return
        pw, ph = self.scaled_pixmap.width(), self.scaled_pixmap.height()
        x_lines = [0] + sorted(self.vertical_lines) + [pw]
        y_lines = [0] + sorted(self.horizontal_lines) + [ph]
        idx = 0
        for i in range(len(x_lines) - 1):
            for j in range(len(y_lines) - 1):
                x2 = x_lines[i + 1] + self.ruler_width
                y2 = y_lines[j + 1] + self.ruler_height
                box = QRect(x2 - 16, y2 - 16, 12, 12)
                if box.contains(pos):
                    self.grid_includes[idx] = not self.grid_includes[idx]
                    self.update()
                    return
                idx += 1

        for vx in self.vertical_lines:
            px = vx + self.ruler_width
            if QRect(px - 7, self.ruler_height, 14, 14).contains(pos):
                self.vertical_lines.remove(vx)
                if self.on_guides_updated:
                    self.on_guides_updated()
                self.update()
                return
            if QRect(px + 2, self.ruler_height + 2, 30, 30).contains(pos):
                self.show_inline_editor(vx, "vertical")
                return
        for hy in self.horizontal_lines:
            py = hy + self.ruler_height
            if QRect(self.ruler_width, py - 7, 14, 14).contains(pos):
                self.horizontal_lines.remove(hy)
                if self.on_guides_updated:
                    self.on_guides_updated()
                self.update()
                return
            if QRect(self.ruler_width + 2, py - 12, 30, 30).contains(pos):
                self.show_inline_editor(hy, "horizontal")
                return

        if pos.y() < self.ruler_height:
            x = pos.x() - self.ruler_width
            if self.is_line_valid(x, self.vertical_lines):
                self.vertical_lines.append(x)
                if self.on_guides_updated:
                    self.on_guides_updated()
        elif pos.x() < self.ruler_width:
            y = pos.y() - self.ruler_height
            if self.is_line_valid(y, self.horizontal_lines):
                self.horizontal_lines.append(y)
                if self.on_guides_updated:
                    self.on_guides_updated()
        self.update()

    def show_inline_editor(self, original_value, axis):
        if self.inline_editor:
            self.inline_editor.setParent(None)
            self.inline_editor.deleteLater()
        editor = InlineEdit(axis, original_value, self.apply_line_edit, self)
        if axis == "vertical":
            editor.move(original_value + self.ruler_width + 10, self.ruler_height + 20)
        else:
            editor.move(self.ruler_width + 10, original_value + self.ruler_height + 10)
        editor.show()
        self.inline_editor = editor

    def apply_line_edit(self, new_value, axis, original_value):
        lines = self.vertical_lines if axis == "vertical" else self.horizontal_lines
        if original_value not in lines:
            return
        idx = lines.index(original_value)
        if all(abs(new_value - other) >= 24 for i, other in enumerate(lines) if i != idx):
            lines[idx] = new_value
            if self.on_error: self.on_error("")
            if self.on_guides_updated: self.on_guides_updated()
        else:
            if self.on_error: self.on_error(f"{axis.title()} lines must be at least 24px apart.")
        self.inline_editor = None
        self.update()

    def clear_canvas(self):
        self.pixmap_loaded = None
        self.scaled_pixmap = None
        self.setPixmap(QPixmap())
        self.vertical_lines.clear()
        self.horizontal_lines.clear()
        self.grid_includes.clear()
        self.update()
        if self.on_image_loaded:
            self.on_image_loaded(None)
"""
SONORA Studio - Real-time Rolling Waveform Renderer (Optimized)
High-performance oscilloscope using pre-allocated numpy buffers and batch line drawing.
"""

import numpy as np
from PySide6.QtCore import Qt, QLine
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget
from app.config import config


class LiveWaveformWidget(QWidget):
    """High-performance real-time rolling audio waveform oscilloscope."""

    def __init__(self, parent=None, buffer_points: int = 400):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.buffer_points = buffer_points

        # Fast contiguous numpy ring arrays
        self.max_vals = np.zeros(buffer_points, dtype=np.float32)
        self.min_vals = np.zeros(buffer_points, dtype=np.float32)

        self.accent_color = QColor(config.get("accent_color", "#00E5A3"))
        self.bg_color = QColor("#12141B")
        self.grid_color = QColor("#1E212D")

    def update_accent(self, color_hex: str):
        self.accent_color = QColor(color_hex)
        self.update()

    def add_chunk(self, chunk: np.ndarray):
        """Consume real audio chunk from recording engine callback."""
        if len(chunk) == 0:
            return

        # Vectorized roll & append
        l_data = chunk[:, 0] if chunk.ndim > 1 else chunk

        l_mx = float(np.max(l_data))
        l_mn = float(np.min(l_data))

        self.max_vals[:-1] = self.max_vals[1:]
        self.max_vals[-1] = l_mx
        self.min_vals[:-1] = self.min_vals[1:]
        self.min_vals[-1] = l_mn

        self.update()

    def clear(self):
        """Reset waveform display."""
        self.max_vals.fill(0.0)
        self.min_vals.fill(0.0)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)  # Fast pixel crispness

        w = self.width()
        h = self.height()
        mid_y = h / 2.0

        # Background
        painter.fillRect(0, 0, w, h, self.bg_color)

        # Draw subtle grid lines
        painter.setPen(QPen(self.grid_color, 1, Qt.DashLine))
        painter.drawLine(0, int(h * 0.25), w, int(h * 0.25))
        painter.drawLine(0, int(h * 0.75), w, int(h * 0.75))

        # Center zero line
        painter.setPen(QPen(QColor("#2B2F3E"), 1))
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        num_points = self.buffer_points
        dx = w / float(num_points)
        scale = mid_y * 0.92

        y1_arr = (mid_y - self.max_vals * scale).astype(int)
        y2_arr = (mid_y - self.min_vals * scale).astype(int)

        lines = []
        for i in range(num_points):
            x = int(i * dx)
            y1 = y1_arr[i]
            y2 = y2_arr[i]
            if y1 == y2:
                y1 -= 1
                y2 += 1
            lines.append(QLine(x, y1, x, y2))

        # Gradient for waveform
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, self.accent_color.lighter(130))
        gradient.setColorAt(0.5, self.accent_color)
        gradient.setColorAt(1.0, self.accent_color.darker(130))

        painter.setPen(QPen(gradient, 1))
        painter.drawLines(lines)

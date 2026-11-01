"""
SONORA Studio - Professional Stereo Level Meter (VU / Peak / RMS)
Real-time hardware level visualization with peak-hold and clipping detection.
"""

import time
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QFont
from PySide6.QtWidgets import QWidget


class LevelMeter(QWidget):
    """Dual-channel VU / Peak / RMS audio level meter with hardware clipping warning."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(55)
        self.setMinimumHeight(180)

        # Levels in linear 0.0 to 1.0
        self.peak_l = 0.0
        self.peak_r = 0.0
        self.rms_l = 0.0
        self.rms_r = 0.0

        # Peak hold values
        self.hold_l = 0.0
        self.hold_r = 0.0
        self.hold_decay_time = time.time()

        # Clipping state
        self.is_clipping = False
        self.clip_time = 0.0

        # Smooth update timer for meter ballistics
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._ballistics_tick)
        self.timer.start(25)  # 40 fps

    def update_levels(self, peak_l: float, peak_r: float, rms_l: float, rms_r: float, is_clipping: bool):
        """Called from audio engine."""
        self.peak_l = max(0.0, min(peak_l, 1.0))
        self.peak_r = max(0.0, min(peak_r, 1.0))
        self.rms_l = max(0.0, min(rms_l, 1.0))
        self.rms_r = max(0.0, min(rms_r, 1.0))

        if self.peak_l > self.hold_l:
            self.hold_l = self.peak_l
        if self.peak_r > self.hold_r:
            self.hold_r = self.peak_r

        if is_clipping:
            self.is_clipping = True
            self.clip_time = time.time()

        self.update()

    def _ballistics_tick(self):
        """Simulate peak decay ballistics."""
        decay = 0.02
        if self.hold_l > 0.0:
            self.hold_l = max(0.0, self.hold_l - decay)
        if self.hold_r > 0.0:
            self.hold_r = max(0.0, self.hold_r - decay)

        # Clear clip LED after 1.5s
        if self.is_clipping and (time.time() - self.clip_time > 1.5):
            self.is_clipping = False

        self.update()

    @staticmethod
    def _linear_to_y(lin_val: float, height: int) -> int:
        """Convert linear amplitude 0.0-1.0 to decibel Y coordinate."""
        if lin_val <= 0.001:
            db = -60.0
        else:
            db = 20.0 * np.log10(lin_val)
        # Map -60 dB .. 0 dB to height .. 0
        norm = (db + 60.0) / 60.0
        norm = max(0.0, min(norm, 1.0))
        return int(height * (1.0 - norm))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Margins
        top = 22  # space for clip indicator
        bottom = h - 6
        meter_h = bottom - top

        bar_w = 12
        spacing = 4
        left_x = (w - (bar_w * 2 + spacing + 20)) // 2 + 18
        right_x = left_x + bar_w + spacing

        # Background track
        painter.fillRect(left_x, top, bar_w, meter_h, QColor("#14161D"))
        painter.fillRect(right_x, top, bar_w, meter_h, QColor("#14161D"))

        # Gradients for active levels
        grad = QLinearGradient(0, top, 0, bottom)
        grad.setColorAt(0.0, QColor("#EF4444"))   # 0 dB Red
        grad.setColorAt(0.15, QColor("#F59E0B"))  # -6 dB Amber
        grad.setColorAt(0.4, QColor("#10B981"))   # -18 dB Green
        grad.setColorAt(1.0, QColor("#00E5A3"))   # -60 dB Teal

        # Draw Left Bar
        y_peak_l = top + self._linear_to_y(self.peak_l, meter_h)
        bar_h_l = bottom - y_peak_l
        if bar_h_l > 0:
            painter.fillRect(left_x, y_peak_l, bar_w, bar_h_l, grad)

        # Draw Right Bar
        y_peak_r = top + self._linear_to_y(self.peak_r, meter_h)
        bar_h_r = bottom - y_peak_r
        if bar_h_r > 0:
            painter.fillRect(right_x, y_peak_r, bar_w, bar_h_r, grad)

        # Peak Hold markers
        painter.setPen(QColor("#FFFFFF"))
        y_hold_l = top + self._linear_to_y(self.hold_l, meter_h)
        painter.drawLine(left_x, y_hold_l, left_x + bar_w, y_hold_l)

        y_hold_r = top + self._linear_to_y(self.hold_r, meter_h)
        painter.drawLine(right_x, y_hold_r, right_x + bar_w, y_hold_r)

        # Clipping LED
        clip_color = QColor("#EF4444") if self.is_clipping else QColor("#374151")
        painter.setBrush(clip_color)
        painter.setPen(Qt.NoPen)
        clip_w = bar_w * 2 + spacing
        painter.drawRoundedRect(left_x, 4, clip_w, 12, 3, 3)

        painter.setPen(QColor("#FFFFFF" if self.is_clipping else "#9CA3AF"))
        font = QFont("Segoe UI", 8, QFont.Bold)
        painter.setFont(font)
        painter.drawText(left_x, 4, clip_w, 12, Qt.AlignCenter, "CLIP")

        # Decibel Tick marks on the left
        painter.setPen(QColor("#6B7280"))
        font_ticks = QFont("Segoe UI", 7)
        painter.setFont(font_ticks)

        db_marks = [0, -6, -12, -24, -36, -48]
        for db in db_marks:
            lin = 10.0 ** (db / 20.0)
            y_tick = top + self._linear_to_y(lin, meter_h)
            painter.drawText(2, y_tick + 4, f"{abs(db):2d}")
            painter.drawLine(left_x - 3, y_tick, left_x - 1, y_tick)

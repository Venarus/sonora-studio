"""
SONORA Studio - Professional Interactive Timeline Waveform (High-Performance & Keyboard-Enabled)
Multi-channel waveform editor with vectorized NumPy decimation, QPixmap caching,
zoom, pan, selection, playhead, time-ruler, and Backspace/Delete key editing.
"""

from typing import Optional, Tuple
import numpy as np
from PySide6.QtCore import Qt, Signal, QRectF, QLine, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QKeyEvent, QPolygonF
from PySide6.QtWidgets import QWidget
from app.config import config


class TimelineWaveformWidget(QWidget):
    """High-performance vectorized waveform editor timeline supporting zoom, selection, playhead, and keyboard."""

    cursor_moved = Signal(float)  # seconds
    selection_changed = Signal(float, float)  # start_sec, end_sec
    delete_requested = Signal()   # Triggered by Backspace or Delete key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setFocusPolicy(Qt.StrongFocus)  # Capture keyboard events
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

        # Audio data: shape (samples, channels)
        self._audio: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._total_samples: int = 0

        # Viewport boundaries (in sample indices)
        self.view_start = 0
        self.view_end = 0

        # Cursor and Selection (in seconds)
        self.playhead_sec = 0.0
        self.selection_start_sec: Optional[float] = None
        self.selection_end_sec: Optional[float] = None

        # Interaction state
        self._is_selecting = False
        self._drag_start_x = 0
        self._is_panning = False
        self._pan_start_x = 0
        self._pan_start_view_start = 0

        self.accent_color = QColor(config.get("accent_color", "#00E5A3"))
        self.bg_color = QColor("#111319")
        self.waveform_color = QColor("#00E5A3")
        self.ruler_height = 24

        # Waveform Static Background Cache (QPixmap) for ultra-fast rendering
        self._wave_cache: Optional[QPixmap] = None
        self._cache_dirty = True
        self._last_width = 0
        self._last_height = 0

    @property
    def duration_seconds(self) -> float:
        if self._total_samples > 0 and self._sample_rate > 0:
            return self._total_samples / self._sample_rate
        return 0.0

    def set_audio_data(self, audio: Optional[np.ndarray], sr: int):
        """Load new audio data into view."""
        self._sample_rate = sr
        if audio is not None and len(audio) > 0:
            self._audio = audio if audio.ndim == 2 else audio[:, np.newaxis]
            self._total_samples = len(self._audio)
            self.view_start = 0
            self.view_end = self._total_samples
        else:
            self._audio = None
            self._total_samples = 0
            self.view_start = 0
            self.view_end = 0

        self.playhead_sec = 0.0
        self.selection_start_sec = None
        self.selection_end_sec = None
        self._cache_dirty = True
        self.update()

    def set_playhead_position(self, pos_sec: float):
        """Update current playback position."""
        self.playhead_sec = max(0.0, min(pos_sec, self.duration_seconds))
        if self.duration_seconds > 0 and self.view_end > self.view_start:
            view_start_sec = self.view_start / self._sample_rate
            view_end_sec = self.view_end / self._sample_rate
            if self.playhead_sec > view_end_sec:
                span = self.view_end - self.view_start
                self.view_start = min(int(self.playhead_sec * self._sample_rate), self._total_samples - span)
                self.view_end = self.view_start + span
                self._cache_dirty = True
        self.update()

    def set_selection(self, start_sec: Optional[float], end_sec: Optional[float]):
        """Programmatically set selection."""
        self.selection_start_sec = start_sec
        self.selection_end_sec = end_sec
        self.update()

    def zoom(self, factor: float, center_norm: float = 0.5):
        """Zoom in (<1.0) or out (>1.0) around relative position."""
        if self._total_samples <= 0:
            return
        curr_span = self.view_end - self.view_start
        new_span = max(int(curr_span * factor), int(self._sample_rate * 0.05))
        new_span = min(new_span, self._total_samples)

        center_sample = self.view_start + int(curr_span * center_norm)
        self.view_start = max(0, center_sample - int(new_span * center_norm))
        self.view_end = min(self._total_samples, self.view_start + new_span)
        if self.view_end - self.view_start < new_span:
            self.view_start = max(0, self.view_end - new_span)
        self._cache_dirty = True
        self.update()

    def zoom_in(self):
        self.zoom(0.7)

    def zoom_out(self):
        self.zoom(1.4)

    def zoom_fit(self):
        self.view_start = 0
        self.view_end = self._total_samples
        self._cache_dirty = True
        self.update()

    def _x_to_time(self, x: float) -> float:
        w = max(self.width(), 1)
        norm = max(0.0, min(x / float(w), 1.0))
        span_samples = self.view_end - self.view_start
        sample = self.view_start + norm * span_samples
        return sample / float(self._sample_rate) if self._sample_rate > 0 else 0.0

    def _time_to_x(self, t_sec: float) -> float:
        if self._sample_rate <= 0:
            return 0.0
        sample = t_sec * self._sample_rate
        span_samples = max(self.view_end - self.view_start, 1)
        norm = (sample - self.view_start) / float(span_samples)
        return norm * self.width()

    # -------------------------------------------------------------
    # KEYBOARD INTERACTION (Backspace / Delete to remove selection)
    # -------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if self.selection_start_sec is not None and self.selection_end_sec is not None:
                self.delete_requested.emit()
                event.accept()
                return
        super().keyPressEvent(event)

    # -------------------------------------------------------------
    # MOUSE INTERACTION
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        self.setFocus()
        if self._audio is None or self._total_samples == 0:
            return

        if event.button() == Qt.LeftButton:
            t = self._x_to_time(event.position().x())
            self._is_selecting = True
            self._drag_start_x = event.position().x()
            self.selection_start_sec = t
            self.selection_end_sec = t
            self.playhead_sec = t
            self.cursor_moved.emit(t)
            self.update()

        elif event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start_x = event.position().x()
            self._pan_start_view_start = self.view_start

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            t = self._x_to_time(event.position().x())
            self.selection_end_sec = t
            s = min(self.selection_start_sec, self.selection_end_sec)
            e = max(self.selection_start_sec, self.selection_end_sec)
            self.selection_changed.emit(s, e)
            self.update()

        elif self._is_panning:
            dx = event.position().x() - self._pan_start_x
            span = self.view_end - self.view_start
            sample_delta = int((dx / float(self.width())) * span)
            new_start = max(0, min(self._total_samples - span, self._pan_start_view_start - sample_delta))
            self.view_start = new_start
            self.view_end = new_start + span
            self._cache_dirty = True
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_selecting:
            self._is_selecting = False
            if self.selection_start_sec is not None and self.selection_end_sec is not None:
                if abs(event.position().x() - self._drag_start_x) < 4:
                    self.selection_start_sec = None
                    self.selection_end_sec = None
                else:
                    s = min(self.selection_start_sec, self.selection_end_sec)
                    e = max(self.selection_start_sec, self.selection_end_sec)
                    self.selection_start_sec = s
                    self.selection_end_sec = e
                    self.selection_changed.emit(s, e)
            self.update()

        elif event.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False

    def wheelEvent(self, event):
        if self._audio is None or self._total_samples == 0:
            return
        delta = event.angleDelta().y()
        norm_x = event.position().x() / float(max(self.width(), 1))
        if delta > 0:
            self.zoom(0.8, center_norm=norm_x)
        else:
            self.zoom(1.25, center_norm=norm_x)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cache_dirty = True

    # -------------------------------------------------------------
    # PAINTING
    # -------------------------------------------------------------
    def _rebuild_cache(self, w: int, h: int):
        pixmap = QPixmap(w, h)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(0, 0, w, h, self.bg_color)

        if self._audio is None or self._total_samples == 0:
            p.setPen(QColor("#6B7280"))
            p.setFont(QFont("Segoe UI", 12))
            p.drawText(0, 0, w, h, Qt.AlignCenter, "Kaydedilen veya yüklenen ses burada düzenlenmek üzere görüntülenecektir.")
            p.end()
            self._wave_cache = pixmap
            self._cache_dirty = False
            return

        self._paint_ruler(p, w)

        wave_top = self.ruler_height
        wave_h = h - wave_top
        channels = self._audio.shape[1]
        ch_h = wave_h / float(channels)

        span_samples = max(self.view_end - self.view_start, 1)
        visible_data = self._audio[self.view_start:self.view_end]

        step = max(1, span_samples // w)
        n_blocks = min(w, span_samples // step)

        p.setPen(QPen(self.waveform_color, 1))

        for ch in range(channels):
            ch_data = visible_data[:, ch]
            mid_y = wave_top + ch * ch_h + ch_h / 2.0

            p.setPen(QPen(QColor("#1E222D"), 1))
            p.drawLine(0, int(wave_top + ch * ch_h), w, int(wave_top + ch * ch_h))

            lbl = "Sol (L)" if ch == 0 and channels > 1 else ("Sağ (R)" if ch == 1 else "Mono")
            p.setPen(QColor("#4B5563"))
            p.setFont(QFont("Segoe UI", 8, QFont.Bold))
            p.drawText(6, int(wave_top + ch * ch_h + 14), lbl)

            if n_blocks > 0 and len(ch_data) >= n_blocks * step:
                truncated = ch_data[:n_blocks * step].reshape((n_blocks, step))
                maxs = np.max(truncated, axis=1)
                mins = np.min(truncated, axis=1)

                scale = ch_h * 0.44
                y1_arr = (mid_y - maxs * scale).astype(int)
                y2_arr = (mid_y - mins * scale).astype(int)

                lines = []
                for px in range(n_blocks):
                    y1 = y1_arr[px]
                    y2 = y2_arr[px]
                    if y1 == y2:
                        y1 -= 1
                        y2 += 1
                    lines.append(QLine(px, y1, px, y2))

                p.setPen(QPen(self.waveform_color, 1))
                p.drawLines(lines)

        p.end()
        self._wave_cache = pixmap
        self._cache_dirty = False

    def paintEvent(self, event):
        painter = QPainter(self)
        w = self.width()
        h = self.height()

        if self._cache_dirty or self._wave_cache is None or w != self._last_width or h != self._last_height:
            self._last_width = w
            self._last_height = h
            self._rebuild_cache(w, h)

        if self._wave_cache:
            painter.drawPixmap(0, 0, self._wave_cache)

        if self._audio is None or self._total_samples == 0:
            return

        wave_top = self.ruler_height
        wave_h = h - wave_top

        # Draw Selection Highlight
        if self.selection_start_sec is not None and self.selection_end_sec is not None:
            s_sec = min(self.selection_start_sec, self.selection_end_sec)
            e_sec = max(self.selection_start_sec, self.selection_end_sec)
            x_start = self._time_to_x(s_sec)
            x_end = self._time_to_x(e_sec)
            sel_w = max(1.0, x_end - x_start)

            sel_rect = QRectF(x_start, wave_top, sel_w, wave_h)
            painter.fillRect(sel_rect, QColor(0, 229, 163, 45))

            painter.setPen(QPen(QColor(0, 229, 163, 190), 1))
            painter.drawLine(int(x_start), wave_top, int(x_start), h)
            painter.drawLine(int(x_end), wave_top, int(x_end), h)

        # Draw Playhead Line
        px_cursor = self._time_to_x(self.playhead_sec)
        if 0 <= px_cursor <= w:
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.drawLine(int(px_cursor), 0, int(px_cursor), h)

            painter.setBrush(QColor("#FFFFFF"))
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(QPolygonF([
                QPointF(px_cursor - 5, 0),
                QPointF(px_cursor + 5, 0),
                QPointF(px_cursor, self.ruler_height - 6)
            ]))

    def _paint_ruler(self, painter: QPainter, width: int):
        painter.fillRect(0, 0, width, self.ruler_height, QColor("#181B24"))
        painter.setPen(QPen(QColor("#2B2F3D"), 1))
        painter.drawLine(0, self.ruler_height - 1, width, self.ruler_height - 1)

        span_sec = (self.view_end - self.view_start) / float(self._sample_rate)
        if span_sec <= 0:
            return

        if span_sec < 5:
            tick_step = 0.5
        elif span_sec < 20:
            tick_step = 1.0
        elif span_sec < 60:
            tick_step = 5.0
        elif span_sec < 300:
            tick_step = 15.0
        else:
            tick_step = 60.0

        start_t = self.view_start / float(self._sample_rate)
        first_tick = (int(start_t / tick_step) + 1) * tick_step
        curr_t = first_tick

        painter.setPen(QColor("#9CA3AF"))
        painter.setFont(QFont("Segoe UI", 7))

        while curr_t < (self.view_end / float(self._sample_rate)):
            x = self._time_to_x(curr_t)
            painter.drawLine(int(x), self.ruler_height - 6, int(x), self.ruler_height - 1)

            mins = int(curr_t) // 60
            secs = int(curr_t) % 60
            if tick_step < 1.0:
                ms = int((curr_t - int(curr_t)) * 10)
                txt = f"{mins:02d}:{secs:02d}.{ms}"
            else:
                txt = f"{mins:02d}:{secs:02d}"

            painter.drawText(int(x) + 3, self.ruler_height - 7, txt)
            curr_t += tick_step

"""
SONORA Studio - Audio Buffer & Non-Destructive Editing Engine
Maintains in-memory audio state, undo/redo history stack, and sample-level operations.
"""

from typing import Optional, List, Tuple
import numpy as np
import soundfile as sf

from app.audio.dsp import AudioDSP
from app.core.logger import get_logger
from app.core.signals import signals

logger = get_logger("AudioBuffer")


class AudioBuffer:
    """Manages audio memory, edit operations, and multi-level Undo/Redo history."""

    def __init__(self, max_history: int = 25):
        self._data: Optional[np.ndarray] = None  # Always shape: (samples, channels)
        self._sample_rate: int = 44100
        self._filepath: Optional[str] = None
        self._is_dirty: bool = False

        # History stacks: store tuples of (data_copy, sample_rate, description)
        self._undo_stack: List[Tuple[np.ndarray, int, str]] = []
        self._redo_stack: List[Tuple[np.ndarray, int, str]] = []
        self._max_history = max_history

        # Clipboard
        self._clipboard: Optional[np.ndarray] = None
        self._clipboard_sr: int = 44100

        # Cursor and Selection (in samples)
        self.cursor_sample: int = 0
        self.selection_start: Optional[int] = None
        self.selection_end: Optional[int] = None

    @property
    def is_loaded(self) -> bool:
        return self._data is not None and len(self._data) > 0

    @property
    def data(self) -> Optional[np.ndarray]:
        return self._data

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def channels(self) -> int:
        if self._data is not None:
            return self._data.shape[1]
        return 1

    @property
    def total_samples(self) -> int:
        return len(self._data) if self._data is not None else 0

    @property
    def duration_seconds(self) -> float:
        if self._data is not None and self._sample_rate > 0:
            return len(self._data) / self._sample_rate
        return 0.0

    @property
    def filepath(self) -> Optional[str]:
        return self._filepath

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def load_file(self, filepath: str) -> bool:
        """Load audio file from disk into the editor buffer."""
        try:
            data, sr = sf.read(filepath, dtype='float32')
            if data.ndim == 1:
                data = data[:, np.newaxis]
            self._data = data.astype(np.float32)
            self._sample_rate = sr
            self._filepath = filepath
            self._is_dirty = False
            self._undo_stack.clear()
            self._redo_stack.clear()
            self.cursor_sample = 0
            self.selection_start = None
            self.selection_end = None
            self._emit_history_changed()
            logger.info(f"Editor dosyası yüklendi: {filepath} ({sr} Hz, {data.shape[1]} kanal)")
            return True
        except Exception as e:
            logger.error(f"Editor dosya yükleme hatası: {e}")
            signals.toast_requested.emit(f"Dosya açılamadı: {e}", "error")
            return False

    def load_from_array(self, data: np.ndarray, sr: int, name: str = "Yeni Proje"):
        """Load directly from existing NumPy array."""
        if data.ndim == 1:
            data = data[:, np.newaxis]
        self._data = data.astype(np.float32)
        self._sample_rate = sr
        self._filepath = name
        self._is_dirty = True
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.cursor_sample = 0
        self.selection_start = None
        self.selection_end = None
        self._emit_history_changed()

    def _push_undo(self, description: str):
        """Save state to undo stack before modifying buffer."""
        if self._data is not None:
            self._undo_stack.append((self._data.copy(), self._sample_rate, description))
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)
            self._redo_stack.clear()
            self._is_dirty = True
            self._emit_history_changed()

    def _emit_history_changed(self):
        signals.editor_history_changed.emit(len(self._undo_stack) > 0, len(self._redo_stack) > 0)

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> bool:
        """Rollback one edit operation."""
        if not self.can_undo():
            return False
        prev_data, prev_sr, desc = self._undo_stack.pop()
        if self._data is not None:
            self._redo_stack.append((self._data.copy(), self._sample_rate, desc))
        self._data = prev_data
        self._sample_rate = prev_sr
        self._emit_history_changed()
        signals.toast_requested.emit(f"Geri alındı: {desc}", "info")
        return True

    def redo(self) -> bool:
        """Reapply previously undone edit operation."""
        if not self.can_redo():
            return False
        next_data, next_sr, desc = self._redo_stack.pop()
        if self._data is not None:
            self._undo_stack.append((self._data.copy(), self._sample_rate, desc))
        self._data = next_data
        self._sample_rate = next_sr
        self._emit_history_changed()
        signals.toast_requested.emit(f"Yinelendi: {desc}", "info")
        return True

    # -------------------------------------------------------------
    # SELECTION HELPERS
    # -------------------------------------------------------------
    def get_selection_bounds(self) -> Tuple[int, int]:
        """Return validated (start_sample, end_sample) tuple."""
        if self._data is None:
            return 0, 0
        total = len(self._data)
        if self.selection_start is None or self.selection_end is None:
            return 0, total
        s = max(0, min(self.selection_start, self.selection_end))
        e = min(total, max(self.selection_start, self.selection_end))
        if s == e:
            return 0, total
        return s, e

    def set_selection_sec(self, start_sec: float, end_sec: float):
        """Set selection using time in seconds."""
        if self._sample_rate <= 0:
            return
        self.selection_start = max(0, int(start_sec * self._sample_rate))
        self.selection_end = min(self.total_samples, int(end_sec * self._sample_rate))

    def clear_selection(self):
        self.selection_start = None
        self.selection_end = None

    # -------------------------------------------------------------
    # EDITING OPERATIONS
    # -------------------------------------------------------------
    def cut(self) -> bool:
        """Cut selected audio to clipboard and delete it."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        if s >= e:
            return False
        self._push_undo("Kes")
        self._clipboard = self._data[s:e].copy()
        self._clipboard_sr = self._sample_rate
        # Delete range
        self._data = np.delete(self._data, np.s_[s:e], axis=0)
        self.cursor_sample = s
        self.clear_selection()
        signals.toast_requested.emit("Seçim kesildi.", "info")
        return True

    def copy(self) -> bool:
        """Copy selected audio to clipboard."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        if s >= e:
            return False
        self._clipboard = self._data[s:e].copy()
        self._clipboard_sr = self._sample_rate
        signals.toast_requested.emit("Seçim panoya kopyalandı.", "info")
        return True

    def paste(self) -> bool:
        """Paste clipboard audio at cursor position."""
        if self._clipboard is None or not self.is_loaded:
            return False
        self._push_undo("Yapıştır")

        # Match channels if needed
        clip = self._clipboard
        if clip.shape[1] != self._data.shape[1]:
            if self._data.shape[1] == 2 and clip.shape[1] == 1:
                clip = np.repeat(clip, 2, axis=1)
            elif self._data.shape[1] == 1 and clip.shape[1] == 2:
                clip = np.mean(clip, axis=1, keepdims=True)

        ins_pos = max(0, min(self.cursor_sample, len(self._data)))
        self._data = np.insert(self._data, ins_pos, clip, axis=0)
        self.cursor_sample = ins_pos + len(clip)
        self.clear_selection()
        signals.toast_requested.emit("Ses yapıştırıldı.", "info")
        return True

    def delete_selection(self) -> bool:
        """Delete selected range."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        if s >= e:
            return False
        self._push_undo("Seçimi Sil")
        self._data = np.delete(self._data, np.s_[s:e], axis=0)
        self.cursor_sample = s
        self.clear_selection()
        signals.toast_requested.emit("Seçilen bölge silindi.", "info")
        return True

    def trim(self) -> bool:
        """Keep only selected range, deleting outside."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        if s >= e or (s == 0 and e == len(self._data)):
            return False
        self._push_undo("Kırp (Seçimi Koru)")
        self._data = self._data[s:e].copy()
        self.cursor_sample = 0
        self.clear_selection()
        signals.toast_requested.emit("Seçim dışı kırpıldı.", "info")
        return True

    def duplicate_selection(self) -> bool:
        """Duplicate selected region immediately after itself."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        if s >= e:
            return False
        self._push_undo("Çoğalt")
        selected_part = self._data[s:e]
        self._data = np.insert(self._data, e, selected_part, axis=0)
        self.clear_selection()
        signals.toast_requested.emit("Seçilen ses çoğaltıldı.", "info")
        return True

    def fade_in(self, duration_sec: float = 0.5) -> bool:
        """Apply fade in to selection or beginning."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        fade_samples = min(int(duration_sec * self._sample_rate), e - s)
        if fade_samples <= 0:
            return False
        self._push_undo("Fade In")
        self._data[s:s + fade_samples] = AudioDSP.fade_in(self._data[s:s + fade_samples], fade_samples)
        signals.toast_requested.emit("Fade In uygulandı.", "info")
        return True

    def fade_out(self, duration_sec: float = 0.5) -> bool:
        """Apply fade out to selection or end."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        fade_samples = min(int(duration_sec * self._sample_rate), e - s)
        if fade_samples <= 0:
            return False
        self._push_undo("Fade Out")
        self._data[e - fade_samples:e] = AudioDSP.fade_out(self._data[e - fade_samples:e], fade_samples)
        signals.toast_requested.emit("Fade Out uygulandı.", "info")
        return True

    def normalize(self, target_db: float = -0.5) -> bool:
        """Normalize entire audio or selection."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        self._push_undo(f"Normalize ({target_db} dB)")
        self._data[s:e] = AudioDSP.normalize_peak(self._data[s:e], target_db=target_db)
        signals.toast_requested.emit(f"Normalize edildi ({target_db} dB).", "info")
        return True

    def apply_gain(self, gain_db: float) -> bool:
        """Apply gain in dB to selection or entire file."""
        if not self.is_loaded or abs(gain_db) < 0.01:
            return False
        s, e = self.get_selection_bounds()
        self._push_undo(f"Ses Seviyesi ({gain_db:+.1f} dB)")
        self._data[s:e] = AudioDSP.apply_gain(self._data[s:e], gain_db=gain_db)
        signals.toast_requested.emit(f"Ses seviyesi değiştirildi ({gain_db:+.1f} dB).", "info")
        return True

    def convert_channels(self, target: str = "stereo") -> bool:
        """Convert Mono to Stereo or Stereo to Mono."""
        if not self.is_loaded:
            return False
        curr_ch = self._data.shape[1]
        if target == "stereo" and curr_ch == 1:
            self._push_undo("Stereo'ya Dönüştür")
            self._data = np.repeat(self._data, 2, axis=1)
            signals.toast_requested.emit("Stereo'ya dönüştürüldü.", "info")
            return True
        elif target == "mono" and curr_ch == 2:
            self._push_undo("Mono'ya Dönüştür")
            self._data = np.mean(self._data, axis=1, keepdims=True)
            signals.toast_requested.emit("Mono'ya dönüştürüldü.", "info")
            return True
        return False

    def reverse(self) -> bool:
        """Reverse audio in selection."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        self._push_undo("Ters Çevir")
        self._data[s:e] = self._data[s:e][::-1]
        signals.toast_requested.emit("Ses ters çevrildi.", "info")
        return True

    def silence_selection(self) -> bool:
        """Zero out selected region."""
        if not self.is_loaded:
            return False
        s, e = self.get_selection_bounds()
        self._push_undo("Sessiz Yap")
        self._data[s:e] = 0.0
        signals.toast_requested.emit("Seçim sessiz yapıldı.", "info")
        return True


# Global editor instance
editor_buffer = AudioBuffer()

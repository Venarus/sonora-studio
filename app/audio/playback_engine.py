"""
SONORA Studio - Professional Audio Playback Engine
Non-blocking streaming playback with seeking, looping, variable speed,
live position synchronization, and instant A/B track comparison.
"""

import threading
import time
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal

from app.config import config
from app.core.logger import get_logger
from app.core.signals import signals

logger = get_logger("PlaybackEngine")


class PlaybackEngine:
    """Thread-safe playback engine supporting arbitrary numpy buffers or audio files."""

    def __init__(self):
        self._is_playing = False
        self._is_paused = False
        self._stream: Optional[sd.OutputStream] = None

        # Audio buffers (shape: samples, channels)
        self._audio_data: Optional[np.ndarray] = None
        self._sample_rate = 44100
        self._total_samples = 0
        self._current_sample = 0

        # A/B Comparison Buffers
        self._track_a_data: Optional[np.ndarray] = None
        self._track_b_data: Optional[np.ndarray] = None
        self._active_track: str = "A"  # "A" (Original) or "B" (Processed)

        # Playback properties
        self._volume = 1.0  # Linear gain
        self._speed = 1.0
        self._loop_enabled = False
        self._loop_start_sample = 0
        self._loop_end_sample = 0

        self._lock = threading.Lock()
        self._last_signal_time = 0.0

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def duration_seconds(self) -> float:
        if self._total_samples > 0 and self._sample_rate > 0:
            return self._total_samples / self._sample_rate
        return 0.0

    @property
    def position_seconds(self) -> float:
        if self._total_samples > 0 and self._sample_rate > 0:
            return min(self._current_sample / self._sample_rate, self.duration_seconds)
        return 0.0

    @property
    def active_track(self) -> str:
        return self._active_track

    def load_file(self, filepath: str) -> bool:
        """Load an audio file from disk into memory."""
        try:
            data, sr = sf.read(filepath, dtype='float32')
            if data.ndim == 1:
                data = data[:, np.newaxis]
            self.load_buffer(data, sr)
            self._track_a_data = data.copy()
            self._track_b_data = None
            self._active_track = "A"
            logger.info(f"Ses yüklendi: {filepath} ({sr} Hz, {data.shape[1]} kanal, {len(data)/sr:.2f} sn)")
            return True
        except Exception as e:
            logger.error(f"Ses yükleme hatası ({filepath}): {e}")
            signals.toast_requested.emit(f"Ses yüklenemedi: {e}", "error")
            return False

    def load_buffer(self, audio: np.ndarray, sr: int):
        """Set playback data directly from numpy array."""
        self.stop()
        with self._lock:
            if audio.ndim == 1:
                self._audio_data = audio[:, np.newaxis].astype(np.float32)
            else:
                self._audio_data = audio.astype(np.float32)
            self._sample_rate = sr
            self._total_samples = len(self._audio_data)
            self._current_sample = 0
            self._loop_start_sample = 0
            self._loop_end_sample = self._total_samples

        signals.playback_position_changed.emit(0.0, self.duration_seconds)

    def set_ab_tracks(self, original_audio: np.ndarray, processed_audio: np.ndarray, sr: int):
        """Configure Track A (Original) and Track B (Processed) for instant comparison."""
        self.stop()
        with self._lock:
            # Ensure equal length and 2D
            orig = original_audio[:, np.newaxis] if original_audio.ndim == 1 else original_audio
            proc = processed_audio[:, np.newaxis] if processed_audio.ndim == 1 else processed_audio

            min_len = min(len(orig), len(proc))
            self._track_a_data = orig[:min_len].astype(np.float32)
            self._track_b_data = proc[:min_len].astype(np.float32)

            self._active_track = "B"
            self._audio_data = self._track_b_data
            self._sample_rate = sr
            self._total_samples = min_len
            self._current_sample = 0
            self._loop_start_sample = 0
            self._loop_end_sample = min_len

        signals.playback_position_changed.emit(0.0, self.duration_seconds)

    def switch_ab(self, track: str):
        """Switch active track between 'A' and 'B' seamlessly during playback."""
        if track not in ("A", "B"):
            return
        with self._lock:
            self._active_track = track
            if track == "A" and self._track_a_data is not None:
                self._audio_data = self._track_a_data
            elif track == "B" and self._track_b_data is not None:
                self._audio_data = self._track_b_data

    def set_volume(self, vol: float):
        """Set linear volume (0.0 to 1.5)."""
        self._volume = max(0.0, min(vol, 1.5))

    def set_speed(self, speed: float):
        """Set playback speed multiplier (0.5 to 2.0)."""
        self._speed = max(0.5, min(speed, 2.0))

    def set_loop_region(self, start_sec: float, end_sec: float, enabled: bool = True):
        """Set looping boundaries."""
        with self._lock:
            self._loop_enabled = enabled
            self._loop_start_sample = max(0, int(start_sec * self._sample_rate))
            self._loop_end_sample = min(self._total_samples, int(end_sec * self._sample_rate))
            if self._loop_end_sample <= self._loop_start_sample:
                self._loop_end_sample = self._total_samples

    def clear_loop(self):
        with self._lock:
            self._loop_enabled = False

    def seek(self, position_sec: float):
        """Seek to specified time in seconds."""
        with self._lock:
            target = int(position_sec * self._sample_rate)
            self._current_sample = max(0, min(target, self._total_samples))
        signals.playback_position_changed.emit(self.position_seconds, self.duration_seconds)

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """Real-time playback callback from sounddevice."""
        if status:
            logger.warning(f"Oynatma akışı durumu uyarısı: {status}")

        with self._lock:
            if not self._is_playing or self._is_paused or self._audio_data is None:
                outdata.fill(0)
                return

            channels = min(outdata.shape[1], self._audio_data.shape[1])
            start = self._current_sample

            # Determine loop boundary or end boundary
            boundary = self._loop_end_sample if self._loop_enabled else self._total_samples

            # Speed factor handling
            step = self._speed
            needed_samples = int(frames * step)
            end = start + needed_samples

            if start >= boundary:
                if self._loop_enabled:
                    self._current_sample = self._loop_start_sample
                    start = self._loop_start_sample
                    end = start + needed_samples
                else:
                    outdata.fill(0)
                    self._is_playing = False
                    # Notify on main thread
                    threading.Thread(target=signals.playback_finished.emit, daemon=True).start()
                    threading.Thread(target=lambda: signals.playback_state_changed.emit(False, False), daemon=True).start()
                    return

            # Extract slice
            if end <= boundary:
                chunk = self._audio_data[start:end, :channels]
                self._current_sample = end
            else:
                available = boundary - start
                chunk = self._audio_data[start:boundary, :channels]
                if self._loop_enabled:
                    self._current_sample = self._loop_start_sample
                else:
                    self._current_sample = boundary

            # Resample chunk to fit outdata frames if speed != 1.0 or boundary truncation
            if len(chunk) != frames:
                if len(chunk) > 0:
                    resampled = signal.resample(chunk, frames, axis=0)
                else:
                    resampled = np.zeros((frames, channels), dtype=np.float32)
            else:
                resampled = chunk

            # Apply volume
            resampled = resampled * self._volume

            # Write to output buffer (handle mono to stereo broadcast if needed)
            if outdata.shape[1] == 2 and resampled.shape[1] == 1:
                outdata[:, 0] = resampled[:, 0]
                outdata[:, 1] = resampled[:, 0]
            else:
                outdata[:, :channels] = resampled[:, :channels]
                if channels < outdata.shape[1]:
                    outdata[:, channels:].fill(0)

        # Throttle position signals to ~30 FPS
        now = time.time()
        if now - self._last_signal_time > 0.033:
            self._last_signal_time = now
            signals.playback_position_changed.emit(self.position_seconds, self.duration_seconds)

    def play(self) -> bool:
        """Start or resume playback."""
        if self._audio_data is None or len(self._audio_data) == 0:
            return False

        if self._is_paused and self._stream is not None:
            self._is_paused = False
            self._is_playing = True
            signals.playback_state_changed.emit(True, False)
            return True

        self.stop()

        try:
            device_id = config.get("output_device_id")
            channels = min(2, self._audio_data.shape[1] if self._audio_data.ndim > 1 else 1)
            # If mono, play as 2 channels stereo so both headphones receive sound
            out_channels = 2

            self._stream = sd.OutputStream(
                device=device_id,
                channels=out_channels,
                samplerate=self._sample_rate,
                blocksize=1024,
                dtype="float32",
                callback=self._audio_callback
            )
            self._stream.start()
            self._is_playing = True
            self._is_paused = False
            signals.playback_state_changed.emit(True, False)
            return True
        except Exception as e:
            logger.error(f"Oynatma başlatılamadı: {e}")
            signals.toast_requested.emit(f"Ses çalınamadı: {e}", "error")
            return False

    def pause(self):
        """Pause playback at current position."""
        if self._is_playing and not self._is_paused:
            self._is_paused = True
            signals.playback_state_changed.emit(True, True)

    def stop(self):
        """Stop playback and rewind to start or loop start."""
        self._is_playing = False
        self._is_paused = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Oynatma akışı kapatma hatası: {e}")
            self._stream = None

        with self._lock:
            self._current_sample = self._loop_start_sample if self._loop_enabled else 0

        signals.playback_state_changed.emit(False, False)
        signals.playback_position_changed.emit(self.position_seconds, self.duration_seconds)


# Global instance
player = PlaybackEngine()

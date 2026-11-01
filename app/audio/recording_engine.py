"""
SONORA Studio - Professional Audio Recording Engine (Lag-Free & Real-Time Decoupled)
High-performance decoupled architecture: audio callback does NOT flood Qt event queue.
Features atomic metering, hardware channel auto-adaptation, and crash-resilient disk writes.
"""

import os
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
import soundfile as sf

from app.config import config
from app.core.logger import get_logger
from app.core.signals import signals

logger = get_logger("RecordingEngine")


class RecordingEngine:
    """Threaded audio recorder with decoupled lockless GUI metering and streaming disk capture."""

    def __init__(self):
        self._is_recording = False
        self._is_paused = False
        self._stream: Optional[sd.InputStream] = None
        self._file: Optional[sf.SoundFile] = None
        self._output_filepath: Optional[str] = None

        self._sample_rate = 48000
        self._channels = 2          # Target output channels (1 or 2)
        self._stream_channels = 2   # Hardware stream channels (1 or 2)
        self._device_id: Optional[int] = None
        self._bit_depth = "PCM_24"

        # Threading and Queues
        self._audio_queue: queue.Queue = queue.Queue(maxsize=500)
        self._writer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Decoupled Atomic Level Metering (Read by UI Timer without Qt event loop flooding)
        self.peak_l: float = 0.0
        self.peak_r: float = 0.0
        self.rms_l: float = 0.0
        self.rms_r: float = 0.0
        self.is_clipping: bool = False

        # Latest rolling chunk for oscilloscope display
        self._latest_chunk: Optional[np.ndarray] = None
        self._chunk_lock = threading.Lock()

        # Timing and statistics
        self._start_time = 0.0
        self._elapsed_time = 0.0
        self._total_samples_written = 0

        # Clipping detector threshold
        self._clipping_threshold = 0.995

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def elapsed_seconds(self) -> float:
        if not self._is_recording:
            return 0.0
        if self._is_paused:
            return self._elapsed_time
        return self._elapsed_time + (time.time() - self._start_time)

    def pop_latest_chunk(self) -> Optional[np.ndarray]:
        """Called by UI timer to get latest chunk for live waveform rendering."""
        with self._chunk_lock:
            chunk = self._latest_chunk
            self._latest_chunk = None
            return chunk

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status):
        """High-priority audio callback executed in C PortAudio thread."""
        if not self._is_recording:
            return

        data = indata.copy()

        # Calculate fast Peak and RMS for Left and Right channels
        if data.shape[1] >= 2:
            left_ch = data[:, 0]
            right_ch = data[:, 1]
        else:
            left_ch = data[:, 0]
            right_ch = data[:, 0]

        peak_l = float(np.max(np.abs(left_ch)))
        peak_r = float(np.max(np.abs(right_ch)))
        rms_l = float(np.sqrt(np.mean(left_ch ** 2)))
        rms_r = float(np.sqrt(np.mean(right_ch ** 2)))

        # Update atomic state for UI polling (zero overhead!)
        self.peak_l = peak_l
        self.peak_r = peak_r
        self.rms_l = rms_l
        self.rms_r = rms_r
        if peak_l >= self._clipping_threshold or peak_r >= self._clipping_threshold:
            self.is_clipping = True

        if not self._is_paused:
            # Broadcast mono to stereo if target is stereo
            if self._channels == 2 and data.shape[1] == 1:
                write_chunk = np.repeat(data, 2, axis=1)
            else:
                write_chunk = data

            # Store latest chunk for UI oscilloscope
            with self._chunk_lock:
                self._latest_chunk = write_chunk

            # Push to disk writing queue
            try:
                self._audio_queue.put_nowait(write_chunk)
            except queue.Full:
                pass

    def _disk_writer_loop(self):
        """Dedicated background thread for streaming samples to disk."""
        logger.info(f"Disk yazıcı başlatıldı: {self._output_filepath}")
        flush_counter = 0

        while not self._stop_event.is_set() or not self._audio_queue.empty():
            try:
                chunk = self._audio_queue.get(timeout=0.08)
                if self._file is not None and not self._file.closed:
                    self._file.write(chunk)
                    self._total_samples_written += len(chunk)
                    flush_counter += 1
                    # Flush every ~0.5s to guarantee data preservation
                    if flush_counter >= 15:
                        self._file.flush()
                        flush_counter = 0
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Diske yazma hatası: {e}")

        if self._file is not None and not self._file.closed:
            try:
                self._file.flush()
                self._file.close()
                logger.info(f"Dosya başarıyla kaydedildi ({self._total_samples_written} örnek).")
            except Exception as e:
                logger.error(f"Dosya kapatma hatası: {e}")

    def start_recording(self,
                        device_id: Optional[int] = None,
                        sample_rate: int = 48000,
                        channels: int = 2,
                        bit_depth: str = "PCM_24",
                        custom_filename: Optional[str] = None) -> Tuple[bool, str]:
        """Start recording with automatic hardware channel adaptation."""
        if self._is_recording:
            return False, "Zaten devam eden bir kayıt var."

        # Detect actual hardware input channel limits
        dev_info = None
        try:
            if device_id is not None:
                dev_info = sd.query_devices(device_id)
            else:
                default_in, _ = sd.default.device
                dev_info = sd.query_devices(default_in)
                device_id = default_in
        except Exception:
            pass

        max_in = dev_info.get("max_input_channels", 2) if dev_info else 2
        self._stream_channels = min(channels, max_in)
        if self._stream_channels <= 0:
            self._stream_channels = 1

        self._channels = channels
        self._sample_rate = sample_rate
        self._device_id = device_id
        self._bit_depth = bit_depth
        self._elapsed_time = 0.0
        self._total_samples_written = 0

        # Destination path
        recordings_dir = Path(config.get("recordings_dir"))
        recordings_dir.mkdir(parents=True, exist_ok=True)

        if custom_filename:
            base_name = custom_filename if custom_filename.lower().endswith(".wav") else custom_filename + ".wav"
        else:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H-%M-%S")
            template = config.get("naming_template", "Kayıt_{date}_{time}")
            base_name = template.replace("{date}", date_str).replace("{time}", time_str) + ".wav"

        self._output_filepath = str(recordings_dir / base_name)

        subtype_map = {
            "PCM_16": "PCM_16",
            "PCM_24": "PCM_24",
            "FLOAT_32": "FLOAT"
        }
        subtype = subtype_map.get(bit_depth, "PCM_24")

        # Open sound file for writing
        try:
            self._file = sf.SoundFile(
                self._output_filepath,
                mode="w",
                samplerate=self._sample_rate,
                channels=self._channels,
                subtype=subtype
            )
        except Exception as e:
            err = f"Kayıt dosyası oluşturulamadı: {e}"
            logger.error(err)
            signals.toast_requested.emit(err, "error")
            return False, err

        # Clear queue and start background writer
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

        self._stop_event.clear()
        self._writer_thread = threading.Thread(target=self._disk_writer_loop, daemon=True)
        self._writer_thread.start()

        # Open PortAudio input stream
        try:
            blocksize = int(config.get("buffer_size", 1024))
            self._stream = sd.InputStream(
                device=self._device_id,
                channels=self._stream_channels,
                samplerate=self._sample_rate,
                blocksize=blocksize,
                dtype="float32",
                callback=self._audio_callback
            )
            self._stream.start()
        except Exception as e:
            self._stop_event.set()
            if self._writer_thread:
                self._writer_thread.join(timeout=1.0)
            if self._file and not self._file.closed:
                self._file.close()
            if os.path.exists(self._output_filepath):
                try:
                    os.remove(self._output_filepath)
                except Exception:
                    pass
            err = f"Mikrofon başlatılamadı ({self._stream_channels} kanal, {self._sample_rate} Hz): {e}"
            logger.error(err)
            signals.toast_requested.emit(err, "error")
            return False, err

        self._is_recording = True
        self._is_paused = False
        self._start_time = time.time()

        signals.recording_started.emit()
        signals.toast_requested.emit(f"Kayıt başladı: {Path(self._output_filepath).name}", "info")
        return True, self._output_filepath

    def pause_recording(self):
        if self._is_recording and not self._is_paused:
            self._elapsed_time += time.time() - self._start_time
            self._is_paused = True
            signals.recording_paused.emit()
            signals.toast_requested.emit("Kayıt duraklatıldı.", "warning")

    def resume_recording(self):
        if self._is_recording and self._is_paused:
            self._start_time = time.time()
            self._is_paused = False
            signals.recording_resumed.emit()
            signals.toast_requested.emit("Kayıt devam ediyor.", "info")

    def stop_recording(self) -> Optional[str]:
        """Stop recording, finalize file, and notify all systems."""
        if not self._is_recording:
            return None

        self._is_recording = False
        self._is_paused = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Akış durdurma hatası: {e}")
            self._stream = None

        self._stop_event.set()
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=3.0)
            self._writer_thread = None

        saved_path = self._output_filepath
        logger.info(f"Kayıt başarıyla tamamlandı: {saved_path}")

        # Reset atomic values
        self.peak_l = 0.0
        self.peak_r = 0.0
        self.rms_l = 0.0
        self.rms_r = 0.0
        self.is_clipping = False

        # Notify systems
        signals.recording_stopped.emit(saved_path)
        signals.library_updated.emit()
        signals.toast_requested.emit(f"Kayıt tamamlandı: {Path(saved_path).name}", "success")

        return saved_path


# Global instance
recorder = RecordingEngine()

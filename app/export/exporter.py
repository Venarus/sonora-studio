"""
SONORA Studio - Professional Audio Export Engine
Multi-format audio export (WAV, FLAC, MP3, OGG) with sample rate conversion,
normalization, metadata tags, and background progress tracking.
"""

import os
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import numpy as np
import soundfile as sf
from scipy import signal

from app.audio.dsp import AudioDSP
from app.core.logger import get_logger
from app.core.signals import signals

logger = get_logger("Exporter")


class AudioExporter:
    """Exports audio buffers to disk with format conversions and mastering options."""

    FORMAT_SUBTYPES = {
        "WAV": {
            "PCM_16": "PCM_16",
            "PCM_24": "PCM_24",
            "FLOAT_32": "FLOAT"
        },
        "FLAC": {
            "PCM_16": "PCM_16",
            "PCM_24": "PCM_24"
        },
        "OGG": {
            "VORBIS": "VORBIS"
        },
        "MP3": {
            "DEFAULT": None
        }
    }

    EXPORT_PRESETS: Dict[str, Dict[str, Any]] = {
        "Stüdyo Master WAV (24-bit 48kHz)": {
            "format": "WAV",
            "bit_depth": "PCM_24",
            "sample_rate": 48000,
            "channels": 2,
            "normalize": True,
            "normalize_db": -0.5
        },
        "Kayıpsız FLAC (Master Arşiv)": {
            "format": "FLAC",
            "bit_depth": "PCM_24",
            "sample_rate": 48000,
            "channels": 2,
            "normalize": True,
            "normalize_db": -0.3
        },
        "Yüksek Kalite MP3 (320 kbps)": {
            "format": "MP3",
            "bit_depth": "PCM_16",
            "sample_rate": 44100,
            "channels": 2,
            "normalize": True,
            "normalize_db": -1.0
        },
        "Podcast Hazır MP3 (192 kbps Mono)": {
            "format": "MP3",
            "bit_depth": "PCM_16",
            "sample_rate": 44100,
            "channels": 1,
            "normalize": True,
            "normalize_db": -1.0
        },
        "Kompakt Web OGG (Vorbis)": {
            "format": "OGG",
            "bit_depth": "VORBIS",
            "sample_rate": 44100,
            "channels": 2,
            "normalize": True,
            "normalize_db": -0.5
        }
    }

    @classmethod
    def export(cls,
               audio: np.ndarray,
               src_sr: int,
               output_path: str,
               export_format: str = "WAV",
               target_sr: int = 48000,
               channels: int = 2,
               bit_depth: str = "PCM_24",
               normalize: bool = True,
               normalize_db: float = -0.5,
               metadata: Optional[Dict[str, str]] = None,
               progress_cb: Optional[Callable[[int, str], None]] = None) -> bool:
        """Export audio with all requested settings."""
        try:
            if progress_cb:
                progress_cb(10, "Ses verisi hazırlanıyor...")

            data = audio.copy().astype(np.float32)

            # 1. Channel configuration
            if data.ndim == 1:
                data = data[:, np.newaxis]

            if channels == 1 and data.shape[1] > 1:
                # Downmix to mono
                data = np.mean(data, axis=1, keepdims=True)
            elif channels == 2 and data.shape[1] == 1:
                # Up-mix to stereo
                data = np.repeat(data, 2, axis=1)

            # 2. Resampling if needed
            if src_sr != target_sr:
                if progress_cb:
                    progress_cb(35, f"Örnekleme hızı dönüştürülüyor ({src_sr} -> {target_sr} Hz)...")

                num_target_samples = int(len(data) * float(target_sr) / float(src_sr))
                # Polyphase resample
                from math import gcd
                g = gcd(target_sr, src_sr)
                up = target_sr // g
                down = src_sr // g

                resampled_channels = []
                for ch in range(data.shape[1]):
                    # If ratio is reasonable use resample_poly, else fft resample
                    if up * down < 5000000:
                        resampled_ch = signal.resample_poly(data[:, ch], up, down)
                    else:
                        resampled_ch = signal.resample(data[:, ch], num_target_samples)
                    resampled_channels.append(resampled_ch)

                data = np.column_stack(resampled_channels)

            # 3. Normalization
            if normalize:
                if progress_cb:
                    progress_cb(65, f"Mastering normalizasyonu uygulanıyor ({normalize_db} dBFS)...")
                data = AudioDSP.normalize_peak(data, target_db=normalize_db)

            # 4. Write to disk
            if progress_cb:
                progress_cb(80, f"{export_format} formatında kaydediliyor...")

            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)

            fmt_upper = export_format.upper()
            subtype = None
            if fmt_upper in cls.FORMAT_SUBTYPES:
                subtype = cls.FORMAT_SUBTYPES[fmt_upper].get(bit_depth)

            # Flatten 1-channel to 1D for mono file standard compliance
            write_data = data[:, 0] if data.shape[1] == 1 else data

            if fmt_upper == "MP3":
                sf.write(str(dest), write_data, target_sr, format="MP3")
            elif fmt_upper == "OGG":
                sf.write(str(dest), write_data, target_sr, format="OGG")
            else:
                sf.write(str(dest), write_data, target_sr, format=fmt_upper, subtype=subtype)

            if progress_cb:
                progress_cb(100, "Dışa aktarma tamamlandı.")

            signals.library_updated.emit()
            signals.toast_requested.emit(f"Dışa aktarıldı: {dest.name}", "success")
            return True

        except Exception as e:
            logger.error(f"Dışa aktarma hatası: {e}")
            signals.toast_requested.emit(f"Dışa aktarılamadı: {e}", "error")
            return False

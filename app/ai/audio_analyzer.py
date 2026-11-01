"""
SONORA Studio - Audio Analyzer
Performs in-depth acoustic inspection: SNR, noise floor, hum detection,
clipping statistics, dynamic range, and silence segmentation.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
from scipy import signal


class AudioAnalyzer:
    """Acoustic profiling and artifact detection."""

    @staticmethod
    def analyze(audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """Perform comprehensive acoustic analysis on audio data."""
        # Work with mono downmix for spectral metrics
        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio

        num_samples = len(mono)
        duration_sec = num_samples / sr if sr > 0 else 0.0

        if num_samples == 0:
            return {
                "duration": 0.0,
                "peak_db": -100.0,
                "rms_db": -100.0,
                "noise_floor_db": -100.0,
                "snr_db": 0.0,
                "clipped_samples": 0,
                "has_hum_50hz": False,
                "has_hum_60hz": False,
                "silence_ratio": 0.0,
                "silent_regions": []
            }

        abs_sig = np.abs(mono)
        peak_val = float(np.max(abs_sig))
        peak_db = 20.0 * np.log10(max(peak_val, 1e-6))

        rms_val = float(np.sqrt(np.mean(mono ** 2)))
        rms_db = 20.0 * np.log10(max(rms_val, 1e-6))

        # Clipping detection (> 0.995 linear)
        clipped_samples = int(np.sum(abs_sig >= 0.995))

        # Estimate Noise Floor via bottom 10th percentile of short-term RMS frames
        frame_len = int(sr * 0.05)  # 50ms frames
        if num_samples > frame_len:
            num_frames = num_samples // frame_len
            frames = mono[:num_frames * frame_len].reshape((num_frames, frame_len))
            frame_rms = np.sqrt(np.mean(frames ** 2, axis=1))
            # Sort and take 10th percentile
            p10 = np.percentile(frame_rms, 10)
            noise_floor_db = float(20.0 * np.log10(max(p10, 1e-6)))
        else:
            noise_floor_db = rms_db - 15.0

        snr_db = float(max(0.0, rms_db - noise_floor_db))

        # Detect 50Hz and 60Hz Power Hum via Welch FFT Power Spectral Density
        has_hum_50 = False
        has_hum_60 = False
        try:
            freqs, psd = signal.welch(mono, sr, nperseg=min(sr * 2, num_samples))
            # Find peak near 50Hz (48-52Hz) and 60Hz (58-62Hz)
            idx_50 = np.where((freqs >= 48) & (freqs <= 52))[0]
            idx_60 = np.where((freqs >= 58) & (freqs <= 62))[0]
            idx_surround = np.where((freqs >= 35) & (freqs <= 75))[0]

            if len(idx_surround) > 0:
                surround_mean = np.median(psd[idx_surround])
                if len(idx_50) > 0 and np.max(psd[idx_50]) > surround_mean * 4.0:
                    has_hum_50 = True
                if len(idx_60) > 0 and np.max(psd[idx_60]) > surround_mean * 4.0:
                    has_hum_60 = True
        except Exception:
            pass

        # Silence Detection (< -42 dB for > 350ms)
        silent_regions = AudioAnalyzer.find_silence(mono, sr, threshold_db=-42.0, min_duration_sec=0.35)
        total_silent_duration = sum(end - start for start, end in silent_regions)
        silence_ratio = float((total_silent_duration / duration_sec) * 100.0) if duration_sec > 0 else 0.0

        return {
            "duration": round(duration_sec, 2),
            "peak_db": round(peak_db, 1),
            "rms_db": round(rms_db, 1),
            "noise_floor_db": round(noise_floor_db, 1),
            "snr_db": round(snr_db, 1),
            "clipped_samples": clipped_samples,
            "has_hum_50hz": has_hum_50,
            "has_hum_60hz": has_hum_60,
            "silence_ratio": round(silence_ratio, 1),
            "silent_regions": silent_regions
        }

    @staticmethod
    def find_silence(mono: np.ndarray, sr: int, threshold_db: float = -42.0, min_duration_sec: float = 0.35) -> List[Tuple[float, float]]:
        """Identify intervals of silence / background pauses."""
        num_samples = len(mono)
        frame_size = int(sr * 0.02)  # 20ms
        if frame_size == 0 or num_samples < frame_size:
            return []

        threshold_linear = 10.0 ** (threshold_db / 20.0)
        num_frames = num_samples // frame_size
        frames = mono[:num_frames * frame_size].reshape((num_frames, frame_size))
        rms_frames = np.sqrt(np.mean(frames ** 2, axis=1))

        is_silent = rms_frames < threshold_linear
        min_frames = int(min_duration_sec / 0.02)

        regions = []
        in_silence = False
        start_frame = 0

        for i, silent in enumerate(is_silent):
            if silent and not in_silence:
                in_silence = True
                start_frame = i
            elif not silent and in_silence:
                in_silence = False
                if (i - start_frame) >= min_frames:
                    regions.append((start_frame * 0.02, i * 0.02))

        if in_silence and (len(is_silent) - start_frame) >= min_frames:
            regions.append((start_frame * 0.02, len(is_silent) * 0.02))

        return regions

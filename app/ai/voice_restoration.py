"""
SONORA Studio - Voice Restoration & Audio Cleaning Suite
Contains dedicated processors for De-Hum, De-Click, De-Plosive, De-Esser,
De-Reverb, Voice Isolation, and Silence Trimming.
"""

from typing import List, Tuple, Optional
import numpy as np
from scipy import signal
from app.audio.dsp import AudioDSP
from app.core.logger import get_logger

logger = get_logger("VoiceRestoration")


class VoiceRestoration:
    """Specialized speech and vocal restoration algorithms."""

    # -------------------------------------------------------------
    # 1. HUM REMOVAL (50Hz / 60Hz + Harmonics)
    # -------------------------------------------------------------
    @classmethod
    def remove_hum(cls, audio: np.ndarray, sr: int, base_freq: float = 50.0, harmonics: int = 5) -> np.ndarray:
        """Cascade notch filters on base hum frequency and its integer harmonics."""
        result = audio.copy()
        for i in range(1, harmonics + 1):
            target_f = base_freq * i
            if target_f < (sr * 0.48):
                # Narrow Q notch
                result = AudioDSP.notch_filter(result, sr, freq_hz=target_f, q=35.0)
        return result

    # -------------------------------------------------------------
    # 2. DE-PLOSIVE (Low-frequency microphone pop reduction)
    # -------------------------------------------------------------
    @classmethod
    def de_plosive(cls, audio: np.ndarray, sr: int, cutoff_hz: float = 85.0) -> np.ndarray:
        """Eliminate harsh breath pops and microphone blasts below cutoff."""
        return AudioDSP.highpass_filter(audio, sr, cutoff_hz=cutoff_hz, order=4)

    # -------------------------------------------------------------
    # 3. DE-ESSER (Dynamic sibilance reduction)
    # -------------------------------------------------------------
    @classmethod
    def de_esser(cls, audio: np.ndarray, sr: int,
                 freq_hz: float = 6500.0,
                 threshold_db: float = -22.0,
                 reduction_db: float = 6.0) -> np.ndarray:
        """
        Detects excessive high-frequency sibilant energy ('s', 'sh')
        and dynamically ducks the sibilance frequency band.
        """
        audio_2d, was_1d = AudioDSP.ensure_2d(audio)
        nyquist = 0.5 * sr
        low = max(4000.0 / nyquist, 0.05)
        high = min(8800.0 / nyquist, 0.95)

        # Bandpass filter for sibilance detection
        b, a = signal.butter(2, [low, high], btype='band')
        out = np.zeros_like(audio_2d, dtype=np.float32)

        thresh_linear = 10.0 ** (threshold_db / 20.0)
        max_attenuation = 10.0 ** (-reduction_db / 20.0)

        for ch in range(audio_2d.shape[1]):
            ch_data = audio_2d[:, ch]
            sibilance = signal.filtfilt(b, a, ch_data)
            envelope = np.abs(sibilance)

            # Fast attack (1ms), smooth release (30ms)
            smooth_env = np.zeros_like(envelope)
            curr = 0.0
            for i in range(len(envelope)):
                val = envelope[i]
                if val > curr:
                    curr = 0.6 * curr + 0.4 * val
                else:
                    curr = 0.98 * curr + 0.02 * val
                smooth_env[i] = curr

            # Calculate dynamic gain
            gain_curve = np.ones_like(smooth_env)
            mask = smooth_env > thresh_linear
            if np.any(mask):
                excess = (smooth_env[mask] - thresh_linear) / (thresh_linear + 1e-6)
                duck = np.clip(1.0 - excess * 0.4, max_attenuation, 1.0)
                gain_curve[mask] = duck

            # Apply gain to the sibilance band and recombine
            non_sibilance = ch_data - sibilance
            out[:, ch] = non_sibilance + sibilance * gain_curve

        return AudioDSP.restore_shape(out, was_1d)

    # -------------------------------------------------------------
    # 4. DE-CLICK (Impulsive click & pop removal)
    # -------------------------------------------------------------
    @classmethod
    def de_click(cls, audio: np.ndarray, sr: int, sensitivity: float = 3.5) -> np.ndarray:
        """
        Detects anomalous high-derivative spikes and repairs them via linear interpolation.
        """
        audio_2d, was_1d = AudioDSP.ensure_2d(audio)
        out = audio_2d.copy()

        for ch in range(audio_2d.shape[1]):
            data = out[:, ch]
            diff = np.abs(np.diff(data, prepend=data[0]))
            median_diff = np.median(diff)
            mad = np.median(np.abs(diff - median_diff)) + 1e-6
            threshold = median_diff + sensitivity * 8.0 * mad

            click_indices = np.where(diff > threshold)[0]

            # Interpolate detected clicks
            for idx in click_indices:
                if 2 < idx < len(data) - 3:
                    # Replace with average of immediate neighbors
                    data[idx] = 0.5 * (data[idx - 1] + data[idx + 1])
                    data[idx - 1] = 0.5 * (data[idx - 2] + data[idx])
                    data[idx + 1] = 0.5 * (data[idx] + data[idx + 2])

        return AudioDSP.restore_shape(out, was_1d)

    # -------------------------------------------------------------
    # 5. DE-REVERB (Room reflection suppression)
    # -------------------------------------------------------------
    @classmethod
    def de_reverb(cls, audio: np.ndarray, sr: int, intensity_pct: float = 50.0) -> np.ndarray:
        """
        Reduces room reverberation by suppressing exponential spectral decay tails.
        """
        audio_2d, was_1d = AudioDSP.ensure_2d(audio)
        out_channels = []

        nperseg = 1024
        noverlap = 768
        decay_factor = 0.85 - (intensity_pct / 100.0) * 0.15

        for ch in range(audio_2d.shape[1]):
            channel_data = audio_2d[:, ch]
            f, t, Zxx = signal.stft(channel_data, fs=sr, nperseg=nperseg, noverlap=noverlap)
            mag = np.abs(Zxx)
            phase = np.angle(Zxx)

            # Recursive decay tail estimation
            reverb_tail = np.zeros_like(mag)
            for frame_idx in range(1, mag.shape[1]):
                prev = reverb_tail[:, frame_idx - 1]
                curr = mag[:, frame_idx]
                reverb_tail[:, frame_idx] = np.maximum(curr * 0.3, prev * decay_factor)

            # Suppress tail
            clean_mag = np.maximum(mag - reverb_tail * 0.7, 0.1 * mag)
            Zxx_clean = clean_mag * np.exp(1j * phase)

            _, x_rec = signal.istft(Zxx_clean, fs=sr, nperseg=nperseg, noverlap=noverlap)
            if len(x_rec) > len(channel_data):
                x_rec = x_rec[:len(channel_data)]
            elif len(x_rec) < len(channel_data):
                x_rec = np.pad(x_rec, (0, len(channel_data) - len(x_rec)))

            out_channels.append(x_rec)

        result = np.column_stack(out_channels)
        return result[:, 0] if was_1d else result

    # -------------------------------------------------------------
    # 6. VOICE ISOLATION & VOCAL ENHANCEMENT
    # -------------------------------------------------------------
    @classmethod
    def enhance_voice(cls, audio: np.ndarray, sr: int, clarity_pct: float = 50.0) -> np.ndarray:
        """
        Polishes speech clarity:
        - Highpass below 75Hz (rumble cut)
        - Peaking boost around 2.8kHz - 3.8kHz (vocal intelligibility/clarity)
        - Air presence around 10kHz
        - Gentle compression for consistent volume
        """
        boost_db = (clarity_pct / 100.0) * 4.0

        # Cut mud
        proc = AudioDSP.highpass_filter(audio, sr, cutoff_hz=75.0, order=3)
        # Boost speech presence
        proc = AudioDSP.peaking_eq(proc, sr, center_hz=3200.0, gain_db=boost_db, q=1.2)
        # Air lift
        proc = AudioDSP.peaking_eq(proc, sr, center_hz=9500.0, gain_db=boost_db * 0.6, q=0.8)
        # Smooth voice dynamics
        proc = AudioDSP.compressor(proc, sr, threshold_db=-18.0, ratio=2.5, attack_ms=20.0, release_ms=100.0, makeup_gain_db=1.5)

        return proc

    # -------------------------------------------------------------
    # 7. SILENCE REMOVAL
    # -------------------------------------------------------------
    @classmethod
    def remove_silence(cls, audio: np.ndarray, sr: int, silent_regions: List[Tuple[float, float]]) -> np.ndarray:
        """Remove identified silent regions from audio, joining audible segments."""
        if not silent_regions:
            return audio

        audio_2d, was_1d = AudioDSP.ensure_2d(audio)
        total_samples = len(audio_2d)

        # Build mask of samples to keep
        keep_mask = np.ones(total_samples, dtype=bool)
        for start_sec, end_sec in silent_regions:
            s_idx = max(0, int(start_sec * sr))
            e_idx = min(total_samples, int(end_sec * sr))
            keep_mask[s_idx:e_idx] = False

        if not np.any(keep_mask):
            return audio  # Don't delete entire recording

        trimmed = audio_2d[keep_mask]
        return AudioDSP.restore_shape(trimmed, was_1d)

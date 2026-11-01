"""
SONORA Studio - Professional DSP Audio Processing Suite
Vectorized, high-precision signal processing algorithms using NumPy and SciPy.
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional


class AudioDSP:
    """Core Digital Signal Processing methods for filtering, dynamics, and time/spatial effects."""

    @staticmethod
    def ensure_2d(audio: np.ndarray) -> Tuple[np.ndarray, bool]:
        """Ensure audio array is shape (samples, channels). Returns (array, was_1d)."""
        if audio.ndim == 1:
            return audio[:, np.newaxis], True
        elif audio.ndim == 2:
            if audio.shape[0] < audio.shape[1] and audio.shape[0] <= 2:
                # Transpose if given as (channels, samples)
                return audio.T, False
            return audio, False
        else:
            raise ValueError(f"Geçersiz ses boyutu: {audio.shape}")

    @staticmethod
    def restore_shape(audio_2d: np.ndarray, was_1d: bool) -> np.ndarray:
        """Restore original 1D shape if input was originally 1D."""
        if was_1d:
            return audio_2d[:, 0]
        return audio_2d

    # ---------------------------------------------------------
    # 1. FILTERS (High-Pass, Low-Pass, Band-Pass, Notch)
    # ---------------------------------------------------------
    @classmethod
    def highpass_filter(cls, audio: np.ndarray, sr: int, cutoff_hz: float = 80.0, order: int = 4) -> np.ndarray:
        """Butterworth high-pass filter (cuts rumble, plosives, low hum)."""
        nyquist = 0.5 * sr
        norm_cutoff = min(cutoff_hz / nyquist, 0.99)
        b, a = signal.butter(order, norm_cutoff, btype='high', analog=False)
        audio_2d, was_1d = cls.ensure_2d(audio)
        out = np.zeros_like(audio_2d, dtype=np.float32)
        for ch in range(audio_2d.shape[1]):
            out[:, ch] = signal.filtfilt(b, a, audio_2d[:, ch])
        return cls.restore_shape(out, was_1d)

    @classmethod
    def lowpass_filter(cls, audio: np.ndarray, sr: int, cutoff_hz: float = 12000.0, order: int = 4) -> np.ndarray:
        """Butterworth low-pass filter (cuts high hiss, ultrasonic noise)."""
        nyquist = 0.5 * sr
        norm_cutoff = min(cutoff_hz / nyquist, 0.99)
        b, a = signal.butter(order, norm_cutoff, btype='low', analog=False)
        audio_2d, was_1d = cls.ensure_2d(audio)
        out = np.zeros_like(audio_2d, dtype=np.float32)
        for ch in range(audio_2d.shape[1]):
            out[:, ch] = signal.filtfilt(b, a, audio_2d[:, ch])
        return cls.restore_shape(out, was_1d)

    @classmethod
    def notch_filter(cls, audio: np.ndarray, sr: int, freq_hz: float = 50.0, q: float = 30.0) -> np.ndarray:
        """IIR Notch filter to eliminate a specific single frequency (e.g. 50Hz or 60Hz hum)."""
        nyquist = 0.5 * sr
        w0 = freq_hz / nyquist
        if w0 >= 1.0 or w0 <= 0.0:
            return audio
        b, a = signal.iirnotch(w0, q)
        audio_2d, was_1d = cls.ensure_2d(audio)
        out = np.zeros_like(audio_2d, dtype=np.float32)
        for ch in range(audio_2d.shape[1]):
            out[:, ch] = signal.filtfilt(b, a, audio_2d[:, ch])
        return cls.restore_shape(out, was_1d)

    @classmethod
    def peaking_eq(cls, audio: np.ndarray, sr: int, center_hz: float, gain_db: float, q: float = 1.0) -> np.ndarray:
        """Parametric peaking Bell EQ filter."""
        if abs(gain_db) < 0.05:
            return audio
        nyquist = 0.5 * sr
        w0 = 2 * np.pi * center_hz / sr
        alpha = np.sin(w0) / (2 * q)
        a_gain = 10.0 ** (gain_db / 40.0)  # sqrt(10^(gain/20))

        b0 = 1 + alpha * a_gain
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * a_gain
        a0 = 1 + alpha / a_gain
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / a_gain

        b = np.array([b0, b1, b2]) / a0
        a = np.array([a0, a1, a2]) / a0

        audio_2d, was_1d = cls.ensure_2d(audio)
        out = np.zeros_like(audio_2d, dtype=np.float32)
        for ch in range(audio_2d.shape[1]):
            out[:, ch] = signal.lfilter(b, a, audio_2d[:, ch])
        return cls.restore_shape(out, was_1d)

    # ---------------------------------------------------------
    # 2. DYNAMICS (Compressor, Limiter, Noise Gate)
    # ---------------------------------------------------------
    @classmethod
    def compressor(cls, audio: np.ndarray, sr: int,
                   threshold_db: float = -20.0,
                   ratio: float = 4.0,
                   attack_ms: float = 15.0,
                   release_ms: float = 120.0,
                   makeup_gain_db: float = 2.0) -> np.ndarray:
        """
        Studio-grade dynamic range compressor with smooth attack/release envelope.
        """
        audio_2d, was_1d = cls.ensure_2d(audio)
        num_samples, num_channels = audio_2d.shape

        attack_coeff = np.exp(-1.0 / (sr * (attack_ms / 1000.0)))
        release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))

        out = np.zeros_like(audio_2d, dtype=np.float32)

        for ch in range(num_channels):
            channel_data = audio_2d[:, ch]
            envelope = 0.0
            gain_reduction = np.ones(num_samples, dtype=np.float32)

            for i in range(num_samples):
                val = abs(channel_data[i])
                if val > envelope:
                    envelope = attack_coeff * envelope + (1 - attack_coeff) * val
                else:
                    envelope = release_coeff * envelope + (1 - release_coeff) * val

                env_db = 20.0 * np.log10(max(envelope, 1e-6))

                if env_db > threshold_db:
                    excess = env_db - threshold_db
                    target_db = threshold_db + excess / ratio
                    reduction_db = target_db - env_db
                    gain_reduction[i] = 10.0 ** (reduction_db / 20.0)
                else:
                    gain_reduction[i] = 1.0

            makeup = 10.0 ** (makeup_gain_db / 20.0)
            out[:, ch] = channel_data * gain_reduction * makeup

        return cls.restore_shape(out, was_1d)

    @classmethod
    def limiter(cls, audio: np.ndarray, sr: int, ceiling_db: float = -0.5, release_ms: float = 50.0) -> np.ndarray:
        """Lookahead peak limiter to prevent digital clipping."""
        audio_2d, was_1d = cls.ensure_2d(audio)
        ceiling_linear = 10.0 ** (ceiling_db / 20.0)
        num_samples, num_channels = audio_2d.shape

        # 3ms lookahead buffer
        lookahead = max(int(0.003 * sr), 1)
        release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))

        out = np.zeros_like(audio_2d, dtype=np.float32)

        for ch in range(num_channels):
            ch_data = audio_2d[:, ch]
            # Pad for lookahead
            padded = np.pad(ch_data, (0, lookahead), mode='constant')
            peaks = np.abs(padded)

            envelope = 0.0
            gains = np.ones(num_samples, dtype=np.float32)

            for i in range(num_samples):
                # Lookahead window max
                window_max = np.max(peaks[i:i + lookahead])
                if window_max > ceiling_linear:
                    target_gain = ceiling_linear / window_max
                else:
                    target_gain = 1.0

                if target_gain < envelope or envelope == 0.0:
                    envelope = target_gain
                else:
                    envelope = release_coeff * envelope + (1.0 - release_coeff) * target_gain

                gains[i] = envelope

            out[:, ch] = ch_data * gains

        # Safe hard clip safeguard at ceiling
        out = np.clip(out, -ceiling_linear, ceiling_linear)
        return cls.restore_shape(out, was_1d)

    @classmethod
    def noise_gate(cls, audio: np.ndarray, sr: int,
                   threshold_db: float = -42.0,
                   attack_ms: float = 5.0,
                   hold_ms: float = 40.0,
                   release_ms: float = 100.0) -> np.ndarray:
        """Downward noise gate to mute room noise between speech pauses."""
        audio_2d, was_1d = cls.ensure_2d(audio)
        threshold_linear = 10.0 ** (threshold_db / 20.0)
        num_samples, num_channels = audio_2d.shape

        attack_coeff = np.exp(-1.0 / (sr * (attack_ms / 1000.0)))
        release_coeff = np.exp(-1.0 / (sr * (release_ms / 1000.0)))
        hold_samples = int(sr * (hold_ms / 1000.0))

        out = np.zeros_like(audio_2d, dtype=np.float32)

        for ch in range(num_channels):
            ch_data = audio_2d[:, ch]
            gain = 0.0
            hold_count = 0

            for i in range(num_samples):
                level = abs(ch_data[i])
                if level >= threshold_linear:
                    hold_count = hold_samples
                    target_gain = 1.0
                elif hold_count > 0:
                    hold_count -= 1
                    target_gain = 1.0
                else:
                    target_gain = 0.0

                if target_gain > gain:
                    gain = attack_coeff * gain + (1.0 - attack_coeff) * target_gain
                else:
                    gain = release_coeff * gain + (1.0 - release_coeff) * target_gain

                out[i, ch] = ch_data[i] * gain

        return cls.restore_shape(out, was_1d)

    # ---------------------------------------------------------
    # 3. SPATIAL & TIME EFFECTS (Reverb, Delay, Stereo Width)
    # ---------------------------------------------------------
    @classmethod
    def reverb(cls, audio: np.ndarray, sr: int,
               room_size: float = 0.5,
               damping: float = 0.4,
               wet_dry: float = 0.25) -> np.ndarray:
        """
        Schroeder/Freeverb algorithmic reverberator with 4 parallel comb filters
        and 2 series all-pass diffusion stages.
        """
        audio_2d, was_1d = cls.ensure_2d(audio)
        num_samples, num_channels = audio_2d.shape

        comb_delays_ms = [29.7, 37.1, 41.1, 43.7]
        allpass_delays_ms = [5.0, 1.7]

        out = np.zeros_like(audio_2d, dtype=np.float32)

        for ch in range(num_channels):
            inp = audio_2d[:, ch]
            comb_sum = np.zeros(num_samples, dtype=np.float32)

            for d_ms in comb_delays_ms:
                d_samples = max(int(sr * d_ms / 1000.0), 1)
                buf = np.zeros(d_samples, dtype=np.float32)
                buf_idx = 0
                filtered_val = 0.0
                feedback = min(0.7 + room_size * 0.28, 0.98)
                damp = damping * 0.4

                comb_out = np.zeros(num_samples, dtype=np.float32)
                for i in range(num_samples):
                    delayed = buf[buf_idx]
                    filtered_val = delayed * (1.0 - damp) + filtered_val * damp
                    buf[buf_idx] = inp[i] + filtered_val * feedback
                    comb_out[i] = delayed
                    buf_idx = (buf_idx + 1) % d_samples

                comb_sum += comb_out

            comb_sum *= 0.25  # average comb branches

            # Series All-Pass Diffusers
            ap_signal = comb_sum
            for ap_ms in allpass_delays_ms:
                ap_samples = max(int(sr * ap_ms / 1000.0), 1)
                ap_buf = np.zeros(ap_samples, dtype=np.float32)
                ap_idx = 0
                g = 0.5
                ap_out = np.zeros(num_samples, dtype=np.float32)

                for i in range(num_samples):
                    ap_del = ap_buf[ap_idx]
                    ap_in = ap_signal[i]
                    temp = ap_in + ap_del * (-g)
                    ap_out[i] = ap_del + temp * g
                    ap_buf[ap_idx] = temp
                    ap_idx = (ap_idx + 1) % ap_samples

                ap_signal = ap_out

            dry = inp * (1.0 - wet_dry)
            wet = ap_signal * wet_dry
            out[:, ch] = dry + wet

        return cls.restore_shape(out, was_1d)

    @classmethod
    def delay(cls, audio: np.ndarray, sr: int,
              delay_ms: float = 250.0,
              feedback: float = 0.35,
              wet_dry: float = 0.3) -> np.ndarray:
        """Digital feedback delay effect."""
        audio_2d, was_1d = cls.ensure_2d(audio)
        num_samples, num_channels = audio_2d.shape
        delay_samples = max(int(sr * (delay_ms / 1000.0)), 1)

        out = np.zeros_like(audio_2d, dtype=np.float32)

        for ch in range(num_channels):
            inp = audio_2d[:, ch]
            delay_line = np.zeros(delay_samples, dtype=np.float32)
            d_idx = 0
            wet = np.zeros(num_samples, dtype=np.float32)

            fb = min(max(feedback, 0.0), 0.95)

            for i in range(num_samples):
                delayed = delay_line[d_idx]
                wet[i] = delayed
                delay_line[d_idx] = inp[i] + delayed * fb
                d_idx = (d_idx + 1) % delay_samples

            out[:, ch] = inp * (1.0 - wet_dry) + wet * wet_dry

        return cls.restore_shape(out, was_1d)

    @classmethod
    def stereo_width(cls, audio: np.ndarray, width: float = 1.0) -> np.ndarray:
        """
        Adjust stereo field using Mid/Side processing.
        width = 0.0 (Mono), width = 1.0 (Original), width = 2.0 (Double Wide).
        """
        audio_2d, was_1d = cls.ensure_2d(audio)
        if was_1d or audio_2d.shape[1] < 2:
            return audio

        left = audio_2d[:, 0]
        right = audio_2d[:, 1]

        mid = 0.5 * (left + right)
        side = 0.5 * (left - right) * width

        out = np.zeros_like(audio_2d, dtype=np.float32)
        out[:, 0] = mid + side
        out[:, 1] = mid - side
        return out

    # ---------------------------------------------------------
    # 4. UTILITIES (Normalize, Gain, Fades)
    # ---------------------------------------------------------
    @classmethod
    def normalize_peak(cls, audio: np.ndarray, target_db: float = -0.5) -> np.ndarray:
        """Peak normalization to specified target dBFS."""
        current_peak = np.max(np.abs(audio))
        if current_peak < 1e-7:
            return audio
        target_linear = 10.0 ** (target_db / 20.0)
        gain = target_linear / current_peak
        return audio * gain

    @classmethod
    def apply_gain(cls, audio: np.ndarray, gain_db: float) -> np.ndarray:
        """Apply linear gain from decibels."""
        if abs(gain_db) < 0.01:
            return audio
        linear_gain = 10.0 ** (gain_db / 20.0)
        return audio * linear_gain

    @classmethod
    def fade_in(cls, audio: np.ndarray, num_samples: int) -> np.ndarray:
        """Apply smooth cosine curve fade in."""
        if num_samples <= 0 or len(audio) == 0:
            return audio
        num_samples = min(num_samples, len(audio))
        fade_curve = 0.5 * (1.0 - np.cos(np.linspace(0, np.pi, num_samples)))
        audio_2d, was_1d = cls.ensure_2d(audio)
        out = audio_2d.copy()
        for ch in range(out.shape[1]):
            out[:num_samples, ch] *= fade_curve
        return cls.restore_shape(out, was_1d)

    @classmethod
    def fade_out(cls, audio: np.ndarray, num_samples: int) -> np.ndarray:
        """Apply smooth cosine curve fade out."""
        if num_samples <= 0 or len(audio) == 0:
            return audio
        num_samples = min(num_samples, len(audio))
        fade_curve = 0.5 * (1.0 + np.cos(np.linspace(0, np.pi, num_samples)))
        audio_2d, was_1d = cls.ensure_2d(audio)
        out = audio_2d.copy()
        for ch in range(out.shape[1]):
            out[-num_samples:, ch] *= fade_curve
        return cls.restore_shape(out, was_1d)

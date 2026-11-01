"""
SONORA Studio - Audio Effects Rack & DSP Chain
Modular effects processing with independent bypass, real-time calculation,
and high-fidelity signal flow.
"""

from typing import Dict, Any, Optional
import numpy as np

from app.audio.dsp import AudioDSP
from app.core.logger import get_logger

logger = get_logger("EffectsChain")


class EffectsChain:
    """Manages an ordered chain of mastering and vocal audio effects."""

    def __init__(self):
        # Default effect modules and settings
        self.highpass_enabled = False
        self.highpass_cutoff = 80.0

        self.lowpass_enabled = False
        self.lowpass_cutoff = 14000.0

        self.eq_enabled = False
        self.eq_low_gain = 0.0      # ~120 Hz
        self.eq_mid_gain = 0.0      # ~2.8 kHz
        self.eq_high_gain = 0.0     # ~10 kHz

        self.compressor_enabled = False
        self.comp_threshold_db = -18.0
        self.comp_ratio = 3.5
        self.comp_attack_ms = 15.0
        self.comp_release_ms = 120.0
        self.comp_makeup_db = 2.0

        self.gate_enabled = False
        self.gate_threshold_db = -45.0
        self.gate_release_ms = 100.0

        self.reverb_enabled = False
        self.reverb_room_size = 0.4
        self.reverb_damping = 0.3
        self.reverb_wet = 0.2

        self.delay_enabled = False
        self.delay_time_ms = 220.0
        self.delay_feedback = 0.3
        self.delay_wet = 0.25

        self.stereo_width_enabled = False
        self.stereo_width_factor = 1.0  # 0.0 to 2.0

        self.limiter_enabled = True
        self.limiter_ceiling_db = -0.5

        self.master_gain_db = 0.0

    def process(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Execute effects chain in sequence: Gate -> HPF/LPF -> EQ -> Compressor -> Reverb/Delay -> Width -> Limiter -> Gain."""
        if audio is None or len(audio) == 0:
            return audio

        out = audio.copy().astype(np.float32)

        # 1. Noise Gate
        if self.gate_enabled:
            out = AudioDSP.noise_gate(out, sr, threshold_db=self.gate_threshold_db, release_ms=self.gate_release_ms)

        # 2. High-pass filter
        if self.highpass_enabled:
            out = AudioDSP.highpass_filter(out, sr, cutoff_hz=self.highpass_cutoff)

        # 3. Low-pass filter
        if self.lowpass_enabled:
            out = AudioDSP.lowpass_filter(out, sr, cutoff_hz=self.lowpass_cutoff)

        # 4. 3-Band Parametric Equalizer
        if self.eq_enabled:
            if abs(self.eq_low_gain) > 0.1:
                out = AudioDSP.peaking_eq(out, sr, center_hz=140.0, gain_db=self.eq_low_gain, q=0.9)
            if abs(self.eq_mid_gain) > 0.1:
                out = AudioDSP.peaking_eq(out, sr, center_hz=2800.0, gain_db=self.eq_mid_gain, q=1.2)
            if abs(self.eq_high_gain) > 0.1:
                out = AudioDSP.peaking_eq(out, sr, center_hz=10000.0, gain_db=self.eq_high_gain, q=0.8)

        # 5. Dynamic Compressor
        if self.compressor_enabled:
            out = AudioDSP.compressor(
                out, sr,
                threshold_db=self.comp_threshold_db,
                ratio=self.comp_ratio,
                attack_ms=self.comp_attack_ms,
                release_ms=self.comp_release_ms,
                makeup_gain_db=self.comp_makeup_db
            )

        # 6. Reverb
        if self.reverb_enabled:
            out = AudioDSP.reverb(out, sr, room_size=self.reverb_room_size, damping=self.reverb_damping, wet_dry=self.reverb_wet)

        # 7. Delay
        if self.delay_enabled:
            out = AudioDSP.delay(out, sr, delay_ms=self.delay_time_ms, feedback=self.delay_feedback, wet_dry=self.delay_wet)

        # 8. Stereo Width
        if self.stereo_width_enabled:
            out = AudioDSP.stereo_width(out, width=self.stereo_width_factor)

        # 9. Master Gain
        if abs(self.master_gain_db) > 0.05:
            out = AudioDSP.apply_gain(out, self.master_gain_db)

        # 10. Limiter (Peak safeguard)
        if self.limiter_enabled:
            out = AudioDSP.limiter(out, sr, ceiling_db=self.limiter_ceiling_db)

        return out

    def load_preset(self, preset_dict: Dict[str, Any]):
        """Load values from preset dictionary."""
        for key, val in preset_dict.items():
            if hasattr(self, key):
                setattr(self, key, val)

    def to_dict(self) -> Dict[str, Any]:
        """Export current settings as dictionary."""
        return {
            "highpass_enabled": self.highpass_enabled,
            "highpass_cutoff": self.highpass_cutoff,
            "lowpass_enabled": self.lowpass_enabled,
            "lowpass_cutoff": self.lowpass_cutoff,
            "eq_enabled": self.eq_enabled,
            "eq_low_gain": self.eq_low_gain,
            "eq_mid_gain": self.eq_mid_gain,
            "eq_high_gain": self.eq_high_gain,
            "compressor_enabled": self.compressor_enabled,
            "comp_threshold_db": self.comp_threshold_db,
            "comp_ratio": self.comp_ratio,
            "comp_attack_ms": self.comp_attack_ms,
            "comp_release_ms": self.comp_release_ms,
            "comp_makeup_db": self.comp_makeup_db,
            "gate_enabled": self.gate_enabled,
            "gate_threshold_db": self.gate_threshold_db,
            "gate_release_ms": self.gate_release_ms,
            "reverb_enabled": self.reverb_enabled,
            "reverb_room_size": self.reverb_room_size,
            "reverb_damping": self.reverb_damping,
            "reverb_wet": self.reverb_wet,
            "delay_enabled": self.delay_enabled,
            "delay_time_ms": self.delay_time_ms,
            "delay_feedback": self.delay_feedback,
            "delay_wet": self.delay_wet,
            "stereo_width_enabled": self.stereo_width_enabled,
            "stereo_width_factor": self.stereo_width_factor,
            "limiter_enabled": self.limiter_enabled,
            "limiter_ceiling_db": self.limiter_ceiling_db,
            "master_gain_db": self.master_gain_db,
        }


# Global effects chain instance
effects_chain = EffectsChain()

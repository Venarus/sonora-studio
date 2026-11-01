"""
Unit tests for DSP and AI processing in SONORA Studio.
"""

import unittest
import numpy as np
from app.audio.dsp import AudioDSP
from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.noise_cleaner import NoiseCleaner
from app.ai.voice_restoration import VoiceRestoration
from app.effects.effects_chain import EffectsChain
from app.effects.presets import STUDIO_PRESETS


class TestDSPAndAI(unittest.TestCase):

    def setUp(self):
        self.sr = 44100
        # 1-second 440 Hz test tone + 50 Hz hum + noise
        t = np.linspace(0, 1.0, self.sr, False)
        tone = 0.4 * np.sin(2 * np.pi * 440 * t)
        hum = 0.2 * np.sin(2 * np.pi * 50 * t)
        noise = 0.05 * np.random.normal(0, 1, self.sr)
        self.test_signal = (tone + hum + noise).astype(np.float32)
        # Stereo version
        self.test_stereo = np.column_stack([self.test_signal, self.test_signal])

    def test_highpass_and_lowpass(self):
        hp = AudioDSP.highpass_filter(self.test_signal, self.sr, cutoff_hz=100.0)
        self.assertEqual(len(hp), len(self.test_signal))
        self.assertFalse(np.isnan(hp).any())

        lp = AudioDSP.lowpass_filter(self.test_stereo, self.sr, cutoff_hz=8000.0)
        self.assertEqual(lp.shape, self.test_stereo.shape)
        self.assertFalse(np.isnan(lp).any())

    def test_notch_filter_hum(self):
        notched = AudioDSP.notch_filter(self.test_signal, self.sr, freq_hz=50.0)
        self.assertEqual(len(notched), len(self.test_signal))
        # Hum energy should be lower
        self.assertLess(np.var(notched), np.var(self.test_signal))

    def test_compressor_and_limiter(self):
        comp = AudioDSP.compressor(self.test_signal, self.sr, threshold_db=-15.0, ratio=4.0)
        self.assertEqual(len(comp), len(self.test_signal))
        self.assertFalse(np.isnan(comp).any())

        # Test limiter with high signal
        loud_signal = self.test_signal * 3.0
        limited = AudioDSP.limiter(loud_signal, self.sr, ceiling_db=-0.5)
        max_peak = np.max(np.abs(limited))
        self.assertLessEqual(max_peak, 1.0)

    def test_reverb_and_delay(self):
        rev = AudioDSP.reverb(self.test_stereo, self.sr, room_size=0.5, damping=0.3, wet_dry=0.3)
        self.assertEqual(rev.shape, self.test_stereo.shape)

        del_sig = AudioDSP.delay(self.test_signal, self.sr, delay_ms=100.0, feedback=0.3, wet_dry=0.3)
        self.assertEqual(len(del_sig), len(self.test_signal))

    def test_audio_analyzer(self):
        report = AudioAnalyzer.analyze(self.test_signal, self.sr)
        self.assertIn("peak_db", report)
        self.assertIn("rms_db", report)
        self.assertIn("snr_db", report)
        self.assertIn("has_hum_50hz", report)
        self.assertTrue(report["has_hum_50hz"])

    def test_noise_cleaner_fast(self):
        cleaned = NoiseCleaner.fast_spectral_subtraction(self.test_signal, self.sr, intensity_pct=60.0)
        self.assertEqual(len(cleaned), len(self.test_signal))
        self.assertFalse(np.isnan(cleaned).any())

    def test_voice_restoration(self):
        de_hummed = VoiceRestoration.remove_hum(self.test_signal, self.sr, base_freq=50.0)
        self.assertEqual(len(de_hummed), len(self.test_signal))

        de_essed = VoiceRestoration.de_esser(self.test_signal, self.sr)
        self.assertEqual(len(de_essed), len(self.test_signal))

        de_clicked = VoiceRestoration.de_click(self.test_signal, self.sr)
        self.assertEqual(len(de_clicked), len(self.test_signal))

        enhanced = VoiceRestoration.enhance_voice(self.test_signal, self.sr)
        self.assertEqual(len(enhanced), len(self.test_signal))

    def test_effects_rack_and_presets(self):
        rack = EffectsChain()
        preset = STUDIO_PRESETS["Temiz Ses (Clean Voice)"]
        rack.load_preset(preset)
        out = rack.process(self.test_stereo, self.sr)
        self.assertEqual(out.shape, self.test_stereo.shape)


if __name__ == '__main__':
    unittest.main()

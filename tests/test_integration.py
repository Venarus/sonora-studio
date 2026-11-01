"""
End-to-End integration test for SONORA Studio workflows.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf

from app.config import config
from app.audio.recording_engine import recorder
from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.noise_cleaner import NoiseCleaner
from app.ai.voice_restoration import VoiceRestoration
from app.editor.audio_buffer import editor_buffer
from app.library.file_manager import library
from app.export.exporter import AudioExporter


class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.orig_rec_dir = config.get("recordings_dir")
        self.orig_exp_dir = config.get("exports_dir")

        self.test_dir = tempfile.mkdtemp()
        config.set("recordings_dir", self.test_dir)
        config.set("exports_dir", self.test_dir)

        # Generate a test speech+noise signal
        self.sr = 48000
        duration = 2.0
        t = np.linspace(0, duration, int(self.sr * duration), False)
        voice = 0.3 * np.sin(2 * np.pi * 150 * t) + 0.15 * np.sin(2 * np.pi * 300 * t)
        noise = 0.04 * np.random.normal(0, 1, len(t))
        hum = 0.08 * np.sin(2 * np.pi * 50 * t)

        self.synth_audio = np.column_stack([voice + noise + hum, voice + noise + hum]).astype(np.float32)
        self.raw_wav = os.path.join(self.test_dir, "test_raw_recording.wav")
        sf.write(self.raw_wav, self.synth_audio, self.sr)

    def tearDown(self):
        # Restore original config
        config.set("recordings_dir", self.orig_rec_dir)
        config.set("exports_dir", self.orig_exp_dir)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_complete_workflow(self):
        # 1. File verification in Library
        items = library.list_recordings()
        self.assertGreaterEqual(len(items), 1)
        item = items[0]
        self.assertIn("test_raw_recording", item.name)
        self.assertAlmostEqual(item.duration_sec, 2.0, delta=0.1)

        # 2. Acoustic Analysis
        report = AudioAnalyzer.analyze(self.synth_audio, self.sr)
        self.assertIn("snr_db", report)
        self.assertIn("peak_db", report)
        self.assertTrue(report["has_hum_50hz"])

        # 3. AI Cleaning Pipeline (Non-destructive)
        de_hummed = VoiceRestoration.remove_hum(self.synth_audio, self.sr, base_freq=50.0)
        cleaned = NoiseCleaner.fast_spectral_subtraction(de_hummed, self.sr, intensity_pct=75.0)
        enhanced = VoiceRestoration.enhance_voice(cleaned, self.sr, clarity_pct=60.0)

        clean_wav = os.path.join(self.test_dir, "test_raw_recording_temizlenmis.wav")
        sf.write(clean_wav, enhanced, self.sr)

        self.assertTrue(os.path.exists(self.raw_wav))
        self.assertTrue(os.path.exists(clean_wav))

        # 4. Audio Editor Load, Selection, Backspace Cut & Crop
        buf = editor_buffer
        self.assertTrue(buf.load_file(clean_wav))
        self.assertEqual(buf.channels, 2)

        # Select first 0.5s and delete (simulate Backspace)
        buf.set_selection_sec(0.0, 0.5)
        self.assertTrue(buf.delete_selection())
        self.assertEqual(buf.total_samples, int(self.sr * 1.5))
        self.assertTrue(buf.can_undo())
        # Undo
        self.assertTrue(buf.undo())
        self.assertEqual(buf.total_samples, int(self.sr * 2.0))

        # Select middle and trim
        buf.set_selection_sec(0.5, 1.5)
        self.assertTrue(buf.trim())
        self.assertEqual(buf.total_samples, int(self.sr * 1.0))

        # 5. Export
        flac_out = os.path.join(self.test_dir, "master_output.flac")
        success_flac = AudioExporter.export(
            audio=buf.data,
            src_sr=buf.sample_rate,
            output_path=flac_out,
            export_format="FLAC",
            target_sr=48000,
            channels=2,
            bit_depth="PCM_24"
        )
        self.assertTrue(success_flac)
        self.assertTrue(os.path.exists(flac_out))

        # 6. Library Operations: Duplicate & Delete
        dup_file = library.duplicate_file(Path(clean_wav))
        self.assertIsNotNone(dup_file)
        self.assertTrue(dup_file.exists())

        del_count = library.delete_files([dup_file])
        self.assertEqual(del_count, 1)
        self.assertFalse(dup_file.exists())


if __name__ == '__main__':
    unittest.main()

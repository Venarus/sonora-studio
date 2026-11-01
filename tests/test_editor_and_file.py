"""
Unit tests for AudioBuffer, Editor operations, RecordingLibrary, and Exporter.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
import soundfile as sf

from app.editor.audio_buffer import AudioBuffer
from app.library.file_manager import RecordingLibrary
from app.export.exporter import AudioExporter


class TestEditorAndFile(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sr = 44100
        # 1 second test audio
        t = np.linspace(0, 1.0, self.sr, False)
        self.test_audio = np.column_stack([0.3 * np.sin(2 * np.pi * 440 * t), 0.3 * np.cos(2 * np.pi * 440 * t)]).astype(np.float32)

        # Write test wav
        self.test_wav = os.path.join(self.temp_dir, "test_input.wav")
        sf.write(self.test_wav, self.test_audio, self.sr)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audio_buffer_load_and_undo(self):
        buf = AudioBuffer()
        loaded = buf.load_file(self.test_wav)
        self.assertTrue(loaded)
        self.assertEqual(buf.total_samples, self.sr)
        self.assertEqual(buf.channels, 2)

        # Cut half of it
        buf.set_selection_sec(0.0, 0.5)
        self.assertTrue(buf.cut())
        self.assertEqual(buf.total_samples, int(self.sr * 0.5))
        self.assertTrue(buf.can_undo())

        # Undo cut
        self.assertTrue(buf.undo())
        self.assertEqual(buf.total_samples, self.sr)
        self.assertTrue(buf.can_redo())

        # Redo cut
        self.assertTrue(buf.redo())
        self.assertEqual(buf.total_samples, int(self.sr * 0.5))

    def test_editor_operations(self):
        buf = AudioBuffer()
        buf.load_file(self.test_wav)

        # Normalize
        self.assertTrue(buf.normalize(-1.0))
        peak = np.max(np.abs(buf.data))
        self.assertAlmostEqual(peak, 10.0 ** (-1.0 / 20.0), places=3)

        # Fade in & Fade out
        self.assertTrue(buf.fade_in(0.2))
        self.assertTrue(buf.fade_out(0.2))

        # Reverse
        self.assertTrue(buf.reverse())

        # Channel conversion (Stereo -> Mono -> Stereo)
        self.assertTrue(buf.convert_channels("mono"))
        self.assertEqual(buf.channels, 1)
        self.assertTrue(buf.convert_channels("stereo"))
        self.assertEqual(buf.channels, 2)

    def test_exporter(self):
        out_wav = os.path.join(self.temp_dir, "exported.wav")
        success = AudioExporter.export(
            audio=self.test_audio,
            src_sr=self.sr,
            output_path=out_wav,
            export_format="WAV",
            target_sr=48000,
            channels=2,
            bit_depth="PCM_24",
            normalize=True,
            normalize_db=-0.5
        )
        self.assertTrue(success)
        self.assertTrue(os.path.exists(out_wav))

        # Check exported properties
        info = sf.info(out_wav)
        self.assertEqual(info.samplerate, 48000)
        self.assertEqual(info.channels, 2)

    def test_file_manager_operations(self):
        lib = RecordingLibrary()
        file_path = Path(self.test_wav)

        # Duplicate
        dup_path = lib.duplicate_file(file_path)
        self.assertIsNotNone(dup_path)
        self.assertTrue(dup_path.exists())

        # Rename
        renamed = lib.rename_file(dup_path, "renamed_file.wav")
        self.assertIsNotNone(renamed)
        self.assertTrue(renamed.exists())
        self.assertEqual(renamed.name, "renamed_file.wav")

        # Delete
        deleted = lib.delete_files([renamed])
        self.assertEqual(deleted, 1)
        self.assertFalse(renamed.exists())


if __name__ == '__main__':
    unittest.main()

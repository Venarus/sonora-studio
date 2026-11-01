# Changelog

All notable changes to the **SONORA Studio** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-01

### Added
- **Unified Recording & Waveform Editing Studio (`StudioEditorView`):**
  - Instant hardware enumeration (WASAPI, DirectSound, MME) with sample rates up to 96 kHz.
  - Live 30 FPS oscilloscope with rolling NumPy ring buffer.
  - Dual stereo peak & RMS level meter with hardware clipping warning LED.
  - Interactive multi-channel waveform editor with `QPixmap` layer caching.
  - Keyboard editing: select any audio segment and delete with `Backspace` or `Delete`.
  - Multi-level Undo & Redo (`Ctrl+Z`, `Ctrl+Y`).
  - Region Crop (`Kırp`), Normalization (-0.5 dBFS), Fade In, Fade Out, and manual gain adjustment (+/- dB).
  - Quick in-place save (`Ctrl+S`) and multi-format Save As (`WAV`, `FLAC`, `MP3`).
- **AI Audio Cleaning Studio (`AICleaningStudioView`):**
  - Acoustic Analysis: Peak dB, RMS dB, SNR (Signal-to-Noise Ratio), 50/60 Hz electrical hum detection, clipping & silence percentage.
  - Adaptive & Spectral Gating AI noise reduction for computer fans, AC hiss, and stationary rumble.
  - Speech formant enhancement and vocal clarity isolation.
  - Multi-stage de-reverb, de-click, de-esser, and de-plosive processing.
  - Seamless A/B instant audio comparison switch during playback.
  - 100% non-destructive processing pipeline.
- **Mastering Audio Effects Rack (`AudioEffectsView`):**
  - 3-band parametric EQ (Low, Mid, High).
  - High-pass and Low-pass filters.
  - Dynamic compressor with threshold, ratio, attack, release, and makeup gain.
  - Studio Reverb (Freeverb algorithm) and digital Delay with feedback.
  - Peak Limiter with soft-knee ceiling protection.
  - Curated studio presets: *Clean Voice*, *Natural Speech*, *Warm Radio/Podcast*, *Crystal Clear*, *Studio Recording*.
- **Live Synchronized Recording Library (`RightLibraryPanel`):**
  - Dual-layer filesystem monitoring with `QFileSystemWatcher` and 400ms `os.scandir` poller.
  - Instant metadata parser for duration, sample rate, channels, file size, and modification timestamp.
  - Quick inline playback and favorite starring.
  - Context menu with Windows Explorer integration (`explorer /select,filepath`), duplication, renaming, copying, and deletion.
- **Top Studio Ribbon (`TopStudioBar`):**
  - Modern Windows 11 header ribbon with dropdown menus for fast access to cleaning algorithms, effect presets, and direct export.
- **Multi-Format Export Center (`ExportCenterView`):**
  - High-fidelity polyphase resampling (44.1 kHz, 48 kHz, 96 kHz).
  - Export presets for Studio Master WAV (24-bit), Lossless FLAC, and High-Quality MP3.
  - Custom audio metadata tagging (Title, Artist, Album, Year, Notes).

### Fixed
- Fixed mono USB microphone initialization (`PaErrorCode -9998 Invalid number of channels`) by detecting hardware channel limits and automatically broadcasting mono streams to stereo.
- Fixed UI lag and audio stutter by decoupling real-time PortAudio callbacks from the Qt GUI main thread via atomic shared floats.
- Resolved right-sidebar library crash caused by invalid font prefix `fa5r.star` by migrating to Remix Icons (`ri.star-line` and `ri.star-fill`).

---

### Planned (Roadmap)
- [ ] VST3 / CLAP plugin hosting support.
- [ ] Multitrack overdubbing and multi-mic recording sessions.
- [ ] Real-time AI noise reduction during live recording.
- [ ] Pitch correction and vocal tuning module.

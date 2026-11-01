"""
SONORA Studio - Audio Effects Studio Rack View
Mastering and vocal rack featuring multi-band EQ, compressor, limiter,
noise gate, reverb, delay, stereo widening, and studio presets.
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QFileDialog, QSlider, QCheckBox,
                               QComboBox, QGridLayout, QScrollArea)
import qtawesome as qta
import numpy as np
import soundfile as sf

from app.effects.effects_chain import effects_chain
from app.effects.presets import STUDIO_PRESETS
from app.audio.playback_engine import player
from app.core.signals import signals
from app.config import config
from ui.widgets.timeline_waveform import TimelineWaveformWidget


class AudioEffectsView(QWidget):
    """Studio effects rack with interactive visual modules."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_audio: Optional[np.ndarray] = None
        self.processed_audio: Optional[np.ndarray] = None
        self.sample_rate = 44100
        self.current_filepath: Optional[str] = None

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # 1. TOP HEADER & PRESET PICKER
        top_card = QFrame()
        top_card.setObjectName("cardFrame")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(14)

        self.btn_load = QPushButton(" Dosya Aç")
        self.btn_load.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self.btn_load.clicked.connect(self._select_file_dialog)
        top_layout.addWidget(self.btn_load)

        self.file_lbl = QLabel("Efekt uygulamak için bir ses seçin.")
        self.file_lbl.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        top_layout.addWidget(self.file_lbl, 1)

        preset_lbl = QLabel("Stüdyo Önayarı:")
        preset_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 600;")
        top_layout.addWidget(preset_lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(210)
        for name in STUDIO_PRESETS.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        top_layout.addWidget(self.preset_combo)

        root_layout.addWidget(top_card)

        # 2. SCROLLABLE EFFECTS RACK
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        rack_grid = QGridLayout()
        rack_grid.setSpacing(12)

        # Module 1: Equalizer
        eq_card, self.cb_eq, self.sl_eq_low, self.sl_eq_mid, self.sl_eq_high = self._create_eq_card()
        rack_grid.addWidget(eq_card, 0, 0)

        # Module 2: Compressor
        comp_card, self.cb_comp, self.sl_comp_thresh, self.sl_comp_ratio, self.sl_comp_makeup = self._create_compressor_card()
        rack_grid.addWidget(comp_card, 0, 1)

        # Module 3: Filters (HPF / LPF)
        filter_card, self.cb_hpf, self.sl_hpf, self.cb_lpf, self.sl_lpf = self._create_filters_card()
        rack_grid.addWidget(filter_card, 1, 0)

        # Module 4: Noise Gate
        gate_card, self.cb_gate, self.sl_gate_thresh = self._create_gate_card()
        rack_grid.addWidget(gate_card, 1, 1)

        # Module 5: Reverb
        rev_card, self.cb_rev, self.sl_rev_room, self.sl_rev_wet = self._create_reverb_card()
        rack_grid.addWidget(rev_card, 2, 0)

        # Module 6: Delay
        del_card, self.cb_del, self.sl_del_time, self.sl_del_wet = self._create_delay_card()
        rack_grid.addWidget(del_card, 2, 1)

        # Module 7: Stereo Width & Limiter
        master_card, self.cb_width, self.sl_width, self.cb_limiter, self.sl_gain = self._create_master_card()
        rack_grid.addWidget(master_card, 3, 0, 1, 2)

        content_layout.addLayout(rack_grid)
        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll, 1)

        # 3. INTERACTIVE TIMELINE WAVEFORM
        wave_card = QFrame()
        wave_card.setObjectName("cardFrame")
        wc_layout = QVBoxLayout(wave_card)
        wc_layout.setContentsMargins(10, 8, 10, 8)
        self.timeline = TimelineWaveformWidget()
        self.timeline.setFixedHeight(120)
        wc_layout.addWidget(self.timeline)
        root_layout.addWidget(wave_card)

        # 4. BOTTOM ACTION BAR
        bot_card = QFrame()
        bot_card.setObjectName("cardFrame")
        bot_layout = QHBoxLayout(bot_card)
        bot_layout.setContentsMargins(14, 10, 14, 10)
        bot_layout.setSpacing(12)

        self.btn_preview = QPushButton("  Efektleri Dinle")
        self.btn_preview.setIcon(qta.icon("fa5s.play", color="#0D0E12"))
        self.btn_preview.setObjectName("primaryButton")
        self.btn_preview.setMinimumHeight(42)
        self.btn_preview.clicked.connect(self._render_and_play)
        bot_layout.addWidget(self.btn_preview)

        bot_layout.addStretch()

        self.btn_save = QPushButton(" Efektli Olarak Kaydet")
        self.btn_save.setIcon(qta.icon("fa5s.save", color="#FFFFFF"))
        self.btn_save.setMinimumHeight(42)
        self.btn_save.clicked.connect(self._save_effects_file)
        bot_layout.addWidget(self.btn_save)

        root_layout.addWidget(bot_card)

    def _create_eq_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        h = QHBoxLayout()
        cb = QCheckBox("3-Bant Parametrik Ekolayzer")
        cb.setChecked(True)
        cb.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        h.addWidget(cb)
        h.addStretch()
        h.addWidget(QLabel("EQ"))
        l.addLayout(h)

        sl_low = self._add_param_slider(l, "Bas (140 Hz)", -12, 12, 0, "dB")
        sl_mid = self._add_param_slider(l, "Vokal Mid (2.8 kHz)", -12, 12, 2, "dB")
        sl_high = self._add_param_slider(l, "Tiz Hava (10 kHz)", -12, 12, 2, "dB")
        return card, cb, sl_low, sl_mid, sl_high

    def _create_compressor_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        h = QHBoxLayout()
        cb = QCheckBox("Dinamik Stüdyo Kompresör")
        cb.setChecked(True)
        cb.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        h.addWidget(cb)
        h.addStretch()
        h.addWidget(QLabel("COMP"))
        l.addLayout(h)

        sl_thresh = self._add_param_slider(l, "Eşik (Threshold)", -40, 0, -20, "dB")
        sl_ratio = self._add_param_slider(l, "Oran (Ratio)", 1, 10, 3, ":1")
        sl_makeup = self._add_param_slider(l, "Makyaj Kazancı", 0, 12, 2, "dB")
        return card, cb, sl_thresh, sl_ratio, sl_makeup

    def _create_filters_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        cb_hpf = QCheckBox("Yüksek Geçiren Filtre (HPF / Dip Kesici)")
        cb_hpf.setChecked(True)
        cb_hpf.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        l.addWidget(cb_hpf)
        sl_hpf = self._add_param_slider(l, "Kesim Frekansı", 20, 200, 80, "Hz")

        cb_lpf = QCheckBox("Alçak Geçiren Filtre (LPF / Tıs Kesici)")
        cb_lpf.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        l.addWidget(cb_lpf)
        sl_lpf = self._add_param_slider(l, "Kesim Frekansı", 8000, 18000, 14000, "Hz")
        return card, cb_hpf, sl_hpf, cb_lpf, sl_lpf

    def _create_gate_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        cb = QCheckBox("Gürültü Kapısı (Noise Gate)")
        cb.setChecked(True)
        cb.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        l.addWidget(cb)

        sl_thresh = self._add_param_slider(l, "Açılma Eşiği", -60, -20, -45, "dB")
        return card, cb, sl_thresh

    def _create_reverb_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        cb = QCheckBox("Stüdyo Oda Yankısı (Reverb)")
        cb.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        l.addWidget(cb)

        sl_room = self._add_param_slider(l, "Oda Boyutu", 10, 90, 35, "%")
        sl_wet = self._add_param_slider(l, "Karışım (Wet)", 0, 50, 15, "%")
        return card, cb, sl_room, sl_wet

    def _create_delay_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)

        cb = QCheckBox("Dijital Gecikme (Delay)")
        cb.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        l.addWidget(cb)

        sl_time = self._add_param_slider(l, "Gecikme Süresi", 50, 600, 220, "ms")
        sl_wet = self._add_param_slider(l, "Karışım (Wet)", 0, 50, 20, "%")
        return card, cb, sl_time, sl_wet

    def _create_master_card(self):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QHBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(20)

        # Width
        w_v = QVBoxLayout()
        cb_width = QCheckBox("Stereo Genişletme")
        cb_width.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        w_v.addWidget(cb_width)
        sl_width = self._add_param_slider(w_v, "Genişlik", 0, 200, 100, "%")
        l.addLayout(w_v, 1)

        # Master Gain & Limiter
        m_v = QVBoxLayout()
        cb_limiter = QCheckBox("Tepe Sınırlayıcı (Limiter -0.5 dB)")
        cb_limiter.setChecked(True)
        cb_limiter.setStyleSheet("font-weight: 700; color: #FFFFFF;")
        m_v.addWidget(cb_limiter)
        sl_gain = self._add_param_slider(m_v, "Master Çıkış Kazancı", -12, 12, 0, "dB")
        l.addLayout(m_v, 1)

        return card, cb_width, sl_width, cb_limiter, sl_gain

    def _add_param_slider(self, layout, name: str, min_val: int, max_val: int, cur_val: int, unit: str):
        row = QHBoxLayout()
        lbl = QLabel(name)
        lbl.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        row.addWidget(lbl)

        sl = QSlider(Qt.Horizontal)
        sl.setRange(min_val, max_val)
        sl.setValue(cur_val)
        row.addWidget(sl, 1)

        val_lbl = QLabel(f"{cur_val} {unit}")
        val_lbl.setStyleSheet("font-size: 11px; color: #00E5A3; font-weight: 700; min-width: 50px;")
        sl.valueChanged.connect(lambda v: val_lbl.setText(f"{v} {unit}"))
        row.addWidget(val_lbl)

        layout.addLayout(row)
        return sl

    def _connect_signals(self):
        signals.audio_loaded_for_effects.connect(self.load_audio_file)
        signals.playback_position_changed.connect(lambda cur, tot: self.timeline.set_playhead_position(cur))
        signals.playback_state_changed.connect(self._on_playback_state_changed)

    def load_audio_file(self, filepath: str):
        try:
            data, sr = sf.read(filepath, dtype='float32')
            if data.ndim == 1:
                data = data[:, np.newaxis]
            self.raw_audio = data.astype(np.float32)
            self.sample_rate = sr
            self.current_filepath = filepath
            self.file_lbl.setText(Path(filepath).name)
            self.timeline.set_audio_data(self.raw_audio, self.sample_rate)
            signals.toast_requested.emit(f"Ses yüklendi: {Path(filepath).name}", "info")
        except Exception as e:
            signals.toast_requested.emit(f"Ses açılamadı: {e}", "error")

    def _select_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Efekt Uygulanacak Sesi Seç", "", "Ses Dosyaları (*.wav *.flac *.mp3 *.ogg *.aiff *.m4a)"
        )
        if path:
            self.load_audio_file(path)

    def _on_preset_selected(self):
        name = self.preset_combo.currentText()
        if name in STUDIO_PRESETS:
            p = STUDIO_PRESETS[name]
            effects_chain.load_preset(p)
            self._sync_chain_to_ui()
            signals.toast_requested.emit(f"'{name}' önayarı yüklendi.", "info")

    def _sync_chain_to_ui(self):
        self.cb_eq.setChecked(effects_chain.eq_enabled)
        self.sl_eq_low.setValue(int(effects_chain.eq_low_gain))
        self.sl_eq_mid.setValue(int(effects_chain.eq_mid_gain))
        self.sl_eq_high.setValue(int(effects_chain.eq_high_gain))

        self.cb_comp.setChecked(effects_chain.compressor_enabled)
        self.sl_comp_thresh.setValue(int(effects_chain.comp_threshold_db))
        self.sl_comp_ratio.setValue(int(effects_chain.comp_ratio))
        self.sl_comp_makeup.setValue(int(effects_chain.comp_makeup_db))

        self.cb_hpf.setChecked(effects_chain.highpass_enabled)
        self.sl_hpf.setValue(int(effects_chain.highpass_cutoff))

        self.cb_lpf.setChecked(effects_chain.lowpass_enabled)
        self.sl_lpf.setValue(int(effects_chain.lowpass_cutoff))

        self.cb_gate.setChecked(effects_chain.gate_enabled)
        self.sl_gate_thresh.setValue(int(effects_chain.gate_threshold_db))

        self.cb_rev.setChecked(effects_chain.reverb_enabled)
        self.sl_rev_room.setValue(int(effects_chain.reverb_room_size * 100))
        self.sl_rev_wet.setValue(int(effects_chain.reverb_wet * 100))

        self.cb_del.setChecked(effects_chain.delay_enabled)
        self.sl_del_time.setValue(int(effects_chain.delay_time_ms))
        self.sl_del_wet.setValue(int(effects_chain.delay_wet * 100))

        self.cb_width.setChecked(effects_chain.stereo_width_enabled)
        self.sl_width.setValue(int(effects_chain.stereo_width_factor * 100))

        self.cb_limiter.setChecked(effects_chain.limiter_enabled)
        self.sl_gain.setValue(int(effects_chain.master_gain_db))

    def _sync_ui_to_chain(self):
        effects_chain.eq_enabled = self.cb_eq.isChecked()
        effects_chain.eq_low_gain = float(self.sl_eq_low.value())
        effects_chain.eq_mid_gain = float(self.sl_eq_mid.value())
        effects_chain.eq_high_gain = float(self.sl_eq_high.value())

        effects_chain.compressor_enabled = self.cb_comp.isChecked()
        effects_chain.comp_threshold_db = float(self.sl_comp_thresh.value())
        effects_chain.comp_ratio = float(self.sl_comp_ratio.value())
        effects_chain.comp_makeup_db = float(self.sl_comp_makeup.value())

        effects_chain.highpass_enabled = self.cb_hpf.isChecked()
        effects_chain.highpass_cutoff = float(self.sl_hpf.value())

        effects_chain.lowpass_enabled = self.cb_lpf.isChecked()
        effects_chain.lowpass_cutoff = float(self.sl_lpf.value())

        effects_chain.gate_enabled = self.cb_gate.isChecked()
        effects_chain.gate_threshold_db = float(self.sl_gate_thresh.value())

        effects_chain.reverb_enabled = self.cb_rev.isChecked()
        effects_chain.reverb_room_size = self.sl_rev_room.value() / 100.0
        effects_chain.reverb_wet = self.sl_rev_wet.value() / 100.0

        effects_chain.delay_enabled = self.cb_del.isChecked()
        effects_chain.delay_time_ms = float(self.sl_del_time.value())
        effects_chain.delay_wet = self.sl_del_wet.value() / 100.0

        effects_chain.stereo_width_enabled = self.cb_width.isChecked()
        effects_chain.stereo_width_factor = self.sl_width.value() / 100.0

        effects_chain.limiter_enabled = self.cb_limiter.isChecked()
        effects_chain.master_gain_db = float(self.sl_gain.value())

    def _render_and_play(self):
        if self.raw_audio is None:
            return

        self._sync_ui_to_chain()
        self.processed_audio = effects_chain.process(self.raw_audio, self.sample_rate)

        # Load into player and play
        player.load_buffer(self.processed_audio, self.sample_rate)
        player.play()

        self.timeline.set_audio_data(self.processed_audio, self.sample_rate)

    def _on_playback_state_changed(self, is_playing: bool, is_paused: bool):
        if is_playing and not is_paused:
            self.btn_preview.setIcon(qta.icon("fa5s.pause", color="#EF4444"))
            self.btn_preview.setText("  Duraklat")
        else:
            self.btn_preview.setIcon(qta.icon("fa5s.play", color="#0D0E12"))
            self.btn_preview.setText("  Efektleri Dinle")

    def _save_effects_file(self):
        if self.raw_audio is None:
            return

        self._sync_ui_to_chain()
        proc = effects_chain.process(self.raw_audio, self.sample_rate)

        if self.current_filepath:
            p = Path(self.current_filepath)
            suggested = str(p.parent / f"{p.stem}_efektli.wav")
        else:
            suggested = str(Path(config.get("recordings_dir")) / "efektli_kayit.wav")

        path, _ = QFileDialog.getSaveFileName(
            self, "Efektli Sesi Kaydet", suggested, "WAV (*.wav);;FLAC (*.flac);;MP3 (*.mp3)"
        )
        if path:
            try:
                sf.write(path, proc, self.sample_rate)
                signals.library_updated.emit()
                signals.toast_requested.emit(f"Efektli kayıt kaydedildi: {Path(path).name}", "success")
            except Exception as e:
                signals.toast_requested.emit(f"Kaydetme hatası: {e}", "error")

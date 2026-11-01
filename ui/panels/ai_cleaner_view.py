"""
SONORA Studio - Advanced AI Audio Cleaning Studio View
Interactive audio inspection, multi-stage AI noise reduction, vocal isolation,
de-reverb, de-hum, de-esser, and instant seamless A/B audio comparison.
"""

from pathlib import Path
import threading
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QFileDialog, QSlider, QCheckBox,
                               QComboBox, QGridLayout, QScrollArea, QProgressBar)
import qtawesome as qta
import numpy as np
import soundfile as sf

from app.ai.audio_analyzer import AudioAnalyzer
from app.ai.noise_cleaner import NoiseCleaner
from app.ai.voice_restoration import VoiceRestoration
from app.audio.playback_engine import player
from app.core.signals import signals
from app.config import config
from ui.widgets.timeline_waveform import TimelineWaveformWidget


class AICleaningStudioView(QWidget):
    """AI-powered speech enhancement and noise restoration studio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.raw_audio: Optional[np.ndarray] = None
        self.processed_audio: Optional[np.ndarray] = None
        self.sample_rate = 44100
        self.current_filepath: Optional[str] = None
        self.analysis_report = {}

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # 1. TOP FILE & WORKFLOW HEADER
        top_card = QFrame()
        top_card.setObjectName("cardFrame")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(12)

        self.btn_load_file = QPushButton(" Dosya Seç")
        self.btn_load_file.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self.btn_load_file.clicked.connect(self._select_file_dialog)
        top_layout.addWidget(self.btn_load_file)

        self.file_label = QLabel("Temizlenecek ses dosyası seçilmedi.")
        self.file_label.setStyleSheet("font-weight: 600; color: #FFFFFF; font-size: 13px;")
        top_layout.addWidget(self.file_label, 1)

        self.btn_analyze = QPushButton(" Akustik Analiz Yap")
        self.btn_analyze.setIcon(qta.icon("fa5s.chart-bar", color="#00E5A3"))
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.clicked.connect(self._run_analysis)
        top_layout.addWidget(self.btn_analyze)

        root_layout.addWidget(top_card)

        # 2. SCROLLABLE MIDDLE WORKSPACE (Analysis Card + AI Tool Cards)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(12)

        # 2.A. ACOUSTIC ANALYSIS METRICS CARD
        self.analysis_card = QFrame()
        self.analysis_card.setObjectName("cardFrame")
        ac_layout = QVBoxLayout(self.analysis_card)
        ac_layout.setContentsMargins(14, 12, 14, 12)

        ac_header = QLabel("Akustik Analiz ve Gürültü Profili")
        ac_header.setStyleSheet("font-weight: 700; font-size: 13px; color: #00E5A3;")
        ac_layout.addWidget(ac_header)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.lbl_snr = self._create_metric_widget("Sinyal/Gürültü (SNR)", "-- dB", "fa5s.tachometer-alt")
        self.lbl_noise_floor = self._create_metric_widget("Gürültü Tabanı", "-- dBFS", "fa5s.volume-down")
        self.lbl_peak_rms = self._create_metric_widget("Tepe / RMS", "-- / -- dBFS", "fa5s.chart-line")
        self.lbl_hum = self._create_metric_widget("Şebeke Uğultusu", "Tespit Edilmedi", "fa5s.bolt")
        self.lbl_clips = self._create_metric_widget("Kırpılma (Clipping)", "0 örnek", "fa5s.exclamation-circle")
        self.lbl_silence = self._create_metric_widget("Sessizlik Oranı", "%0.0", "fa5s.microphone-slash")

        grid.addWidget(self.lbl_snr, 0, 0)
        grid.addWidget(self.lbl_noise_floor, 0, 1)
        grid.addWidget(self.lbl_peak_rms, 0, 2)
        grid.addWidget(self.lbl_hum, 1, 0)
        grid.addWidget(self.lbl_clips, 1, 1)
        grid.addWidget(self.lbl_silence, 1, 2)

        ac_layout.addLayout(grid)
        content_layout.addWidget(self.analysis_card)

        # 2.B. AI CLEANING MODULES GRID
        tools_card = QFrame()
        tools_card.setObjectName("cardFrame")
        tc_layout = QVBoxLayout(tools_card)
        tc_layout.setContentsMargins(14, 14, 14, 14)
        tc_layout.setSpacing(14)

        tc_title = QLabel("Yapay Zeka Ses Temizleme ve Restorasyon Araçları")
        tc_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #FFFFFF;")
        tc_layout.addWidget(tc_title)

        tools_grid = QGridLayout()
        tools_grid.setSpacing(14)

        # Tool 1: AI Noise Reduction
        t1, self.cb_nr, self.sl_nr, self.lbl_nr_val = self._create_tool_card(
            "AI Gürültü Azaltma (Spektral Gating)",
            "Klima, fan, dip gürültüsü ve sabit ortam uğultusunu yok eder.",
            "fa5s.brain", default_val=75
        )
        self.cb_nr_mode = QComboBox()
        self.cb_nr_mode.addItem("Sabit Gürültü (Fan, Klima, Tıslama)", "stationary")
        self.cb_nr_mode.addItem("Uyarlanabilir (Değişken Arka Plan)", "adaptive")
        t1.layout().addWidget(self.cb_nr_mode)
        tools_grid.addWidget(t1, 0, 0)

        # Tool 2: Voice Isolation & Clarity
        t2, self.cb_voice, self.sl_voice, self.lbl_voice_val = self._create_tool_card(
            "Vokal Ayrıştırma & Netleştirme",
            "Konuşma frekanslarını öne çıkarır ve arka plan seslerini bastırır.",
            "fa5s.user-astronaut", default_val=60
        )
        tools_grid.addWidget(t2, 0, 1)

        # Tool 3: De-Reverb (Yankı Giderme)
        t3, self.cb_reverb, self.sl_reverb, self.lbl_reverb_val = self._create_tool_card(
            "Yankı Giderme (De-Reverb)",
            "Oda akustiğinden kaynaklanan rahatsız edici oda yankısını azaltır.",
            "fa5s.compress", default_val=50
        )
        tools_grid.addWidget(t3, 1, 0)

        # Tool 4: De-Hum (50Hz / 60Hz Şebeke Uğultusu)
        t4, self.cb_hum, _, _ = self._create_toggle_tool_card(
            "Şebeke Uğultusu Giderme (De-Hum)",
            "50 Hz / 60 Hz elektrik ve topraklama uğultusunu keser.",
            "fa5s.bolt"
        )
        tools_grid.addWidget(t4, 1, 1)

        # Tool 5: De-Click (Çıtırtı / Patlama Giderme)
        t5, self.cb_click, _, _ = self._create_toggle_tool_card(
            "Çıtırtı Giderme (De-Click)",
            "Ağız sesleri, mikrofon tıkırtıları ve ani darbeleri tespit edip siler.",
            "fa5s.cut"
        )
        tools_grid.addWidget(t5, 2, 0)

        # Tool 6: De-Esser (Sıslama / Sibilans Önleyici)
        t6, self.cb_esser, self.sl_esser, self.lbl_esser_val = self._create_tool_card(
            "Sıslama Önleyici (De-Esser)",
            "Sert 'S', 'Ş' ve 'Ç' harflerindeki rahatsız edici tiz patlamaları yumuşatır.",
            "fa5s.feather-alt", default_val=65
        )
        tools_grid.addWidget(t6, 2, 1)

        # Tool 7: De-Plosive (Mikrofon Patlama Önleyici)
        t7, self.cb_plosive, _, _ = self._create_toggle_tool_card(
            "Patlayıcı Ses Filtresi (De-Plosive)",
            "'P', 'B', 'T' harflerindeki düşük frekanslı hava çarpmalarını filtreler.",
            "fa5s.wind"
        )
        tools_grid.addWidget(t7, 3, 0)

        # Tool 8: Silence Removal (Sessizlik Kırpma)
        t8, self.cb_silence, _, _ = self._create_toggle_tool_card(
            "Sessizlikleri Otomatik Kırp",
            "Kayıt içindeki uzun boşlukları tespit edip otomatik olarak çıkartır.",
            "fa5s.fast-forward"
        )
        tools_grid.addWidget(t8, 3, 1)

        tc_layout.addLayout(tools_grid)
        content_layout.addWidget(tools_card)

        scroll.setWidget(scroll_content)
        root_layout.addWidget(scroll, 1)

        # 3. INTERACTIVE TIMELINE WAVEFORM FOR A/B PREVIEW
        wave_card = QFrame()
        wave_card.setObjectName("cardFrame")
        wc_layout = QVBoxLayout(wave_card)
        wc_layout.setContentsMargins(10, 8, 10, 8)
        self.timeline = TimelineWaveformWidget()
        self.timeline.setFixedHeight(120)
        wc_layout.addWidget(self.timeline)
        root_layout.addWidget(wave_card)

        # 4. BOTTOM ACTION & A/B COMPARISON BAR
        action_card = QFrame()
        action_card.setObjectName("cardFrame")
        act_layout = QHBoxLayout(action_card)
        act_layout.setContentsMargins(14, 10, 14, 10)
        act_layout.setSpacing(12)

        # Generate Preview Button
        self.btn_preview = QPushButton("  Önizleme Oluştur")
        self.btn_preview.setIcon(qta.icon("fa5s.play", color="#0D0E12"))
        self.btn_preview.setObjectName("primaryButton")
        self.btn_preview.setMinimumHeight(42)
        self.btn_preview.clicked.connect(self._generate_preview)
        act_layout.addWidget(self.btn_preview)

        # A/B Instant Compare Switcher
        ab_layout = QHBoxLayout()
        ab_layout.setSpacing(4)
        self.btn_ab_orig = QPushButton(" Orijinal (A)")
        self.btn_ab_orig.setCheckable(True)
        self.btn_ab_orig.setChecked(True)
        self.btn_ab_orig.setEnabled(False)
        self.btn_ab_orig.clicked.connect(lambda: self._switch_ab("A"))
        ab_layout.addWidget(self.btn_ab_orig)

        self.btn_ab_proc = QPushButton(" Temizlenmiş (B)")
        self.btn_ab_proc.setCheckable(True)
        self.btn_ab_proc.setEnabled(False)
        self.btn_ab_proc.clicked.connect(lambda: self._switch_ab("B"))
        ab_layout.addWidget(self.btn_ab_proc)
        act_layout.addLayout(ab_layout)

        # Play/Pause Preview
        self.btn_play_preview = QPushButton()
        self.btn_play_preview.setIcon(qta.icon("fa5s.play", color="#00E5A3"))
        self.btn_play_preview.setFixedSize(38, 38)
        self.btn_play_preview.clicked.connect(self._toggle_preview_playback)
        act_layout.addWidget(self.btn_play_preview)

        # Processing progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        act_layout.addWidget(self.progress_bar, 1)

        act_layout.addStretch()

        # Non-Destructive Apply & Save Button
        self.btn_save_clean = QPushButton(" Temizlenmiş Olarak Kaydet")
        self.btn_save_clean.setIcon(qta.icon("fa5s.save", color="#FFFFFF"))
        self.btn_save_clean.setMinimumHeight(42)
        self.btn_save_clean.setEnabled(False)
        self.btn_save_clean.clicked.connect(self._save_cleaned_file)
        act_layout.addWidget(self.btn_save_clean)

        root_layout.addWidget(action_card)

    def _create_metric_widget(self, title: str, default_val: str, icon_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("innerCard")
        l = QHBoxLayout(card)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#00E5A3").pixmap(18, 18))
        l.addWidget(icon_lbl)

        v = QVBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; color: #9CA3AF; font-weight: 600;")
        val = QLabel(default_val)
        val.setStyleSheet("font-size: 13px; font-weight: 700; color: #FFFFFF;")
        v.addWidget(t)
        v.addWidget(val)
        l.addLayout(v)
        card.value_label = val
        return card

    def _create_tool_card(self, title: str, desc: str, icon_name: str, default_val: int = 70):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        # Top row: Checkbox + Title
        h = QHBoxLayout()
        cb = QCheckBox(title)
        cb.setChecked(True)
        cb.setStyleSheet("font-weight: 700; font-size: 13px; color: #FFFFFF;")
        h.addWidget(cb)
        h.addStretch()

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#00E5A3").pixmap(16, 16))
        h.addWidget(icon_lbl)
        l.addLayout(h)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        desc_lbl.setWordWrap(True)
        l.addWidget(desc_lbl)

        # Slider row: Label + Slider + Value
        sl_h = QHBoxLayout()
        sl_lbl = QLabel("Yoğunluk:")
        sl_lbl.setStyleSheet("font-size: 11px; color: #6B7280;")
        sl_h.addWidget(sl_lbl)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(default_val)
        sl_h.addWidget(slider, 1)

        val_lbl = QLabel(f"%{default_val}")
        val_lbl.setStyleSheet("font-weight: 700; color: #00E5A3; font-size: 11px; min-width: 32px;")
        slider.valueChanged.connect(lambda v: val_lbl.setText(f"%{v}"))
        sl_h.addWidget(val_lbl)

        l.addLayout(sl_h)
        return card, cb, slider, val_lbl

    def _create_toggle_tool_card(self, title: str, desc: str, icon_name: str):
        card = QFrame()
        card.setObjectName("innerCard")
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        h = QHBoxLayout()
        cb = QCheckBox(title)
        cb.setChecked(False)
        cb.setStyleSheet("font-weight: 700; font-size: 13px; color: #FFFFFF;")
        h.addWidget(cb)
        h.addStretch()

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#00E5A3").pixmap(16, 16))
        h.addWidget(icon_lbl)
        l.addLayout(h)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("font-size: 11px; color: #9CA3AF;")
        desc_lbl.setWordWrap(True)
        l.addWidget(desc_lbl)

        return card, cb, None, None

    def _connect_signals(self):
        signals.audio_loaded_for_cleaning.connect(self.load_audio_file)
        signals.playback_position_changed.connect(lambda cur, tot: self.timeline.set_playhead_position(cur))
        signals.playback_state_changed.connect(self._on_playback_state_changed)

    def load_audio_file(self, filepath: str):
        """Load audio file into cleaning station."""
        try:
            data, sr = sf.read(filepath, dtype='float32')
            if data.ndim == 1:
                data = data[:, np.newaxis]
            self.raw_audio = data.astype(np.float32)
            self.processed_audio = None
            self.sample_rate = sr
            self.current_filepath = filepath

            self.file_label.setText(Path(filepath).name)
            self.btn_analyze.setEnabled(True)
            self.timeline.set_audio_data(self.raw_audio, self.sample_rate)

            # Auto-run analysis
            self._run_analysis()
            signals.toast_requested.emit(f"Ses yüklendi: {Path(filepath).name}", "info")
        except Exception as e:
            signals.toast_requested.emit(f"Ses açılamadı: {e}", "error")

    def _select_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Temizlenecek Sesi Seç", "", "Ses Dosyaları (*.wav *.flac *.mp3 *.ogg *.aiff *.m4a)"
        )
        if path:
            self.load_audio_file(path)

    def _run_analysis(self):
        """Run acoustic profiling."""
        if self.raw_audio is None:
            return

        report = AudioAnalyzer.analyze(self.raw_audio, self.sample_rate)
        self.analysis_report = report

        self.lbl_snr.value_label.setText(f"{report['snr_db']} dB")
        self.lbl_noise_floor.value_label.setText(f"{report['noise_floor_db']} dBFS")
        self.lbl_peak_rms.value_label.setText(f"{report['peak_db']} / {report['rms_db']} dB")

        # Hum
        hum_text = "Tespit Edilmedi"
        if report['has_hum_50hz']:
            hum_text = "50 Hz Uğultu Var!"
            self.cb_hum.setChecked(True)
        elif report['has_hum_60hz']:
            hum_text = "60 Hz Uğultu Var!"
            self.cb_hum.setChecked(True)
        self.lbl_hum.value_label.setText(hum_text)

        # Clipping
        self.lbl_clips.value_label.setText(f"{report['clipped_samples']} örnek")

        # Silence
        self.lbl_silence.value_label.setText(f"%{report['silence_ratio']}")
        if report['silence_ratio'] > 25.0:
            self.cb_silence.setChecked(True)

    def _generate_preview(self):
        """Run processing pipeline in a background thread."""
        if self.raw_audio is None:
            return

        self.btn_preview.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        # Gather active tools and values
        settings = {
            "nr_enabled": self.cb_nr.isChecked(),
            "nr_intensity": self.sl_nr.value(),
            "nr_mode": self.cb_nr_mode.currentData(),
            "voice_enabled": self.cb_voice.isChecked(),
            "voice_clarity": self.sl_voice.value(),
            "reverb_enabled": self.cb_reverb.isChecked(),
            "reverb_intensity": self.sl_reverb.value(),
            "hum_enabled": self.cb_hum.isChecked(),
            "click_enabled": self.cb_click.isChecked(),
            "esser_enabled": self.cb_esser.isChecked(),
            "plosive_enabled": self.cb_plosive.isChecked(),
            "silence_enabled": self.cb_silence.isChecked()
        }

        thread = threading.Thread(target=self._process_worker, args=(settings,), daemon=True)
        thread.start()

    def _process_worker(self, settings: dict):
        """Execute audio filters sequentially."""
        try:
            proc = self.raw_audio.copy()
            sr = self.sample_rate

            # 1. Hum Removal
            if settings["hum_enabled"]:
                base = 60.0 if self.analysis_report.get("has_hum_60hz") else 50.0
                proc = VoiceRestoration.remove_hum(proc, sr, base_freq=base)

            # 2. De-Click
            if settings["click_enabled"]:
                proc = VoiceRestoration.de_click(proc, sr)

            # 3. De-Plosive
            if settings["plosive_enabled"]:
                proc = VoiceRestoration.de_plosive(proc, sr)

            # 4. AI Noise Reduction
            if settings["nr_enabled"]:
                proc = NoiseCleaner.reduce_noise(
                    proc, sr,
                    intensity_pct=settings["nr_intensity"],
                    mode=settings["nr_mode"]
                )

            # 5. De-Reverb
            if settings["reverb_enabled"]:
                proc = VoiceRestoration.de_reverb(proc, sr, intensity_pct=settings["reverb_intensity"])

            # 6. De-Esser
            if settings["esser_enabled"]:
                proc = VoiceRestoration.de_esser(proc, sr)

            # 7. Voice Enhancement
            if settings["voice_enabled"]:
                proc = VoiceRestoration.enhance_voice(proc, sr, clarity_pct=settings["voice_clarity"])

            # 8. Silence Removal
            if settings["silence_enabled"] and self.analysis_report.get("silent_regions"):
                proc = VoiceRestoration.remove_silence(proc, sr, self.analysis_report["silent_regions"])

            self.processed_audio = proc

            # Send back to main UI
            QTimer.singleShot(0, self._on_processing_complete)

        except Exception as e:
            QTimer.singleShot(0, lambda: signals.toast_requested.emit(f"İşleme hatası: {e}", "error"))
            QTimer.singleShot(0, lambda: self.btn_preview.setEnabled(True))

    def _on_processing_complete(self):
        self.progress_bar.setVisible(False)
        self.btn_preview.setEnabled(True)
        self.btn_save_clean.setEnabled(True)
        self.btn_ab_orig.setEnabled(True)
        self.btn_ab_proc.setEnabled(True)
        self.btn_ab_proc.setChecked(True)
        self.btn_ab_orig.setChecked(False)

        # Setup A/B in player
        player.set_ab_tracks(self.raw_audio, self.processed_audio, self.sample_rate)
        player.switch_ab("B")

        # Update waveform with processed audio
        self.timeline.set_audio_data(self.processed_audio, self.sample_rate)

        signals.toast_requested.emit("Temizleme tamamlandı! A/B karşılaştırması hazır.", "success")

    def _switch_ab(self, track: str):
        if track == "A":
            self.btn_ab_orig.setChecked(True)
            self.btn_ab_proc.setChecked(False)
            player.switch_ab("A")
            self.timeline.set_audio_data(self.raw_audio, self.sample_rate)
            signals.toast_requested.emit("Orijinal Sinyal (A)", "info")
        else:
            self.btn_ab_orig.setChecked(False)
            self.btn_ab_proc.setChecked(True)
            player.switch_ab("B")
            self.timeline.set_audio_data(self.processed_audio, self.sample_rate)
            signals.toast_requested.emit("Temizlenmiş Sinyal (B)", "success")

    def _toggle_preview_playback(self):
        if player.is_playing and not player.is_paused:
            player.pause()
        else:
            player.play()

    def _on_playback_state_changed(self, is_playing: bool, is_paused: bool):
        if is_playing and not is_paused:
            self.btn_play_preview.setIcon(qta.icon("fa5s.pause", color="#EF4444"))
        else:
            self.btn_play_preview.setIcon(qta.icon("fa5s.play", color="#00E5A3"))

    def _save_cleaned_file(self):
        """Save cleaned audio non-destructively to disk."""
        if self.processed_audio is None:
            return

        if self.current_filepath:
            p = Path(self.current_filepath)
            suggested = str(p.parent / f"{p.stem}_temizlenmis.wav")
        else:
            suggested = str(Path(config.get("recordings_dir")) / "temizlenmis_kayit.wav")

        path, _ = QFileDialog.getSaveFileName(
            self, "Temizlenmiş Sesi Kaydet", suggested, "WAV (*.wav);;FLAC (*.flac);;MP3 (*.mp3)"
        )
        if path:
            try:
                sf.write(path, self.processed_audio, self.sample_rate)
                signals.library_updated.emit()
                signals.toast_requested.emit(f"Temizlenmiş kayıt kaydedildi: {Path(path).name}", "success")
            except Exception as e:
                signals.toast_requested.emit(f"Kaydetme hatası: {e}", "error")

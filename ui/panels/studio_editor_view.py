"""
SONORA Studio - Unified Recording Studio & Waveform Editor View (Lag-Free & Optimized)
High-performance decoupled 30 FPS GUI polling, zero Qt event loop bottlenecks,
immediate waveform editing with Backspace deletion, cropping, and instant library sync.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QComboBox, QSlider, QStackedWidget,
                               QFileDialog)
import qtawesome as qta
import numpy as np
import soundfile as sf

from app.audio.device_manager import AudioDeviceManager
from app.audio.recording_engine import recorder
from app.audio.playback_engine import player
from app.editor.audio_buffer import editor_buffer
from app.core.signals import signals
from app.config import config
from ui.widgets.level_meter import LevelMeter
from ui.widgets.live_waveform import LiveWaveformWidget
from ui.widgets.timeline_waveform import TimelineWaveformWidget
from ui.widgets.dialogs import InputTextDialog


class StudioEditorView(QWidget):
    """All-in-one studio environment uniting live recording and precision audio editing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._populate_devices()
        self._connect_signals()
        self._setup_shortcuts()

        # Dedicated 30 FPS Decoupled UI Poller (Zero Lag!)
        self._gui_timer = QTimer(self)
        self._gui_timer.timeout.connect(self._gui_tick)
        self._gui_timer.start(33)  # ~30 FPS

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 12, 16, 12)
        root_layout.setSpacing(10)

        # -------------------------------------------------------------
        # 1. TOP HARDWARE & RECORDING DECK
        # -------------------------------------------------------------
        top_card = QFrame()
        top_card.setObjectName("cardFrame")
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(12)

        # Microphone Dropdown
        mic_v = QVBoxLayout()
        mic_lbl = QLabel("Giriş Mikrofonu:")
        mic_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(260)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        mic_v.addWidget(mic_lbl)
        mic_v.addWidget(self.device_combo)
        top_layout.addLayout(mic_v, 2)

        # Sample Rate
        sr_v = QVBoxLayout()
        sr_lbl = QLabel("Örnekleme Hızı:")
        sr_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.sr_combo = QComboBox()
        sr_v.addWidget(sr_lbl)
        sr_v.addWidget(self.sr_combo)
        top_layout.addLayout(sr_v, 1)

        # Channels
        ch_v = QVBoxLayout()
        ch_lbl = QLabel("Kanal:")
        ch_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.ch_combo = QComboBox()
        self.ch_combo.addItem("Stereo (2 Kanal)", 2)
        self.ch_combo.addItem("Mono (1 Kanal)", 1)
        ch_v.addWidget(ch_lbl)
        ch_v.addWidget(self.ch_combo)
        top_layout.addLayout(ch_v, 1)

        # Bit Depth
        depth_v = QVBoxLayout()
        depth_lbl = QLabel("Bit Derinliği:")
        depth_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.depth_combo = QComboBox()
        self.depth_combo.addItem("24-bit PCM (Stüdyo)", "PCM_24")
        self.depth_combo.addItem("16-bit PCM (Standart)", "PCM_16")
        self.depth_combo.addItem("32-bit Float", "FLOAT_32")
        depth_v.addWidget(depth_lbl)
        depth_v.addWidget(self.depth_combo)
        top_layout.addLayout(depth_v, 1)

        # High-res VU Level Meter
        self.level_meter = LevelMeter()
        self.level_meter.setFixedSize(65, 54)
        top_layout.addWidget(self.level_meter)

        root_layout.addWidget(top_card)

        # -------------------------------------------------------------
        # 2. RECORDING TRANSPORT & DIGITAL TIMER BAR
        # -------------------------------------------------------------
        rec_bar = QFrame()
        rec_bar.setObjectName("cardFrame")
        rb_layout = QHBoxLayout(rec_bar)
        rb_layout.setContentsMargins(16, 8, 16, 8)
        rb_layout.setSpacing(14)

        # Big Studio Record Button
        self.btn_record = QPushButton("  KAYDA BAŞLA")
        self.btn_record.setIcon(qta.icon("fa5s.circle", color="#FFFFFF"))
        self.btn_record.setObjectName("bigRecordButton")
        self.btn_record.setMinimumSize(180, 46)
        self.btn_record.clicked.connect(self._toggle_record)
        rb_layout.addWidget(self.btn_record)

        # Pause / Resume Button
        self.btn_pause = QPushButton(" Duraklat")
        self.btn_pause.setIcon(qta.icon("fa5s.pause", color="#FFFFFF"))
        self.btn_pause.setEnabled(False)
        self.btn_pause.setMinimumSize(110, 40)
        self.btn_pause.clicked.connect(self._toggle_pause)
        rb_layout.addWidget(self.btn_pause)

        # Stop & Save Button
        self.btn_stop = QPushButton("  Durdur ve Kaydet")
        self.btn_stop.setIcon(qta.icon("fa5s.save", color="#00E5A3"))
        self.btn_stop.setObjectName("primaryButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumSize(170, 42)
        self.btn_stop.setToolTip("Kaydı sonlandırır, ses dosyası olarak kaydeder ve düzenleyiciye aktarır")
        self.btn_stop.clicked.connect(self._stop_and_load_editor)
        rb_layout.addWidget(self.btn_stop)

        # Digital Timer
        self.timer_label = QLabel("00:00:00.0")
        self.timer_label.setStyleSheet("""
            font-family: 'Consolas', 'Cascadia Code', monospace;
            font-size: 26px;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: 1.5px;
            padding: 0 10px;
        """)
        rb_layout.addWidget(self.timer_label)

        rb_layout.addStretch()

        # Active File Label / Info
        self.lbl_active_info = QLabel("Stüdyo hazır. Kayda başlayın veya bir dosya açın.")
        self.lbl_active_info.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 500;")
        rb_layout.addWidget(self.lbl_active_info)

        root_layout.addWidget(rec_bar)

        # -------------------------------------------------------------
        # 3. CENTER DYNAMIC WAVEFORM DISPLAY (Live Osiloskop <-> Timeline Editor)
        # -------------------------------------------------------------
        wave_card = QFrame()
        wave_card.setObjectName("cardFrame")
        wc_layout = QVBoxLayout(wave_card)
        wc_layout.setContentsMargins(10, 8, 10, 8)
        wc_layout.setSpacing(6)

        # Stacked display: 0 = Interactive Timeline Editor, 1 = Live Recording Waveform
        self.wave_stack = QStackedWidget()

        # Index 0: Interactive Timeline Waveform Editor
        self.timeline_waveform = TimelineWaveformWidget()
        self.timeline_waveform.cursor_moved.connect(self._on_timeline_seek)
        self.timeline_waveform.selection_changed.connect(self._on_timeline_selection)
        self.timeline_waveform.delete_requested.connect(self._delete_selection_via_key)
        self.wave_stack.addWidget(self.timeline_waveform)

        # Index 1: Live Recording Oscilloscope
        self.live_waveform = LiveWaveformWidget()
        self.wave_stack.addWidget(self.live_waveform)

        wc_layout.addWidget(self.wave_stack, 1)

        # -------------------------------------------------------------
        # 4. EDITING TOOLBAR (Crop, Backspace, Fade, Normalize, Gain, Save)
        # -------------------------------------------------------------
        edit_tb = QHBoxLayout()
        edit_tb.setSpacing(8)

        # Backspace / Delete Button
        self.btn_del = QPushButton(" Seçimi Sil (Backspace)")
        self.btn_del.setIcon(qta.icon("fa5s.backspace", color="#EF4444"))
        self.btn_del.setToolTip("Seçilen ses aralığını siler (Backspace veya Delete tuşu)")
        self.btn_del.clicked.connect(self._delete_selection_via_key)
        edit_tb.addWidget(self.btn_del)

        # Crop Button
        self.btn_trim = QPushButton(" Kırp (Seçimi Koru)")
        self.btn_trim.setIcon(qta.icon("fa5s.crop-alt", color="#00E5A3"))
        self.btn_trim.setToolTip("Seçili bölge haricindeki tüm kısımları siler")
        self.btn_trim.clicked.connect(self._trim)
        edit_tb.addWidget(self.btn_trim)

        # Undo / Redo
        self.btn_undo = QPushButton(" Geri Al")
        self.btn_undo.setIcon(qta.icon("fa5s.undo", color="#9CA3AF"))
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._undo)
        edit_tb.addWidget(self.btn_undo)

        self.btn_redo = QPushButton(" Yinele")
        self.btn_redo.setIcon(qta.icon("fa5s.redo", color="#9CA3AF"))
        self.btn_redo.setEnabled(False)
        self.btn_redo.clicked.connect(self._redo)
        edit_tb.addWidget(self.btn_redo)

        # Fade in & out
        self.btn_fade_in = QPushButton("Fade In")
        self.btn_fade_in.clicked.connect(lambda: self._apply_edit(lambda: editor_buffer.fade_in(0.4)))
        edit_tb.addWidget(self.btn_fade_in)

        self.btn_fade_out = QPushButton("Fade Out")
        self.btn_fade_out.clicked.connect(lambda: self._apply_edit(lambda: editor_buffer.fade_out(0.4)))
        edit_tb.addWidget(self.btn_fade_out)

        # Normalize
        self.btn_norm = QPushButton("Normalize (-0.5 dB)")
        self.btn_norm.clicked.connect(lambda: self._apply_edit(lambda: editor_buffer.normalize(-0.5)))
        edit_tb.addWidget(self.btn_norm)

        # Gain
        self.btn_gain = QPushButton("Kazanç...")
        self.btn_gain.clicked.connect(self._prompt_gain)
        edit_tb.addWidget(self.btn_gain)

        edit_tb.addStretch()

        # Direct In-Place Save Button
        self.btn_save = QPushButton("  Kaydet (Ctrl+S)")
        self.btn_save.setIcon(qta.icon("fa5s.save", color="#00E5A3"))
        self.btn_save.setToolTip("Değişiklikleri mevcut dosyaya doğrudan kaydeder")
        self.btn_save.clicked.connect(self._save_active_file)
        edit_tb.addWidget(self.btn_save)

        # Save As Button
        self.btn_save_as = QPushButton("  Farklı Kaydet...")
        self.btn_save_as.setIcon(qta.icon("fa5s.file-export", color="#9CA3AF"))
        self.btn_save_as.setToolTip("Yeni bir isimle veya farklı ses formatında kaydet")
        self.btn_save_as.clicked.connect(self._save_as_file)
        edit_tb.addWidget(self.btn_save_as)

        # Send to AI Cleaner
        self.btn_send_cleaner = QPushButton(" YZ ile Temizle")
        self.btn_send_cleaner.setIcon(qta.icon("fa5s.magic", color="#00E5A3"))
        self.btn_send_cleaner.clicked.connect(self._send_to_ai_cleaner)
        edit_tb.addWidget(self.btn_send_cleaner)

        wc_layout.addLayout(edit_tb)
        root_layout.addWidget(wave_card, 1)

        # -------------------------------------------------------------
        # 5. BOTTOM PLAYBACK TRANSPORT BAR
        # -------------------------------------------------------------
        trans_card = QFrame()
        trans_card.setObjectName("cardFrame")
        trans_layout = QHBoxLayout(trans_card)
        trans_layout.setContentsMargins(14, 8, 14, 8)
        trans_layout.setSpacing(12)

        # Play / Pause & Stop
        self.btn_play = QPushButton()
        self.btn_play.setIcon(qta.icon("fa5s.play", color="#00E5A3"))
        self.btn_play.setFixedSize(38, 38)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #232733;
                border: 1px solid #363C4E;
                border-radius: 19px;
            }
            QPushButton:hover {
                border-color: #00E5A3;
            }
        """)
        self.btn_play.clicked.connect(self._toggle_playback)
        trans_layout.addWidget(self.btn_play)

        self.btn_stop_play = QPushButton()
        self.btn_stop_play.setIcon(qta.icon("fa5s.stop", color="#FFFFFF"))
        self.btn_stop_play.setFixedSize(34, 34)
        self.btn_stop_play.clicked.connect(self._stop_playback)
        trans_layout.addWidget(self.btn_stop_play)

        # Loop Toggle
        self.btn_loop = QPushButton()
        self.btn_loop.setIcon(qta.icon("fa5s.redo-alt", color="#9CA3AF"))
        self.btn_loop.setCheckable(True)
        self.btn_loop.setToolTip("Seçimi Sürekli Döngüde Çal")
        self.btn_loop.setFixedSize(34, 34)
        self.btn_loop.clicked.connect(self._toggle_loop)
        trans_layout.addWidget(self.btn_loop)

        # Time readout
        self.time_lbl = QLabel("00:00.0 / 00:00.0")
        self.time_lbl.setStyleSheet("font-family: 'Consolas', monospace; font-size: 14px; font-weight: 700; color: #FFFFFF;")
        trans_layout.addWidget(self.time_lbl)

        # Selection readout
        self.selection_lbl = QLabel("Seçim Yok")
        self.selection_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        trans_layout.addWidget(self.selection_lbl)

        trans_layout.addStretch()

        # Playback speed
        speed_lbl = QLabel("Hız:")
        speed_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        trans_layout.addWidget(speed_lbl)

        self.speed_combo = QComboBox()
        self.speed_combo.addItem("0.5x", 0.5)
        self.speed_combo.addItem("0.75x", 0.75)
        self.speed_combo.addItem("1.0x", 1.0)
        self.speed_combo.addItem("1.25x", 1.25)
        self.speed_combo.addItem("1.5x", 1.5)
        self.speed_combo.addItem("2.0x", 2.0)
        self.speed_combo.setCurrentIndex(2)
        self.speed_combo.currentIndexChanged.connect(lambda: player.set_speed(self.speed_combo.currentData() or 1.0))
        trans_layout.addWidget(self.speed_combo)

        # Volume slider
        vol_icon = QLabel()
        vol_icon.setPixmap(qta.icon("fa5s.volume-up", color="#9CA3AF").pixmap(15, 15))
        trans_layout.addWidget(vol_icon)

        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 150)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.valueChanged.connect(lambda v: player.set_volume(v / 100.0))
        trans_layout.addWidget(self.vol_slider)

        root_layout.addWidget(trans_card)

        # Default: timeline waveform editor visible
        self.wave_stack.setCurrentIndex(0)

    def _setup_shortcuts(self):
        self.sc_space = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.sc_space.activated.connect(self._toggle_playback)

        self.sc_undo = QShortcut(QKeySequence.Undo, self)
        self.sc_undo.activated.connect(self._undo)

        self.sc_redo = QShortcut(QKeySequence.Redo, self)
        self.sc_redo.activated.connect(self._redo)

        self.sc_save = QShortcut(QKeySequence.Save, self)
        self.sc_save.activated.connect(self._save_active_file)

    def _populate_devices(self):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        input_devs = AudioDeviceManager.get_input_devices()
        default_id = AudioDeviceManager.get_default_input_device_id()

        selected_idx = 0
        for i, dev in enumerate(input_devs):
            label = AudioDeviceManager.format_device_label(dev, is_input=True)
            self.device_combo.addItem(label, dev["id"])
            if dev["id"] == default_id:
                selected_idx = i

        if input_devs:
            self.device_combo.setCurrentIndex(selected_idx)
            self._update_sample_rates(input_devs[selected_idx]["id"])

        self.device_combo.blockSignals(False)

    def _on_device_changed(self, index: int):
        device_id = self.device_combo.currentData()
        if device_id is not None:
            self._update_sample_rates(device_id)

    def _update_sample_rates(self, device_id: int):
        self.sr_combo.clear()
        supported = AudioDeviceManager.get_supported_sample_rates(device_id, is_input=True)
        for sr in supported:
            khz = sr / 1000.0
            self.sr_combo.addItem(f"{sr} Hz ({khz:.1f} kHz)", sr)

        idx_48 = self.sr_combo.findData(48000)
        if idx_48 >= 0:
            self.sr_combo.setCurrentIndex(idx_48)

    def _connect_signals(self):
        signals.recording_started.connect(self._on_recording_started)
        signals.recording_paused.connect(self._on_recording_paused)
        signals.recording_resumed.connect(self._on_recording_resumed)
        signals.recording_stopped.connect(self._on_recording_stopped)

        signals.audio_loaded_for_editing.connect(self.load_audio_file)
        signals.editor_history_changed.connect(self._on_history_changed)
        signals.playback_position_changed.connect(self._on_playback_pos_changed)
        signals.playback_state_changed.connect(self._on_playback_state_changed)

    def _gui_tick(self):
        """High-performance 30 FPS polling loop: updates VU meters and live waveform smoothly."""
        if recorder.is_recording:
            # Poll atomic metering values without Qt signal bottlenecks
            self.level_meter.update_levels(
                recorder.peak_l, recorder.peak_r,
                recorder.rms_l, recorder.rms_r,
                recorder.is_clipping
            )
            # Update live waveform oscilloscope
            chunk = recorder.pop_latest_chunk()
            if chunk is not None:
                self.live_waveform.add_chunk(chunk)

            # Update digital clock
            el = recorder.elapsed_seconds
            t_sec = int(el)
            hrs = t_sec // 3600
            mins = (t_sec % 3600) // 60
            secs = t_sec % 60
            ms = int((el - t_sec) * 10)
            self.timer_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms}")

    # -------------------------------------------------------------
    # RECORDING ACTIONS
    # -------------------------------------------------------------
    def _toggle_record(self):
        if not recorder.is_recording:
            device_id = self.device_combo.currentData()
            sr = self.sr_combo.currentData() or 48000
            channels = self.ch_combo.currentData() or 2
            bit_depth = self.depth_combo.currentData() or "PCM_24"

            # Switch to live oscilloscope
            self.live_waveform.clear()
            self.wave_stack.setCurrentIndex(1)

            ok, path = recorder.start_recording(
                device_id=device_id,
                sample_rate=sr,
                channels=channels,
                bit_depth=bit_depth
            )
            if not ok:
                self.wave_stack.setCurrentIndex(0)
                signals.toast_requested.emit(f"Kayıt başlatılamadı: {path}", "error")
        else:
            self._stop_and_load_editor()

    def _toggle_pause(self):
        if recorder.is_recording:
            if recorder.is_paused:
                recorder.resume_recording()
            else:
                recorder.pause_recording()

    def _stop_and_load_editor(self):
        """Stop recording, flush file, and immediately load into the interactive editor on this screen!"""
        if recorder.is_recording:
            saved_path = recorder.stop_recording()
            if saved_path and Path(saved_path).exists():
                self.wave_stack.setCurrentIndex(0)
                self.load_audio_file(saved_path)
                signals.library_updated.emit()
                signals.toast_requested.emit(f"Kayıt kaydedildi ve düzenlemeye hazır: {Path(saved_path).name}", "success")

    def _on_recording_started(self):
        self.btn_record.setText("  KAYDI BİTİR VE DÜZENLE")
        self.btn_record.setStyleSheet("""
            QPushButton#bigRecordButton {
                background-color: #B91C1C;
                border: 3px solid rgba(255, 255, 255, 0.4);
            }
        """)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText(" Duraklat")
        self.btn_stop.setEnabled(True)
        self.device_combo.setEnabled(False)
        self.sr_combo.setEnabled(False)
        self.ch_combo.setEnabled(False)
        self.depth_combo.setEnabled(False)
        self.lbl_active_info.setText("🔴 Canlı kayıt yapılıyor...")

    def _on_recording_paused(self):
        self.btn_pause.setText(" Devam Et")
        self.btn_pause.setIcon(qta.icon("fa5s.play", color="#FFFFFF"))
        self.lbl_active_info.setText("⏸️ Kayıt duraklatıldı.")

    def _on_recording_resumed(self):
        self.btn_pause.setText(" Duraklat")
        self.btn_pause.setIcon(qta.icon("fa5s.pause", color="#FFFFFF"))
        self.lbl_active_info.setText("🔴 Canlı kayıt yapılıyor...")

    def _on_recording_stopped(self, saved_path: str):
        self.btn_record.setText("  KAYDA BAŞLA")
        self.btn_record.setStyleSheet("")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.device_combo.setEnabled(True)
        self.sr_combo.setEnabled(True)
        self.ch_combo.setEnabled(True)
        self.depth_combo.setEnabled(True)
        self.level_meter.update_levels(0.0, 0.0, 0.0, 0.0, False)

    # -------------------------------------------------------------
    # AUDIO EDITING & KEYBOARD (Backspace / Delete / Crop / Fade)
    # -------------------------------------------------------------
    def load_audio_file(self, filepath: str):
        """Load audio file into editor buffer and waveform display."""
        if editor_buffer.load_file(filepath):
            self.wave_stack.setCurrentIndex(0)
            name = Path(filepath).name
            ch_str = "Stereo" if editor_buffer.channels == 2 else "Mono"
            self.lbl_active_info.setText(f"📁 {name} ({editor_buffer.sample_rate} Hz • {ch_str} • {editor_buffer.duration_seconds:.2f} sn)")
            self.timeline_waveform.set_audio_data(editor_buffer.data, editor_buffer.sample_rate)
            player.load_buffer(editor_buffer.data, editor_buffer.sample_rate)
            self._update_time_label(0.0, editor_buffer.duration_seconds)
            self.timeline_waveform.setFocus()

    def _delete_selection_via_key(self):
        """Called when Backspace or Delete key is pressed on the waveform."""
        if not editor_buffer.is_loaded:
            return
        s, e = editor_buffer.get_selection_bounds()
        if s >= e:
            signals.toast_requested.emit("Silmek için önce dalga formu üzerinde bir alan seçin.", "info")
            return
        if editor_buffer.delete_selection():
            self._sync_buffer_to_views()
            signals.toast_requested.emit("Seçilen bölge silindi (Geri almak için Ctrl+Z).", "info")

    def _trim(self):
        if not editor_buffer.is_loaded:
            return
        s, e = editor_buffer.get_selection_bounds()
        if s >= e:
            signals.toast_requested.emit("Kırpmak için önce bir bölge seçin.", "info")
            return
        if editor_buffer.trim():
            self._sync_buffer_to_views()
            signals.toast_requested.emit("Seçim dışı kırpıldı.", "info")

    def _undo(self):
        if editor_buffer.undo():
            self._sync_buffer_to_views()

    def _redo(self):
        if editor_buffer.redo():
            self._sync_buffer_to_views()

    def _apply_edit(self, op_callable):
        if op_callable():
            self._sync_buffer_to_views()

    def _sync_buffer_to_views(self):
        self.timeline_waveform.set_audio_data(editor_buffer.data, editor_buffer.sample_rate)
        player.load_buffer(editor_buffer.data, editor_buffer.sample_rate)
        self._update_time_label(0.0, editor_buffer.duration_seconds)
        self.timeline_waveform.setFocus()

    def _prompt_gain(self):
        dlg = InputTextDialog(self, "Ses Seviyesi (Kazanç)", "Uygulanacak dB miktarını girin (+3, -6 gibi):", initial_text="3.0")
        if dlg.exec():
            try:
                val = float(dlg.get_text().replace(",", "."))
                editor_buffer.apply_gain(val)
                self._sync_buffer_to_views()
            except ValueError:
                signals.toast_requested.emit("Geçersiz sayısal dB değeri.", "warning")

    def _save_active_file(self):
        """Save edited buffer directly into current file without dialog interruption."""
        if not editor_buffer.is_loaded:
            signals.toast_requested.emit("Kaydedilecek ses bulunamadı.", "warning")
            return

        if not editor_buffer.filepath:
            self._save_as_file()
            return

        target_path = editor_buffer.filepath
        try:
            sf.write(target_path, editor_buffer.data, editor_buffer.sample_rate)
            editor_buffer._is_dirty = False
            signals.library_updated.emit()
            signals.toast_requested.emit(f"Kayıt güncellendi ve kaydedildi: {Path(target_path).name}", "success")
        except Exception as e:
            signals.toast_requested.emit(f"Doğrudan kaydetme hatası: {e}. Farklı kaydetmeyi deneyin.", "error")
            self._save_as_file()

    def _save_as_file(self):
        """Prompt user for destination and format."""
        if not editor_buffer.is_loaded:
            signals.toast_requested.emit("Kaydedilecek ses bulunamadı.", "warning")
            return

        default_path = editor_buffer.filepath or str(Path(config.get("recordings_dir")) / "duzenlenmis_kayit.wav")
        path, _ = QFileDialog.getSaveFileName(
            self, "Sesi Farklı Kaydet", default_path, "WAV (*.wav);;FLAC (*.flac);;MP3 (*.mp3)"
        )
        if path:
            try:
                sf.write(path, editor_buffer.data, editor_buffer.sample_rate)
                editor_buffer._filepath = path
                editor_buffer._is_dirty = False
                signals.library_updated.emit()
                signals.toast_requested.emit(f"Yeni kayıt kaydedildi: {Path(path).name}", "success")
            except Exception as e:
                signals.toast_requested.emit(f"Kaydetme hatası: {e}", "error")

    def _send_to_ai_cleaner(self):
        if not editor_buffer.is_loaded:
            return
        if editor_buffer.is_dirty or not editor_buffer.filepath:
            temp_path = str(Path(config.get("cache_dir")) / "cleaner_input.wav")
            sf.write(temp_path, editor_buffer.data, editor_buffer.sample_rate)
            signals.audio_loaded_for_cleaning.emit(temp_path)
        else:
            signals.audio_loaded_for_cleaning.emit(editor_buffer.filepath)
        signals.switch_view_requested.emit("ai_cleaner")

    def _on_history_changed(self, can_undo: bool, can_redo: bool):
        self.btn_undo.setEnabled(can_undo)
        self.btn_redo.setEnabled(can_redo)

    # -------------------------------------------------------------
    # PLAYBACK ENGINE SYNCHRONIZATION
    # -------------------------------------------------------------
    def _toggle_playback(self):
        if not editor_buffer.is_loaded:
            return
        if player.is_playing and not player.is_paused:
            player.pause()
        else:
            player.play()

    def _stop_playback(self):
        player.stop()
        self.timeline_waveform.set_playhead_position(0.0)

    def _toggle_loop(self):
        is_loop = self.btn_loop.isChecked()
        s, e = editor_buffer.get_selection_bounds()
        if is_loop and s < e and editor_buffer.sample_rate > 0:
            player.set_loop_region(s / editor_buffer.sample_rate, e / editor_buffer.sample_rate, True)
            signals.toast_requested.emit("Döngüsel çalma aktif.", "info")
        else:
            player.clear_loop()

    def _on_timeline_seek(self, sec: float):
        player.seek(sec)
        editor_buffer.cursor_sample = int(sec * editor_buffer.sample_rate)

    def _on_timeline_selection(self, s_sec: float, e_sec: float):
        editor_buffer.set_selection_sec(s_sec, e_sec)
        dur = abs(e_sec - s_sec)
        mins_s, secs_s = int(s_sec) // 60, int(s_sec) % 60
        mins_e, secs_e = int(e_sec) // 60, int(e_sec) % 60
        self.selection_lbl.setText(f"Seçim: {mins_s:02d}:{secs_s:02d} -> {mins_e:02d}:{secs_e:02d} ({dur:.2f} sn)")

    def _on_playback_pos_changed(self, cur_sec: float, total_sec: float):
        self.timeline_waveform.set_playhead_position(cur_sec)
        self._update_time_label(cur_sec, total_sec)

    def _on_playback_state_changed(self, is_playing: bool, is_paused: bool):
        if is_playing and not is_paused:
            self.btn_play.setIcon(qta.icon("fa5s.pause", color="#EF4444"))
        else:
            self.btn_play.setIcon(qta.icon("fa5s.play", color="#00E5A3"))

    def _update_time_label(self, cur_sec: float, total_sec: float):
        c_mins, c_secs = int(cur_sec) // 60, int(cur_sec) % 60
        c_ms = int((cur_sec - int(cur_sec)) * 10)
        t_mins, t_secs = int(total_sec) // 60, int(total_sec) % 60
        t_ms = int((total_sec - int(total_sec)) * 10)
        self.time_lbl.setText(f"{c_mins:02d}:{c_secs:02d}.{c_ms} / {t_mins:02d}:{t_secs:02d}.{t_ms}")

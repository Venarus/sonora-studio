"""
SONORA Studio - Application Settings View
Comprehensive preferences for audio hardware, storage paths, AI algorithms,
visual design themes, and performance configuration.
"""

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QFileDialog, QLineEdit, QComboBox,
                               QCheckBox, QSpinBox, QGridLayout, QScrollArea)
import qtawesome as qta

from app.audio.device_manager import AudioDeviceManager
from app.config import config, ACCENT_PRESETS
from app.core.signals import signals


class SettingsView(QWidget):
    """Configuration panel managing user preferences and hardware bindings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_values()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # Scroll area for clean layout
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(14)

        # 1. AUDIO HARDWARE CARD
        card_audio = self._create_card("Ses Donanımı ve Kayıt Ayarları", "fa5s.headphones")
        grid_audio = QGridLayout()
        grid_audio.setSpacing(12)

        # Input device
        grid_audio.addWidget(QLabel("Varsayılan Giriş (Mikrofon):"), 0, 0)
        self.combo_in_dev = QComboBox()
        grid_audio.addWidget(self.combo_in_dev, 0, 1)

        # Output device
        grid_audio.addWidget(QLabel("Varsayılan Çıkış (Hoparlör/Kulaklık):"), 1, 0)
        self.combo_out_dev = QComboBox()
        grid_audio.addWidget(self.combo_out_dev, 1, 1)

        # Buffer size
        grid_audio.addWidget(QLabel("Tampon Boyutu (Buffer Size):"), 2, 0)
        self.combo_buffer = QComboBox()
        self.combo_buffer.addItem("256 Örnek (Düşük Gecikme)", 256)
        self.combo_buffer.addItem("512 Örnek (Dengeli)", 512)
        self.combo_buffer.addItem("1024 Örnek (Stüdyo Standart)", 1024)
        self.combo_buffer.addItem("2048 Örnek (Yüksek Kararlılık)", 2048)
        grid_audio.addWidget(self.combo_buffer, 2, 1)

        # Default sample rate
        grid_audio.addWidget(QLabel("Varsayılan Örnekleme Hızı:"), 3, 0)
        self.combo_sr = QComboBox()
        self.combo_sr.addItem("48000 Hz (Stüdyo / Video)", 48000)
        self.combo_sr.addItem("44100 Hz (Müzik / CD)", 44100)
        self.combo_sr.addItem("96000 Hz (Mastering)", 96000)
        grid_audio.addWidget(self.combo_sr, 3, 1)

        card_audio.layout().addLayout(grid_audio)
        layout.addWidget(card_audio)

        # 2. STORAGE & PATHS CARD
        card_storage = self._create_card("Depolama ve Dosya Yolları", "fa5s.folder")
        grid_storage = QGridLayout()
        grid_storage.setSpacing(10)

        # Recordings folder
        grid_storage.addWidget(QLabel("Kayıtlar Dizini:"), 0, 0)
        self.txt_rec_dir = QLineEdit()
        grid_storage.addWidget(self.txt_rec_dir, 0, 1)
        btn_rec = QPushButton("Gözat...")
        btn_rec.clicked.connect(lambda: self._browse_dir(self.txt_rec_dir))
        grid_storage.addWidget(btn_rec, 0, 2)

        # Exports folder
        grid_storage.addWidget(QLabel("Dışa Aktarma Dizini:"), 1, 0)
        self.txt_exp_dir = QLineEdit()
        grid_storage.addWidget(self.txt_exp_dir, 1, 1)
        btn_exp = QPushButton("Gözat...")
        btn_exp.clicked.connect(lambda: self._browse_dir(self.txt_exp_dir))
        grid_storage.addWidget(btn_exp, 1, 2)

        # Naming template
        grid_storage.addWidget(QLabel("Otomatik Dosya Adı Şablonu:"), 2, 0)
        self.txt_naming = QLineEdit()
        grid_storage.addWidget(self.txt_naming, 2, 1, 1, 2)

        card_storage.layout().addLayout(grid_storage)
        layout.addWidget(card_storage)

        # 3. AI & PERFORMANCE CARD
        card_ai = self._create_card("Yapay Zeka ve İşleme Motoru", "fa5s.microchip")
        grid_ai = QGridLayout()
        grid_ai.setSpacing(12)

        grid_ai.addWidget(QLabel("AI Gürültü Azaltma Motoru:"), 0, 0)
        self.combo_ai_engine = QComboBox()
        self.combo_ai_engine.addItem("Spektral Gating AI (Önerilen - Temiz & Doğal)", "spectral_gate")
        self.combo_ai_engine.addItem("Harmonik Vokal İzolasyonu", "harmonic_ai")
        self.combo_ai_engine.addItem("Hızlı Çok Bantlı Wiener Filtresi", "fast_wiener")
        grid_ai.addWidget(self.combo_ai_engine, 0, 1)

        grid_ai.addWidget(QLabel("İşlemci İş Parçacığı (CPU Threads):"), 1, 0)
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 16)
        self.spin_threads.setValue(4)
        grid_ai.addWidget(self.spin_threads, 1, 1)

        card_ai.layout().addLayout(grid_ai)
        layout.addWidget(card_ai)

        # 4. INTERFACE & THEME CARD
        card_ui = self._create_card("Arayüz ve Tema Özelleştirme", "fa5s.palette")
        grid_ui = QGridLayout()
        grid_ui.setSpacing(12)

        grid_ui.addWidget(QLabel("Tema Modu:"), 0, 0)
        self.combo_theme = QComboBox()
        self.combo_theme.addItem("Koyu Grafit Modu (Varsayılan)", "dark")
        self.combo_theme.addItem("Açık Stüdyo Modu", "light")
        grid_ui.addWidget(self.combo_theme, 0, 1)

        grid_ui.addWidget(QLabel("Vurgu Rengi:"), 1, 0)
        self.combo_accent = QComboBox()
        for name, hex_val in ACCENT_PRESETS.items():
            self.combo_accent.addItem(name, hex_val)
        grid_ui.addWidget(self.combo_accent, 1, 1)

        self.cb_right_lib = QCheckBox("Sağ Kayıt Kütüphanesi Panelini Göster")
        self.cb_right_lib.setChecked(True)
        grid_ui.addWidget(self.cb_right_lib, 2, 0, 1, 2)

        card_ui.layout().addLayout(grid_ui)
        layout.addWidget(card_ui)

        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)

        # SAVE BUTTON ROW
        btn_h = QHBoxLayout()
        btn_h.addStretch()

        btn_save = QPushButton("  Ayarları Kaydet ve Uygula")
        btn_save.setIcon(qta.icon("fa5s.check", color="#0D0E12"))
        btn_save.setObjectName("primaryButton")
        btn_save.setMinimumSize(220, 46)
        btn_save.clicked.connect(self.save_values)
        btn_h.addWidget(btn_save)

        root_layout.addLayout(btn_h)

    def _create_card(self, title: str, icon_name: str) -> QFrame:
        card = QFrame()
        card.setObjectName("cardFrame")
        l = QVBoxLayout(card)
        l.setContentsMargins(16, 14, 16, 14)
        l.setSpacing(12)

        h = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color="#00E5A3").pixmap(18, 18))
        h.addWidget(icon_lbl)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #FFFFFF;")
        h.addWidget(t_lbl)
        h.addStretch()
        l.addLayout(h)
        return card

    def _browse_dir(self, line_edit: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, "Klasör Seç", line_edit.text())
        if d:
            line_edit.setText(d)

    def load_values(self):
        """Populate controls with current settings."""
        # Devices
        self.combo_in_dev.clear()
        for dev in AudioDeviceManager.get_input_devices():
            self.combo_in_dev.addItem(AudioDeviceManager.format_device_label(dev, True), dev["id"])
        idx_in = self.combo_in_dev.findData(config.get("input_device_id"))
        if idx_in >= 0:
            self.combo_in_dev.setCurrentIndex(idx_in)

        self.combo_out_dev.clear()
        for dev in AudioDeviceManager.get_output_devices():
            self.combo_out_dev.addItem(AudioDeviceManager.format_device_label(dev, False), dev["id"])
        idx_out = self.combo_out_dev.findData(config.get("output_device_id"))
        if idx_out >= 0:
            self.combo_out_dev.setCurrentIndex(idx_out)

        # Buffers
        idx_buf = self.combo_buffer.findData(config.get("buffer_size", 1024))
        if idx_buf >= 0:
            self.combo_buffer.setCurrentIndex(idx_buf)

        # Sample rate
        idx_sr = self.combo_sr.findData(config.get("sample_rate", 48000))
        if idx_sr >= 0:
            self.combo_sr.setCurrentIndex(idx_sr)

        # Directories
        self.txt_rec_dir.setText(config.get("recordings_dir"))
        self.txt_exp_dir.setText(config.get("exports_dir"))
        self.txt_naming.setText(config.get("naming_template", "Kayıt_{date}_{time}"))

        # AI
        idx_ai = self.combo_ai_engine.findData(config.get("ai_engine", "spectral_gate"))
        if idx_ai >= 0:
            self.combo_ai_engine.setCurrentIndex(idx_ai)
        self.spin_threads.setValue(config.get("max_threads", 4))

        # UI
        idx_th = self.combo_theme.findData(config.get("theme", "dark"))
        if idx_th >= 0:
            self.combo_theme.setCurrentIndex(idx_th)

        idx_ac = self.combo_accent.findData(config.get("accent_color", "#00E5A3"))
        if idx_ac >= 0:
            self.combo_accent.setCurrentIndex(idx_ac)

        self.cb_right_lib.setChecked(config.get("show_right_library", True))

    def save_values(self):
        """Save settings to disk and notify application."""
        config.set("input_device_id", self.combo_in_dev.currentData())
        config.set("output_device_id", self.combo_out_dev.currentData())
        config.set("buffer_size", self.combo_buffer.currentData() or 1024)
        config.set("sample_rate", self.combo_sr.currentData() or 48000)

        config.set("recordings_dir", self.txt_rec_dir.text().strip())
        config.set("exports_dir", self.txt_exp_dir.text().strip())
        config.set("naming_template", self.txt_naming.text().strip())

        config.set("ai_engine", self.combo_ai_engine.currentData() or "spectral_gate")
        config.set("max_threads", self.spin_threads.value())

        config.set("theme", self.combo_theme.currentData() or "dark")
        config.set("accent_color", self.combo_accent.currentData() or "#00E5A3")
        config.set("show_right_library", self.cb_right_lib.isChecked())

        signals.theme_changed.emit()
        signals.library_updated.emit()
        signals.toast_requested.emit("Ayarlar başarıyla kaydedildi.", "success")

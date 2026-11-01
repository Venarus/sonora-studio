"""
SONORA Studio - Modern Top Studio Navigation & Action Bar
Replaces the left sidebar with a sleek horizontal ribbon with dropdown submenus,
direct export presets, and library toggling.
"""

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QPushButton, QLabel,
                               QMenu, QButtonGroup)
import qtawesome as qta

from app.core.signals import signals
from app.config import config
from app.library.file_manager import library
from app.editor.audio_buffer import editor_buffer
from app.export.exporter import AudioExporter


class TopStudioBar(QFrame):
    """Studio top navigation ribbon with menu drop-downs and quick actions."""

    navigation_requested = Signal(str)  # view id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            TopStudioBar {
                background-color: #14161F;
                border-bottom: 1px solid #282C3A;
            }
        """)
        self._buttons = {}
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        # 1. Brand Logo & Title
        brand_h = QHBoxLayout()
        brand_h.setSpacing(8)

        logo_lbl = QLabel()
        logo_lbl.setPixmap(qta.icon("fa5s.wave-square", color="#00E5A3").pixmap(20, 20))
        brand_h.addWidget(logo_lbl)

        brand_title = QLabel("SONORA")
        brand_title.setStyleSheet("font-size: 15px; font-weight: 800; letter-spacing: 1px; color: #FFFFFF;")
        brand_h.addWidget(brand_title)

        studio_badge = QLabel("PRO")
        studio_badge.setStyleSheet("""
            background-color: rgba(0, 229, 163, 0.15);
            color: #00E5A3;
            border: 1px solid rgba(0, 229, 163, 0.3);
            border-radius: 3px;
            font-size: 9px;
            font-weight: 800;
            padding: 1px 4px;
        """)
        brand_h.addWidget(studio_badge)

        layout.addLayout(brand_h)
        layout.addSpacing(16)

        # 2. Main Navigation Buttons & Dropdown Menus
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        btn_style = """
            QPushButton {
                background-color: transparent;
                color: #D1D5DB;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #202432;
                color: #FFFFFF;
            }
            QPushButton:checked {
                background-color: #272C3E;
                color: #00E5A3;
                border-bottom: 2px solid #00E5A3;
            }
            QPushButton::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
                padding-right: 4px;
            }
        """

        # Tab 1: Studio & Waveform Editor
        self.btn_studio = QPushButton(" 🎙️ Kayıt & Düzenleme")
        self.btn_studio.setCheckable(True)
        self.btn_studio.setChecked(True)
        self.btn_studio.setStyleSheet(btn_style)
        self.btn_studio.clicked.connect(lambda: self.navigation_requested.emit("studio"))
        self.btn_group.addButton(self.btn_studio)
        self._buttons["studio"] = self.btn_studio
        layout.addWidget(self.btn_studio)

        # Tab 2: AI Audio Cleaner with Dropdown Options
        self.btn_cleaner = QPushButton(" ✨ YZ Ses Temizleme ▾")
        self.btn_cleaner.setCheckable(True)
        self.btn_cleaner.setStyleSheet(btn_style)
        self.btn_cleaner.clicked.connect(lambda: self.navigation_requested.emit("ai_cleaner"))
        self._setup_cleaner_menu(self.btn_cleaner)
        self.btn_group.addButton(self.btn_cleaner)
        self._buttons["ai_cleaner"] = self.btn_cleaner
        layout.addWidget(self.btn_cleaner)

        # Tab 3: Effects Studio with Dropdown Options
        self.btn_effects = QPushButton(" 🎛️ Ses Efektleri ▾")
        self.btn_effects.setCheckable(True)
        self.btn_effects.setStyleSheet(btn_style)
        self.btn_effects.clicked.connect(lambda: self.navigation_requested.emit("effects"))
        self._setup_effects_menu(self.btn_effects)
        self.btn_group.addButton(self.btn_effects)
        self._buttons["effects"] = self.btn_effects
        layout.addWidget(self.btn_effects)

        # Tab 4: Recording Library Table
        self.btn_library = QPushButton(" 📁 Kütüphane Tablosu")
        self.btn_library.setCheckable(True)
        self.btn_library.setStyleSheet(btn_style)
        self.btn_library.clicked.connect(lambda: self.navigation_requested.emit("library"))
        self.btn_group.addButton(self.btn_library)
        self._buttons["library"] = self.btn_library
        layout.addWidget(self.btn_library)

        # Tab 5: Settings
        self.btn_settings = QPushButton(" ⚙️ Ayarlar")
        self.btn_settings.setCheckable(True)
        self.btn_settings.setStyleSheet(btn_style)
        self.btn_settings.clicked.connect(lambda: self.navigation_requested.emit("settings"))
        self.btn_group.addButton(self.btn_settings)
        self._buttons["settings"] = self.btn_settings
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        # 3. Direct Export Center Button with Preset Dropdown Menu
        self.btn_export = QPushButton(" 📤 Dışa Aktar ▾")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setMinimumHeight(34)
        self.btn_export.setStyleSheet("""
            QPushButton#primaryButton {
                background-color: #00E5A3;
                color: #0D0E12;
                font-weight: 700;
                border-radius: 6px;
                padding: 6px 14px;
            }
            QPushButton#primaryButton:hover {
                background-color: #2EEAB5;
            }
        """)
        self._setup_export_menu(self.btn_export)
        layout.addWidget(self.btn_export)

        # 4. Right Library Sidebar Toggle Button
        self.btn_toggle_lib = QPushButton()
        self.btn_toggle_lib.setIcon(qta.icon("fa5s.columns", color="#9CA3AF"))
        self.btn_toggle_lib.setToolTip("Sağ Kütüphane Panelini Göster / Gizle")
        self.btn_toggle_lib.setFixedSize(34, 34)
        self.btn_toggle_lib.setStyleSheet("""
            QPushButton {
                background-color: #1F2330;
                border: 1px solid #2E3345;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #292E40;
                border-color: #00E5A3;
            }
        """)
        self.btn_toggle_lib.clicked.connect(self._toggle_right_library)
        layout.addWidget(self.btn_toggle_lib)

    def _setup_cleaner_menu(self, btn: QPushButton):
        menu = QMenu(btn)
        menu.setStyleSheet(self._menu_style())

        a_open = menu.addAction(qta.icon("fa5s.magic", color="#00E5A3"), "Tam Temizleme Stüdyosunu Aç")
        a_open.triggered.connect(lambda: self.navigation_requested.emit("ai_cleaner"))
        menu.addSeparator()

        a_nr = menu.addAction(qta.icon("fa5s.brain", color="#00E5A3"), "Gürültü Azaltma (Spektral)")
        a_nr.triggered.connect(lambda: self.navigation_requested.emit("ai_cleaner"))

        a_clarity = menu.addAction(qta.icon("fa5s.user-astronaut", color="#00E5A3"), "Vokal Netleştirme")
        a_clarity.triggered.connect(lambda: self.navigation_requested.emit("ai_cleaner"))

        a_reverb = menu.addAction(qta.icon("fa5s.compress", color="#00E5A3"), "Oda Yankısı Giderici")
        a_reverb.triggered.connect(lambda: self.navigation_requested.emit("ai_cleaner"))

        a_hum = menu.addAction(qta.icon("fa5s.bolt", color="#00E5A3"), "50/60 Hz Şebeke Uğultusu Kesici")
        a_hum.triggered.connect(lambda: self.navigation_requested.emit("ai_cleaner"))

        btn.setMenu(menu)

    def _setup_effects_menu(self, btn: QPushButton):
        menu = QMenu(btn)
        menu.setStyleSheet(self._menu_style())

        a_open = menu.addAction(qta.icon("fa5s.sliders-h", color="#00E5A3"), "Tam Efekt Rack'ini Aç")
        a_open.triggered.connect(lambda: self.navigation_requested.emit("effects"))
        menu.addSeparator()

        a_pod = menu.addAction(qta.icon("fa5s.podcast", color="#F59E0B"), "Önayar: Sıcak Podcast / Radyo")
        a_pod.triggered.connect(lambda: self.navigation_requested.emit("effects"))

        a_clean = menu.addAction(qta.icon("fa5s.microphone", color="#00E5A3"), "Önayar: Temiz Doğal Konuşma")
        a_clean.triggered.connect(lambda: self.navigation_requested.emit("effects"))

        a_studio = menu.addAction(qta.icon("fa5s.compact-disc", color="#6366F1"), "Önayar: Profesyonel Stüdyo Master")
        a_studio.triggered.connect(lambda: self.navigation_requested.emit("effects"))

        btn.setMenu(menu)

    def _setup_export_menu(self, btn: QPushButton):
        menu = QMenu(btn)
        menu.setStyleSheet(self._menu_style())

        a_full = menu.addAction(qta.icon("fa5s.file-export", color="#00E5A3"), "Gelişmiş Dışa Aktarma Merkezi...")
        a_full.triggered.connect(lambda: self.navigation_requested.emit("export"))
        menu.addSeparator()

        a_wav = menu.addAction(qta.icon("fa5s.file-audio", color="#FFFFFF"), "Hızlı WAV Kaydet (24-bit 48kHz)")
        a_wav.triggered.connect(lambda: self._quick_export("WAV"))

        a_mp3 = menu.addAction(qta.icon("fa5s.music", color="#FFFFFF"), "Hızlı MP3 Kaydet (Yüksek Kalite)")
        a_mp3.triggered.connect(lambda: self._quick_export("MP3"))

        a_flac = menu.addAction(qta.icon("fa5s.archive", color="#FFFFFF"), "Hızlı FLAC Kaydet (Kayıpsız)")
        a_flac.triggered.connect(lambda: self._quick_export("FLAC"))

        btn.setMenu(menu)

    def _menu_style(self) -> str:
        return """
            QMenu {
                background-color: #1A1D27;
                color: #FFFFFF;
                border: 1px solid #2F3547;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #262B3D;
                color: #00E5A3;
            }
        """

    def _quick_export(self, fmt: str):
        """Export active editor audio immediately to Exports folder."""
        if not editor_buffer.is_loaded:
            signals.toast_requested.emit("Dışa aktarılacak aktif ses yok.", "warning")
            return

        exp_dir = Path(config.get("exports_dir"))
        exp_dir.mkdir(parents=True, exist_ok=True)

        stem = Path(editor_buffer.filepath).stem if editor_buffer.filepath else "Sonora_Kayit"
        out_path = exp_dir / f"{stem}_disa_aktarim.{fmt.lower()}"

        success = AudioExporter.export(
            audio=editor_buffer.data,
            src_sr=editor_buffer.sample_rate,
            output_path=str(out_path),
            export_format=fmt,
            target_sr=48000 if fmt == "WAV" else 44100,
            channels=2,
            bit_depth="PCM_24" if fmt == "WAV" else "PCM_16"
        )
        if success:
            signals.toast_requested.emit(f"Hızlı dışa aktarıldı: {out_path.name}", "success")

    def _toggle_right_library(self):
        curr = config.get("show_right_library", True)
        config.set("show_right_library", not curr)
        signals.theme_changed.emit()

    def set_active_module(self, mod_id: str):
        if mod_id in self._buttons:
            self._buttons[mod_id].setChecked(True)

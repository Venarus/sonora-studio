"""
SONORA Studio - Export Center View
High-resolution multi-format audio rendering, sample rate conversion,
normalization, metadata tags, and studio export presets.
"""

from pathlib import Path
import threading
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QFileDialog, QLineEdit, QComboBox,
                               QCheckBox, QDoubleSpinBox, QGridLayout, QProgressBar)
import qtawesome as qta
import numpy as np
import soundfile as sf

from app.export.exporter import AudioExporter
from app.editor.audio_buffer import editor_buffer
from app.core.signals import signals
from app.config import config


class ExportCenterView(QWidget):
    """Audio export dashboard with format and metadata settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_audio: Optional[np.ndarray] = None
        self.source_sr = 48000
        self.source_filepath: Optional[str] = None

        self._init_ui()
        self._load_from_active_editor()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # 1. SOURCE SELECTION HEADER
        src_card = QFrame()
        src_card.setObjectName("cardFrame")
        src_layout = QHBoxLayout(src_card)
        src_layout.setContentsMargins(14, 10, 14, 10)
        src_layout.setSpacing(12)

        self.btn_browse = QPushButton(" Kaynak Dosya Seç")
        self.btn_browse.setIcon(qta.icon("fa5s.folder-open", color="#FFFFFF"))
        self.btn_browse.clicked.connect(self._select_source_file)
        src_layout.addWidget(self.btn_browse)

        self.lbl_src = QLabel("Dışa aktarılacak ses seçilmedi.")
        self.lbl_src.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        src_layout.addWidget(self.lbl_src, 1)

        self.btn_use_editor = QPushButton(" Düzenleyicideki Sesi Kullan")
        self.btn_use_editor.setIcon(qta.icon("fa5s.wave-square", color="#00E5A3"))
        self.btn_use_editor.clicked.connect(self._load_from_active_editor)
        src_layout.addWidget(self.btn_use_editor)

        root_layout.addWidget(src_card)

        # 2. PRESETS AND FORMAT CONFIGURATION
        cfg_card = QFrame()
        cfg_card.setObjectName("cardFrame")
        cfg_layout = QVBoxLayout(cfg_card)
        cfg_layout.setContentsMargins(16, 14, 16, 14)
        cfg_layout.setSpacing(14)

        # Presets Row
        preset_h = QHBoxLayout()
        preset_lbl = QLabel("Dışa Aktarma Önayarı:")
        preset_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #FFFFFF;")
        preset_h.addWidget(preset_lbl)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(260)
        for name in AudioExporter.EXPORT_PRESETS.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_h.addWidget(self.preset_combo)
        preset_h.addStretch()
        cfg_layout.addLayout(preset_h)

        # Technical Settings Grid
        grid = QGridLayout()
        grid.setSpacing(12)

        # Format
        fmt_lbl = QLabel("Ses Formatı:")
        fmt_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItem("WAV (Kayıpsız / Broadcast)", "WAV")
        self.fmt_combo.addItem("FLAC (Sıkıştırılmış Kayıpsız)", "FLAC")
        self.fmt_combo.addItem("MP3 (Evrensel Sıkıştırılmış)", "MP3")
        self.fmt_combo.addItem("OGG (Vorbis Açık Kaynak)", "OGG")
        self.fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        grid.addWidget(fmt_lbl, 0, 0)
        grid.addWidget(self.fmt_combo, 1, 0)

        # Sample Rate
        sr_lbl = QLabel("Örnekleme Hızı:")
        sr_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.sr_combo = QComboBox()
        self.sr_combo.addItem("48000 Hz (Stüdyo / Video)", 48000)
        self.sr_combo.addItem("44100 Hz (CD / Standart)", 44100)
        self.sr_combo.addItem("96000 Hz (Yüksek Çözünürlük)", 96000)
        grid.addWidget(sr_lbl, 0, 1)
        grid.addWidget(self.sr_combo, 1, 1)

        # Channels
        ch_lbl = QLabel("Kanal Yapısı:")
        ch_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.ch_combo = QComboBox()
        self.ch_combo.addItem("Stereo (2 Kanal)", 2)
        self.ch_combo.addItem("Mono (1 Kanal)", 1)
        grid.addWidget(ch_lbl, 0, 2)
        grid.addWidget(self.ch_combo, 1, 2)

        # Bit Depth
        depth_lbl = QLabel("Bit Derinliği:")
        depth_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
        self.depth_combo = QComboBox()
        self.depth_combo.addItem("24-bit PCM", "PCM_24")
        self.depth_combo.addItem("16-bit PCM", "PCM_16")
        self.depth_combo.addItem("32-bit Float", "FLOAT_32")
        grid.addWidget(depth_lbl, 0, 3)
        grid.addWidget(self.depth_combo, 1, 3)

        cfg_layout.addLayout(grid)

        # Normalization Row
        norm_h = QHBoxLayout()
        self.cb_normalize = QCheckBox("Dışa aktarmadan önce tepe seviyesini normalize et")
        self.cb_normalize.setChecked(True)
        self.cb_normalize.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        norm_h.addWidget(self.cb_normalize)

        norm_db_lbl = QLabel("Hedef Seviye:")
        norm_db_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        norm_h.addWidget(norm_db_lbl)

        self.spin_norm_db = QDoubleSpinBox()
        self.spin_norm_db.setRange(-20.0, 0.0)
        self.spin_norm_db.setValue(-0.5)
        self.spin_norm_db.setSuffix(" dBFS")
        norm_h.addWidget(self.spin_norm_db)
        norm_h.addStretch()

        cfg_layout.addLayout(norm_h)
        root_layout.addWidget(cfg_card)

        # 3. METADATA TAGS
        meta_card = QFrame()
        meta_card.setObjectName("cardFrame")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(16, 14, 16, 14)
        meta_layout.setSpacing(10)

        meta_title = QLabel("Ses Meta Verileri (Etiketler)")
        meta_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #FFFFFF;")
        meta_layout.addWidget(meta_title)

        m_grid = QGridLayout()
        m_grid.setSpacing(10)

        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Başlık (Örn: Bölüm 1 - Röportaj)")
        m_grid.addWidget(QLabel("Başlık:"), 0, 0)
        m_grid.addWidget(self.txt_title, 0, 1)

        self.txt_artist = QLineEdit()
        self.txt_artist.setPlaceholderText("Sanatçı / Konuşmacı")
        m_grid.addWidget(QLabel("Konuşmacı:"), 0, 2)
        m_grid.addWidget(self.txt_artist, 0, 3)

        self.txt_album = QLineEdit()
        self.txt_album.setPlaceholderText("Albüm / Seri Adı")
        m_grid.addWidget(QLabel("Albüm / Seri:"), 1, 0)
        m_grid.addWidget(self.txt_album, 1, 1)

        self.txt_year = QLineEdit()
        self.txt_year.setPlaceholderText("2026")
        m_grid.addWidget(QLabel("Yıl:"), 1, 2)
        m_grid.addWidget(self.txt_year, 1, 3)

        meta_layout.addLayout(m_grid)
        root_layout.addWidget(meta_card)

        # 4. DESTINATION & EXPORT BUTTON
        dest_card = QFrame()
        dest_card.setObjectName("cardFrame")
        dest_layout = QVBoxLayout(dest_card)
        dest_layout.setContentsMargins(16, 14, 16, 14)
        dest_layout.setSpacing(12)

        # Destination Folder & Filename
        out_h = QHBoxLayout()
        out_lbl = QLabel("Kayıt Konumu:")
        out_lbl.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        out_h.addWidget(out_lbl)

        self.txt_output_dir = QLineEdit(config.get("exports_dir"))
        out_h.addWidget(self.txt_output_dir, 1)

        btn_browse_dir = QPushButton(" Gözat...")
        btn_browse_dir.clicked.connect(self._select_export_dir)
        out_h.addWidget(btn_browse_dir)

        dest_layout.addLayout(out_h)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        dest_layout.addWidget(self.progress_bar)

        # Export Button
        btn_h = QHBoxLayout()
        btn_h.addStretch()

        self.btn_export = QPushButton("  Dışa Aktarmayı Başlat")
        self.btn_export.setIcon(qta.icon("fa5s.file-export", color="#0D0E12"))
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.setMinimumSize(220, 48)
        self.btn_export.clicked.connect(self._start_export)
        btn_h.addWidget(self.btn_export)

        dest_layout.addLayout(btn_h)
        root_layout.addWidget(dest_card)

        root_layout.addStretch()

    def _load_from_active_editor(self):
        if editor_buffer.is_loaded:
            self.source_audio = editor_buffer.data.copy()
            self.source_sr = editor_buffer.sample_rate
            self.source_filepath = editor_buffer.filepath
            name = Path(editor_buffer.filepath).name if editor_buffer.filepath else "Duzenlenmis_Ses.wav"
            self.lbl_src.setText(f"Düzenleyicideki Aktif Ses ({name})")
            self.txt_title.setText(Path(name).stem)

    def _select_source_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Dışa Aktarılacak Sesi Seç", "", "Ses Dosyaları (*.wav *.flac *.mp3 *.ogg *.aiff *.m4a)"
        )
        if path:
            try:
                data, sr = sf.read(path, dtype='float32')
                self.source_audio = data
                self.source_sr = sr
                self.source_filepath = path
                self.lbl_src.setText(Path(path).name)
                self.txt_title.setText(Path(path).stem)
                signals.toast_requested.emit(f"Kaynak seçildi: {Path(path).name}", "info")
            except Exception as e:
                signals.toast_requested.emit(f"Dosya okunamadı: {e}", "error")

    def _select_export_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Dışa Aktarma Klasörü Seç", self.txt_output_dir.text())
        if d:
            self.txt_output_dir.setText(d)

    def _on_preset_changed(self):
        name = self.preset_combo.currentText()
        if name in AudioExporter.EXPORT_PRESETS:
            p = AudioExporter.EXPORT_PRESETS[name]
            # Set Format
            idx = self.fmt_combo.findData(p["format"])
            if idx >= 0:
                self.fmt_combo.setCurrentIndex(idx)
            # Set SR
            idx_sr = self.sr_combo.findData(p["sample_rate"])
            if idx_sr >= 0:
                self.sr_combo.setCurrentIndex(idx_sr)
            # Channels
            idx_ch = self.ch_combo.findData(p["channels"])
            if idx_ch >= 0:
                self.ch_combo.setCurrentIndex(idx_ch)
            # Depth
            idx_d = self.depth_combo.findData(p["bit_depth"])
            if idx_d >= 0:
                self.depth_combo.setCurrentIndex(idx_d)
            # Normalization
            self.cb_normalize.setChecked(p.get("normalize", True))
            self.spin_norm_db.setValue(p.get("normalize_db", -0.5))

    def _on_format_changed(self):
        fmt = self.fmt_combo.currentData()
        if fmt in ("MP3", "OGG"):
            self.depth_combo.setEnabled(False)
        else:
            self.depth_combo.setEnabled(True)

    def _start_export(self):
        if self.source_audio is None:
            signals.toast_requested.emit("Lütfen önce bir ses seçin veya kaydedin.", "warning")
            return

        out_dir = Path(self.txt_output_dir.text().strip())
        out_dir.mkdir(parents=True, exist_ok=True)

        fmt = self.fmt_combo.currentData() or "WAV"
        ext = fmt.lower()
        title_stem = self.txt_title.text().strip() or "Sonora_Export"
        final_filename = f"{title_stem}.{ext}"
        out_path = out_dir / final_filename

        sr = self.sr_combo.currentData() or 48000
        channels = self.ch_combo.currentData() or 2
        bit_depth = self.depth_combo.currentData() or "PCM_24"
        norm = self.cb_normalize.isChecked()
        norm_db = self.spin_norm_db.value()

        self.btn_export.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)

        thread = threading.Thread(
            target=self._export_worker,
            args=(out_path, fmt, sr, channels, bit_depth, norm, norm_db),
            daemon=True
        )
        thread.start()

    def _export_worker(self, out_path: Path, fmt: str, sr: int, channels: int, bit_depth: str, norm: bool, norm_db: float):
        def progress_cb(pct: int, msg: str):
            QTimer.singleShot(0, lambda: self.progress_bar.setValue(pct))

        success = AudioExporter.export(
            audio=self.source_audio,
            src_sr=self.source_sr,
            output_path=str(out_path),
            export_format=fmt,
            target_sr=sr,
            channels=channels,
            bit_depth=bit_depth,
            normalize=norm,
            normalize_db=norm_db,
            progress_cb=progress_cb
        )

        QTimer.singleShot(0, lambda: self._on_export_finished(success, str(out_path)))

    def _on_export_finished(self, success: bool, out_path_str: str):
        self.btn_export.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            signals.toast_requested.emit(f"Dışa aktarıldı: {Path(out_path_str).name}", "success")

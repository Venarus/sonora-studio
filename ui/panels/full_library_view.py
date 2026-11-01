"""
SONORA Studio - Full-Screen Recording Library Manager
Comprehensive file management, multi-selection, bulk operations,
disk metrics, folder organization, and direct module loading.
"""

from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFrame, QLineEdit, QComboBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QMenu, QFileDialog)
import qtawesome as qta

from app.library.file_manager import library, LibraryItem
from app.audio.playback_engine import player
from app.core.signals import signals
from app.config import config
from ui.widgets.dialogs import ConfirmDialog, InputTextDialog


class FullLibraryView(QWidget):
    """Full-featured file manager table for all studio recordings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()
        self.refresh_table()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        # 1. TOP TOOLBAR & CONTROLS
        tb_card = QFrame()
        tb_card.setObjectName("cardFrame")
        tb_layout = QHBoxLayout(tb_card)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kayıt adında ara...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self.refresh_table)
        tb_layout.addWidget(self.search_input)

        # Format filter
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItem("Tüm Formatlar", "all")
        self.fmt_combo.addItem("WAV Dosyaları", "wav")
        self.fmt_combo.addItem("FLAC Dosyaları", "flac")
        self.fmt_combo.addItem("MP3 Dosyaları", "mp3")
        self.fmt_combo.addItem("OGG Dosyaları", "ogg")
        self.fmt_combo.currentIndexChanged.connect(self.refresh_table)
        tb_layout.addWidget(self.fmt_combo)

        # Folder selector
        self.folder_combo = QComboBox()
        self.folder_combo.addItem("Tüm Kayıtlar (Ana Dizin)", "")
        self.folder_combo.currentIndexChanged.connect(self.refresh_table)
        tb_layout.addWidget(self.folder_combo)

        self.btn_new_folder = QPushButton(" Yeni Klasör")
        self.btn_new_folder.setIcon(qta.icon("fa5s.folder-plus", color="#FFFFFF"))
        self.btn_new_folder.clicked.connect(self._create_folder)
        tb_layout.addWidget(self.btn_new_folder)

        tb_layout.addStretch()

        # Explorer reveal button
        self.btn_explorer = QPushButton(" Windows Gezgininde Aç")
        self.btn_explorer.setIcon(qta.icon("fa5s.external-link-alt", color="#FFFFFF"))
        self.btn_explorer.clicked.connect(lambda: library.open_containing_folder())
        tb_layout.addWidget(self.btn_explorer)

        main_layout.addWidget(tb_card)

        # 2. BULK OPERATIONS ACTION BAR
        bulk_bar = QHBoxLayout()
        bulk_bar.setSpacing(8)

        self.btn_bulk_play = QPushButton(" Çal")
        self.btn_bulk_play.setIcon(qta.icon("fa5s.play", color="#00E5A3"))
        self.btn_bulk_play.clicked.connect(self._play_selected)
        bulk_bar.addWidget(self.btn_bulk_play)

        self.btn_bulk_edit = QPushButton(" Düzenleyicide Aç")
        self.btn_bulk_edit.setIcon(qta.icon("fa5s.wave-square", color="#6366F1"))
        self.btn_bulk_edit.clicked.connect(self._open_selected_in_editor)
        bulk_bar.addWidget(self.btn_bulk_edit)

        self.btn_bulk_clean = QPushButton(" YZ ile Temizle")
        self.btn_bulk_clean.setIcon(qta.icon("fa5s.magic", color="#00E5A3"))
        self.btn_bulk_clean.clicked.connect(self._open_selected_in_cleaner)
        bulk_bar.addWidget(self.btn_bulk_clean)

        self.btn_bulk_del = QPushButton(" Seçilenleri Sil")
        self.btn_bulk_del.setObjectName("dangerButton")
        self.btn_bulk_del.setIcon(qta.icon("fa5s.trash-alt", color="#EF4444"))
        self.btn_bulk_del.clicked.connect(self._delete_selected)
        bulk_bar.addWidget(self.btn_bulk_del)

        bulk_bar.addStretch()
        main_layout.addLayout(bulk_bar)

        # 3. RECORDINGS TABLE
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "★", "Dosya Adı", "Süre", "Format", "Örnekleme", "Boyut", "Değiştirilme", "Durum"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.itemDoubleClicked.connect(lambda item: self._open_selected_in_editor())
        main_layout.addWidget(self.table, 1)

        # 4. FOOTER METRICS SUMMARY
        footer_card = QFrame()
        footer_card.setObjectName("cardFrame")
        f_layout = QHBoxLayout(footer_card)
        f_layout.setContentsMargins(14, 8, 14, 8)

        self.lbl_stats = QLabel("Toplam: 0 Dosya • 00:00:00 Toplam Süre • 0 MB Disk Alanı")
        self.lbl_stats.setStyleSheet("color: #9CA3AF; font-size: 12px; font-weight: 600;")
        f_layout.addWidget(self.lbl_stats)
        f_layout.addStretch()

        btn_refresh = QPushButton(" Yenile")
        btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#9CA3AF"))
        btn_refresh.clicked.connect(self.refresh_table)
        f_layout.addWidget(btn_refresh)

        main_layout.addWidget(footer_card)

    def _connect_signals(self):
        signals.library_updated.connect(self.refresh_table)

    def refresh_table(self):
        """Re-scan folder and populate table."""
        # Update folders
        curr_folder = self.folder_combo.currentData()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem("Tüm Kayıtlar (Ana Dizin)", "")
        for sub in library.list_subfolders():
            self.folder_combo.addItem(f"📁 {sub}", sub)
        idx = self.folder_combo.findData(curr_folder)
        if idx >= 0:
            self.folder_combo.setCurrentIndex(idx)
        self.folder_combo.blockSignals(False)

        # Query items
        q = self.search_input.text().strip()
        fmt = self.fmt_combo.currentData() or "all"
        subfolder = self.folder_combo.currentData()

        items = library.list_recordings(search_query=q, format_filter=fmt, subfolder=subfolder)

        self.table.setRowCount(len(items))

        total_duration = 0.0
        total_size = 0

        for r, it in enumerate(items):
            total_duration += it.duration_sec
            total_size += it.size_bytes

            # 0. Fav
            star_item = QTableWidgetItem("★" if it.is_favorite else "☆")
            star_item.setTextAlignment(Qt.AlignCenter)
            star_item.setForeground(Qt.yellow if it.is_favorite else Qt.gray)
            star_item.setData(Qt.UserRole, str(it.path))
            self.table.setItem(r, 0, star_item)

            # 1. Name
            name_item = QTableWidgetItem(it.name)
            name_item.setData(Qt.UserRole, str(it.path))
            self.table.setItem(r, 1, name_item)

            # 2. Duration
            dur_item = QTableWidgetItem(it.formatted_duration)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, dur_item)

            # 3. Format
            fmt_item = QTableWidgetItem(it.format_str)
            fmt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, fmt_item)

            # 4. SR
            sr_item = QTableWidgetItem(f"{it.sample_rate} Hz" if it.sample_rate else "--")
            sr_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 4, sr_item)

            # 5. Size
            sz_item = QTableWidgetItem(it.formatted_size)
            sz_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 5, sz_item)

            # 6. Date
            dt_item = QTableWidgetItem(it.formatted_date)
            dt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 6, dt_item)

            # 7. Status
            status_str = "YZ Temizlenmiş" if it.is_processed else "Orijinal Kayıt"
            st_item = QTableWidgetItem(status_str)
            st_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 7, st_item)

        # Summary
        hrs = int(total_duration) // 3600
        mins = (int(total_duration) % 3600) // 60
        secs = int(total_duration) % 60
        mb = total_size / (1024.0 * 1024.0)
        self.lbl_stats.setText(f"Toplam: {len(items)} Kayıt • {hrs:02d}:{mins:02d}:{secs:02d} Toplam Süre • {mb:.1f} MB Disk Alanı")

    def _get_selected_paths(self):
        paths = []
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        for r in rows:
            item = self.table.item(r, 0)
            if item:
                p_str = item.data(Qt.UserRole)
                if p_str:
                    paths.append(Path(p_str))
        return paths

    def _play_selected(self):
        paths = self._get_selected_paths()
        if paths:
            player.load_file(str(paths[0]))
            player.play()

    def _open_selected_in_editor(self):
        paths = self._get_selected_paths()
        if paths:
            signals.audio_loaded_for_editing.emit(str(paths[0]))
            signals.switch_view_requested.emit("editor")

    def _open_selected_in_cleaner(self):
        paths = self._get_selected_paths()
        if paths:
            signals.audio_loaded_for_cleaning.emit(str(paths[0]))
            signals.switch_view_requested.emit("ai_cleaner")

    def _delete_selected(self):
        paths = self._get_selected_paths()
        if not paths:
            return
        dlg = ConfirmDialog(self, "Kayıtları Sil", f"Seçili {len(paths)} dosyayı kalıcı olarak silmek istediğinizden emin misiniz?", is_danger=True)
        if dlg.exec():
            library.delete_files(paths)

    def _create_folder(self):
        dlg = InputTextDialog(self, "Yeni Klasör", "Oluşturulacak klasör adını girin:")
        if dlg.exec():
            name = dlg.get_text()
            if name:
                library.create_subfolder(name)

    def _show_context_menu(self, pos):
        paths = self._get_selected_paths()
        if not paths:
            return
        menu = QMenu(self)

        act_play = menu.addAction(qta.icon("fa5s.play", color="#00E5A3"), "Çal")
        act_play.triggered.connect(self._play_selected)

        act_edit = menu.addAction(qta.icon("fa5s.wave-square", color="#6366F1"), "Düzenleyicide Aç")
        act_edit.triggered.connect(self._open_selected_in_editor)

        act_clean = menu.addAction(qta.icon("fa5s.magic", color="#00E5A3"), "YZ ile Temizle")
        act_clean.triggered.connect(self._open_selected_in_cleaner)

        menu.addSeparator()

        act_reveal = menu.addAction(qta.icon("fa5s.folder-open", color="#9CA3AF"), "Windows Gezgininde Göster")
        act_reveal.triggered.connect(lambda: library.reveal_in_explorer(paths[0]))

        menu.addSeparator()

        act_del = menu.addAction(qta.icon("fa5s.trash-alt", color="#EF4444"), "Sil")
        act_del.triggered.connect(self._delete_selected)

        menu.exec(self.table.mapToGlobal(pos))

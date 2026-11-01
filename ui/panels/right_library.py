"""
SONORA Studio - Right Sidebar Recording Library (Live Real-Time Sync & Auto-Detect)
Real Windows filesystem audio manager with live 800ms directory polling,
QFileSystemWatcher dual-layer sync, clear empty states, and Explorer integration.
"""

import os
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QSize, QFileSystemWatcher, QTimer
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QComboBox, QListWidget, QListWidgetItem,
                               QWidget, QPushButton, QMenu)
import qtawesome as qta

from app.library.file_manager import library, LibraryItem
from app.audio.playback_engine import player
from app.core.signals import signals
from app.config import config
from ui.widgets.dialogs import ConfirmDialog, InputTextDialog


class RecordingListItemWidget(QWidget):
    """Custom item widget rendering rich recording metadata and quick play."""

    def __init__(self, item: LibraryItem, parent_list=None):
        super().__init__(parent_list)
        self.item = item
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Quick Play Button
        self.btn_play = QPushButton()
        self.btn_play.setFixedSize(28, 28)
        self.btn_play.setIcon(qta.icon("fa5s.play", color="#00E5A3"))
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #232733;
                border: 1px solid #333849;
                border-radius: 14px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #2C3141;
                border-color: #00E5A3;
            }
        """)
        self.btn_play.clicked.connect(self._toggle_quick_play)
        layout.addWidget(self.btn_play)

        # Text Details (Name, duration, size, date)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        # Top line: Name + Processed badge
        top_h = QHBoxLayout()
        name_lbl = QLabel(self.item.name)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 12px; color: #FFFFFF;")
        top_h.addWidget(name_lbl)

        if self.item.is_processed:
            badge = QLabel(" YZ ")
            badge.setStyleSheet("background: rgba(0,229,163,0.15); color: #00E5A3; border-radius: 3px; font-size: 9px; font-weight: 700;")
            top_h.addWidget(badge)

        top_h.addStretch()
        info_layout.addLayout(top_h)

        # Subtitle: Duration • Size • Date
        sub_lbl = QLabel(f"{self.item.formatted_duration} • {self.item.formatted_size} • {self.item.formatted_date}")
        sub_lbl.setStyleSheet("font-size: 10px; color: #9CA3AF;")
        info_layout.addWidget(sub_lbl)

        layout.addLayout(info_layout, 1)

        # Favorite star button
        self.btn_fav = QPushButton()
        self.btn_fav.setFixedSize(24, 24)
        fav_icon = "ri.star-fill" if self.item.is_favorite else "ri.star-line"
        fav_color = "#F59E0B" if self.item.is_favorite else "#6B7280"
        self.btn_fav.setIcon(qta.icon(fav_icon, color=fav_color))
        self.btn_fav.setStyleSheet("background: transparent; border: none; padding: 0px;")
        self.btn_fav.clicked.connect(self._toggle_favorite)
        layout.addWidget(self.btn_fav)

    def _toggle_quick_play(self):
        if player.is_playing:
            player.stop()
            self.btn_play.setIcon(qta.icon("fa5s.play", color="#00E5A3"))
        else:
            if player.load_file(str(self.item.path)):
                player.play()
                self.btn_play.setIcon(qta.icon("fa5s.pause", color="#EF4444"))

    def _toggle_favorite(self):
        is_fav = library.toggle_favorite(self.item.path)
        fav_icon = "ri.star-fill" if is_fav else "ri.star-line"
        fav_color = "#F59E0B" if is_fav else "#6B7280"
        self.btn_fav.setIcon(qta.icon(fav_icon, color=fav_color))


class RightLibraryPanel(QFrame):
    """Integrated right sidebar file manager with dual-layer real-time sync."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightSidebar")
        self.setFixedWidth(290)

        self._cached_file_count = -1
        self._cached_mtime = 0.0
        self._last_selected_path: Optional[str] = None

        # 1. Qt FileSystemWatcher
        self.fs_watcher = QFileSystemWatcher(self)
        self._setup_fs_watcher()

        # 2. Robust 400ms Real-Time Directory Poller (guarantees live sync on Windows!)
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self._check_disk_changes)
        self.sync_timer.start(400)

        self._init_ui()
        self._connect_signals()
        self.refresh_list()

    def _setup_fs_watcher(self):
        rec_dir = Path(config.get("recordings_dir"))
        rec_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.fs_watcher.addPath(str(rec_dir))
            self.fs_watcher.directoryChanged.connect(self.refresh_list)
        except Exception:
            pass

    def _check_disk_changes(self):
        """Ultra-fast (0.1ms) check if directory files or mtime changed on Windows disk."""
        rec_dir = Path(config.get("recordings_dir"))
        if not rec_dir.exists():
            return
        try:
            files = [f for f in os.scandir(rec_dir) if f.is_file() and f.name.lower().endswith(('.wav', '.flac', '.mp3', '.ogg', '.m4a'))]
            audio_count = len(files)
            max_mtime = max((f.stat().st_mtime for f in files), default=0.0)
            if audio_count != self._cached_file_count or max_mtime != self._cached_mtime:
                self._cached_file_count = audio_count
                self._cached_mtime = max_mtime
                self.refresh_list()
        except Exception:
            pass

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header: Title + Open Folder Button
        header = QHBoxLayout()
        header_lbl = QLabel("Kayıt Kütüphanesi")
        header_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #FFFFFF;")
        header.addWidget(header_lbl)
        header.addStretch()

        self.btn_open_folder = QPushButton()
        self.btn_open_folder.setToolTip("Kayıtlar Klasörünü Windows Gezgininde Aç")
        self.btn_open_folder.setIcon(qta.icon("fa5s.external-link-alt", color="#9CA3AF"))
        self.btn_open_folder.setFixedSize(28, 28)
        self.btn_open_folder.clicked.connect(lambda: library.open_containing_folder())
        header.addWidget(self.btn_open_folder)

        layout.addLayout(header)

        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Kayıtlarda ara...")
        self.search_input.textChanged.connect(self.refresh_list)
        layout.addWidget(self.search_input)

        # Sort and Filter row
        sort_h = QHBoxLayout()
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("En Yeni", "date_desc")
        self.sort_combo.addItem("En Eski", "date_asc")
        self.sort_combo.addItem("İsim (A-Z)", "name_asc")
        self.sort_combo.addItem("Süre", "duration_desc")
        self.sort_combo.addItem("Boyut", "size_desc")
        self.sort_combo.currentIndexChanged.connect(self.refresh_list)
        sort_h.addWidget(self.sort_combo, 1)

        # Favorite Filter Button (Clear outline vs filled gold visual state)
        self.fav_filter_btn = QPushButton()
        self.fav_filter_btn.setCheckable(True)
        self.fav_filter_btn.setToolTip("Favori Filtresi (Açıkken sadece yıldızlı kayıtları listeler)")
        self.fav_filter_btn.setIcon(qta.icon("ri.star-line", color="#6B7280"))
        self.fav_filter_btn.setFixedSize(30, 30)
        self.fav_filter_btn.clicked.connect(self._on_fav_filter_clicked)
        sort_h.addWidget(self.fav_filter_btn)

        layout.addLayout(sort_h)

        # Empty State Message Label (Visible when no files match filter)
        self.empty_lbl = QLabel("")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setWordWrap(True)
        self.empty_lbl.setStyleSheet("color: #6B7280; font-size: 11px; padding: 20px 10px; background: rgba(255,255,255,0.02); border-radius: 6px;")
        self.empty_lbl.setVisible(False)
        layout.addWidget(self.empty_lbl)

        # Recordings List Widget
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget, 1)

        # Footer statistics & quick actions
        footer = QHBoxLayout()
        self.stats_lbl = QLabel("0 kayıt")
        self.stats_lbl.setStyleSheet("color: #6B7280; font-size: 11px;")
        footer.addWidget(self.stats_lbl)
        footer.addStretch()

        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(qta.icon("fa5s.sync-alt", color="#9CA3AF"))
        self.btn_refresh.setFixedSize(26, 26)
        self.btn_refresh.setToolTip("Listeyi Şimdi Yenile")
        self.btn_refresh.clicked.connect(self.refresh_list)
        footer.addWidget(self.btn_refresh)

        layout.addLayout(footer)

    def _on_fav_filter_clicked(self):
        is_active = self.fav_filter_btn.isChecked()
        fav_icon = "ri.star-fill" if is_active else "ri.star-line"
        fav_color = "#F59E0B" if is_active else "#6B7280"
        self.fav_filter_btn.setIcon(qta.icon(fav_icon, color=fav_color))
        self.refresh_list()

    def _connect_signals(self):
        signals.library_updated.connect(self.refresh_list)
        signals.recording_stopped.connect(self._on_recording_saved)

    def _on_recording_saved(self, saved_path: str):
        # Auto-disable favorite filter if on, so user immediately sees new recording!
        if self.fav_filter_btn.isChecked():
            self.fav_filter_btn.setChecked(False)
            self.fav_filter_btn.setIcon(qta.icon("ri.star-line", color="#6B7280"))
        self.refresh_list(select_path=saved_path)

    def refresh_list(self, select_path: Optional[str] = None):
        """Reload recordings directly from Windows disk."""
        search_query = self.search_input.text().strip()
        sort_by = self.sort_combo.currentData() or "date_desc"
        only_fav = self.fav_filter_btn.isChecked()

        if select_path:
            self._last_selected_path = str(Path(select_path).resolve())

        items = library.list_recordings(
            search_query=search_query,
            sort_by=sort_by,
            only_favorites=only_fav
        )

        self.list_widget.clear()

        if len(items) == 0:
            self.list_widget.setVisible(False)
            self.empty_lbl.setVisible(True)
            if only_fav:
                self.empty_lbl.setText("★ Favori kayıt bulunamadı.\n(Tüm kayıtları görmek için yıldız filtresini kapatın)")
            elif search_query:
                self.empty_lbl.setText(f"'{search_query}' ile eşleşen kayıt bulunamadı.")
            else:
                self.empty_lbl.setText("📁 Henüz kayıt yapılmadı.\nKayda başlamak için 'KAYDA BAŞLA' butonuna tıklayın.")
        else:
            self.empty_lbl.setVisible(False)
            self.list_widget.setVisible(True)
            target_item_widget = None
            norm_target = os.path.normcase(self._last_selected_path) if self._last_selected_path else None

            for it in items:
                list_item = QListWidgetItem(self.list_widget)
                list_item.setSizeHint(QSize(0, 52))
                resolved_str = str(it.path.resolve())
                list_item.setData(Qt.UserRole, resolved_str)

                widget = RecordingListItemWidget(it, self.list_widget)
                self.list_widget.setItemWidget(list_item, widget)

                if norm_target and os.path.normcase(resolved_str) == norm_target:
                    target_item_widget = list_item

            if target_item_widget:
                self.list_widget.setCurrentItem(target_item_widget)
                self.list_widget.scrollToItem(target_item_widget)

        self.stats_lbl.setText(f"{len(items)} kayıt")

    def _on_item_double_clicked(self, item: QListWidgetItem):
        path_str = item.data(Qt.UserRole)
        if path_str:
            signals.audio_loaded_for_editing.emit(path_str)
            signals.switch_view_requested.emit("studio")

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            menu = QMenu(self)
            act_paste = menu.addAction(qta.icon("fa5s.paste", color="#9CA3AF"), "Buraya Yapıştır")
            act_paste.triggered.connect(lambda: library.paste_from_clipboard())
            act_explorer = menu.addAction(qta.icon("fa5s.folder-open", color="#9CA3AF"), "Gezginde Aç")
            act_explorer.triggered.connect(lambda: library.open_containing_folder())
            menu.exec(self.list_widget.mapToGlobal(pos))
            return

        path = Path(item.data(Qt.UserRole))
        menu = QMenu(self)

        act_play = menu.addAction(qta.icon("fa5s.play", color="#00E5A3"), "Çal")
        act_play.triggered.connect(lambda: self._play_file(path))

        menu.addSeparator()

        act_edit = menu.addAction(qta.icon("fa5s.wave-square", color="#6366F1"), "Stüdyoda Düzenle")
        act_edit.triggered.connect(lambda: self._open_in_editor(path))

        act_clean = menu.addAction(qta.icon("fa5s.magic", color="#00E5A3"), "YZ ile Temizle")
        act_clean.triggered.connect(lambda: self._open_in_cleaner(path))

        act_fx = menu.addAction(qta.icon("fa5s.sliders-h", color="#F59E0B"), "Ses Efektlerine Aktar")
        act_fx.triggered.connect(lambda: self._open_in_effects(path))

        menu.addSeparator()

        act_rename = menu.addAction(qta.icon("fa5s.edit", color="#9CA3AF"), "Yeniden Adlandır")
        act_rename.triggered.connect(lambda: self._rename_file(path))

        act_dup = menu.addAction(qta.icon("fa5s.clone", color="#9CA3AF"), "Çoğalt (Kopya)")
        act_dup.triggered.connect(lambda: library.duplicate_file(path))

        act_copy = menu.addAction(qta.icon("fa5s.copy", color="#9CA3AF"), "Kopyala")
        act_copy.triggered.connect(lambda: library.copy_to_clipboard([path]))

        act_cut = menu.addAction(qta.icon("fa5s.cut", color="#9CA3AF"), "Kes")
        act_cut.triggered.connect(lambda: library.cut_to_clipboard([path]))

        act_reveal = menu.addAction(qta.icon("fa5s.folder-open", color="#9CA3AF"), "Windows Gezgininde Göster")
        act_reveal.triggered.connect(lambda: library.reveal_in_explorer(path))

        menu.addSeparator()

        act_delete = menu.addAction(qta.icon("fa5s.trash-alt", color="#EF4444"), "Sil")
        act_delete.triggered.connect(lambda: self._delete_file(path))

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _play_file(self, path: Path):
        player.load_file(str(path))
        player.play()

    def _open_in_editor(self, path: Path):
        signals.audio_loaded_for_editing.emit(str(path))
        signals.switch_view_requested.emit("studio")

    def _open_in_cleaner(self, path: Path):
        signals.audio_loaded_for_cleaning.emit(str(path))
        signals.switch_view_requested.emit("ai_cleaner")

    def _open_in_effects(self, path: Path):
        signals.audio_loaded_for_effects.emit(str(path))
        signals.switch_view_requested.emit("effects")

    def _rename_file(self, path: Path):
        dlg = InputTextDialog(self, "Yeniden Adlandır", "Yeni dosya adını girin:", initial_text=path.stem)
        if dlg.exec():
            new_name = dlg.get_text()
            if new_name:
                library.rename_file(path, new_name)

    def _delete_file(self, path: Path):
        dlg = ConfirmDialog(self, "Kaydı Sil", f"'{path.name}' dosyasını kalıcı olarak silmek istediğinizden emin misiniz?", is_danger=True)
        if dlg.exec():
            library.delete_files([path])

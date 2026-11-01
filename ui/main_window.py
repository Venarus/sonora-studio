"""
SONORA Studio - Main Desktop Application Window (Modern Top-Bar Architecture)
Workspace integrating unified recording & editing, AI cleaning, effects rack,
full library manager, and top action ribbon.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QStackedWidget)

from app.config import config
from app.core.signals import signals
from app.audio.recording_engine import recorder
from ui.theme import get_stylesheet
from ui.widgets.title_bar import CustomTitleBar
from ui.widgets.toast import ToastNotification
from ui.widgets.dialogs import ConfirmDialog

from ui.panels.top_studio_bar import TopStudioBar
from ui.panels.right_library import RightLibraryPanel
from ui.panels.studio_editor_view import StudioEditorView
from ui.panels.ai_cleaner_view import AICleaningStudioView
from ui.panels.effects_view import AudioEffectsView
from ui.panels.full_library_view import FullLibraryView
from ui.panels.export_view import ExportCenterView
from ui.panels.settings_view import SettingsView


class MainWindow(QMainWindow):
    """Primary application frame hosting top studio ribbon, workspace, and right library."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setMinimumSize(1150, 750)
        self.resize(1340, 850)

        self._init_ui()
        self._apply_theme()
        self._connect_signals()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Frameless Title Bar
        self.title_bar = CustomTitleBar(self)
        root_layout.addWidget(self.title_bar)

        # 2. Modern Top Studio Navigation Ribbon
        self.top_bar = TopStudioBar(self)
        self.top_bar.navigation_requested.connect(self._switch_view_by_id)
        root_layout.addWidget(self.top_bar)

        # 3. Main Workspace Body (Center Stack + Right Library)
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Center Stacked Workspace
        self.center_stack = QStackedWidget(self)

        # 0: Unified Studio & Waveform Editor
        self.view_studio = StudioEditorView(self)
        # 1: AI Audio Cleaning Station
        self.view_cleaner = AICleaningStudioView(self)
        # 2: Audio Effects Rack
        self.view_effects = AudioEffectsView(self)
        # 3: Full Screen Library Manager
        self.view_library = FullLibraryView(self)
        # 4: Export Center
        self.view_export = ExportCenterView(self)
        # 5: Settings
        self.view_settings = SettingsView(self)

        self.center_stack.addWidget(self.view_studio)    # index 0
        self.center_stack.addWidget(self.view_cleaner)   # index 1
        self.center_stack.addWidget(self.view_effects)   # index 2
        self.center_stack.addWidget(self.view_library)   # index 3
        self.center_stack.addWidget(self.view_export)    # index 4
        self.center_stack.addWidget(self.view_settings)  # index 5

        body_layout.addWidget(self.center_stack, 1)

        # Right Library Sidebar
        self.right_library = RightLibraryPanel(self)
        body_layout.addWidget(self.right_library)

        root_layout.addWidget(body, 1)

        self._view_map = {
            "studio": 0,
            "ai_cleaner": 1,
            "effects": 2,
            "library": 3,
            "export": 4,
            "settings": 5
        }

    def _switch_view_by_id(self, view_id: str):
        if view_id in self._view_map:
            idx = self._view_map[view_id]
            self.center_stack.setCurrentIndex(idx)
            self.top_bar.set_active_module(view_id)

            # Auto-hide right sidebar when full library table view is open
            if view_id == "library":
                self.right_library.setVisible(False)
            else:
                self.right_library.setVisible(config.get("show_right_library", True))

    def _apply_theme(self):
        theme_name = config.get("theme", "dark")
        accent = config.get("accent_color", "#00E5A3")
        qss = get_stylesheet(theme=theme_name, accent_hex=accent)
        self.setStyleSheet(qss)
        self.right_library.setVisible(config.get("show_right_library", True))

    def _connect_signals(self):
        signals.switch_view_requested.connect(self._switch_view_by_id)
        signals.toast_requested.connect(self.show_toast)
        signals.theme_changed.connect(self._apply_theme)

        # Title bar status synchronization
        signals.recording_started.connect(lambda: self.title_bar.set_status("KAYITTA", "recording"))
        signals.recording_paused.connect(lambda: self.title_bar.set_status("DURAKLATILDI", "processing"))
        signals.recording_resumed.connect(lambda: self.title_bar.set_status("KAYITTA", "recording"))
        signals.recording_stopped.connect(lambda p: self.title_bar.set_status("HAZIR", "ready"))

    def show_toast(self, message: str, level: str = "info"):
        toast = ToastNotification(self, message, level)
        toast.show()
        x = self.width() - toast.width() - 25
        y = 52
        toast.move(x, y)

    def closeEvent(self, event):
        if recorder.is_recording:
            dlg = ConfirmDialog(
                self,
                "Kayıt Devam Ediyor",
                "Aktif bir kayıt devam ediyor. Çıkarsanız kayıt tamamlanıp kaydedilecektir. Çıkmak istiyor musunuz?",
                is_danger=True
            )
            if dlg.exec():
                recorder.stop_recording()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

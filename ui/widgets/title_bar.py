"""
SONORA Studio - Windows 11 Custom Title Bar
Integrated title bar with window movement, state badges, and window controls.
"""

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
import qtawesome as qta


class CustomTitleBar(QWidget):
    """Custom frameless window title bar with native Windows controls."""

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.window = parent_window
        self.setFixedHeight(38)
        self._drag_pos = QPoint()

        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(10)

        # App Icon & Title
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(qta.icon("fa5s.wave-square", color="#00E5A3").pixmap(18, 18))
        layout.addWidget(self.icon_lbl)

        self.title_lbl = QLabel("SONORA Studio Pro")
        self.title_lbl.setStyleSheet("font-weight: 700; font-size: 13px; letter-spacing: 0.5px;")
        layout.addWidget(self.title_lbl)

        # Status badge (HAZIR, KAYITTA, İŞLENİYOR)
        self.status_badge = QLabel(" HAZIR ")
        self.status_badge.setStyleSheet("""
            background-color: rgba(0, 229, 163, 0.15);
            color: #00E5A3;
            border: 1px solid rgba(0, 229, 163, 0.3);
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
        """)
        layout.addWidget(self.status_badge)

        layout.addStretch()

        # Window Controls (Minimize, Maximize/Restore, Close)
        btn_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                width: 44px;
                height: 38px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """
        close_style = """
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 0px;
                padding: 0px;
                width: 44px;
                height: 38px;
            }
            QPushButton:hover {
                background-color: #E81123;
                color: #FFFFFF;
            }
        """

        self.btn_min = QPushButton()
        self.btn_min.setIcon(qta.icon("fa5s.minus", color="#9CA3AF"))
        self.btn_min.setStyleSheet(btn_style)
        self.btn_min.clicked.connect(self.window.showMinimized)
        layout.addWidget(self.btn_min)

        self.btn_max = QPushButton()
        self.btn_max.setIcon(qta.icon("fa5s.expand-alt", color="#9CA3AF"))
        self.btn_max.setStyleSheet(btn_style)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        layout.addWidget(self.btn_max)

        self.btn_close = QPushButton()
        self.btn_close.setIcon(qta.icon("fa5s.times", color="#9CA3AF"))
        self.btn_close.setStyleSheet(close_style)
        self.btn_close.clicked.connect(self.window.close)
        layout.addWidget(self.btn_close)

    def set_status(self, text: str, state_type: str = "ready"):
        """Update studio status badge."""
        self.status_badge.setText(f" {text} ")
        if state_type == "recording":
            self.status_badge.setStyleSheet("""
                background-color: rgba(239, 68, 68, 0.2);
                color: #EF4444;
                border: 1px solid rgba(239, 68, 68, 0.4);
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
            """)
        elif state_type == "processing":
            self.status_badge.setStyleSheet("""
                background-color: rgba(245, 158, 11, 0.2);
                color: #F59E0B;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
            """)
        else:  # ready
            self.status_badge.setStyleSheet("""
                background-color: rgba(0, 229, 163, 0.15);
                color: #00E5A3;
                border: 1px solid rgba(0, 229, 163, 0.3);
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
            """)

    def _toggle_max_restore(self):
        if self.window.isMaximized():
            self.window.showNormal()
            self.btn_max.setIcon(qta.icon("fa5s.expand-alt", color="#9CA3AF"))
        else:
            self.window.showMaximized()
            self.btn_max.setIcon(qta.icon("fa5s.compress-alt", color="#9CA3AF"))

    # Mouse drag events for frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.window.isMaximized():
            self.window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_max_restore()
            event.accept()

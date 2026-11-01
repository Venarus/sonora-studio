"""
SONORA Studio - Modern Modal Dialogs
Windows 11 styled dialogs for user confirmations, text input, and progress tracking.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QProgressBar)
import qtawesome as qta


class ConfirmDialog(QDialog):
    """Modern confirmation dialog for destructive actions."""

    def __init__(self, parent, title: str, message: str, is_danger: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1C24;
                border: 1px solid #2F3342;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header with icon
        header_layout = QHBoxLayout()
        icon_name = "fa5s.exclamation-triangle" if is_danger else "fa5s.question-circle"
        icon_color = "#EF4444" if is_danger else "#00E5A3"
        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=icon_color).pixmap(24, 24))
        header_layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #D1D5DB; font-size: 13px; line-height: 1.4;")
        layout.addWidget(msg_lbl)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("Onayla")
        if is_danger:
            self.btn_confirm.setObjectName("dangerButton")
            self.btn_confirm.setText("Sil")
        else:
            self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)


class InputTextDialog(QDialog):
    """Modern input dialog for renaming or new folder name."""

    def __init__(self, parent, title: str, prompt: str, initial_text: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(380)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1C24;
                border: 1px solid #2F3342;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(title_lbl)

        prompt_lbl = QLabel(prompt)
        prompt_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(prompt_lbl)

        self.line_edit = QLineEdit(initial_text)
        self.line_edit.selectAll()
        layout.addWidget(self.line_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_ok = QPushButton("Kaydet")
        self.btn_ok.setObjectName("primaryButton")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def get_text(self) -> str:
        return self.line_edit.text().strip()


class ProcessingDialog(QDialog):
    """Modal progress dialog for background audio tasks with progress bar and status text."""

    def __init__(self, parent, task_title: str):
        super().__init__(parent)
        self.setWindowTitle(task_title)
        self.setFixedWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #1A1C24;
                border: 1px solid #2F3342;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        self.title_lbl = QLabel(task_title)
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #FFFFFF;")
        layout.addWidget(self.title_lbl)

        self.status_lbl = QLabel("İşlem başlatılıyor...")
        self.status_lbl.setStyleSheet("color: #9CA3AF; font-size: 12px;")
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def set_progress(self, percent: int, text: str):
        self.progress_bar.setValue(percent)
        self.status_lbl.setText(text)

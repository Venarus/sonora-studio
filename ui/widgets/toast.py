"""
SONORA Studio - Toast Notification Overlay
Modern non-intrusive floating toasts that auto-dismiss.
"""

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QGraphicsOpacityEffect
import qtawesome as qta


class ToastNotification(QWidget):
    """Floating alert box displayed on top of the main window."""

    def __init__(self, parent, message: str, level: str = "info", duration_ms: int = 3500):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self._init_ui(message, level)

        # Timer to auto close
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)
        self.timer.start(duration_ms)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        # Fade in animation
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

    def _init_ui(self, message: str, level: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        color_map = {
            "success": ("#00E5A3", "fa5s.check-circle"),
            "warning": ("#F59E0B", "fa5s.exclamation-triangle"),
            "error": ("#EF4444", "fa5s.times-circle"),
            "info": ("#00B4D8", "fa5s.info-circle")
        }
        color, icon_name = color_map.get(level, color_map["info"])

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(18, 18))
        layout.addWidget(icon_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setStyleSheet("color: #FFFFFF; font-weight: 500; font-size: 13px;")
        layout.addWidget(msg_lbl)

        self.setStyleSheet(f"""
            ToastNotification {{
                background-color: #1F222C;
                border: 1px solid {color};
                border-radius: 8px;
            }}
        """)
        self.adjustSize()

    def _fade_out(self):
        self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

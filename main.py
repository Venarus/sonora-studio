"""
SONORA STUDIO — Professional AI Audio Recorder & Editor
Windows 11 Desktop Application Entrypoint (Optimized)
"""

import sys
import os
import ctypes
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
import qtawesome as qta

from app.config import APP_NAME, APP_VERSION, ORGANIZATION_NAME, config
from app.core.logger import get_logger
from ui.main_window import MainWindow

logger = get_logger("Main")


def setup_windows_taskbar_integration():
    """Ensure Windows taskbar recognizes SONORA Studio as an independent application."""
    if os.name == "nt":
        try:
            myappid = f"sonora.audio.studio.pro.{APP_VERSION}"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            logger.debug(f"Taskbar AppUserModelID ayarlanamadı: {e}")


def exception_hook(exctype, value, tb):
    """Global uncaught exception handler to prevent silent crashes."""
    import traceback
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Beklenmeyen Sistem Hatası:\n{err_msg}")
    print(err_msg, file=sys.stderr)


def main():
    sys.excepthook = exception_hook
    setup_windows_taskbar_integration()

    # Enable High DPI and Modern Font Rendering
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)

    # Set High-Resolution Application Icon
    ico_path = ROOT_DIR / "assets" / "icons" / "sonora.ico"
    if ico_path.exists():
        app.setWindowIcon(QIcon(str(ico_path)))
    else:
        app.setWindowIcon(qta.icon("fa5s.wave-square", color="#00E5A3"))

    # Default UI Font
    font = QFont("Segoe UI Variable Display", 10)
    if not font.exactMatch():
        font = QFont("Segoe UI", 10)
    app.setFont(font)

    logger.info(f"=== {APP_NAME} {APP_VERSION} Başlatılıyor ===")

    # Initialize and display Main Window
    window = MainWindow()
    if ico_path.exists():
        window.setWindowIcon(QIcon(str(ico_path)))
    window.show()

    exit_code = app.exec()
    logger.info(f"=== {APP_NAME} Kapatıldı (Çıkış Kodu: {exit_code}) ===")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

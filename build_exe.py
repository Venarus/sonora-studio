"""
SONORA Studio - PyInstaller Executable Builder
Builds a standalone Windows 11 executable bundled with custom studio icon.
"""

import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
DIST_DIR = ROOT_DIR / "dist"
ICO_PATH = ROOT_DIR / "assets" / "icons" / "sonora.ico"


def build():
    print("=" * 60)
    print("  SONORA Studio - Windows Executable Derleyici")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=SONORA_Studio",
        "--noconsole",
        "--onedir",
        "--clean",
        f"--icon={ICO_PATH}",
        f"--add-data={ROOT_DIR / 'assets'};assets",
        f"--add-data={ROOT_DIR / 'app'};app",
        f"--add-data={ROOT_DIR / 'ui'};ui",
        "--hidden-import=PySide6",
        "--hidden-import=qtawesome",
        "--hidden-import=sounddevice",
        "--hidden-import=soundfile",
        "--hidden-import=scipy.signal",
        "--hidden-import=noisereduce",
        str(ROOT_DIR / "main.py")
    ]

    print("\nDerleme komutu çalıştırılıyor:")
    print(" ".join(cmd))
    print("\nLütfen bekleyin...")

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("  [BAŞARILI] SONORA Studio başarıyla derlendi!")
        print(f"  Çıktı klasörü: {DIST_DIR / 'SONORA_Studio'}")
        print("=" * 60)
    else:
        print("\n[HATA] Derleme sırasında hata oluştu. Kod:", result.returncode)


if __name__ == "__main__":
    build()

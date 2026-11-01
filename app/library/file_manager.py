"""
SONORA Studio - Integrated Recording Library & Windows File Manager
Performs actual Windows filesystem operations: copy, cut, paste, rename,
move, delete, duplicate, favorites, metadata extraction, and Explorer integration.
"""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import soundfile as sf
from app.config import config
from app.core.logger import get_logger
from app.core.signals import signals

logger = get_logger("FileManager")


class LibraryItem:
    """Represents an audio file item in the library with parsed metadata."""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.stem = path.stem
        self.suffix = path.suffix.lower()
        self.size_bytes = 0
        self.modified_time = datetime.fromtimestamp(0)
        self.duration_sec = 0.0
        self.sample_rate = 0
        self.channels = 0
        self.format_str = path.suffix.upper().replace(".", "")
        self.is_favorite = False
        self.is_processed = "_temizlenmis" in self.stem or "_islenmis" in self.stem or "_cleaned" in self.stem

        self.refresh_metadata()

    def refresh_metadata(self):
        """Read file stat and soundfile headers."""
        if not self.path.exists():
            return
        try:
            stat = self.path.stat()
            self.size_bytes = stat.st_size
            self.modified_time = datetime.fromtimestamp(stat.st_mtime)

            # Read soundfile header without loading entire audio into RAM
            try:
                info = sf.info(str(self.path))
                self.duration_sec = info.duration
                self.sample_rate = info.samplerate
                self.channels = info.channels
                self.format_str = info.format
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Metadata okuma hatası ({self.path}): {e}")

    @property
    def formatted_size(self) -> str:
        kb = self.size_bytes / 1024.0
        if kb < 1024.0:
            return f"{kb:.1f} KB"
        mb = kb / 1024.0
        return f"{mb:.1f} MB"

    @property
    def formatted_duration(self) -> str:
        total_sec = int(self.duration_sec)
        mins = total_sec // 60
        secs = total_sec % 60
        ms = int((self.duration_sec - total_sec) * 10)
        return f"{mins:02d}:{secs:02d}.{ms}"

    @property
    def formatted_date(self) -> str:
        return self.modified_time.strftime("%d.%m.%Y %H:%M")


class RecordingLibrary:
    """Manages audio recordings and folders in the recordings directory."""

    def __init__(self):
        self.favorites: set = set()
        self._clipboard_paths: List[Path] = []
        self._clipboard_action: Optional[str] = None  # "copy" or "cut"
        self._load_favorites()

    def _get_favorites_file(self) -> Path:
        cache_dir = Path(config.get("cache_dir"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "favorites.txt"

    def _load_favorites(self):
        fav_file = self._get_favorites_file()
        if fav_file.exists():
            try:
                with open(fav_file, "r", encoding="utf-8") as f:
                    self.favorites = set(line.strip() for line in f if line.strip())
            except Exception:
                self.favorites = set()

    def _save_favorites(self):
        try:
            with open(self._get_favorites_file(), "w", encoding="utf-8") as f:
                for path_str in self.favorites:
                    f.write(f"{path_str}\n")
        except Exception as e:
            logger.error(f"Favoriler kaydedilemedi: {e}")

    def toggle_favorite(self, path: Path) -> bool:
        """Toggle favorite state of file."""
        path_str = str(path.resolve())
        if path_str in self.favorites:
            self.favorites.remove(path_str)
            fav = False
        else:
            self.favorites.add(path_str)
            fav = True
        self._save_favorites()
        signals.library_updated.emit()
        return fav

    def list_recordings(self,
                        search_query: str = "",
                        sort_by: str = "date_desc",
                        format_filter: str = "all",
                        only_favorites: bool = False,
                        subfolder: Optional[str] = None) -> List[LibraryItem]:
        """Scan directory and return sorted, filtered LibraryItem list."""
        base_dir = Path(config.get("recordings_dir"))
        if subfolder:
            scan_dir = base_dir / subfolder
        else:
            scan_dir = base_dir

        scan_dir.mkdir(parents=True, exist_ok=True)

        supported_exts = {".wav", ".flac", ".mp3", ".ogg", ".aiff", ".m4a"}
        items: List[LibraryItem] = []

        try:
            for entry in scan_dir.iterdir():
                if entry.is_file() and entry.suffix.lower() in supported_exts:
                    item = LibraryItem(entry)
                    item.is_favorite = str(entry.resolve()) in self.favorites

                    # Apply search filter
                    if search_query and search_query.lower() not in item.name.lower():
                        continue

                    # Apply format filter
                    if format_filter != "all" and item.suffix.lower() != f".{format_filter.lower()}":
                        continue

                    # Apply favorites filter
                    if only_favorites and not item.is_favorite:
                        continue

                    items.append(item)
        except Exception as e:
            logger.error(f"Kayıtlar listelenirken hata: {e}")

        # Sorting
        if sort_by == "date_desc":
            items.sort(key=lambda x: x.modified_time, reverse=True)
        elif sort_by == "date_asc":
            items.sort(key=lambda x: x.modified_time, reverse=False)
        elif sort_by == "name_asc":
            items.sort(key=lambda x: x.name.lower(), reverse=False)
        elif sort_by == "name_desc":
            items.sort(key=lambda x: x.name.lower(), reverse=True)
        elif sort_by == "duration_desc":
            items.sort(key=lambda x: x.duration_sec, reverse=True)
        elif sort_by == "size_desc":
            items.sort(key=lambda x: x.size_bytes, reverse=True)

        return items

    def list_subfolders(self) -> List[str]:
        """List subdirectories in recordings directory."""
        base_dir = Path(config.get("recordings_dir"))
        subfolders = []
        if base_dir.exists():
            for p in base_dir.iterdir():
                if p.is_dir() and not p.name.startswith("."):
                    subfolders.append(p.name)
        return sorted(subfolders)

    def create_subfolder(self, folder_name: str) -> bool:
        """Create a new organization folder."""
        base_dir = Path(config.get("recordings_dir"))
        target = base_dir / folder_name.strip()
        try:
            target.mkdir(parents=True, exist_ok=False)
            signals.library_updated.emit()
            signals.toast_requested.emit(f"Klasör oluşturuldu: {folder_name}", "success")
            return True
        except Exception as e:
            logger.error(f"Klasör oluşturma hatası: {e}")
            signals.toast_requested.emit(f"Klasör oluşturulamadı: {e}", "error")
            return False

    def rename_file(self, old_path: Path, new_name: str) -> Optional[Path]:
        """Rename file on disk safely without overwriting."""
        if not new_name.endswith(old_path.suffix):
            new_name += old_path.suffix

        target = old_path.parent / new_name
        if target == old_path:
            return old_path

        if target.exists():
            signals.toast_requested.emit("Bu isimde bir dosya zaten var!", "warning")
            return None

        try:
            old_path.rename(target)
            # Update favorites if needed
            old_str = str(old_path.resolve())
            if old_str in self.favorites:
                self.favorites.remove(old_str)
                self.favorites.add(str(target.resolve()))
                self._save_favorites()

            signals.library_updated.emit()
            signals.toast_requested.emit(f"Yeniden adlandırıldı: {new_name}", "success")
            return target
        except Exception as e:
            logger.error(f"Yeniden adlandırma hatası: {e}")
            signals.toast_requested.emit(f"Adlandırılamadı: {e}", "error")
            return None

    def duplicate_file(self, src_path: Path) -> Optional[Path]:
        """Create a duplicate copy of file on disk with safe suffix."""
        if not src_path.exists():
            return None

        parent = src_path.parent
        stem = src_path.stem
        ext = src_path.suffix

        counter = 1
        target = parent / f"{stem}_kopya{ext}"
        while target.exists():
            counter += 1
            target = parent / f"{stem}_kopya_{counter}{ext}"

        try:
            shutil.copy2(src_path, target)
            signals.library_updated.emit()
            signals.toast_requested.emit(f"Dosya çoğaltıldı: {target.name}", "success")
            return target
        except Exception as e:
            logger.error(f"Çoğaltma hatası: {e}")
            signals.toast_requested.emit(f"Çoğaltılamadı: {e}", "error")
            return None

    def delete_files(self, paths: List[Path]) -> int:
        """Delete files permanently from Windows disk."""
        deleted_count = 0
        for p in paths:
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                    deleted_count += 1
                    # Remove from favorites
                    p_str = str(p.resolve())
                    if p_str in self.favorites:
                        self.favorites.remove(p_str)
                except Exception as e:
                    logger.error(f"Dosya silme hatası ({p}): {e}")

        if deleted_count > 0:
            self._save_favorites()
            signals.library_updated.emit()
            signals.toast_requested.emit(f"{deleted_count} kayıt silindi.", "info")

        return deleted_count

    def copy_to_clipboard(self, paths: List[Path]):
        """Stage files for copy operation."""
        self._clipboard_paths = [p for p in paths if p.exists()]
        self._clipboard_action = "copy"
        signals.toast_requested.emit(f"{len(self._clipboard_paths)} dosya panoya kopyalandı.", "info")

    def cut_to_clipboard(self, paths: List[Path]):
        """Stage files for cut (move) operation."""
        self._clipboard_paths = [p for p in paths if p.exists()]
        self._clipboard_action = "cut"
        signals.toast_requested.emit(f"{len(self._clipboard_paths)} dosya kesildi.", "info")

    def paste_from_clipboard(self, target_folder: Optional[Path] = None) -> int:
        """Paste staged files into target directory."""
        if not self._clipboard_paths:
            return 0

        dest_dir = target_folder or Path(config.get("recordings_dir"))
        dest_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for src in self._clipboard_paths:
            if not src.exists():
                continue

            target = dest_dir / src.name
            # Avoid overwrite
            if target.exists() and target != src:
                stem = src.stem
                ext = src.suffix
                c = 1
                while target.exists():
                    target = dest_dir / f"{stem}_{c}{ext}"
                    c += 1

            try:
                if self._clipboard_action == "cut":
                    shutil.move(src, target)
                else:
                    shutil.copy2(src, target)
                count += 1
            except Exception as e:
                logger.error(f"Yapıştırma hatası: {e}")

        if self._clipboard_action == "cut":
            self._clipboard_paths.clear()
            self._clipboard_action = None

        if count > 0:
            signals.library_updated.emit()
            signals.toast_requested.emit(f"{count} dosya yapıştırıldı.", "success")

        return count

    def reveal_in_explorer(self, path: Path):
        """Reveal file in Windows File Explorer (explorer.exe /select,path)."""
        if not path.exists():
            signals.toast_requested.emit("Dosya bulunamadı.", "warning")
            return
        try:
            # On Windows, /select, selects the specific file
            norm_path = os.path.normpath(str(path.resolve()))
            subprocess.Popen(f'explorer /select,"{norm_path}"')
        except Exception as e:
            logger.error(f"Explorer açma hatası: {e}")
            signals.toast_requested.emit(f"Dosya konumu açılamadı: {e}", "error")

    def open_containing_folder(self, folder: Optional[Path] = None):
        """Open recordings folder in Windows File Explorer."""
        target = folder or Path(config.get("recordings_dir"))
        target.mkdir(parents=True, exist_ok=True)
        try:
            norm_path = os.path.normpath(str(target.resolve()))
            subprocess.Popen(f'explorer "{norm_path}"')
        except Exception as e:
            logger.error(f"Klasör açma hatası: {e}")


# Global library instance
library = RecordingLibrary()

"""
SONORA Studio - Application Configuration & Settings Manager
Handles user preferences, paths, audio presets, and persistent state.
"""

import os
import json
from pathlib import Path

# Application constants
APP_NAME = "SONORA Studio"
APP_VERSION = "1.0.0 Pro"
ORGANIZATION_NAME = "SONORA Audio Labs"

# Default directories in user Documents
DOCUMENTS_DIR = Path(os.path.expanduser("~")) / "Documents" / "SONORA Studio"
DEFAULT_RECORDINGS_DIR = DOCUMENTS_DIR / "Recordings"
DEFAULT_EXPORTS_DIR = DOCUMENTS_DIR / "Exports"
DEFAULT_CACHE_DIR = DOCUMENTS_DIR / "Cache"
CONFIG_FILE_PATH = DOCUMENTS_DIR / "settings.json"

DEFAULT_SETTINGS = {
    # Audio Recording Settings
    "input_device_id": None,
    "input_device_name": "",
    "output_device_id": None,
    "output_device_name": "",
    "sample_rate": 48000,
    "channels": 2,
    "bit_depth": "PCM_24",
    "buffer_size": 1024,
    "default_format": "wav",
    
    # Storage & Files
    "recordings_dir": str(DEFAULT_RECORDINGS_DIR),
    "exports_dir": str(DEFAULT_EXPORTS_DIR),
    "cache_dir": str(DEFAULT_CACHE_DIR),
    "naming_template": "Kayıt_{date}_{time}",
    "auto_backup": True,
    
    # AI & Cleaning Settings
    "ai_engine": "spectral_gate",  # "spectral_gate", "harmonic_ai", "deep_clean"
    "noise_reduction_strength": 75,
    "processing_quality": "balanced",  # "fast", "balanced", "ultra"
    "max_threads": 4,
    
    # Interface Settings
    "theme": "dark",  # "dark" or "light"
    "accent_color": "#00E5A3",  # Neon Teal Studio Accent
    "waveform_style": "smooth",  # "smooth", "bars", "outline"
    "show_right_library": True,
    "auto_save_projects": True,
    "language": "tr"
}

ACCENT_PRESETS = {
    "Neon Zümrüt (Varsayılan)": "#00E5A3",
    "Elektrik İndigo": "#6366F1",
    "Gökyüzü Mavisi": "#00B4D8",
    "Kehribar Altın": "#F59E0B",
    "Siber Macenta": "#EC4899",
    "Stüdyo Kırmızı": "#EF4444"
}


class ConfigManager:
    """Singleton configuration manager that loads and saves JSON settings safely."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._init_config()
        return cls._instance
        
    def _init_config(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self._ensure_directories()
        self.load_settings()
        
    def _ensure_directories(self):
        """Ensure all required folders exist on Windows filesystem."""
        try:
            DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
            Path(self.settings["recordings_dir"]).mkdir(parents=True, exist_ok=True)
            Path(self.settings["exports_dir"]).mkdir(parents=True, exist_ok=True)
            Path(self.settings["cache_dir"]).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"[ConfigManager] Dizin oluşturma hatası: {e}")
            
    def load_settings(self):
        """Load settings from JSON file if present."""
        if CONFIG_FILE_PATH.exists():
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception as e:
                print(f"[ConfigManager] Ayar okuma hatası: {e}")
        else:
            self.save_settings()
            
    def save_settings(self):
        """Write current settings to JSON file."""
        try:
            CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Ayar kaydetme hatası: {e}")
            
    def get(self, key, default=None):
        return self.settings.get(key, default)
        
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
        
    def update(self, mapping: dict):
        self.settings.update(mapping)
        self.save_settings()


# Global accessor
config = ConfigManager()

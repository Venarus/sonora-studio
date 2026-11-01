"""
SONORA Studio - Shared Application State
"""

from typing import Optional


class AppState:
    """Stores transient runtime state accessible across views and background workers."""
    def __init__(self):
        self.current_recording_path: Optional[str] = None
        self.active_editor_path: Optional[str] = None
        self.active_cleaner_path: Optional[str] = None
        self.active_effects_path: Optional[str] = None
        self.is_recording: bool = False
        self.is_recording_paused: bool = False
        self.is_playing: bool = False
        self.is_playing_paused: bool = False
        self.active_view: str = "studio"


state = AppState()

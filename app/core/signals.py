"""
SONORA Studio - Central Event Bus (Qt Signals)
Provides decoupled, thread-safe communication between audio threads, AI processors, and UI.
"""

from PySide6.QtCore import QObject, Signal


class AppSignals(QObject):
    """Singleton event bus using Qt Signals for cross-thread safety."""
    
    # Recording signals
    recording_started = Signal()
    recording_paused = Signal()
    recording_resumed = Signal()
    recording_stopped = Signal(str)  # saved file path
    recording_level_updated = Signal(float, float, float, float, bool)  # peak_l, peak_r, rms_l, rms_r, is_clipping
    recording_waveform_chunk = Signal(object)  # np.ndarray
    recording_duration_updated = Signal(float)  # seconds
    
    # Playback signals
    playback_state_changed = Signal(bool, bool)  # is_playing, is_paused
    playback_position_changed = Signal(float, float)  # current_seconds, total_seconds
    playback_finished = Signal()
    
    # Module navigation and data passing
    audio_loaded_for_editing = Signal(str)   # filepath
    audio_loaded_for_cleaning = Signal(str)  # filepath
    audio_loaded_for_effects = Signal(str)   # filepath
    switch_view_requested = Signal(str)     # view_id (e.g. "editor", "ai_cleaner")
    
    # Library updates
    library_updated = Signal()
    file_selected_in_library = Signal(str)
    
    # AI and Batch Processing signals
    processing_started = Signal(str)  # task name
    processing_progress = Signal(int, str)  # percent 0-100, status message
    processing_finished = Signal(str, str)  # output_path, error_message (empty if success)
    
    # UI Notification and Customization
    toast_requested = Signal(str, str)  # message, level ("info", "success", "warning", "error")
    theme_changed = Signal()
    device_list_updated = Signal()
    editor_history_changed = Signal(bool, bool)  # can_undo, can_redo


# Global singleton instance
signals = AppSignals()

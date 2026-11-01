"""
SONORA Studio - Audio Device Manager
Enumerates, inspects, and validates real audio input and output devices.
"""

from typing import List, Dict, Any, Optional
import sounddevice as sd
from app.core.logger import get_logger

logger = get_logger("DeviceManager")


class AudioDeviceManager:
    """Manages audio hardware enumeration, capabilities, and format validation."""

    STANDARD_SAMPLE_RATES = [44100, 48000, 88200, 96000, 192000]

    @classmethod
    def get_devices(cls) -> List[Dict[str, Any]]:
        """Return all sound devices reported by the OS backend."""
        try:
            raw_devices = sd.query_devices()
            devices = []
            for i, dev in enumerate(raw_devices):
                dev_info = dict(dev)
                dev_info["id"] = i
                dev_info["hostapi_name"] = sd.query_hostapis(dev["hostapi"])["name"]
                devices.append(dev_info)
            return devices
        except Exception as e:
            logger.error(f"Ses cihazları listelenirken hata: {e}")
            return []

    @classmethod
    def get_input_devices(cls) -> List[Dict[str, Any]]:
        """Return only valid microphone/input devices."""
        devices = cls.get_devices()
        input_devs = [d for d in devices if d["max_input_channels"] > 0]
        return input_devs

    @classmethod
    def get_output_devices(cls) -> List[Dict[str, Any]]:
        """Return only valid speaker/output devices."""
        devices = cls.get_devices()
        output_devs = [d for d in devices if d["max_output_channels"] > 0]
        return output_devs

    @classmethod
    def get_default_input_device_id(cls) -> Optional[int]:
        """Get default OS recording device ID."""
        try:
            default_in, _ = sd.default.device
            if default_in is not None and default_in >= 0:
                return default_in
            # Fallback to first available input device
            in_devs = cls.get_input_devices()
            return in_devs[0]["id"] if in_devs else None
        except Exception as e:
            logger.warning(f"Varsayılan giriş cihazı alınamadı: {e}")
            return None

    @classmethod
    def get_default_output_device_id(cls) -> Optional[int]:
        """Get default OS playback device ID."""
        try:
            _, default_out = sd.default.device
            if default_out is not None and default_out >= 0:
                return default_out
            out_devs = cls.get_output_devices()
            return out_devs[0]["id"] if out_devs else None
        except Exception as e:
            logger.warning(f"Varsayılan çıkış cihazı alınamadı: {e}")
            return None

    @classmethod
    def get_supported_sample_rates(cls, device_id: int, is_input: bool = True) -> List[int]:
        """Test and return actual hardware-supported sample rates for the selected device."""
        supported = []
        for sr in cls.STANDARD_SAMPLE_RATES:
            try:
                if is_input:
                    sd.check_input_settings(device=device_id, samplerate=sr)
                else:
                    sd.check_output_settings(device=device_id, samplerate=sr)
                supported.append(sr)
            except Exception:
                continue
        # If none verified, at least include 48000 and 44100 as standard fallback
        if not supported:
            supported = [44100, 48000]
        return supported

    @classmethod
    def format_device_label(cls, dev: Dict[str, Any], is_input: bool = True) -> str:
        """Create a clean, descriptive Turkish label for device dropdowns."""
        name = dev.get("name", "Bilinmeyen Cihaz")
        api = dev.get("hostapi_name", "")
        channels = dev.get("max_input_channels" if is_input else "max_output_channels", 2)
        ch_str = f"{channels} Kanal" if channels > 1 else "Mono (1 Kanal)"
        return f"{name} ({api}) — {ch_str}"

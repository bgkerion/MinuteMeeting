"""Platform-specific discovery of system-audio loopback sources.

Windows  — WASAPI loopback on the default output device (built-in).
Linux    — PulseAudio/PipeWire monitor source (built-in).
macOS    — not supported natively; returns None (use BlackHole instead).
"""

from __future__ import annotations

import platform
from dataclasses import dataclass

import sounddevice as sd


@dataclass(frozen=True)
class LoopbackDevice:
    device_index: int
    sample_rate: int
    channels: int     # channels to capture (1 = mono, 2 = stereo)
    label: str        # human-readable name for status bar


def find_loopback_device() -> LoopbackDevice | None:
    """Return the best available system-audio loopback source, or None."""
    os_name = platform.system()
    if os_name == "Windows":
        return _find_wasapi_loopback()
    if os_name == "Linux":
        return _find_linux_monitor()
    return None


# ------------------------------------------------------------------
# Windows — WASAPI loopback
# ------------------------------------------------------------------

def _find_wasapi_loopback() -> LoopbackDevice | None:
    if not hasattr(sd, "WasapiSettings"):
        return None
    try:
        output_idx = sd.default.device[1]
        if output_idx < 0:
            return None
        info = sd.query_devices(output_idx)
        sr = int(info.get("default_samplerate", 48_000))
        # Loopback captures the output channels of the device (not input channels)
        ch = min(int(info.get("max_output_channels", 2)), 2)
        ch = max(ch, 1)
        name = info.get("name", "output device")
        return LoopbackDevice(device_index=output_idx, sample_rate=sr,
                              channels=ch, label=name)
    except Exception:
        return None


# ------------------------------------------------------------------
# Linux — PulseAudio / PipeWire monitor source
# ------------------------------------------------------------------

def _find_linux_monitor() -> LoopbackDevice | None:
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            name = str(dev.get("name", ""))
            if "monitor" in name.lower() and int(dev.get("max_input_channels", 0)) > 0:
                sr = int(dev.get("default_samplerate", 44_100))
                ch = min(int(dev.get("max_input_channels", 2)), 2)
                return LoopbackDevice(device_index=i, sample_rate=sr,
                                      channels=ch, label=name)
    except Exception:
        pass
    return None

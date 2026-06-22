"""Tests for audio/loopback.py — no audio hardware required."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from minute_meeting.audio.loopback import (
    LoopbackDevice,
    _find_linux_monitor,
    _find_macos_blackhole,
    find_loopback_device,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dev(name: str, *, inputs: int = 0, outputs: int = 0, sr: float = 44_100.0) -> dict:
    return {
        "name": name,
        "max_input_channels": inputs,
        "max_output_channels": outputs,
        "default_samplerate": sr,
    }


# ---------------------------------------------------------------------------
# _find_macos_blackhole
# ---------------------------------------------------------------------------

def test_blackhole_detected() -> None:
    devices = [
        _dev("Built-in Microphone", inputs=1),
        _dev("BlackHole 2ch", inputs=2, sr=44_100.0),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_macos_blackhole()
    assert lb is not None
    assert lb.label == "BlackHole 2ch"
    assert lb.channels == 2
    assert lb.sample_rate == 44_100


def test_blackhole_channels_capped_at_two() -> None:
    """BlackHole 16ch has 16 input channels; we only need 2 for stereo mix."""
    devices = [_dev("BlackHole 16ch", inputs=16, sr=48_000.0)]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_macos_blackhole()
    assert lb is not None
    assert lb.channels == 2


def test_blackhole_not_found_returns_none() -> None:
    devices = [_dev("Built-in Microphone", inputs=1)]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_macos_blackhole()
    assert lb is None


def test_blackhole_name_case_insensitive() -> None:
    devices = [_dev("BlackHole 2ch", inputs=2)]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_macos_blackhole()
    assert lb is not None


def test_blackhole_zero_input_channels_ignored() -> None:
    """A device named 'blackhole' with no input channels must be skipped."""
    devices = [_dev("BlackHole output", inputs=0, outputs=2)]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_macos_blackhole()
    assert lb is None


def test_blackhole_sd_exception_returns_none() -> None:
    with patch("sounddevice.query_devices", side_effect=RuntimeError("PortAudio error")):
        lb = _find_macos_blackhole()
    assert lb is None


# ---------------------------------------------------------------------------
# _find_linux_monitor
# ---------------------------------------------------------------------------

def test_linux_monitor_detected() -> None:
    devices = [
        _dev("Built-in Microphone", inputs=1),
        _dev("alsa_output.pci.monitor", inputs=2, sr=48_000.0),
    ]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_linux_monitor()
    assert lb is not None
    assert "monitor" in lb.label.lower()
    assert lb.sample_rate == 48_000


def test_linux_monitor_not_found_returns_none() -> None:
    devices = [_dev("Built-in Microphone", inputs=1)]
    with patch("sounddevice.query_devices", return_value=devices):
        lb = _find_linux_monitor()
    assert lb is None


# ---------------------------------------------------------------------------
# find_loopback_device — platform dispatch
# ---------------------------------------------------------------------------

def test_find_loopback_darwin_dispatches_to_blackhole() -> None:
    devices = [_dev("BlackHole 2ch", inputs=2)]
    with patch("platform.system", return_value="Darwin"), \
         patch("sounddevice.query_devices", return_value=devices):
        lb = find_loopback_device()
    assert lb is not None
    assert "BlackHole" in lb.label


def test_find_loopback_linux_dispatches_to_monitor() -> None:
    devices = [_dev("pulse.monitor", inputs=2)]
    with patch("platform.system", return_value="Linux"), \
         patch("sounddevice.query_devices", return_value=devices):
        lb = find_loopback_device()
    assert lb is not None


def test_find_loopback_unknown_os_returns_none() -> None:
    with patch("platform.system", return_value="FreeBSD"):
        lb = find_loopback_device()
    assert lb is None


def test_find_loopback_darwin_no_blackhole_returns_none() -> None:
    devices = [_dev("Built-in Microphone", inputs=1)]
    with patch("platform.system", return_value="Darwin"), \
         patch("sounddevice.query_devices", return_value=devices):
        lb = find_loopback_device()
    assert lb is None

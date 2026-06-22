"""Tests for utils/device.py — no GPU required."""

from __future__ import annotations

import pytest

from minute_meeting.utils.device import speechbrain_device, torch_device, whisper_device


def test_whisper_device_returns_two_strings() -> None:
    device, compute_type = whisper_device()
    assert isinstance(device, str)
    assert isinstance(compute_type, str)


def test_whisper_device_valid_values() -> None:
    device, compute_type = whisper_device()
    assert device in ("cpu", "cuda")
    assert compute_type in ("int8", "float16")


def test_torch_device_valid_value() -> None:
    device = torch_device()
    assert device in ("cpu", "cuda", "mps")


def test_whisper_device_cpu_when_no_cuda() -> None:
    import torch
    if torch.cuda.is_available():
        pytest.skip("CUDA available — test targets CPU-only environment")
    device, compute_type = whisper_device()
    assert device == "cpu"
    assert compute_type == "int8"


def test_torch_device_returns_cpu_when_no_accelerator() -> None:
    import torch
    if torch.cuda.is_available() or torch.backends.mps.is_available():
        pytest.skip("Accelerator available — test targets CPU-only environment")
    assert torch_device() == "cpu"


def test_speechbrain_device_never_returns_mps() -> None:
    # SpeechBrain from_hparams does not set device_type for 'mps'; always cpu/cuda
    device = speechbrain_device()
    assert device in ("cpu", "cuda")
    assert device != "mps"

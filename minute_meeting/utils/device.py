"""Auto-detect the best compute device for each inference backend."""

from __future__ import annotations

import platform


def torch_device() -> str:
    """Best device for plain-PyTorch tensor operations.

    Priority: CUDA > MPS (Apple Silicon) > CPU.
    """
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if platform.system() == "Darwin" and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def speechbrain_device() -> str:
    """Best device for SpeechBrain inference (from_hparams).

    SpeechBrain's Pretrained.__init__ sets device_type only for 'cpu' and
    'cuda'; passing 'mps' leaves device_type unset and crashes TorchAutocast.
    Until SpeechBrain adds MPS support, fall back to CPU on Apple Silicon.
    """
    import torch

    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def whisper_device() -> tuple[str, str]:
    """Device and compute_type for WhisperX / ctranslate2.

    ctranslate2 does not support MPS, so on macOS the transcription backend
    always runs on CPU regardless of Apple Silicon.
    Returns (device, compute_type).
    """
    import torch

    if torch.cuda.is_available():
        return "cuda", "float16"
    return "cpu", "int8"

"""Runtime checks for optional system-level dependencies."""

from __future__ import annotations

import shutil


def check_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def require_ffmpeg() -> None:
    if not check_ffmpeg():
        raise EnvironmentError(
            "ffmpeg non trovato nel PATH. "
            "Installalo per abilitare l'importazione di file video:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )

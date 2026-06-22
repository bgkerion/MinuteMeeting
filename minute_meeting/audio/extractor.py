"""Extract the audio track from a video file using ffmpeg."""

from __future__ import annotations

import shutil
from pathlib import Path

import ffmpeg


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "ffmpeg non trovato nel PATH.\n"
            "Installalo prima di usare l'estrazione audio da video:\n"
            "  macOS:  brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def extract_audio(video_path: Path, output_path: Path, sample_rate: int = 16_000) -> Path:
    """Extract mono 16-kHz WAV from *video_path* and write to *output_path*."""
    _require_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        (
            ffmpeg
            .input(str(video_path))
            .output(
                str(output_path),
                ac=1,
                ar=sample_rate,
                acodec="pcm_s16le",
                vn=None,
            )
            .overwrite_output()
            .run(capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else "(nessun output)"
        raise RuntimeError(
            f"ffmpeg ha fallito durante l'estrazione audio:\n{stderr}"
        ) from None
    return output_path

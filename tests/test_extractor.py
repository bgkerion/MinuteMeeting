"""Tests for audio/extractor.py — no real video files required."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from minute_meeting.audio.extractor import _require_ffmpeg, extract_audio


def test_require_ffmpeg_raises_when_missing() -> None:
    with patch.object(shutil, "which", return_value=None):
        with pytest.raises(EnvironmentError, match="ffmpeg"):
            _require_ffmpeg()


def test_require_ffmpeg_passes_when_present() -> None:
    with patch.object(shutil, "which", return_value="/usr/bin/ffmpeg"):
        _require_ffmpeg()  # must not raise


def test_extract_audio_raises_runtime_error_on_ffmpeg_failure(tmp_path: Path) -> None:
    import ffmpeg as _ffmpeg

    fake_error = _ffmpeg.Error("ffmpeg", stdout=b"", stderr=b"test error")

    with patch.object(shutil, "which", return_value="/usr/bin/ffmpeg"):
        with patch("ffmpeg.input") as mock_input:
            mock_stream = MagicMock()
            mock_stream.output.return_value = mock_stream
            mock_stream.overwrite_output.return_value = mock_stream
            mock_stream.run.side_effect = fake_error
            mock_input.return_value = mock_stream

            with pytest.raises(RuntimeError, match="ffmpeg ha fallito"):
                extract_audio(Path("fake.mp4"), tmp_path / "out.wav")


def test_extract_audio_stderr_none_does_not_crash(tmp_path: Path) -> None:
    import ffmpeg as _ffmpeg

    fake_error = _ffmpeg.Error("ffmpeg", stdout=b"", stderr=None)

    with patch.object(shutil, "which", return_value="/usr/bin/ffmpeg"):
        with patch("ffmpeg.input") as mock_input:
            mock_stream = MagicMock()
            mock_stream.output.return_value = mock_stream
            mock_stream.overwrite_output.return_value = mock_stream
            mock_stream.run.side_effect = fake_error
            mock_input.return_value = mock_stream

            with pytest.raises(RuntimeError, match="nessun output"):
                extract_audio(Path("fake.mp4"), tmp_path / "out.wav")

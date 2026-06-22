"""Tests for audio/preprocessor.py — no audio hardware required."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from minute_meeting.audio.preprocessor import SAMPLE_RATE, preprocess


@pytest.fixture
def sine_wav(tmp_path: Path) -> Path:
    """440 Hz sine wave, 1 second, float32 WAV."""
    t = np.linspace(0, 1, SAMPLE_RATE, endpoint=False, dtype=np.float32)
    audio = np.sin(2 * np.pi * 440 * t)
    path = tmp_path / "sine.wav"
    sf.write(str(path), audio, SAMPLE_RATE)
    return path


# ---------------------------------------------------------------------------
# Return type and shape
# ---------------------------------------------------------------------------

def test_preprocess_returns_float32(sine_wav: Path) -> None:
    audio, sr = preprocess(sine_wav)
    assert audio.dtype == np.float32


def test_preprocess_returns_correct_sample_rate(sine_wav: Path) -> None:
    _, sr = preprocess(sine_wav)
    assert sr == SAMPLE_RATE


def test_preprocess_length_preserved(sine_wav: Path) -> None:
    audio, _ = preprocess(sine_wav)
    assert len(audio) == SAMPLE_RATE  # 1 second × 16 000 samples/s


def test_preprocess_output_is_1d(sine_wav: Path) -> None:
    audio, _ = preprocess(sine_wav)
    assert audio.ndim == 1


# ---------------------------------------------------------------------------
# Peak normalisation
# ---------------------------------------------------------------------------

def test_preprocess_peak_normalised_to_0891(sine_wav: Path) -> None:
    audio, _ = preprocess(sine_wav)
    # Normalization: output = reduced / peak(reduced) * 0.891
    assert abs(np.max(np.abs(audio)) - 0.891) < 1e-4


# ---------------------------------------------------------------------------
# Optional output_path
# ---------------------------------------------------------------------------

def test_preprocess_writes_output_file(sine_wav: Path, tmp_path: Path) -> None:
    out = tmp_path / "cleaned.wav"
    preprocess(sine_wav, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_preprocess_output_file_is_valid_wav(sine_wav: Path, tmp_path: Path) -> None:
    out = tmp_path / "cleaned.wav"
    preprocess(sine_wav, output_path=out)
    saved, sr = sf.read(str(out))
    assert sr == SAMPLE_RATE
    assert len(saved) == SAMPLE_RATE


def test_preprocess_no_output_path_does_not_write(sine_wav: Path, tmp_path: Path) -> None:
    default_out = tmp_path / "cleaned.wav"
    preprocess(sine_wav)  # no output_path
    assert not default_out.exists()

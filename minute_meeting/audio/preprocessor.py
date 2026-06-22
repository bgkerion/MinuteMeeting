"""Audio preprocessing: noise reduction and normalisation."""

from __future__ import annotations

from pathlib import Path

import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf


SAMPLE_RATE = 16_000


def preprocess(
    input_path: Path,
    output_path: Path | None = None,
    denoise: bool = False,
) -> tuple[np.ndarray, int]:
    """Load audio, optionally apply noise reduction, return (samples, sample_rate).

    If *output_path* is given the cleaned audio is also saved there.
    """
    audio, sr = librosa.load(str(input_path), sr=SAMPLE_RATE, mono=True)
    reduced = nr.reduce_noise(y=audio, sr=sr) if denoise else audio
    # Peak normalise to -1 dBFS
    peak = np.max(np.abs(reduced))
    if peak > 0:
        reduced = reduced / peak * 0.891  # 10^(-1/20)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), reduced, sr)

    return reduced, sr

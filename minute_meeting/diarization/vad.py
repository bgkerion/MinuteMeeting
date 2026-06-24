"""Voice Activity Detection using SpeechBrain."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from speechbrain.inference.VAD import VAD

from minute_meeting.utils.device import speechbrain_device
from minute_meeting.utils.paths import CACHE_DIR


@dataclass
class SpeechSegment:
    start: float  # seconds
    end: float    # seconds


class VoiceActivityDetector:
    """Wraps SpeechBrain VAD to return speech segments."""

    _MODEL_SOURCE = "speechbrain/vad-crdnn-libriparty"
    _SAVEDIR = str(CACHE_DIR / "vad-crdnn-libriparty")

    def __init__(self, device: str | None = None) -> None:
        self._device = device or speechbrain_device()
        self._vad: VAD | None = None

    def _load(self) -> VAD:
        if self._vad is None:
            self._vad = VAD.from_hparams(
                source=self._MODEL_SOURCE,
                savedir=self._SAVEDIR,
                run_opts={"device": self._device},
            )
        return self._vad

    def detect(self, audio: np.ndarray, sample_rate: int = 16_000) -> list[SpeechSegment]:
        vad = self._load()
        wav = torch.from_numpy(audio.astype(np.float32)).unsqueeze(0).to(self._device)
        # SpeechBrain VAD expects a file path or a tensor; use tensor API
        prob_chunks = vad.get_speech_prob_chunk(wav)
        prob_th = vad.apply_threshold(prob_chunks).float()
        boundaries = vad.get_boundaries(prob_th, output_value="seconds")

        segments: list[SpeechSegment] = []
        for start, end in boundaries.tolist():
            segments.append(SpeechSegment(start=float(start), end=float(end)))
        return segments

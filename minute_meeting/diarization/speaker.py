"""Speaker embedding extraction using SpeechBrain ECAPA-TDNN."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from speechbrain.inference.speaker import EncoderClassifier

from minute_meeting.diarization.vad import SpeechSegment
from minute_meeting.utils.device import speechbrain_device

_CACHE_DIR = Path.home() / ".cache" / "minute_meeting"


@dataclass
class SpeakerSegment:
    start: float
    end: float
    embedding: np.ndarray
    speaker_id: str = ""


class SpeakerEmbedder:
    """Extracts per-segment speaker embeddings with ECAPA-TDNN."""

    _MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
    _SAVEDIR = str(_CACHE_DIR / "spkrec-ecapa-voxceleb")

    def __init__(self, device: str | None = None) -> None:
        self._device = device or speechbrain_device()
        self._encoder: EncoderClassifier | None = None

    def _load(self) -> None:
        if self._encoder is None:
            self._encoder = EncoderClassifier.from_hparams(
                source=self._MODEL_SOURCE,
                savedir=self._SAVEDIR,
                run_opts={"device": self._device},
            )

    def embed_segments(
        self,
        audio: np.ndarray,
        segments: list[SpeechSegment],
        sample_rate: int = 16_000,
    ) -> list[SpeakerSegment]:
        self._load()
        assert self._encoder is not None

        results: list[SpeakerSegment] = []
        for seg in segments:
            start_idx = int(seg.start * sample_rate)
            end_idx = int(seg.end * sample_rate)
            chunk = audio[start_idx:end_idx]
            if len(chunk) < sample_rate * 0.25:  # skip segments shorter than 250 ms
                continue
            wav = torch.from_numpy(chunk.astype(np.float32)).unsqueeze(0).to(self._device)
            with torch.no_grad():
                emb = self._encoder.encode_batch(wav)
            embedding = emb.squeeze().cpu().numpy()
            results.append(SpeakerSegment(start=seg.start, end=seg.end, embedding=embedding))

        return results

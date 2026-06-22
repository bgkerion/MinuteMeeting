"""WhisperX-based transcription with word-level timestamps."""

from __future__ import annotations

from dataclasses import dataclass, field, replace as dc_replace
from pathlib import Path
from typing import Any

import numpy as np
import whisperx

from minute_meeting.utils.device import whisper_device


@dataclass
class Word:
    text: str
    start: float
    end: float
    speaker: str = ""


@dataclass
class TranscriptionResult:
    language: str
    words: list[Word] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)


class Transcriber:
    """Transcribes audio with WhisperX and aligns to word-level timestamps.

    WhisperX uses ctranslate2 which does not support MPS; on macOS the
    backend is always CPU regardless of Apple Silicon availability.
    """

    def __init__(
        self,
        model_size: str = "small",
        language: str | None = None,
        initial_prompt: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ) -> None:
        self._model_size = model_size
        self._language = language
        self._initial_prompt = initial_prompt or None
        _dev, _ct = whisper_device()
        self._device = device or _dev
        self._compute_type = compute_type or _ct
        self._model: Any = None
        self._align_model: Any = None
        self._align_meta: Any = None
        self._align_language: str | None = None

    def _ensure_model(self) -> None:
        if self._model is None:
            self._model = whisperx.load_model(
                self._model_size,
                self._device,
                compute_type=self._compute_type,
            )

    def _ensure_align(self, language: str) -> None:
        if self._align_model is None or self._align_language != language:
            self._align_model, self._align_meta = whisperx.load_align_model(
                language_code=language,
                device=self._device,
            )
            self._align_language = language

    def transcribe(self, audio: np.ndarray | Path, sample_rate: int = 16_000) -> TranscriptionResult:
        if isinstance(audio, Path):
            import librosa
            audio_arr, sample_rate = librosa.load(str(audio), sr=sample_rate, mono=True)
        else:
            audio_arr = audio.astype(np.float32)

        self._ensure_model()
        if self._initial_prompt:
            # initial_prompt lives inside model.options (a faster-whisper TranscriptionOptions
            # dataclass); FasterWhisperPipeline.transcribe() has no such kwarg directly.
            _orig_opts = self._model.options
            self._model.options = dc_replace(_orig_opts, initial_prompt=self._initial_prompt)
            try:
                raw = self._model.transcribe(audio_arr, batch_size=8)
            finally:
                self._model.options = _orig_opts
        else:
            raw = self._model.transcribe(audio_arr, batch_size=8)
        language = self._language or raw.get("language", "it")

        self._ensure_align(language)

        aligned = whisperx.align(
            raw["segments"],
            self._align_model,
            self._align_meta,
            audio_arr,
            self._device,
            return_char_alignments=False,
        )

        words: list[Word] = []
        for seg in aligned.get("word_segments", []):
            # WhisperX sets start/end to None when forced alignment fails for a word;
            # dict.get(key, default) returns None if the key exists with value None.
            s = seg.get("start")
            e = seg.get("end")
            words.append(Word(
                text=seg.get("word", ""),
                start=float(s) if s is not None else 0.0,
                end=float(e) if e is not None else 0.0,
            ))

        return TranscriptionResult(
            language=language,
            words=words,
            segments=aligned.get("segments", []),
        )

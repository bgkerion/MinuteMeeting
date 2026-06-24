"""Background QThread worker that orchestrates the full processing pipeline."""

from __future__ import annotations

import math
import os
import tempfile
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from minute_meeting.audio.extractor import extract_audio
from minute_meeting.audio.preprocessor import preprocess
from minute_meeting.diarization.clustering import assign_speakers
from minute_meeting.diarization.speaker import SpeakerEmbedder
from minute_meeting.diarization.vad import VoiceActivityDetector
from minute_meeting.transcription.transcriber import Transcriber, TranscriptionResult

# Real-time factor: processing_seconds per audio_second, calibrated on 4 CPU cores.
_MODEL_RTF: dict[str, float] = {
    "tiny":     0.20,
    "base":     0.40,
    "small":    0.85,
    "medium":   1.80,
    "large":    3.20,
    "large-v2": 3.20,
    "large-v3": 3.50,
}


def _estimate_total(audio_secs: float, model_size: str, cpu_cores: int) -> float:
    rtf = _MODEL_RTF.get(model_size, _MODEL_RTF.get(model_size.split("-")[0], 1.0))
    # Sublinear speedup with more cores (empirical sqrt approximation).
    core_factor = math.sqrt(4 / max(cpu_cores, 1))
    return audio_secs * rtf * core_factor + audio_secs * 0.15


def _fmt_time(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s}s" if s < 60 else f"{s // 60}min {s % 60:02d}s"


_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}


class ProcessingWorker(QObject):
    finished: Signal = Signal(object)
    error: Signal = Signal(str)
    # (percent 0-100, stage description)
    progress: Signal = Signal(int, str)

    def __init__(
        self,
        source_path: Path,
        model_size: str = "small",
        language: str | None = None,
        initial_prompt: str | None = None,
        denoise: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._source = source_path
        self._model_size = model_size
        self._language = language
        self._initial_prompt = initial_prompt
        self._denoise = denoise

    def run(self) -> None:
        try:
            self.progress.emit(0, "Preparazione audio…")
            audio_path = self._prepare_audio()
            is_temp = audio_path != self._source
            try:
                self.progress.emit(8, "Normalizzazione audio…")
                audio, sr = preprocess(audio_path, denoise=self._denoise)
            finally:
                if is_temp:
                    audio_path.unlink(missing_ok=True)

            audio_secs = len(audio) / sr
            cpu_cores = os.cpu_count() or 4
            estimated = _estimate_total(audio_secs, self._model_size, cpu_cores)
            t0 = time.monotonic()
            audio_label = _fmt_time(audio_secs)

            def _prog(pct: int, msg: str) -> None:
                remaining = estimated - (time.monotonic() - t0)
                eta = f"~{_fmt_time(remaining)} rimanenti" if remaining > 2 else "quasi finito"
                self.progress.emit(pct, f"{msg}  [audio: {audio_label}, {eta}]")

            _prog(18, "Rilevamento voce…")
            vad = VoiceActivityDetector()
            speech_segs = vad.detect(audio, sr)

            _prog(33, "Analisi caratteristiche speaker…")
            embedder = SpeakerEmbedder()
            speaker_segs = embedder.embed_segments(audio, speech_segs, sr)

            _prog(48, "Identificazione speaker…")
            assign_speakers(speaker_segs)

            transcriber = Transcriber(
                model_size=self._model_size,
                language=self._language,
                initial_prompt=self._initial_prompt,
            )

            # Map transcriber sub-progress (0-100) → worker range 50-93
            def _transcription_progress(pct: int, msg: str) -> None:
                remaining = estimated - (time.monotonic() - t0)
                eta = f"~{_fmt_time(remaining)} rimanenti" if remaining > 2 else "quasi finito"
                self.progress.emit(50 + pct * 43 // 100, f"{msg}  [{eta}]")

            result = transcriber.transcribe(audio, sr, on_progress=_transcription_progress)

            _prog(95, "Assegnazione speaker…")
            self._merge_speakers(result, speaker_segs)
            elapsed = _fmt_time(time.monotonic() - t0)
            self.progress.emit(100, f"Completato  (in {elapsed})")
            self.finished.emit(result)

        except Exception:  # noqa: BLE001
            self.error.emit(traceback.format_exc())

    # ------------------------------------------------------------------

    def _prepare_audio(self) -> Path:
        if self._source.suffix.lower() in _VIDEO_EXTENSIONS:
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            out = Path(tmp.name)
            tmp.close()
            try:
                return extract_audio(self._source, out)
            except Exception:  # noqa: BLE001
                out.unlink(missing_ok=True)
                raise
        return self._source

    @staticmethod
    def _merge_speakers(result: TranscriptionResult, speaker_segs: list) -> None:
        """Tag each word in *result* with the speaker active at that time."""
        for word in result.words:
            mid = (word.start + word.end) / 2
            for seg in speaker_segs:
                if seg.start <= mid <= seg.end:
                    word.speaker = seg.speaker_id
                    break

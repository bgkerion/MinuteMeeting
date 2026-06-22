"""Background QThread worker that orchestrates the full processing pipeline."""

from __future__ import annotations

import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from minute_meeting.audio.extractor import extract_audio
from minute_meeting.audio.preprocessor import preprocess
from minute_meeting.diarization.clustering import assign_speakers
from minute_meeting.diarization.speaker import SpeakerEmbedder
from minute_meeting.diarization.vad import VoiceActivityDetector
from minute_meeting.transcription.transcriber import Transcriber, TranscriptionResult


_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}


class ProcessingWorker(QObject):
    finished: Signal = Signal(object)
    error: Signal = Signal(str)

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
            audio_path = self._prepare_audio()
            is_temp = audio_path != self._source
            try:
                audio, sr = preprocess(audio_path, denoise=self._denoise)
            finally:
                if is_temp:
                    audio_path.unlink(missing_ok=True)

            vad = VoiceActivityDetector()
            speech_segs = vad.detect(audio, sr)

            embedder = SpeakerEmbedder()
            speaker_segs = embedder.embed_segments(audio, speech_segs, sr)
            assign_speakers(speaker_segs)

            transcriber = Transcriber(
                model_size=self._model_size,
                language=self._language,
                initial_prompt=self._initial_prompt,
            )
            result = transcriber.transcribe(audio, sr)

            self._merge_speakers(result, speaker_segs)
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

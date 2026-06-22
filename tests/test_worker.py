"""Tests for ProcessingWorker helper logic — no audio hardware or ML models."""

from __future__ import annotations

import numpy as np

from minute_meeting.diarization.speaker import SpeakerSegment
from minute_meeting.transcription.transcriber import TranscriptionResult, Word
from minute_meeting.ui.worker import ProcessingWorker


def _word(start: float, end: float, text: str = "w") -> Word:
    return Word(text=text, start=start, end=end)


def _seg(start: float, end: float, speaker_id: str) -> SpeakerSegment:
    seg = SpeakerSegment(start=start, end=end, embedding=np.zeros(3, dtype=np.float32))
    seg.speaker_id = speaker_id
    return seg


# ---------------------------------------------------------------------------
# _merge_speakers
# ---------------------------------------------------------------------------

def test_merge_assigns_speaker_to_word() -> None:
    result = TranscriptionResult(language="it", words=[_word(0.5, 1.5)])
    ProcessingWorker._merge_speakers(result, [_seg(0.0, 2.0, "Speaker_01")])
    assert result.words[0].speaker == "Speaker_01"


def test_merge_no_matching_segment_keeps_empty() -> None:
    result = TranscriptionResult(language="it", words=[_word(5.0, 6.0)])
    ProcessingWorker._merge_speakers(result, [_seg(0.0, 2.0, "Speaker_01")])
    assert result.words[0].speaker == ""


def test_merge_empty_segments_leaves_all_empty() -> None:
    result = TranscriptionResult(language="it", words=[_word(0.5, 1.5)])
    ProcessingWorker._merge_speakers(result, [])
    assert result.words[0].speaker == ""


def test_merge_empty_words_does_not_crash() -> None:
    result = TranscriptionResult(language="it", words=[])
    ProcessingWorker._merge_speakers(result, [_seg(0.0, 2.0, "Speaker_01")])
    assert result.words == []


def test_merge_multiple_speakers() -> None:
    result = TranscriptionResult(language="it", words=[
        _word(0.5, 1.5),
        _word(3.0, 4.0),
    ])
    segs = [
        _seg(0.0, 2.0, "Speaker_01"),
        _seg(2.5, 5.0, "Speaker_02"),
    ]
    ProcessingWorker._merge_speakers(result, segs)
    assert result.words[0].speaker == "Speaker_01"
    assert result.words[1].speaker == "Speaker_02"


def test_merge_word_at_segment_boundary() -> None:
    # mid-point of word (0.0, 2.0) is 1.0; segment ends at 1.0 → inclusive match
    result = TranscriptionResult(language="it", words=[_word(0.0, 2.0)])
    ProcessingWorker._merge_speakers(result, [_seg(0.0, 1.0, "Speaker_01")])
    assert result.words[0].speaker == "Speaker_01"


def test_merge_first_matching_segment_wins() -> None:
    # Two overlapping segments — first match should be used
    result = TranscriptionResult(language="it", words=[_word(0.5, 1.5)])
    segs = [
        _seg(0.0, 2.0, "Speaker_01"),
        _seg(0.0, 2.0, "Speaker_02"),
    ]
    ProcessingWorker._merge_speakers(result, segs)
    assert result.words[0].speaker == "Speaker_01"

"""Smoke tests that do not require ML models or audio hardware."""

import re

import numpy as np

from minute_meeting.diarization.clustering import assign_speakers
from minute_meeting.diarization.speaker import SpeakerSegment


def _make_seg(start: float, end: float, emb: list[float]) -> SpeakerSegment:
    return SpeakerSegment(start=start, end=end, embedding=np.array(emb, dtype=np.float32))


# ---------------------------------------------------------------------------
# assign_speakers — clustering
# ---------------------------------------------------------------------------

def test_assign_speakers_two_clusters() -> None:
    segs = [
        _make_seg(0.0, 2.0, [1.0, 0.0, 0.0]),
        _make_seg(2.0, 4.0, [1.0, 0.1, 0.0]),
        _make_seg(4.0, 6.0, [0.0, 0.0, 1.0]),
        _make_seg(6.0, 8.0, [0.0, 0.1, 1.0]),
    ]
    result = assign_speakers(segs, n_speakers=2)
    labels = {s.speaker_id for s in result}
    assert len(labels) == 2
    assert result[0].speaker_id == result[1].speaker_id
    assert result[2].speaker_id == result[3].speaker_id
    assert result[0].speaker_id != result[2].speaker_id


def test_assign_speakers_empty() -> None:
    assert assign_speakers([]) == []


def test_assign_speakers_single() -> None:
    segs = [_make_seg(0.0, 1.0, [1.0, 0.0])]
    result = assign_speakers(segs, n_speakers=1)
    assert result[0].speaker_id == "Speaker_01"


def test_assign_speakers_n_exceeds_segments() -> None:
    segs = [
        _make_seg(0.0, 2.0, [1.0, 0.0]),
        _make_seg(2.0, 4.0, [0.0, 1.0]),
    ]
    result = assign_speakers(segs, n_speakers=5)
    assert len({s.speaker_id for s in result}) <= 2


def test_assign_speakers_speaker_id_format() -> None:
    segs = [
        _make_seg(0.0, 2.0, [1.0, 0.0]),
        _make_seg(2.0, 4.0, [0.0, 1.0]),
    ]
    assign_speakers(segs, n_speakers=2)
    for s in segs:
        assert re.match(r"^Speaker_\d{2}$", s.speaker_id), s.speaker_id


def test_assign_speakers_modifies_in_place() -> None:
    segs = [
        _make_seg(0.0, 2.0, [1.0, 0.0]),
        _make_seg(2.0, 4.0, [0.0, 1.0]),
    ]
    result = assign_speakers(segs, n_speakers=2)
    assert result is segs
    assert all(s.speaker_id != "" for s in segs)


def test_assign_speakers_auto_detection() -> None:
    # Cosine distance between groups ≈ 1.0 → well above default threshold 0.65
    segs = [
        _make_seg(0.0, 2.0, [1.0, 0.0, 0.0]),
        _make_seg(2.0, 4.0, [1.0, 0.05, 0.0]),
        _make_seg(4.0, 6.0, [0.0, 0.0, 1.0]),
        _make_seg(6.0, 8.0, [0.0, 0.05, 1.0]),
    ]
    result = assign_speakers(segs)  # n_speakers=None → auto
    assert result[0].speaker_id == result[1].speaker_id
    assert result[2].speaker_id == result[3].speaker_id
    assert result[0].speaker_id != result[2].speaker_id

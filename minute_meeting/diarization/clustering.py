"""Cluster speaker embeddings to assign speaker labels."""

from __future__ import annotations

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.preprocessing import normalize

from minute_meeting.diarization.speaker import SpeakerSegment


def assign_speakers(
    segments: list[SpeakerSegment],
    n_speakers: int | None = None,
    max_speakers: int = 10,
    distance_threshold: float = 0.65,
) -> list[SpeakerSegment]:
    """Cluster *segments* by embedding similarity and set speaker_id in-place.

    If *n_speakers* is None, the number of clusters is estimated automatically
    using *distance_threshold*.
    """
    if not segments:
        return segments

    if len(segments) == 1:
        segments[0].speaker_id = "Speaker_01"
        return segments

    embeddings = np.stack([s.embedding for s in segments])
    embeddings = normalize(embeddings, norm="l2")

    if n_speakers is not None:
        n_speakers = min(n_speakers, len(segments))
        clustering = AgglomerativeClustering(
            n_clusters=n_speakers,
            metric="cosine",
            linkage="average",
        )
    else:
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="cosine",
            linkage="average",
        )

    labels = clustering.fit_predict(embeddings)
    n_found = int(labels.max()) + 1
    # Cap at max_speakers
    if n_found > max_speakers:
        clustering = AgglomerativeClustering(
            n_clusters=max_speakers,
            metric="cosine",
            linkage="average",
        )
        labels = clustering.fit_predict(embeddings)

    for seg, label in zip(segments, labels):
        seg.speaker_id = f"Speaker_{label + 1:02d}"

    return segments

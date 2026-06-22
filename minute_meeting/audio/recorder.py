"""Real-time audio recording via sounddevice.

Single-stream (mic only) on macOS.
Dual-stream (mic + system-audio loopback) on Windows and Linux when
a loopback device is found and use_loopback=True.
"""

from __future__ import annotations

import platform
import queue
import sys
import threading
import traceback
from pathlib import Path
from typing import Callable

import librosa
import numpy as np
import sounddevice as sd
import soundfile as sf

from minute_meeting.audio.loopback import LoopbackDevice, find_loopback_device


class AudioRecorder:
    """Records microphone (and optionally system audio) to a WAV file."""

    SAMPLE_RATE = 16_000
    CHANNELS = 1
    DTYPE = "int16"

    def __init__(
        self,
        output_path: Path,
        on_level: Callable[[float], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        use_loopback: bool = True,
    ) -> None:
        self._output_path = output_path
        self._on_level = on_level
        self._on_error = on_error
        self._q_mic: queue.Queue[np.ndarray] = queue.Queue()
        self._q_lb: queue.Queue[np.ndarray] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._loopback: LoopbackDevice | None = (
            find_loopback_device() if use_loopback else None
        )

    @property
    def has_loopback(self) -> bool:
        return self._loopback is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> Path:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        return self._output_path

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _report_error(self, message: str) -> None:
        print(f"[AudioRecorder] {message}", file=sys.stderr, flush=True)
        if self._on_error is not None:
            self._on_error(message)

    def _mic_callback(self, indata: np.ndarray, frames: int, time, status) -> None:  # noqa: ANN001
        if status:
            print(f"[AudioRecorder] mic status: {status}", file=sys.stderr, flush=True)
        chunk = indata.copy()
        self._q_mic.put(chunk)
        if self._on_level is not None:
            rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))
            self._on_level(rms)

    def _lb_callback(self, indata: np.ndarray, frames: int, time, status) -> None:  # noqa: ANN001
        if status:
            print(f"[AudioRecorder] loopback status: {status}", file=sys.stderr, flush=True)
        self._q_lb.put(indata.copy())

    @staticmethod
    def _drain(q: queue.Queue) -> list[np.ndarray]:
        chunks: list[np.ndarray] = []
        while True:
            try:
                chunks.append(q.get_nowait())
            except queue.Empty:
                break
        return chunks

    def _open_loopback_stream(self) -> sd.InputStream | None:
        lb = self._loopback
        if lb is None:
            return None
        try:
            kwargs: dict = dict(
                device=lb.device_index,
                samplerate=lb.sample_rate,
                channels=lb.channels,
                dtype="float32",
                callback=self._lb_callback,
            )
            if platform.system() == "Windows" and hasattr(sd, "WasapiSettings"):
                kwargs["extra_settings"] = sd.WasapiSettings(loopback=True)
            stream = sd.InputStream(**kwargs)
            stream.start()
            return stream
        except Exception as exc:
            print(f"[AudioRecorder] loopback unavailable: {exc}", file=sys.stderr)
            self._loopback = None   # signal has_loopback → False
            return None

    def _record_loop(self) -> None:
        mic_frames: list[np.ndarray] = []
        lb_frames: list[np.ndarray] = []

        try:
            mic_stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype=self.DTYPE,
                callback=self._mic_callback,
            )
            mic_stream.start()
        except Exception:
            self._report_error(traceback.format_exc())
            return

        lb_stream = self._open_loopback_stream()

        try:
            while not self._stop_event.is_set():
                try:
                    chunk = self._q_mic.get(timeout=0.1)
                    mic_frames.append(chunk)
                except queue.Empty:
                    continue
                lb_frames.extend(self._drain(self._q_lb))
        except Exception:
            self._report_error(traceback.format_exc())
            return
        finally:
            mic_stream.stop()
            mic_stream.close()
            if lb_stream is not None:
                try:
                    lb_stream.stop()
                    lb_stream.close()
                except Exception:
                    pass

        mic_frames.extend(self._drain(self._q_mic))
        lb_frames.extend(self._drain(self._q_lb))

        if not mic_frames:
            return

        try:
            audio = self._mix(mic_frames, lb_frames)
            sf.write(str(self._output_path), audio, self.SAMPLE_RATE)
        except Exception:
            self._report_error(traceback.format_exc())

    def _mix(
        self,
        mic_frames: list[np.ndarray],
        lb_frames: list[np.ndarray],
    ) -> np.ndarray:
        # Mic: int16 mono @ SAMPLE_RATE → normalise to float32 [-1, 1]
        mic = np.concatenate(mic_frames).flatten().astype(np.float32) / 32_768.0

        if not lb_frames or self._loopback is None:
            return (mic * 32_768.0).clip(-32_768, 32_767).astype(np.int16)

        lb = np.concatenate(lb_frames)
        if lb.ndim > 1:                    # stereo → mono
            lb = lb.mean(axis=1)

        if self._loopback.sample_rate != self.SAMPLE_RATE:
            lb = librosa.resample(
                lb, orig_sr=self._loopback.sample_rate, target_sr=self.SAMPLE_RATE
            )

        n = min(len(mic), len(lb))
        # Mix only the overlapping portion; preserve full mic length beyond that.
        if n > 0:
            blended = (mic[:n] + lb[:n]) * 0.5
            result = np.concatenate([blended, mic[n:]])
        else:
            result = mic
        return (result * 32_768.0).clip(-32_768, 32_767).astype(np.int16)

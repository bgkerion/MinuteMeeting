"""Widget for live microphone recording."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import sounddevice as sd

from minute_meeting.audio.recorder import AudioRecorder


class RecorderWidget(QWidget):
    recording_saved = Signal(object)   # emits Path
    recording_error = Signal(str)      # emits error message for MainWindow to display
    recording_status = Signal(str)     # emits informational messages for status bar
    _level_updated = Signal(int)       # marshal audio-thread RMS to UI thread
    _error_received = Signal(str)      # marshal audio-thread error to UI thread

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recorder: AudioRecorder | None = None
        self._tmp_path: Path | None = None
        self._capture_system_audio: bool = True
        self._build()

    def set_capture_system_audio(self, enabled: bool) -> None:
        self._capture_system_audio = enabled

    def _build(self) -> None:
        box = QGroupBox("Registrazione microfono")
        inner = QHBoxLayout()

        self._btn_record = QPushButton("Avvia registrazione")
        self._btn_record.setCheckable(True)
        self._btn_record.toggled.connect(self._on_toggle)
        inner.addWidget(self._btn_record)

        self._level = QProgressBar()
        self._level.setRange(0, 10000)
        self._level.setValue(0)
        self._level.setFixedWidth(150)
        self._level.setTextVisible(False)
        inner.addWidget(QLabel("Livello:"))
        inner.addWidget(self._level)
        inner.addStretch()

        # Queued connections: signals emitted from audio thread, slots run in UI thread
        self._level_updated.connect(self._level.setValue)
        self._error_received.connect(self._on_recorder_error)

        box.setLayout(inner)
        layout = QVBoxLayout(self)
        layout.addWidget(box)

    @Slot(bool)
    def _on_toggle(self, checked: bool) -> None:
        if checked:
            self._btn_record.setText("Interrompi registrazione")
            try:
                dev = sd.query_devices(kind="input")
                dev_name = dev.get("name", "sconosciuto")
            except Exception:  # noqa: BLE001
                dev_name = "sconosciuto"
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            self._tmp_path = Path(tmp.name)
            tmp.close()
            self._recorder = AudioRecorder(
                self._tmp_path,
                on_level=self._update_level,
                on_error=self._forward_error,
                use_loopback=self._capture_system_audio,
            )
            if self._recorder.has_loopback:
                status = f"Registrazione in corso — microfono: {dev_name} + audio di sistema"
            else:
                status = f"Registrazione in corso — microfono: {dev_name}"
            self.recording_status.emit(status)
            self._recorder.start()
        else:
            self._btn_record.setText("Avvia registrazione")
            self._level.setValue(0)
            if self._recorder:
                saved = self._recorder.stop()
                self._recorder = None
                if saved.exists() and saved.stat().st_size > 0:
                    self.recording_saved.emit(saved)
                else:
                    saved.unlink(missing_ok=True)

    def _update_level(self, rms: float) -> None:
        # called from sounddevice audio thread — emit signal to cross to UI thread
        self._level_updated.emit(min(int(rms * 50_000), 10000))

    def _forward_error(self, message: str) -> None:
        # called from recorder thread — marshal to UI thread via signal
        self._error_received.emit(message)

    def stop_if_recording(self) -> None:
        """Abort an active recording without saving — for use on app close."""
        if self._recorder is not None:
            self._recorder.stop()
            self._recorder = None
        if self._tmp_path is not None:
            self._tmp_path.unlink(missing_ok=True)
            self._tmp_path = None
        self._btn_record.setChecked(False)  # _on_toggle(False) sees recorder=None → no-op

    @Slot(str)
    def _on_recorder_error(self, message: str) -> None:
        # Stop and discard BEFORE resetting the button: setChecked(False) triggers
        # _on_toggle(False) which would otherwise emit recording_saved if the
        # recorder managed to write a partial file before the error.
        if self._recorder:
            self._recorder.stop()
            self._recorder = None
        if self._tmp_path:
            self._tmp_path.unlink(missing_ok=True)
            self._tmp_path = None
        self._btn_record.setChecked(False)  # _on_toggle(False) sees recorder=None → no-op
        self.recording_error.emit(message)

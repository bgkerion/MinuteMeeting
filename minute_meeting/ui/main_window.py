"""Main application window."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, QThread, Slot
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from minute_meeting.transcription.transcriber import TranscriptionResult
from minute_meeting.ui.widgets.recorder_widget import RecorderWidget
from minute_meeting.ui.widgets.settings_dialog import SettingsDialog
from minute_meeting.ui.widgets.transcript_widget import TranscriptWidget
from minute_meeting.ui.worker import ProcessingWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MinuteMeeting")
        self.resize(1100, 720)

        self._worker: ProcessingWorker | None = None
        self._worker_thread: QThread | None = None

        self._settings = QSettings("MinuteMeeting", "MinuteMeeting")
        self._model_size: str = self._settings.value("transcription/model_size", "small")
        lang = self._settings.value("transcription/language", "")
        self._language: str | None = lang if lang else None
        self._initial_prompt: str = self._settings.value("transcription/initial_prompt", "")
        self._denoise: bool = self._settings.value("audio/denoise", False, type=bool)
        self._capture_system_audio: bool = self._settings.value(
            "audio/capture_system_audio", True, type=bool
        )

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()

        self._load_style(self._is_dark_mode())
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                lambda _: self._load_style(self._is_dark_mode())
            )
        except AttributeError:
            pass  # colorSchemeChanged requires Qt 6.5+

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = QToolBar("Main", self)
        bar.setMovable(False)
        self.addToolBar(bar)

        open_act = QAction("Apri file…", self)
        open_act.setShortcut("Ctrl+O")
        open_act.triggered.connect(self._on_open_file)
        bar.addAction(open_act)

        bar.addSeparator()

        export_act = QAction("Esporta…", self)
        export_act.setShortcut("Ctrl+E")
        export_act.triggered.connect(self._on_export)
        bar.addAction(export_act)

        bar.addSeparator()

        settings_act = QAction("Impostazioni…", self)
        settings_act.setShortcut("Ctrl+,")
        settings_act.triggered.connect(self._on_settings)
        bar.addAction(settings_act)

    def _build_central(self) -> None:
        splitter = QSplitter(Qt.Orientation.Vertical)

        self._recorder = RecorderWidget(self)
        self._recorder.set_capture_system_audio(self._capture_system_audio)
        self._recorder.recording_saved.connect(self._process_audio)
        self._recorder.recording_error.connect(self._on_recorder_error)
        self._recorder.recording_status.connect(
            lambda msg: self._status.showMessage(msg)
        )
        splitter.addWidget(self._recorder)

        self._transcript = TranscriptWidget(self)
        splitter.addWidget(self._transcript)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    def _build_statusbar(self) -> None:
        self._status = QStatusBar(self)
        self._btn_cancel = QPushButton("Annulla")
        self._btn_cancel.setVisible(False)
        self._btn_cancel.setFixedWidth(80)
        self._status.addPermanentWidget(self._btn_cancel)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._progress.setFixedWidth(200)
        self._status.addPermanentWidget(self._progress)
        self.setStatusBar(self._status)

    @staticmethod
    def _is_dark_mode() -> bool:
        try:
            return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        except AttributeError:
            # Qt < 6.5: infer from window background luminance
            p = QApplication.instance().palette()
            return p.color(QPalette.ColorRole.Window).lightness() < 128

    def _load_style(self, is_dark: bool = False) -> None:
        name = "dark.qss" if is_dark else "main.qss"
        if hasattr(sys, "_MEIPASS"):
            qss_path = Path(sys._MEIPASS) / "minute_meeting" / "ui" / "styles" / name
        else:
            qss_path = Path(__file__).parent / "styles" / name
        if qss_path.exists():
            QApplication.instance().setStyleSheet(qss_path.read_text())

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @Slot()
    def _on_open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Apri file audio o video",
            "",
            "Media (*.wav *.mp3 *.mp4 *.mkv *.avi *.mov *.flac *.ogg);;Tutti i file (*)",
        )
        if path:
            self._process_audio(Path(path))

    @Slot()
    def _on_export(self) -> None:
        text = self._transcript.get_text()
        if not text.strip():
            QMessageBox.information(self, "Esporta", "Nessuna trascrizione da esportare.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva trascrizione", "verbale.txt", "Testo (*.txt);;Tutti (*)"
        )
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self._status.showMessage(f"Salvato in {path}", 4000)

    @Slot(object)
    def _process_audio(self, path: Path) -> None:
        if self._worker_thread and self._worker_thread.isRunning():
            QMessageBox.warning(self, "Elaborazione in corso",
                                "Attendere il completamento dell'elaborazione corrente.")
            return

        self._transcript.clear()
        self._status.showMessage("Elaborazione in corso…")
        self._progress.setVisible(True)

        self._worker_thread = QThread(self)
        self._worker = ProcessingWorker(
            path,
            model_size=self._model_size,
            language=self._language,
            initial_prompt=self._initial_prompt or None,
            denoise=self._denoise,
        )
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_processing_progress)
        self._worker.finished.connect(self._on_processing_done)
        self._worker.error.connect(self._on_processing_error)
        self._worker.cancelled.connect(self._on_processing_cancelled)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker.cancelled.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        self._worker_thread.finished.connect(self._clear_worker)

        self._btn_cancel.setVisible(True)
        self._btn_cancel.clicked.connect(self._worker.cancel)
        self._worker_thread.start()

    @Slot()
    def _clear_worker(self) -> None:
        # called after deleteLater() is scheduled — drop Python refs before C++ object dies
        self._worker_thread = None
        self._worker = None

    @Slot(int, str)
    def _on_processing_progress(self, percent: int, stage: str) -> None:
        self._progress.setValue(percent)
        if stage:
            self._status.showMessage(f"{stage} ({percent}%)")

    def _hide_progress(self) -> None:
        self._progress.setValue(0)
        self._progress.setVisible(False)
        self._btn_cancel.setVisible(False)
        try:
            self._btn_cancel.clicked.disconnect()
        except RuntimeError:
            pass

    @Slot(object)
    def _on_processing_done(self, result: object) -> None:
        self._hide_progress()
        if not isinstance(result, TranscriptionResult):
            return
        if result.words:
            self._status.showMessage(
                f"Elaborazione completata — {len(result.words)} parole trascritte.", 5000
            )
        else:
            self._status.showMessage(
                "Elaborazione completata — nessun parlato rilevato nel file audio.", 8000
            )
        self._transcript.set_result(result)

    @Slot()
    def _on_processing_cancelled(self) -> None:
        self._hide_progress()
        self._status.showMessage("Elaborazione annullata.", 4000)

    @Slot(str)
    def _on_processing_error(self, message: str) -> None:
        self._hide_progress()
        self._status.showMessage("Errore durante l'elaborazione.", 4000)
        QMessageBox.critical(self, "Errore", message)

    @Slot()
    def _on_settings(self) -> None:
        dlg = SettingsDialog(
            model_size=self._model_size,
            language=self._language or "",
            initial_prompt=self._initial_prompt,
            denoise=self._denoise,
            capture_system_audio=self._capture_system_audio,
            parent=self,
        )
        if dlg.exec() == SettingsDialog.DialogCode.Accepted:
            self._model_size = dlg.model_size
            self._language = dlg.language or None
            self._initial_prompt = dlg.initial_prompt
            self._denoise = dlg.denoise
            self._capture_system_audio = dlg.capture_system_audio
            self._settings.setValue("transcription/model_size", self._model_size)
            self._settings.setValue("transcription/language", self._language or "")
            self._settings.setValue("transcription/initial_prompt", self._initial_prompt)
            self._settings.setValue("audio/denoise", self._denoise)
            self._settings.setValue("audio/capture_system_audio", self._capture_system_audio)
            self._recorder.set_capture_system_audio(self._capture_system_audio)
            self._status.showMessage(
                f"Impostazioni salvate — modello: {self._model_size}, "
                f"lingua: {self._language or 'auto-rileva'}, "
                f"riduzione rumore: {'sì' if self._denoise else 'no'}",
                4000,
            )

    @Slot(str)
    def _on_recorder_error(self, message: str) -> None:
        self._status.showMessage("Errore microfono.", 5000)
        QMessageBox.critical(
            self,
            "Errore microfono",
            f"Impossibile aprire il microfono:\n\n{message}\n\n"
            "Verifica che l'app abbia il permesso di accedere al microfono in:\n"
            "Impostazioni di sistema → Privacy e sicurezza → Microfono",
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        # Abort active recording so PortAudio streams are closed cleanly and
        # the temp WAV is removed before the process exits.
        self._recorder.stop_if_recording()
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            if not self._worker_thread.wait(5000):
                # Thread still busy after 5 s — keep window open rather than
                # destroying a running QThread (undefined behaviour / crash).
                event.ignore()
                return
        event.accept()

"""Settings dialog — Whisper model size and transcription language."""

from __future__ import annotations

import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from minute_meeting.audio.loopback import find_loopback_device

_MODELS: list[tuple[str, str]] = [
    ("base — veloce, qualità minima", "base"),
    ("small — buon compromesso (consigliato)", "small"),
    ("medium — qualità alta", "medium"),
    ("large-v3 — qualità massima, lento", "large-v3"),
]

_LANGUAGES: list[tuple[str, str]] = [
    ("Auto-rileva", ""),
    ("Italiano", "it"),
    ("English", "en"),
    ("Français", "fr"),
    ("Deutsch", "de"),
    ("Español", "es"),
    ("Português", "pt"),
    ("Nederlands", "nl"),
    ("Polski", "pl"),
    ("Русский", "ru"),
    ("中文", "zh"),
    ("日本語", "ja"),
    ("한국어", "ko"),
    ("العربية", "ar"),
]

_PROMPT_LIMIT = 900   # ~224 Whisper tokens


def _loopback_status() -> tuple[bool, str]:
    """Return (available, tooltip) based on the current platform and installed drivers."""
    os_name = platform.system()
    if os_name in ("Windows", "Linux"):
        return True, ""
    if os_name == "Darwin":
        lb = find_loopback_device()
        if lb is not None:
            return True, (
                f"BlackHole rilevato ({lb.label}).\n"
                "Per catturare l'audio di sistema imposta l'uscita audio del Mac\n"
                "su un Multi-Output Device che includa BlackHole (Audio MIDI Setup)."
            )
        return False, (
            "BlackHole non trovato.\n"
            "Scaricalo da existential.audio/blackhole, installalo e\n"
            "configura un Multi-Output Device in Audio MIDI Setup."
        )
    return False, "Non disponibile su questo sistema operativo."


class SettingsDialog(QDialog):
    def __init__(
        self,
        model_size: str,
        language: str,
        initial_prompt: str = "",
        denoise: bool = False,
        capture_system_audio: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Impostazioni trascrizione")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._model_combo = QComboBox()
        for label, value in _MODELS:
            self._model_combo.addItem(label, value)
        self._select(self._model_combo, model_size, 1)   # fallback → small

        self._lang_combo = QComboBox()
        for label, value in _LANGUAGES:
            self._lang_combo.addItem(label, value)
        self._select(self._lang_combo, language, 0)       # fallback → auto

        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlaceholderText(
            "Es: Riunione CDA. Partecipanti: Mario Rossi, Laura Bianchi. "
            "Argomenti: budget Q3, roadmap prodotto."
        )
        self._prompt_edit.setPlainText(initial_prompt)
        self._prompt_edit.setFixedHeight(80)
        self._prompt_edit.textChanged.connect(self._update_char_count)

        self._char_label = QLabel()
        self._char_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._update_char_count()

        self._denoise_check = QCheckBox("Attiva riduzione del rumore")
        self._denoise_check.setChecked(denoise)

        loopback_ok, loopback_tip = _loopback_status()
        self._loopback_check = QCheckBox("Registra anche l'audio di sistema (Meet, Teams, Zoom…)")
        self._loopback_check.setChecked(capture_system_audio and loopback_ok)
        self._loopback_check.setEnabled(loopback_ok)
        if loopback_tip:
            self._loopback_check.setToolTip(loopback_tip)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.addRow("Modello Whisper:", self._model_combo)
        form.addRow("Lingua:", self._lang_combo)
        form.addRow("Contesto:", self._prompt_edit)
        form.addRow("", self._char_label)
        form.addRow("Audio:", self._denoise_check)
        form.addRow("", self._loopback_check)

        note = QLabel(
            "I modelli vengono scaricati automaticamente al primo utilizzo "
            "e salvati in ~/.cache/whisperx. Modelli più grandi richiedono "
            "più tempo e memoria RAM."
        )
        note.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addSpacing(8)
        layout.addWidget(note)
        layout.addSpacing(4)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    def _update_char_count(self) -> None:
        n = len(self._prompt_edit.toPlainText())
        self._char_label.setText(f"{n} / {_PROMPT_LIMIT} caratteri")
        over = n > _PROMPT_LIMIT
        self._char_label.setStyleSheet("color: red;" if over else "")

    @staticmethod
    def _select(combo: QComboBox, value: str, fallback: int) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(fallback)

    @property
    def model_size(self) -> str:
        return self._model_combo.currentData()

    @property
    def language(self) -> str:
        """Empty string means auto-detect."""
        return self._lang_combo.currentData()

    @property
    def initial_prompt(self) -> str:
        return self._prompt_edit.toPlainText().strip()

    @property
    def denoise(self) -> bool:
        return self._denoise_check.isChecked()

    @property
    def capture_system_audio(self) -> bool:
        return self._loopback_check.isChecked()

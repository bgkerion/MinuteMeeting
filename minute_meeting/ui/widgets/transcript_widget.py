"""Widget that displays the diarized transcript."""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QGroupBox, QTextEdit, QVBoxLayout, QWidget

from minute_meeting.transcription.transcriber import TranscriptionResult

_SPEAKER_COLORS = [
    "#1a6fa8", "#a83232", "#2e8b57", "#b5651d",
    "#6a0dad", "#2f4f4f", "#8b4513", "#006400",
]


class TranscriptWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()
        self._speaker_color: dict[str, str] = {}

    def _build(self) -> None:
        box = QGroupBox("Trascrizione")
        inner = QVBoxLayout()
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        inner.addWidget(self._text)
        box.setLayout(inner)

        layout = QVBoxLayout(self)
        layout.addWidget(box)

    def clear(self) -> None:
        self._text.clear()
        self._speaker_color.clear()

    def get_text(self) -> str:
        return self._text.toPlainText()

    def set_result(self, result: TranscriptionResult) -> None:
        self._text.clear()
        cursor = self._text.textCursor()

        current_speaker = None
        buffer: list[str] = []
        first_block = True

        def flush() -> None:
            nonlocal current_speaker, first_block
            if not buffer:
                return
            fmt = QTextCharFormat()
            color = self._color_for(current_speaker or "")
            fmt.setForeground(QColor(color))
            prefix = "" if first_block else "\n"
            label = f"{prefix}[{current_speaker or 'Sconosciuto'}]  "
            cursor.insertText(label, fmt)
            plain = QTextCharFormat()
            cursor.insertText(" ".join(buffer) + " ", plain)
            buffer.clear()
            first_block = False

        for word in result.words:
            if word.speaker != current_speaker:
                flush()
                current_speaker = word.speaker
            buffer.append(word.text)

        flush()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self._text.setTextCursor(cursor)

    def _color_for(self, speaker: str) -> str:
        if speaker not in self._speaker_color:
            idx = len(self._speaker_color) % len(_SPEAKER_COLORS)
            self._speaker_color[speaker] = _SPEAKER_COLORS[idx]
        return self._speaker_color[speaker]

"""Entry point — launches the PySide6 application."""

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from minute_meeting.ui.main_window import MainWindow


def _patch_bundle_path() -> None:
    # When frozen by PyInstaller the bundle directory is not in PATH, so
    # subprocesses (ffmpeg) would not find bundled executables.
    if hasattr(sys, "_MEIPASS"):
        bundle_dir = str(Path(sys._MEIPASS))
        os.environ["PATH"] = bundle_dir + os.pathsep + os.environ.get("PATH", "")


def main() -> None:
    _patch_bundle_path()
    app = QApplication(sys.argv)
    app.setApplicationName("MinuteMeeting")
    app.setApplicationVersion("1.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

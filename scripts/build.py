"""
Costruisce il bundle distribuibile con PyInstaller.

Uso:
    poetry run python scripts/build.py [--onefile] [--debug]

Opzioni:
    --onefile   produce un singolo eseguibile (avvio lento per bundle grandi)
    --debug     abilita la console e i log di PyInstaller

Output:
    dist/MinuteMeeting/   (onedir, default)
    dist/MinuteMeeting    (onefile, se --onefile)
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SPEC = ROOT / "minute_meeting.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def _require(tool: str, install_hint: str) -> None:
    if not shutil.which(tool):
        sys.exit(f"[ERRORE] '{tool}' non trovato nel PATH.\n{install_hint}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MinuteMeeting con PyInstaller")
    parser.add_argument("--onefile", action="store_true",
                        help="Produce un singolo eseguibile invece di una cartella")
    parser.add_argument("--debug", action="store_true",
                        help="Abilita console e log verbosi")
    args = parser.parse_args()

    # Verifica dipendenze di sistema ancora utili in fase di build
    _require("git", "  Installa Git: https://git-scm.com/downloads")

    if platform.system() == "Windows":
        # Su Windows ffmpeg.exe può essere bundlato: accettiamo sia PATH che root del progetto
        ffmpeg_local = ROOT / "ffmpeg.exe"
        if not shutil.which("ffmpeg") and not ffmpeg_local.exists():
            sys.exit(
                "[ERRORE] ffmpeg non trovato.\n"
                "  Opzione 1 (consigliata per il bundle): scarica ffmpeg.exe da\n"
                "    https://github.com/BtbN/ffmpeg-builds/releases/latest\n"
                "    e copialo nella root del progetto accanto a questo script.\n"
                "    Verrà incluso automaticamente nel bundle.\n"
                "  Opzione 2: installa ffmpeg nel PATH:\n"
                "    winget install Gyan.FFmpeg"
            )
        if ffmpeg_local.exists():
            print(f"[build] ffmpeg.exe trovato in {ffmpeg_local} — sarà incluso nel bundle.")
    else:
        _require("ffmpeg",
                 "  macOS: brew install ffmpeg\n"
                 "  Linux: sudo apt install ffmpeg")

    print(f"[build] Sistema: {platform.system()} {platform.machine()}")
    print(f"[build] Python:  {sys.version.split()[0]}")
    print(f"[build] Spec:    {SPEC}")
    print()

    cmd: list[str] = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"]

    if args.onefile:
        # Lo spec usa exclude_binaries=True + COLLECT (pattern onedir).
        # Passare --onefile produce un bundle corrotto perché i binari risultano
        # esclusi dall'EXE e il COLLECT viene ignorato.
        print("[build] ERRORE: --onefile non è compatibile con questo spec.")
        print("[build] Per onefile modifica minute_meeting.spec:")
        print("[build]   - imposta exclude_binaries=False in EXE(...)")
        print("[build]   - rimuovi il blocco COLLECT(...)")
        sys.exit(1)

    print("[build] Modalità: onedir   (avvio rapido, cartella dist/MinuteMeeting/)")

    if args.debug:
        cmd += ["--debug", "all", "--console"]
        print("[build] Debug:   attivo")

    print()
    subprocess.run(cmd, cwd=ROOT, check=True)

    exe_suffix = ".exe" if platform.system() == "Windows" else ""
    artifact = DIST / "MinuteMeeting" / f"MinuteMeeting{exe_suffix}"

    print()
    print(f"[build] Completato. Eseguibile: {artifact}")


if __name__ == "__main__":
    main()

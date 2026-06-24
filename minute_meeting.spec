# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec per MinuteMeeting — cross-platform (macOS / Windows).
# Uso:  poetry run python scripts/build.py
#   oppure direttamente:
#         poetry run pyinstaller minute_meeting.spec --noconfirm
#
# Output: dist/MinuteMeeting/   (modalità onedir — avvio rapido)
#
# NOTA DIMENSIONI: il bundle include torch CPU (~600 MB), speechbrain,
# faster-whisper e ctranslate2. La cartella dist risultante pesa ~1,5-2 GB.
# I modelli Whisper/SpeechBrain vengono scaricati al primo avvio (~1-3 GB
# aggiuntivi in ~/.cache), NON sono inclusi nel bundle.
#
# WINDOWS: prima di eseguire, scarica ffmpeg.exe nella root del progetto.
# Il file verrà incluso automaticamente nel bundle.
# Vedi .github/workflows/build-windows.yml per il processo automatico.

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

# ---------------------------------------------------------------------------
# Raccolta dati / binari / hidden-imports dai pacchetti ML
# (collect_all gestisce YAML, pesi statici, librerie native)
# ---------------------------------------------------------------------------

datas    = []
binaries = []
hiddenimports = []


def _grab(pkg: str) -> None:
    d, b, h = collect_all(pkg)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)


_grab("torch")
_grab("torchaudio")
_grab("speechbrain")
_grab("faster_whisper")
_grab("ctranslate2")
_grab("transformers")
_grab("tokenizers")
_grab("librosa")
_grab("soundfile")
_grab("audioread")
_grab("noisereduce")
_grab("whisperx")

# sounddevice richiede collect_all per includere il binario PortAudio (.dylib/.so/.dll)
_grab("sounddevice")

# scikit-learn usa estensioni Cython che PyInstaller non rileva
hiddenimports += collect_submodules("sklearn")

# Foglio di stile Qt e file di configurazione esempio
datas += [
    (str(ROOT / "minute_meeting" / "ui" / "styles" / "main.qss"),
     "minute_meeting/ui/styles"),
    (str(ROOT / "minute_meeting" / "ui" / "styles" / "dark.qss"),
     "minute_meeting/ui/styles"),
    (str(ROOT / ".env.example"), "."),
]

# Windows: bundla ffmpeg.exe se presente nella root del progetto
if sys.platform == "win32":
    _ffmpeg = ROOT / "ffmpeg.exe"
    if _ffmpeg.exists():
        binaries += [(str(_ffmpeg), ".")]

# ---------------------------------------------------------------------------
# Analisi
# ---------------------------------------------------------------------------

a = Analysis(
    [str(ROOT / "minute_meeting" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "minute_meeting",
        "minute_meeting.audio.recorder",
        "minute_meeting.audio.loopback",
        "minute_meeting.audio.extractor",
        "minute_meeting.audio.preprocessor",
        "minute_meeting.transcription.transcriber",
        "minute_meeting.diarization.vad",
        "minute_meeting.diarization.speaker",
        "minute_meeting.diarization.clustering",
        "minute_meeting.ui.main_window",
        "minute_meeting.ui.worker",
        "minute_meeting.ui.widgets.recorder_widget",
        "minute_meeting.ui.widgets.settings_dialog",
        "minute_meeting.ui.widgets.transcript_widget",
        "minute_meeting.utils.env_check",
        # Backends audio necessari a librosa / soundfile
        "sounddevice",
        "cffi",
        "numpy",
        "scipy.signal",
        "scipy.ndimage",
    ],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "xmlrpc",
        "http.server",
        "pydoc",
        "doctest",
        "difflib",
        "pdb",
        "profile",
        "cProfile",
        "timeit",
        "trace",
        "antigravity",
        "this",
        "turtledemo",
        "lib2to3",
        # Matplotlib è importato transitivamente da alcuni pacchetti ma non serve
        "matplotlib.tests",
        "matplotlib.testing",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# Eseguibile e bundle onedir
# ---------------------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MinuteMeeting",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # GUI app — nessuna finestra console
    # icon="assets/icon.ico",  # decommentare quando si aggiunge un'icona
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MinuteMeeting",
)
